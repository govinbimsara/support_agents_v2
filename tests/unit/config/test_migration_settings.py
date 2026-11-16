"""Unit tests for the migration database URL (ADR-0014, NFR-REL-04).

DATABASE_URL_DIRECT is a credential. It must come only from the process environment and
must never appear in an error message, a traceback or a repr. Fixtures use fake values.
"""

import traceback
from pathlib import Path

import pytest

from app.config import ConfigError, load_migration_settings, migration_url

pytestmark = pytest.mark.unit

VAR = "DATABASE_URL_DIRECT"
FAKE_PASSWORD = "not-a-real-pw"
DIRECT_URL = f"postgresql://app_user:{FAKE_PASSWORD}@ep-quiet-sky-123456.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"


@pytest.fixture(autouse=True)
def _no_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a DATABASE_URL_DIRECT from the developer's shell out of the tests."""
    monkeypatch.delenv(VAR, raising=False)


def test_nfr_rel_04_loads_direct_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, DIRECT_URL)

    url = migration_url(load_migration_settings())

    assert url.drivername == "postgresql+psycopg"
    assert url.host == "ep-quiet-sky-123456.ap-southeast-1.aws.neon.tech"
    assert url.password == FAKE_PASSWORD
    assert url.query == {"sslmode": "require"}


def test_nfr_rel_04_postgres_scheme_alias_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, DIRECT_URL.replace("postgresql://", "postgres://", 1))

    assert migration_url(load_migration_settings()).drivername == "postgresql+psycopg"


def test_nfr_rel_04_url_and_settings_hide_the_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, DIRECT_URL)
    settings = load_migration_settings()
    url = migration_url(settings)

    for rendered in (repr(settings), str(settings), repr(url), str(url)):
        assert FAKE_PASSWORD not in rendered


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        (None, "missing"),
        ("", "empty"),
        ("   ", "blank"),
        (f"not a url {FAKE_PASSWORD}", "unparsable"),
        (f"mysql://u:{FAKE_PASSWORD}@db.example/x", "wrong-scheme"),
        (f"postgresql://u:{FAKE_PASSWORD}@ep-a-b-123456-pooler.neon.tech/x", "pooler"),
        (f"postgresql://u:{FAKE_PASSWORD}@ep-x.neon.tech:abc/db", "non-numeric-port"),
        (f"postgresql://u:{FAKE_PASSWORD}@ep-x.neon.tech:99999999/db", "port-too-large"),
        (f"postgresql://u:{FAKE_PASSWORD}@ep-x.neon.tech:0/db", "port-zero"),
    ],
    ids=[
        "missing",
        "empty",
        "blank",
        "unparsable",
        "wrong-scheme",
        "pooler-endpoint",
        "non-numeric-port",
        "port-too-large",
        "port-zero",
    ],
)
def test_nfr_rel_04_bad_value_raises_config_error_naming_only_the_variable(
    monkeypatch: pytest.MonkeyPatch, value: str | None, reason: str
) -> None:
    if value is not None:
        monkeypatch.setenv(VAR, value)

    with pytest.raises(ConfigError) as excinfo:
        load_migration_settings()

    full_traceback = "".join(traceback.format_exception(excinfo.value))
    assert VAR in str(excinfo.value), reason
    assert FAKE_PASSWORD not in full_traceback, reason
    if value and value.strip():  # a blank value is trivially a substring of any traceback
        assert value not in full_traceback, reason


def test_nfr_rel_04_pooler_endpoint_error_explains_why(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(VAR, f"postgresql://u:{FAKE_PASSWORD}@ep-a-b-123456-pooler.neon.tech/x")

    with pytest.raises(ConfigError, match="pooled"):
        load_migration_settings()


def test_nfr_rel_04_dotenv_is_not_a_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The URL is environment-only: a .env in the working directory must not be read."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(f"{VAR}={DIRECT_URL}\n", encoding="utf-8")

    with pytest.raises(ConfigError, match=VAR):
        load_migration_settings()
