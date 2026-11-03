"""Tests for streaming data fetcher and loader."""

import io
import zipfile
from pathlib import Path
import pytest

from msha_triage.fetch import (
    load_mines_mapping,
    open_stream,
    stream_pipe_delimited,
)


def test_open_stream_plain_text(sample_violations_path: Path):
    """Verify open_stream can read plain pipe-delimited text."""
    stream = open_stream(sample_violations_path)
    try:
        first_line = stream.readline()
        assert "EVENT_NO|" in first_line
        assert "VIOLATION_NO|" in first_line
    finally:
        stream.close()


def test_open_stream_zip(tmp_path: Path, sample_violations_path: Path):
    """Verify open_stream can extract and stream directly from zip archive."""
    zip_path = tmp_path / "test_viol.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(sample_violations_path, arcname="Violations.txt")

    stream = open_stream(zip_path)
    try:
        first_line = stream.readline()
        assert "EVENT_NO|" in first_line
    finally:
        stream.close()


def test_stream_pipe_delimited(sample_violations_path: Path):
    """Verify stream_pipe_delimited yields valid row dictionaries."""
    rows = list(stream_pipe_delimited(sample_violations_path))
    assert len(rows) > 0
    first = rows[0]
    assert "VIOLATION_NO" in first
    assert "MINE_ID" in first
    assert "PROPOSED_PENALTY" in first
    assert "LAST_ACTION_CD" in first


def test_load_mines_mapping(sample_mines_path: Path):
    """Verify loading mines mapping produces correct lookup entries."""
    mapping = load_mines_mapping(sample_mines_path)
    assert len(mapping) > 0
    for mid, info in mapping.items():
        assert "mine_name" in info
        assert "operator_name" in info
        assert "state" in info
        assert len(info["state"]) == 2


def test_missing_file_raises_not_found(tmp_path: Path):
    """Verify proper error on missing file path."""
    with pytest.raises(FileNotFoundError):
        open_stream(tmp_path / "non_existent.txt")
