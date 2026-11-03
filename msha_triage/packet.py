"""Triage Packet Generator.

Generates comprehensive per-operator markdown compliance dossiers:
- Citation inventory table with 30-day contest clock countdown
- Pattern of Violations (POV) proxy assessment under 30 CFR Part 104
- Mitigation argument checklist tailored to standard families
- Pre-filled Informal Conference Request Letter Template (30 CFR 100.6 + 110(c))
"""

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from msha_triage.triage import CitationRecord, OperatorTriage

# Standard Family Mitigation Knowledge Base
STANDARD_FAMILY_DEFENSES: Dict[str, Dict[str, str]] = {
    "roof_control": {
        "title": "30 CFR Part 75 Subpart C — Underground Roof Support & Control Plans",
        "prefixes": ("75.2", "75.202", "75.220", "56.3", "57.3"),
        "key_standards": "75.202(a), 75.220(a)(1), 56.3200, 57.3200",
        "negligence_arguments": (
            "- Operator conducted and documented mandatory pre-shift examinations under 75.360 prior to shift entry.\n"
            "- Visual examination of ribs/roof showed no adverse geological cracking or sudden faulting at time of pre-shift.\n"
            "- Adverse condition resulted from sudden geological stress/cleat formation rather than lack of reasonable care.\n"
            "- Certified roof bolters acted in accordance with the approved Roof Control Plan sequence without deviation."
        ),
        "gravity_arguments": (
            "- Miners were working under permanently supported roof or beneath certified automated temporary roof support (ATRS).\n"
            "- No individual was exposed under unsupported brow; physical barriers or warning danger tags were posted.\n"
            "- Challenge Significant & Substantial (S&S) designation under the Mathies Coal Co. 4-prong test: no reasonable likelihood that injury would occur given operational controls."
        ),
        "statutory_shielding": (
            "- Document supervisory logs to protect foremen from personal civil liability assessments under Section 110(c) of the Mine Act (30 U.S.C. § 820(c))."
        ),
    },
    "ventilation": {
        "title": "30 CFR Part 75 Subpart D — Underground Mine Ventilation & Methane Control",
        "prefixes": ("75.3", "75.370", "75.380", "57.8"),
        "key_standards": "75.370(a)(1), 75.380(d)(1), 75.360, 57.8518",
        "negligence_arguments": (
            "- Continuous electronic atmospheric monitoring system (AMS) showed no methane excursions (< 0.25% CH4).\n"
            "- Ventilation curtain displacement was transient caused by shuttle car passage during active production cycle.\n"
            "- Certified section foreman had already scheduled immediate curtain adjustment before inspector arrival."
        ),
        "gravity_arguments": (
            "- Measured air velocity exceeded minimum CFM required by approved Ventilation Plan at last open crosscut.\n"
            "- Low likelihood of explosive atmosphere or oxygen deficiency in the designated return/intake split.\n"
            "- Rebuttal of S&S designation: Mathies Step 3 failure—no reasonable likelihood of an ignition or fire."
        ),
        "statutory_shielding": (
            "- Verify calibrated anemometer calibration certificates to shield supervisory staff from 110(c) willful/knowing negligence referrals."
        ),
    },
    "combustible_materials": {
        "title": "30 CFR Part 75 Subpart E — Combustible Materials & Rock Dusting",
        "prefixes": ("75.4", "75.400", "75.403"),
        "key_standards": "75.400, 75.403",
        "negligence_arguments": (
            "- Belt conveyor clean-up was scheduled and actively underway as part of the section's regular operational cycle.\n"
            "- Spillage was localized near transfer point rather than extensive across multiple breaks or crosscuts.\n"
            "- Mechanical component (roller/idler) was turning freely with bearing temperatures operating within normal limits."
        ),
        "gravity_arguments": (
            "- High inherent moisture content of wet coal spillage prevented rapid propagation of flame.\n"
            "- Rock dust application on rib, roof, and floor exceeded statutory 80% total noncombustible content (TNC).\n"
            "- Request MSHA laboratory split-sample analysis rather than relying on inspector visual estimation."
        ),
        "statutory_shielding": (
            "- Confirm belt examiner examination records and dust survey compliance to demonstrate institutional diligence."
        ),
    },
    "electrical": {
        "title": "30 CFR Part 75/77 Subpart F & Part 56/57 Subpart K — Electrical Safety & Permissibility",
        "prefixes": ("75.5", "75.503", "75.512", "75.517", "77.5", "56.12", "57.12"),
        "key_standards": "75.503, 75.512, 75.517, 56.12004, 56.12008, 56.12032",
        "negligence_arguments": (
            "- Lock-out, tag-out and power de-energization procedures were strictly enforced during maintenance.\n"
            "- Cable scuff/insulation wear was superficial with outer jacket intact and zero exposed live conductors.\n"
            "- Weekly electrical examinations under 75.512 or monthly tests were current and documented in official log."
        ),
        "gravity_arguments": (
            "- Ground fault and circuit breaker interrupters were tested and calibrated, ensuring instantaneous trip in event of fault.\n"
            "- Atmosphere was non-gassy and free of combustible accumulations at the machine location.\n"
            "- Challenge S&S: zero electrical shock or fire hazard given dual-layer insulated cabling."
        ),
        "statutory_shielding": (
            "- Submit certified electrician examination signatures to demonstrate full operator oversight under 30 CFR 75.512."
        ),
    },
    "machinery_guarding": {
        "title": "30 CFR Part 56/57 Subpart M & Part 77 Subpart E — Machinery Guarding & Equipment",
        "prefixes": ("56.14", "57.14", "77.4", "77.16", "56.14107", "56.14132"),
        "key_standards": "56.14107(a), 56.14130, 56.14132(a), 77.400(a), 77.1606",
        "negligence_arguments": (
            "- Moving parts were guarded by location, elevation (>7 ft), or structural framework preventing human contact.\n"
            "- Equipment pre-operational checklist under 56.14100 was executed at start of shift; defect developed during shift.\n"
            "- Safety guard was briefly removed for emergency maintenance with equipment locked and tagged out."
        ),
        "gravity_arguments": (
            "- Normal work station or travelway does not require miner presence in proximity to the guarded component.\n"
            "- E-stop cords, interlocks, or presence-sensing devices were fully operational.\n"
            "- Eliminate S&S: Contact with rotating shaft or pinch point was highly unlikely during regular operating duties."
        ),
        "statutory_shielding": (
            "- Pre-shift mobile equipment check sheets substantiate low negligence and refute intentional disregard."
        ),
    },
    "housekeeping_general": {
        "title": "30 CFR Part 56/57 Subpart S — Housekeeping, Travelways & General Safety",
        "prefixes": ("56.20", "57.20", "56.11", "57.11", "77.205"),
        "key_standards": "56.20003(a), 56.11001, 77.205(a)",
        "negligence_arguments": (
            "- Material accumulation was transient following an active process maintenance cycle or shift changeover.\n"
            "- Designated walkway, handrails, and lighting provided uninterrupted safe passage around the area.\n"
            "- Cleanup crew was dispatched as part of regular end-of-shift housekeeping protocol."
        ),
        "gravity_arguments": (
            "- Low slip/trip potential given non-skid walking surfaces and low pedestrian traffic volume.\n"
            "- Miners in the area were wearing mandated steel-toe metatarsal safety footwear.\n"
            "- S&S designation unjustified under Mathies Step 4: No reasonable likelihood of a serious disabling injury."
        ),
        "statutory_shielding": (
            "- Establish compliance with workplace examination rules under 56.18002 to extinguish individual supervisor scrutiny."
        ),
    },
    "training_records": {
        "title": "30 CFR Part 46 / 48 — Mandatory Miner Training & Task Certifications",
        "prefixes": ("46.", "48.", "46.7", "48.27"),
        "key_standards": "46.7(a), 48.27(a)(1), 46.8, 48.28",
        "negligence_arguments": (
            "- Miner received full hands-on task instruction from experienced supervisor prior to machine operation.\n"
            "- Omission was purely clerical regarding timely Form 5000-23 entry rather than substantive failure to train.\n"
            "- Miner possessed extensive prior mining experience on identical equipment classes."
        ),
        "gravity_arguments": (
            "- Miner operated the machinery safely and competently without incident or near-miss.\n"
            "- Clerical documentation deficiency does not constitute a hazard reasonably likely to cause injury."
        ),
        "statutory_shielding": (
            "- Submit signed training rosters and internal safety briefs to clear supervisory personnel under 110(c)."
        ),
    },
}


