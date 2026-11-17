"""Unit tests for the Alembic environment and baseline revision (ADR-0014, NFR-REL-04).

No database: offline mode renders SQL to a buffer and never reads DATABASE_URL_DIRECT.
"""

import configparser
import io
import logging
import re
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from tests.unit.config.test_migration_settings import FAKE_PASSWORD

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def alembic_config() -> Config:
    # No ini file: skips env.py's logging reconfiguration so other tests' logging is untouched.
    return Config(toml_file=str(ROOT / "pyproject.toml"))


def _engine_logger_level(ini_text: str) -> int:
    """Numeric level of the logger whose qualname is ``sqlalchemy.engine``.

    Found by qualname, not by section name, so renaming the section cannot hide it.
    Interpolation is off because the ini holds ``%(...)s`` log-format strings.
    """
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(ini_text)
    for name in parser.sections():
        if name.startswith("logger_") and parser[name].get("qualname") == "sqlalchemy.engine":
            return logging.getLevelNamesMapping()[parser[name]["level"].strip().upper()]
    raise AssertionError("no [logger_*] section with qualname = sqlalchemy.engine")


# Only the obviously fake passwords used in tests may appear in a credential URL.
ALLOWED_FAKE_PASSWORDS = frozenset({FAKE_PASSWORD})
_CREDENTIAL_URL = re.compile(r"postgres(?:ql)?(?:\+\w+)?://[^\s:/@]+:(?P<password>[^\s@]+)@")


def _credential_urls(text: str) -> list[str]:
    """Return postgres(ql):// URLs in ``text`` that embed a password not on the fake allow-list."""
    return [
        match.group(0)
        for match in _CREDENTIAL_URL.finditer(text)
        if match["password"] not in ALLOWED_FAKE_PASSWORDS
    ]


def test_adr_0014_single_empty_baseline_head(alembic_config: Config) -> None:
    script = ScriptDirectory.from_config(alembic_config)

    assert script.get_heads() == ["0001"]
    baseline = script.get_revision("0001")
    assert baseline is not None
    assert baseline.down_revision is None


def test_adr_0014_baseline_offline_sql_creates_no_tables_schemas_or_extensions(
    alembic_config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DATABASE_URL_DIRECT", raising=False)
    buffer = io.StringIO()
    alembic_config.output_buffer = buffer

    command.upgrade(alembic_config, "head", sql=True)

    sql = buffer.getvalue()
    created = re.findall(
        r"CREATE\s+(?:TABLE|SCHEMA|EXTENSION|INDEX)\s+(?:IF NOT EXISTS\s+)?(\S+)", sql, re.I
    )
    assert created == ["alembic_version"]  # Alembic's own bookkeeping table, nothing else
    assert "adk" not in sql.lower()


@pytest.mark.parametrize(
    "text",
    [
        "postgresql://user:password@host/db",
        "postgres://u:s3cret@host",
        "postgresql+asyncpg://u:p@host/db",
        "url = 'postgresql://app:hunter2@ep-x.neon.tech:5432/neondb?sslmode=require'",
    ],
    ids=["postgresql", "postgres-scheme", "driver-suffix", "embedded-in-code"],
)
def test_nfr_rel_04_credential_url_scan_flags_real_looking_urls(text: str) -> None:
    assert _credential_urls(text) != []


@pytest.mark.parametrize(
    "text",
    [
        f"postgresql://u:{FAKE_PASSWORD}@host/db",
        "https://user:pw@example.com/path",
        "postgresql://host/db",
        "postgresql://user@host/db",
    ],
    ids=["known-fake", "not-postgres", "no-credentials", "no-password"],
)
def test_nfr_rel_04_credential_url_scan_allows_fakes_and_credential_free_urls(text: str) -> None:
    assert _credential_urls(text) == []


def test_nfr_rel_04_no_database_url_is_configured_in_repo_files(alembic_config: Config) -> None:
    ini_text = (ROOT / "alembic.ini").read_text(encoding="utf-8")

    assert alembic_config.get_main_option("sqlalchemy.url") is None  # [tool.alembic] has none
    # Comments may mention the setting; an active assignment must not exist.
    assert not re.search(r"^\s*sqlalchemy\.url\s*=", ini_text, re.M)
    assert "://" not in ini_text.replace("https://", "")


def test_nfr_rel_04_no_credential_url_in_config_docs_or_migration_files() -> None:
    """No postgres(ql)://user:password@ anywhere a connection string could be pasted by mistake."""
    files = [
        ROOT / "alembic.ini",
        ROOT / "pyproject.toml",
        ROOT / "CLAUDE.md",
        *sorted(ROOT.glob("migrations/**/*.py")),
    ]

    offenders = [
        str(path.relative_to(ROOT))
        for path in files
        if _credential_urls(path.read_text(encoding="utf-8", errors="replace"))
    ]

    assert offenders == []


def test_nfr_rel_04_online_mode_without_url_fails_before_connecting(
    alembic_config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """env.py must stop with a ConfigError naming the variable, not try to connect."""
    from app.config import ConfigError

    monkeypatch.delenv("DATABASE_URL_DIRECT", raising=False)

    with pytest.raises(ConfigError, match="DATABASE_URL_DIRECT"):
        command.current(alembic_config)


SAMPLE_INI_INFO = """
[logger_sqlalchemy]
level = INFO
handlers =
qualname = sqlalchemy.engine
"""


def test_nfr_rel_04_engine_logger_level_helper_reads_the_level_by_qualname() -> None:
    assert _engine_logger_level(SAMPLE_INI_INFO) == logging.INFO


def test_nfr_rel_04_engine_logger_level_helper_fails_when_the_logger_is_missing() -> None:
    with pytest.raises(AssertionError, match=re.escape("sqlalchemy.engine")):
        _engine_logger_level("[logger_root]\nlevel = WARNING\nqualname =\n")


def test_nfr_rel_04_sqlalchemy_engine_logger_is_warning_or_higher() -> None:
    """INFO/DEBUG on sqlalchemy.engine logs every statement and can expose connection details."""
    ini_text = (ROOT / "alembic.ini").read_text(encoding="utf-8")

    assert _engine_logger_level(ini_text) >= logging.WARNING
