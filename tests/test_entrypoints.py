"""Tests for top-level entry point imports and modules."""

import fetch
import triage
import packet
import leads


def test_toplevel_imports():
    """Verify top-level module wrappers re-export correctly."""
    assert hasattr(fetch, "stream_pipe_delimited")
    assert hasattr(fetch, "load_mines_mapping")
    assert hasattr(triage, "TriageEngine")
    assert hasattr(triage, "CitationRecord")
    assert hasattr(packet, "generate_triage_packet")
    assert hasattr(packet, "generate_informal_conference_letter")
    assert hasattr(leads, "write_leads_csv")