def match_standard_defense(part_section: str) -> Dict[str, str]:
    """Find the best matching defense category for a CFR standard."""
    cleaned = part_section.strip()
    for cat_key, cat_data in STANDARD_FAMILY_DEFENSES.items():
        for prefix in cat_data["prefixes"]:
            if cleaned.startswith(prefix):
                return cat_data

    # Default fallback defense
    return {
        "title": f"30 CFR Standard {cleaned} — General Safety Compliance Defense",
        "key_standards": cleaned,
        "negligence_arguments": (
            f"- Operator established and strictly enforced safety standard operating procedures covering {cleaned}.\n"
            "- Regular pre-shift examinations did not disclose the cited condition prior to the inspector's arrival.\n"
            "- The cited condition was an isolated aberration rather than systematic supervisory neglect."
        ),
        "gravity_arguments": (
            "- Redundant engineering safeguards and protective PPE minimized risk to zero or negligible levels.\n"
            "- Challenge S&S designation under the Mathies Coal Co. 4-prong test: no reasonable likelihood of serious injury."
        ),
        "statutory_shielding": (
            "- Compile shift logs and supervisory records to insulate mine agents under Section 110(c) of the Mine Act."
        ),
    }


def generate_informal_conference_letter(
    triage: OperatorTriage,
    msha_district_name: str = "MSHA District Manager",
    msha_district_address: str = "[MSHA District Office Address on File]",
) -> str:
    """Generate a pre-filled, submission-ready Informal Conference Request Letter.

    Pre-fills operator name, mine IDs, citations, proposed penalties, and
    formal reservations under 30 CFR 100.6, 30 CFR Part 104, and 30 U.S.C. 815(a).
    """
    citation_lines = []
    total_penalty = 0.0
    for t in triage.contestable_tickets:
        citation_lines.append(
            f"  - Citation/Order No.: {t.violation_no} | Mine ID: {t.mine_id} ({t.mine_name}) | "
            f"30 CFR § {t.part_section} | Negligence: {t.negligence} | S&S: {'YES' if t.sig_sub else 'NO'} | "
            f"Proposed Penalty: ${t.proposed_penalty:,.2f}"
        )
        total_penalty += t.proposed_penalty

    citations_block = "\n".join(citation_lines)
    primary_mine = next(iter(triage.mines)) if triage.mines else "VARIOUS"
    primary_state = next(iter(triage.states)) if triage.states else "US"

    letter_text = f"""# FORMAL REQUEST FOR INFORMAL CONFERENCE PURSUANT TO 30 CFR § 100.6
**AND PRESERVATION OF CONTEST RIGHTS UNDER SECTION 105(a) OF THE MINE ACT (30 U.S.C. § 815(a))**

**DATE:** {date.today().strftime('%B %d, %Y')}

**TO:**
District Manager
Mine Safety and Health Administration (MSHA)
District Enforcement Division
{msha_district_address}

**FROM (MINE OPERATOR):**
**{triage.operator_name}**
Primary Mine ID(s): {', '.join(sorted(triage.mines))}
Operating Jurisdiction(s): {', '.join(sorted(triage.states)) if triage.states else 'General'}

**RE:** Request for Informal Conference under 30 CFR § 100.6
Proposed Penalty Assessment Batch | Total Exposure Under Review: **${total_penalty:,.2f}** ({triage.contestable_count} Citations)

Dear District Manager:

Pursuant to Title 30, Code of Federal Regulations, Section 100.6 (30 CFR § 100.6), **{triage.operator_name}** ("Operator") hereby timely requests an **Informal Assessment Conference** to review the proposed civil penalties, gravity assessments, negligence classifications, and Significant and Substantial ("S&S") findings for the citations and orders listed below:

### SCHEDULE OF CITATIONS UNDER REVIEW:
{citations_block}

### STATEMENT OF ISSUES & BASIS FOR REVIEW:
Operator respectfully requests conference review and penalty modification based on the following measured statutory grounds:

1. **Reclassification of Negligence Levels (30 CFR § 100.3(d)):**
   The issuing inspector evaluated negligence as Moderate or High on citations where the Operator exhibited reasonable care, conducted diligent pre-shift examinations, and maintained documented preventative maintenance protocols. Operator will present shift examination logs and witness statements establishing that the cited conditions developed suddenly or were obscured by circumstances beyond reasonable foresight.

2. **Elimination of Significant and Substantial ("S&S") Designations (*Mathies* Standard):**
   Several citations carry the "S&S" designation despite failing the mandatory four-prong legal test articulated by the Federal Mine Safety and Health Review Commission in *Mathies Coal Co.*, 6 FMSC 1 (1984), and *Newtown Energy, Inc.*, 38 FMSC 2033 (2016). Specifically, given redundant engineering controls, restricted miner access, and required personal protective equipment, there was no reasonable likelihood that the cited condition would result in an injury of a reasonably serious nature.

3. **Pattern of Violations (POV) Prevention (30 CFR Part 104):**
   Retention of unsupported S&S designations improperly increases the Operator's S&S violation rate and frequency metrics evaluated under MSHA's Pattern of Violations screening criteria (30 CFR Part 104). Eliminating improper S&S designations during this informal conference is essential to ensure that MSHA's public POV scoring reflects actual operating safety.

4. **Protection Against Individual Liability Referrals (30 U.S.C. § 820(c) / Section 110(c)):**
   Operator will demonstrate institutional compliance programs and supervisory oversight, affirmatively confirming that corporate agents and section foremen did not knowingly, willfully, or recklessly authorize or permit the cited conditions.

5. **Good Faith Abatement (30 CFR § 100.3(f)):**
   In all matters, Operator immediately abated the condition in good faith within the statutory time frame specified by the inspector under Section 104(a).

### RESERVATION OF FORMAL CONTEST RIGHTS (30 U.S.C. § 815(a)):
Please be advised that this request for an informal conference does not toll the 30-day statutory deadline to contest proposed assessments under Section 105(a) of the Federal Mine Safety and Health Act of 1977 unless an amended assessment is issued. **{triage.operator_name}** explicitly reserves all rights to formally contest the citations, orders, and proposed penalties before the Federal Mine Safety and Health Review Commission (FMSHRC) if mutual agreement is not achieved at the conference.

Please contact the undersigned safety director at your earliest convenience to schedule the informal conference date.

Respectfully submitted,

____________________________________________________
**Safety Director / Authorized Compliance Representative**
**{triage.operator_name}**
Direct Contact: [Corporate Safety Department Phone/Email]
Filing Record Copy Kept at Mine Office
"""
    return letter_text


