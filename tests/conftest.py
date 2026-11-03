"""Pytest configuration and shared fixtures for MSHA Citation Triage Desk tests."""

from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def sample_violations_path() -> Path:
    """Return path to sample violations fixture."""
    p = FIXTURES_DIR / "sample_violations.txt"
    assert p.is_file(), f"Fixture file not found: {p}"
    return p


@pytest.fixture
def sample_mines_path() -> Path:
    """Return path to sample mines fixture."""
    p = FIXTURES_DIR / "sample_mines.txt"
    assert p.is_file(), f"Fixture file not found: {p}"
    return p
