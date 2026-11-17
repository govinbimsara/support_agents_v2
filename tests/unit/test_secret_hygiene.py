"""Repo-wide secret hygiene checks (NFR-REL-04).

These scan source text only. They never open env files.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SCANNED_DIRS = ("app", "migrations")
HIDE_PASSWORD_OFF = re.compile(r"hide_password\s*=\s*False")


def _files_under(*dirs: str) -> list[Path]:
    return sorted(
        path
        for directory in dirs
        for path in (ROOT / directory).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def test_nfr_rel_04_hide_password_false_appears_nowhere_in_app_or_migrations() -> None:
    """SQLAlchemy's ``hide_password=False`` renders the real password; never use or mention it."""
    offenders = [
        str(path.relative_to(ROOT))
        for path in _files_under(*SCANNED_DIRS)
        if HIDE_PASSWORD_OFF.search(path.read_text(encoding="utf-8", errors="replace"))
    ]

    assert offenders == []
