"""Tests for CLI pipeline invocation."""

from datetime import date
from pathlib import Path

from msha_triage.cli import run_pipeline


def test_run_pipeline_end_to_end(
    tmp_path: Path, sample_violations_path: Path, sample_mines_path: Path
):
    """Verify end-to-end execution of pipeline produces leads.csv and packets."""
    out_dir = tmp_path / "output"
    ref_date = date(2026, 11, 3)

    results, ranked = run_pipeline(
        violations_path=sample_violations_path,
        mines_path=sample_mines_path,
        reference_date=ref_date,
        output_dir=out_dir,
        min_exposure=100.0,  # Lower threshold for fixture test
        top_n_packets=5,
    )

    assert len(results) > 0
    assert len(ranked) > 0

    leads_file = out_dir / "leads.csv"
    assert leads_file.is_file()
    assert leads_file.stat().st_size > 0

    packets_dir = out_dir / "packets"
    assert packets_dir.is_dir()
    packet_files = list(packets_dir.glob("*.md"))
    assert len(packet_files) > 0
