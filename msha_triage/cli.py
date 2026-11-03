"""Command-line interface for MSHA Citation Triage Desk."""

import argparse
import sys
from datetime import date
from pathlib import Path

from msha_triage.fetch import (
    DEFAULT_LOCAL_DIR,
    DEFAULT_STAGING_DIR,
    ensure_mines_file,
    ensure_violations_file,
    load_mines_mapping,
    stream_pipe_delimited,
)
from msha_triage.leads import write_leads_csv
from msha_triage.packet import generate_triage_packet
from msha_triage.triage import TriageEngine, parse_msha_date


def run_pipeline(
    violations_path: Path,
    mines_path: Path,
    reference_date: date,
    output_dir: Path,
    min_exposure: float = 2000.0,
    top_n_packets: int = 25,
):
    """Run full triage pipeline from streaming raw datasets."""
    print(f"Loading Mines metadata from: {mines_path}...")
    mines_map = load_mines_mapping(mines_path)
    print(f"Loaded {len(mines_map):,} mines into memory lookup.")

    print(f"Streaming Violations from: {violations_path}...")
    violations_stream = stream_pipe_delimited(violations_path)

    engine = TriageEngine(
        reference_date=reference_date,
        contest_window_days=25,
        pov_trailing_days=365,
        pov_threshold=5,
    )

    print("Executing streaming triage and POV proxy calculations...")
    triage_results = engine.process_stream(violations_stream, mines_map)

    # Rank and summarize
    ranked = engine.filter_and_rank(triage_results, min_exposure=min_exposure)
    total_operators_ge_2k = len(ranked)
    total_exposure = sum(t.aggregate_exposure for t in ranked)
    total_tickets = sum(t.contestable_count for t in ranked)

    print("\n" + "=" * 70)
    print("MSHA CITATION TRIAGE DESK — RUN SUMMARY")
    print("=" * 70)
    print(f"Reference Date: {reference_date.isoformat()}")
    print(f"Total Qualified Operators (>= ${min_exposure:,.2f}): {total_operators_ge_2k}")
    print(f"Total Contestable Penalties at Risk: ${total_exposure:,.2f}")
    print(f"Total Contestable Tickets: {total_tickets:,}")
    print("=" * 70)

    # Write leads.csv
    leads_csv_path = output_dir / "leads.csv"
    leads = write_leads_csv(triage_results, leads_csv_path, min_exposure=min_exposure)
    print(f"\n✓ Wrote {len(leads)} qualified leads to: {leads_csv_path}")

    # Generate packets for top N
    packets_dir = output_dir / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    top_ops = ranked[:top_n_packets]

    print(f"\nGenerating triage packets for top {len(top_ops)} operators...")
    for idx, op_triage in enumerate(top_ops, 1):
        slug = op_triage.operator_name.lower().replace(" ", "_").replace(",", "").replace(".", "")
        packet_path = packets_dir / f"{idx:02d}_{slug}_triage_packet.md"
        generate_triage_packet(op_triage, packet_path)
        print(f"  [{idx:02d}] {op_triage.operator_name}: ${op_triage.aggregate_exposure:,.2f} ({op_triage.contestable_count} tickets) -> {packet_path.name}")

    print(f"\n✓ Completed generating {len(top_ops)} packets in: {packets_dir}")
    return triage_results, ranked


def main():
    parser = argparse.ArgumentParser(
        description="MSHA Citation Triage Desk - Contest-Clock & POV Watch Engine"
    )
    subparsers = parser.add_subparsers(dest="command")

    # all
    p_all = subparsers.add_parser("all", help="Execute complete end-to-end triage pipeline")
    p_all.add_argument(
        "--violations",
        type=Path,
        help="Path to Violations.txt or Violations.zip",
    )
    p_all.add_argument(
        "--mines",
        type=Path,
        help="Path to Mines.txt or Mines.zip",
    )
    p_all.add_argument(
        "--ref-date",
        type=str,
        default="2026-11-03",
        help="Reference evaluation date (YYYY-MM-DD), defaults to 2026-11-03",
    )
    p_all.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Output directory for leads.csv and packets",
    )
    p_all.add_argument(
        "--min-exposure",
        type=float,
        default=2000.0,
        help="Minimum contestable penalty exposure threshold (default $2,000)",
    )
    p_all.add_argument(
        "--top-packets",
        type=int,
        default=25,
        help="Number of top operator packets to generate (default 25)",
    )

    args = parser.parse_args()

    if args.command in (None, "all"):
        ref_dt = parse_msha_date(getattr(args, "ref_date", "2026-11-03")) or date(2026, 11, 3)
        viol_p = getattr(args, "violations", None) or ensure_violations_file()
        mine_p = getattr(args, "mines", None) or ensure_mines_file()
        out_d = getattr(args, "output_dir", None) or Path(__file__).resolve().parent.parent
        min_exp = getattr(args, "min_exposure", 2000.0)
        top_p = getattr(args, "top_packets", 25)

        run_pipeline(
            violations_path=viol_p,
            mines_path=mine_p,
            reference_date=ref_dt,
            output_dir=out_d,
            min_exposure=min_exp,
            top_n_packets=top_p,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
