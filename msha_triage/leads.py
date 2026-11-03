"""Leads Generator for MSHA Citation Triage Desk.

Joins contestable citation triage output with Mines.txt metadata to produce
a ranked, enriched CSV of high-exposure mine operators with active 30-day
contest clocks and POV proxy flags.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Union

from msha_triage.triage import OperatorTriage


def write_leads_csv(
    triage_results: Dict[str, OperatorTriage],
    output_path: Union[str, Path],
    min_exposure: float = 2000.0,
    top_n: Optional[int] = None,
) -> List[Dict[str, Union[str, int, float, bool]]]:
    """Write ranked leads to CSV.

    Args:
        triage_results: Dict of operator name to OperatorTriage.
        output_path: Destination path for leads.csv.
        min_exposure: Minimum aggregate proposed penalty to qualify as a lead (default $2,000).
        top_n: Optional limit on number of leads.

    Returns:
        List of serialized lead dictionaries written to file.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Filter and sort
    qualified = [
        t for t in triage_results.values() if t.aggregate_exposure >= min_exposure
    ]
    qualified.sort(key=lambda x: x.aggregate_exposure, reverse=True)

    if top_n is not None:
        qualified = qualified[:top_n]

    fieldnames = [
        "operator",
        "state",
        "ticket_count",
        "exposure_dollars",
        "largest_ticket",
        "sig_sub_count",
        "pov_flag",
        "top_standards",
        "mines",
        "min_days_remaining",
    ]

    leads_rows: List[Dict[str, Union[str, int, float, bool]]] = []

    for t in qualified:
        states_str = ", ".join(sorted(t.states)) if t.states else "US"
        mines_str = ", ".join(sorted(t.mines))
        top_stds_str = "; ".join(f"{s} ({c})" for s, c in t.top_repeat_standards[:3])

        row_data = {
            "operator": t.operator_name,
            "state": states_str,
            "ticket_count": t.contestable_count,
            "exposure_dollars": round(t.aggregate_exposure, 2),
            "largest_ticket": round(t.largest_ticket, 2),
            "sig_sub_count": t.sig_sub_count,
            "pov_flag": t.pov_proxy_flag,
            "top_standards": top_stds_str,
            "mines": mines_str,
            "min_days_remaining": t.min_days_remaining,
        }
        leads_rows.append(row_data)

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads_rows)

    return leads_rows