def generate_triage_packet(
    triage: OperatorTriage, output_path: Optional[Union[str, Path]] = None
) -> str:
    """Generate a complete per-operator triage dossier markdown."""
    # Summary stats
    total_exposure = triage.aggregate_exposure
    ticket_count = triage.contestable_count
    ss_count = triage.sig_sub_count
    pov_status = "⚠️ CRITICAL — POV PROXIMITY RISK IDENTIFIED" if triage.pov_proxy_flag else "✅ STANDARD MONITORING (Below POV Threshold)"

    # Identify standards appearing in tickets
    ticket_standards = {t.part_section for t in triage.contestable_tickets if t.part_section}

    # Format Citation Inventory Table
    table_rows = []
    for t in sorted(
        triage.contestable_tickets, key=lambda x: x.proposed_penalty, reverse=True
    ):
        ss_str = "**YES**" if t.sig_sub else "No"
        days_left_str = (
            f"**{t.days_remaining_in_clock} days**"
            if t.days_remaining_in_clock is not None
            else "N/A"
        )
        issue_dt_str = t.issue_date.strftime("%m/%d/%Y") if t.issue_date else "N/A"
        action_dt_str = (
            t.last_action_date.strftime("%m/%d/%Y") if t.last_action_date else "N/A"
        )

        table_rows.append(
            f"| `{t.violation_no}` | `{t.mine_id}` | 30 CFR § {t.part_section} | {t.negligence} | "
            f"{t.likelihood} | {ss_str} | **${t.proposed_penalty:,.2f}** | {issue_dt_str} | {action_dt_str} | {days_left_str} |"
        )

    citation_table_md = (
        "| Violation No | Mine ID | CFR Standard | Negligence | Likelihood | S&S? | Proposed Penalty | Issue Date | Proposed Date | Contest Clock Left |\n"
        "| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |\n"
        + "\n".join(table_rows)
    )

    # Top repeat standards list
    top_stds_md = []
    for std, count in triage.top_repeat_standards[:5]:
        top_stds_md.append(f"- **30 CFR § {std}**: {count} citation(s) in active batch")
    top_stds_block = "\n".join(top_stds_md) if top_stds_md else "- None"

    # POV Triggers detail
    pov_details_md = []
    if triage.pov_triggers:
        for trig in triage.pov_triggers:
            batch_note = "*(Present in current contestable batch)*" if trig.appears_in_contestable_batch else "*(Trailing risk at mine)*"
            pov_details_md.append(
                f"- **Mine `{trig.mine_id}` | 30 CFR § {trig.part_section}**: **{trig.trailing_ss_count} S&S violations** in trailing 12 months {batch_note}"
            )
        pov_block = "\n".join(pov_details_md)
    else:
        pov_block = "- Zero mine-standard pairs exceed the >=5 S&S trailing 12-month proxy threshold."

    # Tailored Mitigation Defense Checklists
    defense_sections = []
    used_titles = set()
    for std in sorted(ticket_standards):
        def_data = match_standard_defense(std)
        if def_data["title"] in used_titles:
            continue
        used_titles.add(def_data["title"])

        defense_sections.append(
            f"### Standard Family: {def_data['title']}\n"
            f"**CFR Standards Covered:** `{def_data['key_standards']}`\n\n"
            f"#### 1. Negligence Reduction Strategies (Targeting Low / None):\n"
            f"{def_data['negligence_arguments']}\n\n"
            f"#### 2. Gravity & S&S Elimination Checklist (Mathies 4-Prong Challenge):\n"
            f"{def_data['gravity_arguments']}\n\n"
            f"#### 3. Section 110(c) Supervisory Liability Shielding:\n"
            f"{def_data['statutory_shielding']}\n"
        )

    defense_block = "\n---\n".join(defense_sections)

    # Informal Conference Request Letter
    conference_letter = generate_informal_conference_letter(triage)

    # Compile full packet
    packet_content = f"""# MSHA CITATION TRIAGE & CONTEST DOSSIER
**OPERATOR:** {triage.operator_name}
**DOCUMENT ID:** MSHA-TRIAGE-{triage.operator_name.replace(' ', '-').upper()}-{date.today().strftime('%Y%m%d')}
**COMPLIANCE PROTOCOL:** 30 CFR § 100.6 (Informal Review) & 30 CFR Part 104 (POV Watch)

---

## 1. Executive Summary & Exposure Scorecard
- **Operator Name:** **{triage.operator_name}**
- **Operating Jurisdiction(s):** {', '.join(sorted(triage.states)) if triage.states else 'General'}
- **Active Mines with Citations:** {', '.join(sorted(triage.mines))}
- **Total Contestable Penalties (Proposed Batch):** **${total_exposure:,.2f}**
- **Contestable Citation Count:** **{ticket_count} ticket(s)**
- **Largest Single Penalty:** **${triage.largest_ticket:,.2f}**
- **Significant & Substantial (S&S) Citations:** **{ss_count} ticket(s)** ({round(ss_count / max(1, ticket_count) * 100)}% S&S density)
- **POV Proximity Proxy (30 CFR Part 104):** {pov_status}
- **30-Day Statutory Contest Clock:** **{triage.min_days_remaining} days remaining** on earliest ticket before assessment becomes a final, non-appealable FMSHRC order under 30 U.S.C. § 815(a).

### Historical Resolution Benchmark (MSHA Public Bulk Data 2022–2025):
- 4.4% of paid citations settled below proposed penalty at a median settlement ratio of **0.449 (55% reduction)**.
- For **{triage.operator_name}**, a benchmark 55% penalty reduction yields **${total_exposure * 0.55:,.2f} in direct penalty savings**, in addition to POV point eliminations.
- **Industry Pricing Comparison:**
  - Traditional legal anchor: **$5,000–$8,000** per matter for informal conference; **$15,000+** for formal FMSHRC contest litigation (LawSnap Oct 2025).
  - Triage Desk Document-Prep Service: **$350 flat per-citation triage packet** + **$1,500/mo POV-watch retainer** + optional 15% success fee on reductions.
  - *Non-UPL Compliance Positioning:* This dossier is a compliance data, engineering analytics, and document-preparation service, NOT legal advice. The operator files its own contest and conference requests.

---

## 2. Contestable Citation Inventory & 30-Day Clock Countdown
All citations below have been issued in `Proposed` penalty status within the last 25 days. Every ticket carries an active 30-day statutory contest clock under Section 105(a) of the Federal Mine Safety and Health Act of 1977.

{citation_table_md}

---

## 3. Pattern of Violations (POV) Proximity Risk Analysis (30 CFR Part 104)
Under 30 CFR Part 104, MSHA conducts automated screening of all mines for a **Pattern of Violations (POV)**. A formal POV notice is catastrophic: it mandates a **withdrawal order for EVERY subsequent S&S violation** with zero abatement time, effectively shutting down mine production until a completely clean inspection occurs.

### POV Proxy Metric:
- Screening criteria triggers when a mine accumulates **>=5 S&S violations on the same PART_SECTION within trailing 12 months**.
- **Operator Assessment:**
{pov_block}

### Action Required:
Operators in POV proximity must prioritize contesting and eliminating the S&S designation from every proposed citation in the repeating standard families before the 30-day clock lapses.

---

## 4. Top Repeat Safety Standards in Current Batch
{top_stds_block}

---

## 5. Tailored Mitigation Defense Checklists (By Standard Family)
The following defense arguments are mapped directly to the statutory families represented in your active citations:

{defense_block}

---

## 6. Pre-Filled Informal Conference Request Letter Template
*Instructions: Copy the pre-filled letter below onto operator letterhead, execute signature by authorized safety personnel, and deliver via certified mail or email to your MSHA District Enforcement Office before the earliest 30-day contest window expires.*

{conference_letter}

---

## 7. Regulatory Disclaimer & Service Terms
*This document and its pre-filled templates are compiled by MSHA Citation Triage Desk from public bulk enforcement data published by the Mine Safety and Health Administration. This service provides technical compliance data, penalty analytics, and document preparation assistance. It does not provide legal representation or legal advice. Mine operators file their own informal conference requests and notices of contest under 30 CFR § 100.6 and 30 U.S.C. § 815(a).*
"""

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(packet_content, encoding="utf-8")

    return packet_content
