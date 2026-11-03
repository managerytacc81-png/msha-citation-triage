"""Tests for triage packet generation and informal conference letter templates."""

from datetime import date
from pathlib import Path

from msha_triage.packet import (
    generate_informal_conference_letter,
    generate_triage_packet,
    match_standard_defense,
)
from msha_triage.triage import CitationRecord, OperatorTriage


def test_match_standard_defense():
    """Verify defense strategy matching across known CFR families."""
    roof_def = match_standard_defense("75.202(a)")
    assert "Roof Support" in roof_def["title"]

    vent_def = match_standard_defense("75.370(a)(1)")
    assert "Ventilation" in vent_def["title"]

    dust_def = match_standard_defense("75.400")
    assert "Combustible Materials" in dust_def["title"]

    elec_def = match_standard_defense("56.12004")
    assert "Electrical" in elec_def["title"]

    guard_def = match_standard_defense("56.14107(a)")
    assert "Machinery Guarding" in guard_def["title"]


def test_generate_informal_conference_letter():
    """Verify informal conference letter includes pre-filled citations and statutory citations."""
    ticket = CitationRecord(
        violation_no="9998881",
        mine_id="0100011",
        mine_name="TEST MINE",
        operator_name="Acme Coal Co",
        controller_name="Acme Holdings",
        issue_date=date(2026, 10, 1),
        sig_sub=True,
        part_section="75.202(a)",
        section_of_act="104(a)",
        likelihood="Reasonably Likely",
        inj_illness="Lost Workdays",
        no_affected="1",
        negligence="Moderate",
        proposed_penalty=12500.0,
        bill_print_date=date(2026, 10, 15),
        last_action_cd="Proposed",
        last_action_date=date(2026, 10, 15),
        days_since_action=19,
        days_remaining_in_clock=11,
    )

    triage = OperatorTriage(
        operator_name="Acme Coal Co",
        contestable_tickets=[ticket],
        contestable_count=1,
        aggregate_exposure=12500.0,
        largest_ticket=12500.0,
        sig_sub_count=1,
        mines={"0100011"},
        states={"AL"},
        pov_proxy_flag=True,
        min_days_remaining=11,
    )

    letter = generate_informal_conference_letter(triage)
    assert "Acme Coal Co" in letter
    assert "9998881" in letter
    assert "$12,500.00" in letter
    assert "30 CFR § 100.6" in letter
    assert "30 U.S.C. § 815(a)" in letter
    assert "Section 110(c)" in letter
    assert "Mathies" in letter


def test_generate_triage_packet(tmp_path: Path):
    """Verify complete markdown packet creation and structure."""
    ticket = CitationRecord(
        violation_no="1234567",
        mine_id="0100022",
        mine_name="ALPHA QUARRY",
        operator_name="Alpha Aggregates LLC",
        controller_name="Alpha Corp",
        issue_date=date(2026, 10, 10),
        sig_sub=False,
        part_section="56.14107(a)",
        section_of_act="104(a)",
        likelihood="Unlikely",
        inj_illness="No Lost Workdays",
        no_affected="0",
        negligence="Low",
        proposed_penalty=350.0,
        bill_print_date=date(2026, 10, 20),
        last_action_cd="Proposed",
        last_action_date=date(2026, 10, 20),
        days_since_action=14,
        days_remaining_in_clock=16,
    )

    triage = OperatorTriage(
        operator_name="Alpha Aggregates LLC",
        contestable_tickets=[ticket],
        contestable_count=1,
        aggregate_exposure=350.0,
        largest_ticket=350.0,
        sig_sub_count=0,
        mines={"0100022"},
        states={"TX"},
        pov_proxy_flag=False,
        top_repeat_standards=[("56.14107(a)", 1)],
        min_days_remaining=16,
    )

    out_file = tmp_path / "alpha_packet.md"
    content = generate_triage_packet(triage, out_file)

    assert out_file.is_file()
    assert "Alpha Aggregates LLC" in content
    assert "| `1234567` | `0100022` |" in content
    assert "30-Day Statutory Contest Clock" in content
    assert "Pattern of Violations (POV)" in content
    assert "FORMAL REQUEST FOR INFORMAL CONFERENCE" in content
