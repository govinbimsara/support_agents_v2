"""Unit tests for the config loader (SDD 18 Configuration Reference).

SDD 18: a single app/config/config.yaml holds the defaults; each environment
overrides values with environment variables (prefix GENIE_).
"""

import os
import traceback
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import ConfigError, get_settings, load_settings

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_genie_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep GENIE_* variables from the developer's shell out of the tests."""
    for name in list(os.environ):
        if name.startswith("GENIE_"):
            monkeypatch.delenv(name)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def write_yaml(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


VALID_YAML = "app_name: test_app\nenvironment: demo\nlog_level: WARNING\n"


def test_sdd18_shipped_config_loads_defaults() -> None:
    settings = load_settings()

    assert settings.app_name == "genie_business_support"
    assert settings.environment == "dev"
    assert settings.log_level == "INFO"


def test_sdd18_loads_custom_path(tmp_path: Path) -> None:
    settings = load_settings(write_yaml(tmp_path, VALID_YAML))

    assert settings.app_name == "test_app"
    assert settings.environment == "demo"
    assert settings.log_level == "WARNING"


def test_sdd18_env_var_overrides_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENIE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("GENIE_ENVIRONMENT", "prod")

    settings = load_settings(write_yaml(tmp_path, VALID_YAML))

    assert settings.log_level == "DEBUG"
    assert settings.environment == "prod"
    assert settings.app_name == "test_app"  # not overridden, YAML value kept


def test_sdd18_unprefixed_env_var_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    assert load_settings(write_yaml(tmp_path, VALID_YAML)).log_level == "WARNING"


def test_sdd18_log_level_is_case_insensitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GENIE_LOG_LEVEL", "error")

    assert load_settings(write_yaml(tmp_path, VALID_YAML)).log_level == "ERROR"


@pytest.mark.parametrize(
    ("yaml_text", "field"),
    [
        ("app_name: a\nenvironment: dev\nlog_level: LOUD\n", "log_level"),
        ("app_name: a\nenvironment: staging\nlog_level: INFO\n", "environment"),
        ("app_name: ''\nenvironment: dev\nlog_level: INFO\n", "app_name"),
        ("app_name: a\nenvironment: dev\nlog_level: INFO\nlog_levle: DEBUG\n", "log_levle"),
        ("environment: dev\nlog_level: INFO\n", "app_name"),
    ],
    ids=["bad-log-level", "bad-environment", "empty-app-name", "unknown-key", "missing-key"],
)
def test_sdd18_invalid_yaml_value_raises_config_error(
    tmp_path: Path, yaml_text: str, field: str
) -> None:
    with pytest.raises(ConfigError, match=field):
        load_settings(write_yaml(tmp_path, yaml_text))


@pytest.mark.parametrize(
    ("bad_key_line", "named_key"),
    [
        ('_env_prefix: "sk-not-a-real-secret-123"\n', "_env_prefix"),
        ('_cli_parse_args: "sk-not-a-real-secret-123"\n', "_cli_parse_args"),
        ('1: "sk-not-a-real-secret-123"\n', "1"),
    ],
    ids=["underscore-env-prefix", "underscore-cli-parse-args", "non-string-key"],
)
def test_sdd18_yaml_key_that_is_not_a_field_name_raises_config_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_key_line: str, named_key: str
) -> None:
    """Keys go to pydantic-settings as kwargs; "_"-keys would reconfigure the loader."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")  # must never apply, whatever the YAML says

    with pytest.raises(ConfigError) as excinfo:
        load_settings(write_yaml(tmp_path, VALID_YAML + bad_key_line))

    message = str(excinfo.value)
    assert f"'{named_key}'" in message
    assert "SK-NOT-A-REAL-SECRET-123" not in message.upper()


def test_sdd18_invalid_env_override_raises_config_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GENIE_ENVIRONMENT", "staging")

    with pytest.raises(ConfigError, match="environment"):
        load_settings(write_yaml(tmp_path, VALID_YAML))


@pytest.mark.parametrize(
    "unknown_var",
    ["GENIE_LOGLEVEL", "GENIE_MODELS__LIVE"],
    ids=["typo", "unknown-section"],
)
def test_sdd18_unknown_genie_env_var_raises_config_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unknown_var: str
) -> None:
    """A mistyped override must fail loudly, like a mistyped YAML key, not be ignored."""
    monkeypatch.setenv(unknown_var, "sk-not-a-real-secret-123")

    with pytest.raises(ConfigError) as excinfo:
        load_settings(write_yaml(tmp_path, VALID_YAML))

    message = str(excinfo.value)
    assert unknown_var in message
    assert "SK-NOT-A-REAL-SECRET-123" not in message.upper()


def test_sdd18_error_message_does_not_echo_rejected_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A value set by mistake (it could be a secret) must never reach logs."""
    rejected = "sk-not-a-real-secret-123"
    monkeypatch.setenv("GENIE_LOG_LEVEL", rejected)

    with pytest.raises(ConfigError) as excinfo:
        load_settings(write_yaml(tmp_path, VALID_YAML))

    assert rejected.upper() not in str(excinfo.value).upper()
    assert "log_level" in str(excinfo.value)


def test_sdd18_traceback_does_not_echo_rejected_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """logger.exception() prints the whole chain; a chained ValidationError would leak."""
    rejected = "sk-not-a-real-secret-123"
    monkeypatch.setenv("GENIE_LOG_LEVEL", rejected)

    with pytest.raises(ConfigError) as excinfo:
        load_settings(write_yaml(tmp_path, VALID_YAML))

    full_traceback = "".join(traceback.format_exception(excinfo.value))
    assert rejected.upper() not in full_traceback.upper()


def test_sdd18_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "missing.yaml")


def test_sdd18_unreadable_path_raises_config_error(tmp_path: Path) -> None:
    """A directory (or a file without read permission) is reported, not raised raw."""
    with pytest.raises(ConfigError, match="could not be read"):
        load_settings(tmp_path)


@pytest.mark.parametrize(
    "yaml_text",
    ["app_name: [unclosed\n", "- just\n- a list\n", ""],
    ids=["malformed", "top-level-list", "empty-file"],
)
def test_sdd18_unreadable_yaml_raises_config_error(tmp_path: Path, yaml_text: str) -> None:
    with pytest.raises(ConfigError):
        load_settings(write_yaml(tmp_path, yaml_text))


def test_sdd18_settings_are_immutable() -> None:
    settings = load_settings()

    with pytest.raises(ValidationError):
        settings.log_level = "DEBUG"  # type: ignore[misc]  # asserting frozen at runtime


def test_sdd18_get_settings_is_cached_and_reads_shipped_config() -> None:
    first = get_settings()

    assert get_settings() is first
    assert first.app_name == "genie_business_support"
