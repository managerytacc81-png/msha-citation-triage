"""MSHA Triage Packet Generator entry point."""

from msha_triage.packet import (  # noqa: F401, F403
    STANDARD_FAMILY_DEFENSES,
    generate_informal_conference_letter,
    generate_triage_packet,
    match_standard_defense,
)

if __name__ == "__main__":
    print("MSHA Packet module loaded successfully.")
