"""Tests for leads CSV writer and ranking."""

import csv
from pathlib import Path

from msha_triage.leads import write_leads_csv
from msha_triage.triage import OperatorTriage


def test_write_leads_csv(tmp_path: Path):
    """Verify write_leads_csv outputs correct schema and data rows."""
    triage_map = {
        "High Roller Coal LLC": OperatorTriage(
            operator_name="High Roller Coal LLC",
            contestable_count=15,
            aggregate_exposure=85000.0,
            largest_ticket=22000.0,
            sig_sub_count=6,
            mines={"0100123", "0100456"},
            states={"WV"},
            pov_proxy_flag=True,
            top_repeat_standards=[("75.202(a)", 5), ("75.400", 3)],
            min_days_remaining=7,
        ),
        "Small Gravel Pit Inc": OperatorTriage(
            operator_name="Small Gravel Pit Inc",
            contestable_count=1,
            aggregate_exposure=150.0,
            largest_ticket=150.0,
            sig_sub_count=0,
            mines={"0200999"},
            states={"OH"},
            pov_proxy_flag=False,
            min_days_remaining=22,
        ),
    }

    out_csv = tmp_path / "leads.csv"
    leads = write_leads_csv(triage_map, out_csv, min_exposure=2000.0)

    assert len(leads) == 1
    assert leads[0]["operator"] == "High Roller Coal LLC"
    assert leads[0]["exposure_dollars"] == 85000.0
    assert leads[0]["pov_flag"] is True

    # Read back CSV directly
    with open(out_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["operator"] == "High Roller Coal LLC"
    assert rows[0]["state"] == "WV"
    assert rows[0]["ticket_count"] == "15"
    assert rows[0]["exposure_dollars"] == "85000.0"
    assert rows[0]["min_days_remaining"] == "7"
