"""MSHA Citation Triage Engine.

Computes contestable-NOW window tickets, aggregate penalty exposure,
S&S (significant-and-substantial) counts, POV-proximity proxy risk under
30 CFR Part 104, and top repeat safety standards per operator.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional, Set, Tuple, Union

from msha_triage.fetch import load_mines_mapping, stream_pipe_delimited

# Standard statutory contest period under 30 U.S.C. § 815(a) / 30 CFR Part 100
STATUTORY_CONTEST_DAYS = 30
DEFAULT_CONTESTABLE_WINDOW_DAYS = 25
DEFAULT_POV_TRAILING_DAYS = 365
DEFAULT_POV_SS_THRESHOLD = 5


def parse_msha_date(date_str: str) -> Optional[date]:
    """Parse MSHA date formats (MM/DD/YYYY or YYYY-MM-DD)."""
    if not date_str:
        return None
    cleaned = date_str.strip()
    if not cleaned:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class CitationRecord:
    """Represents a single parsed MSHA citation record."""

    violation_no: str
    mine_id: str
    mine_name: str
    operator_name: str
    controller_name: str
    issue_date: Optional[date]
    sig_sub: bool
    part_section: str
    section_of_act: str
    likelihood: str
    inj_illness: str
    no_affected: str
    negligence: str
    proposed_penalty: float
    bill_print_date: Optional[date]
    last_action_cd: str
    last_action_date: Optional[date]
    days_since_action: Optional[int] = None
    days_remaining_in_clock: Optional[int] = None

    @classmethod
    def from_row(
        cls,
        row: Dict[str, str],
        reference_date: Optional[date] = None,
    ) -> "CitationRecord":
        """Construct CitationRecord from raw row dict."""
        viol_no = row.get("VIOLATION_NO", "").strip()
        mine_id = row.get("MINE_ID", "").strip()
        mine_name = row.get("MINE_NAME", "").strip()
        op_name = row.get("VIOLATOR_NAME", "").strip()
        ctrl_name = row.get("CONTROLLER_NAME", "").strip()

        issue_dt = parse_msha_date(row.get("VIOLATION_ISSUE_DT", ""))
        bill_dt = parse_msha_date(row.get("BILL_PRINT_DT", ""))
        last_dt = parse_msha_date(row.get("LAST_ACTION_DT", ""))
        if not last_dt and bill_dt:
            last_dt = bill_dt

        sig_sub = row.get("SIG_SUB", "").strip().upper() == "Y"
        part_sec = row.get("PART_SECTION", "").strip()
        sec_act = row.get("SECTION_OF_ACT", "").strip()
        likelihood = row.get("LIKELIHOOD", "").strip()
        inj_ill = row.get("INJ_ILLNESS", "").strip()
        no_aff = row.get("NO_AFFECTED", "").strip()
        negligence = row.get("NEGLIGENCE", "").strip()
        action_cd = row.get("LAST_ACTION_CD", "").strip()

        penalty_str = row.get("PROPOSED_PENALTY", "").strip().replace(",", "")
        try:
            penalty = float(penalty_str) if penalty_str else 0.0
        except ValueError:
            penalty = 0.0

        days_since = None
        days_remaining = None
        if reference_date and last_dt:
            days_since = (reference_date - last_dt).days
            days_remaining = max(0, STATUTORY_CONTEST_DAYS - days_since)

        return cls(
            violation_no=viol_no,
            mine_id=mine_id,
            mine_name=mine_name,
            operator_name=op_name,
            controller_name=ctrl_name,
            issue_date=issue_dt,
            sig_sub=sig_sub,
            part_section=part_sec,
            section_of_act=sec_act,
            likelihood=likelihood,
            inj_illness=inj_ill,
            no_affected=no_aff,
            negligence=negligence,
            proposed_penalty=penalty,
            bill_print_date=bill_dt,
            last_action_cd=action_cd,
            last_action_date=last_dt,
            days_since_action=days_since,
            days_remaining_in_clock=days_remaining,
        )


@dataclass
class POVTriggerDetail:
    """Detailed record of a Pattern-of-Violations proxy trigger."""

    mine_id: str
    part_section: str
    trailing_ss_count: int
    appears_in_contestable_batch: bool


@dataclass
class OperatorTriage:
    """Triage analysis summary for a single mine operator."""

    operator_name: str
    contestable_tickets: List[CitationRecord] = field(default_factory=list)
    contestable_count: int = 0
    aggregate_exposure: float = 0.0
    largest_ticket: float = 0.0
    sig_sub_count: int = 0
    mines: Set[str] = field(default_factory=set)
    mine_names: Set[str] = field(default_factory=set)
    states: Set[str] = field(default_factory=set)
    pov_proxy_flag: bool = False
    pov_triggers: List[POVTriggerDetail] = field(default_factory=list)
    top_repeat_standards: List[Tuple[str, int]] = field(default_factory=list)
    min_days_remaining: int = STATUTORY_CONTEST_DAYS


class TriageEngine:
    """Core triage computational engine."""

    def __init__(
        self,
        reference_date: Optional[date] = None,
        contest_window_days: int = DEFAULT_CONTESTABLE_WINDOW_DAYS,
        pov_trailing_days: int = DEFAULT_POV_TRAILING_DAYS,
        pov_threshold: int = DEFAULT_POV_SS_THRESHOLD,
    ):
        """Initialize the triage engine.

        Args:
            reference_date: Date to evaluate against (defaults to today, or 2026-11-03).
            contest_window_days: Maximum days since last action for contestable-NOW (default 25).
            pov_trailing_days: Trailing window in days for S&S POV calculation (default 365).
            pov_threshold: S&S count threshold on same part_section to trigger POV proxy (default 5).
        """
        self.reference_date = reference_date or date.today()
        self.contest_window_days = contest_window_days
        self.pov_trailing_days = pov_trailing_days
        self.pov_threshold = pov_threshold

    def is_contestable_now(self, record: CitationRecord) -> bool:
        """Evaluate if citation is within the contestable-NOW window.

        Conditions:
        - LAST_ACTION_CD == 'Proposed'
        - Action date exists and 0 <= (reference_date - action_date) <= contest_window_days
        """
        if record.last_action_cd.lower() != "proposed":
            return False
        if record.days_since_action is None:
            return False
        return 0 <= record.days_since_action <= self.contest_window_days

    def process_stream(
        self,
        violations_stream: Iterable[Dict[str, str]],
        mines_mapping: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Dict[str, OperatorTriage]:
        """Process streaming violations rows and compute per-operator triage metrics.

        Single-pass algorithm maintaining streaming aggregations.
        """
        mines_map = mines_mapping or {}

        # Tracking structures
        # 1. Trailing S&S count per (mine_id, part_section)
        trailing_ss_counter: Dict[Tuple[str, str], int] = defaultdict(int)

        # 2. Contestable records grouped by operator
        contestable_by_op: Dict[str, List[CitationRecord]] = defaultdict(list)
        standards_by_op: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for row in violations_stream:
            # Check S&S trailing POV accrual
            sig_sub = row.get("SIG_SUB", "").strip().upper() == "Y"
            mid = row.get("MINE_ID", "").strip()
            sec = row.get("PART_SECTION", "").strip()

            if sig_sub and mid and sec:
                issue_dt = parse_msha_date(row.get("VIOLATION_ISSUE_DT", ""))
                if issue_dt:
                    days_ago = (self.reference_date - issue_dt).days
                    if 0 <= days_ago <= self.pov_trailing_days:
                        trailing_ss_counter[(mid, sec)] += 1

            # Check contestable-NOW
            action_cd = row.get("LAST_ACTION_CD", "").strip().lower()
            if action_cd == "proposed":
                record = CitationRecord.from_row(row, self.reference_date)
                if self.is_contestable_now(record):
                    op = record.operator_name or "UNKNOWN OPERATOR"
                    contestable_by_op[op].append(record)
                    if record.part_section:
                        standards_by_op[op][record.part_section] += 1

        # Build final OperatorTriage objects
        results: Dict[str, OperatorTriage] = {}

        for op, tickets in contestable_by_op.items():
            exposure = sum(t.proposed_penalty for t in tickets)
            largest = max((t.proposed_penalty for t in tickets), default=0.0)
            ss_count = sum(1 for t in tickets if t.sig_sub)
            mines = {t.mine_id for t in tickets if t.mine_id}
            mine_names = {t.mine_name for t in tickets if t.mine_name}

            states: Set[str] = set()
            for m in mines:
                if m in mines_map:
                    st = mines_map[m].get("state", "").strip()
                    if st:
                        states.add(st)
                    m_name = mines_map[m].get("mine_name", "").strip()
                    if m_name:
                        mine_names.add(m_name)

            # Check POV-proximity proxy:
            # Any mine associated with this operator having >= pov_threshold S&S
            # on the same PART_SECTION in trailing 12 months.
            pov_triggers: List[POVTriggerDetail] = []
            op_standards = standards_by_op[op]

            # Check all mines associated with this operator's contestable tickets
            for m in mines:
                # Check standards cited across this mine
                for (t_mid, t_sec), count in trailing_ss_counter.items():
                    if t_mid == m and count >= self.pov_threshold:
                        appears_in_batch = t_sec in op_standards
                        pov_triggers.append(
                            POVTriggerDetail(
                                mine_id=m,
                                part_section=t_sec,
                                trailing_ss_count=count,
                                appears_in_contestable_batch=appears_in_batch,
                            )
                        )

            # Sort top repeat standards descending
            sorted_stds = sorted(
                op_standards.items(), key=lambda x: x[1], reverse=True
            )

            # Calculate minimum days remaining
            min_days = min(
                (
                    t.days_remaining_in_clock
                    for t in tickets
                    if t.days_remaining_in_clock is not None
                ),
                default=STATUTORY_CONTEST_DAYS,
            )

            results[op] = OperatorTriage(
                operator_name=op,
                contestable_tickets=tickets,
                contestable_count=len(tickets),
                aggregate_exposure=exposure,
                largest_ticket=largest,
                sig_sub_count=ss_count,
                mines=mines,
                mine_names=mine_names,
                states=states,
                pov_proxy_flag=len(pov_triggers) > 0,
                pov_triggers=pov_triggers,
                top_repeat_standards=sorted_stds,
                min_days_remaining=min_days,
            )

        return results

    def filter_and_rank(
        self,
        triage_map: Dict[str, OperatorTriage],
        min_exposure: float = 0.0,
        top_n: Optional[int] = None,
    ) -> List[OperatorTriage]:
        """Filter operators by minimum exposure and sort by exposure descending."""
        filtered = [
            t for t in triage_map.values() if t.aggregate_exposure >= min_exposure
        ]
        filtered.sort(key=lambda x: x.aggregate_exposure, reverse=True)
        if top_n is not None:
            return filtered[:top_n]
        return filtered
