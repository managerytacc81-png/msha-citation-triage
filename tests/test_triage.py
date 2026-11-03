"""Tests for citation triage and POV proxy calculations."""

from datetime import date
from pathlib import Path
import pytest

from msha_triage.fetch import load_mines_mapping, stream_pipe_delimited
from msha_triage.triage import (
    CitationRecord,
    OperatorTriage,
    TriageEngine,
    parse_msha_date,
)


def test_parse_msha_date():
    """Verify various date format strings parse correctly."""
    assert parse_msha_date("10/25/2026") == date(2026, 10, 25)
    assert parse_msha_date("2026-11-03") == date(2026, 11, 3)
    assert parse_msha_date("") is None
    assert parse_msha_date("invalid") is None


def test_citation_record_from_row():
    """Verify construction of CitationRecord with 30-day contest clock math."""
    ref_date = date(2026, 11, 3)
    row = {
        "VIOLATION_NO": "5064768",
        "MINE_ID": "0100011",
        "MINE_NAME": "IMERYS SYLACAUGA OPERATIONS",
        "VIOLATOR_NAME": "Imerys Carbonates USA, Inc.",
        "CONTROLLER_NAME": "Imerys S A",
        "VIOLATION_ISSUE_DT": "08/13/2026",
        "LAST_ACTION_CD": "Proposed",
        "LAST_ACTION_DT": "10/20/2026",
        "PROPOSED_PENALTY": "151",
        "SIG_SUB": "Y",
        "PART_SECTION": "50.20(a)",
        "NEGLIGENCE": "Moderate",
        "LIKELIHOOD": "Reasonably Likely",
    }
    rec = CitationRecord.from_row(row, ref_date)
    assert rec.violation_no == "5064768"
    assert rec.proposed_penalty == 151.0
    assert rec.sig_sub is True
    assert rec.days_since_action == (date(2026, 11, 3) - date(2026, 10, 20)).days  # 14 days
    assert rec.days_remaining_in_clock == 30 - 14  # 16 days


def test_triage_engine_process_stream(
    sample_violations_path: Path, sample_mines_path: Path
):
    """Verify TriageEngine accurately computes contestable batch and POV metrics."""
    ref_date = date(2026, 11, 3)
    mines_map = load_mines_mapping(sample_mines_path)
    engine = TriageEngine(
        reference_date=ref_date,
        contest_window_days=25,
        pov_trailing_days=365,
        pov_threshold=2,  # lowered threshold for small fixture test
    )

    stream = stream_pipe_delimited(sample_violations_path)
    results = engine.process_stream(stream, mines_map)

    assert len(results) > 0

    # Verify at least one operator has tickets and valid metrics
    for op_name, op_triage in results.items():
        assert isinstance(op_triage, OperatorTriage)
        assert op_triage.contestable_count > 0
        assert op_triage.aggregate_exposure > 0.0
        assert op_triage.min_days_remaining <= 30
        assert op_triage.min_days_remaining >= 0


def test_triage_engine_filter_and_rank():
    """Verify filter_and_rank properly sorts descending by exposure."""
    engine = TriageEngine()
    dummy_results = {
        "Small Op": OperatorTriage(
            operator_name="Small Op",
            aggregate_exposure=500.0,
            contestable_count=2,
        ),
        "Big Op": OperatorTriage(
            operator_name="Big Op",
            aggregate_exposure=50000.0,
            contestable_count=10,
        ),
        "Mid Op": OperatorTriage(
            operator_name="Mid Op",
            aggregate_exposure=12000.0,
            contestable_count=5,
        ),
    }

    ranked = engine.filter_and_rank(dummy_results, min_exposure=1000.0)
    assert len(ranked) == 2
    assert ranked[0].operator_name == "Big Op"
    assert ranked[1].operator_name == "Mid Op"
