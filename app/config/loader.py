"""Typed configuration loader (SDD 18 Configuration Reference).

All tunables live in ``app/config/config.yaml``. Each environment (dev, demo, prod)
overrides values with environment variables named ``GENIE_<KEY>``; nested keys use a
double underscore, e.g. ``GENIE_MODELS__LIVE``. The ``GENIE_`` prefix keeps our
variables apart from generic platform ones such as ``ENVIRONMENT``.

Precedence, highest first: environment variable > config.yaml. The loader never reads
``.env`` files; the deployment platform (or the developer's shell) sets the environment.

Nothing is read at import time. Call :func:`load_settings` (explicit path, for tests and
scripts) or :func:`get_settings` (cached, for the app).
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from sqlalchemy import URL, make_url
from sqlalchemy.exc import ArgumentError

DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")
ENV_PREFIX = "GENIE_"

Environment = Literal["dev", "demo", "prod"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class ConfigError(Exception):
    """Configuration could not be loaded or is invalid.

    Messages name the file or field at fault but never include the rejected value,
    because a mistaken environment variable could hold a secret.
    """


class Settings(BaseSettings):
    """Validated application settings. Immutable once loaded."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_nested_delimiter="__",
        extra="forbid",
        frozen=True,
    )

    app_name: str = Field(min_length=1)
    environment: Environment
    log_level: LogLevel

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper_case_log_level(cls, value: Any) -> Any:
        return value.upper() if isinstance(value, str) else value

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # load_settings() passes the YAML values as init kwargs; listing env_settings
        # first makes GENIE_* variables win over them. The dotenv and secrets-dir
        # sources are left out on purpose.
        return env_settings, init_settings


def load_settings(path: Path = DEFAULT_CONFIG_PATH) -> Settings:
    """Load config.yaml from ``path`` and apply GENIE_* environment overrides.

    Raises:
        ConfigError: the file is missing or unreadable, is not a YAML mapping, or a
            value (from the file or an override) fails validation.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"Config file could not be read: {path}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Config file is not valid YAML: {path}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config file must contain a YAML mapping at the top level: {path}")
    # Keys become kwargs: a "_" key would set a pydantic-settings runtime option
    # (e.g. _env_prefix) instead of failing as an unknown field.
    bad_keys = [key for key in data if not isinstance(key, str) or key.startswith("_")]
    if bad_keys:
        names = ", ".join(repr(str(key)) for key in bad_keys)
        raise ConfigError(f"Config keys must be field names, not {names}: {path}")

    unknown_vars = _unknown_overrides()
    if unknown_vars:
        raise ConfigError(
            "Unknown environment variables (no matching config key): " + ", ".join(unknown_vars)
        )

    try:
        return Settings(**data)
    except ValidationError as exc:
        raise ConfigError(_describe(exc, path)) from None


def _describe(exc: ValidationError, path: Path) -> str:
    """Summarise validation errors by field and reason, without the input values."""
    problems = [
        f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}"
        for error in exc.errors(include_input=False, include_url=False)
    ]
    return f"Invalid configuration ({path}, GENIE_* overrides): " + "; ".join(problems)


def _unknown_overrides() -> list[str]:
    """Names (never values) of GENIE_* variables whose top-level key is not a field.

    pydantic-settings ignores such variables, so a typo would silently keep the YAML value.
    """
    return sorted(
        name
        for name in os.environ
        if name.upper().startswith(ENV_PREFIX)
        and name[len(ENV_PREFIX) :].split("__")[0].lower() not in Settings.model_fields
    )


MIGRATION_URL_VAR = "DATABASE_URL_DIRECT"
MIGRATION_DRIVER = "postgresql+psycopg"
_POSTGRES_BACKENDS = {"postgresql", "postgres"}
_MAX_PORT = 65535
# make_url raises ArgumentError for a malformed URL and ValueError for a non-numeric port.
# A named tuple keeps this stable under both the project's ruff and the older pre-commit
# ruff, which disagree on the Python 3.14 form ``except A, B:``.
_URL_PARSE_ERRORS = (ArgumentError, ValueError)


class MigrationSettings(BaseSettings):
    """Settings for Alembic only (ADR-0014, NFR-REL-04). Environment variables only.

    Kept apart from :class:`Settings` so the chat API and voice worker never load the
    direct (non-pooled) database credential. It is not in ``config.yaml`` and no dotenv
    or secrets-dir source is configured: the deployment platform or the developer's
    shell sets ``DATABASE_URL_DIRECT``. The value is a ``SecretStr``, so ``repr`` hides it.
    """

    model_config = SettingsConfigDict(extra="forbid", frozen=True)

    database_url_direct: SecretStr = Field(validation_alias=MIGRATION_URL_VAR)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (env_settings,)


def load_migration_settings() -> MigrationSettings:
    """Read and check ``DATABASE_URL_DIRECT`` from the environment.

    Raises:
        ConfigError: the variable is missing, empty, not a PostgreSQL URL, or points at a
            pooled Neon endpoint. Messages name the variable, never its value, and the
            underlying exception is suppressed because SQLAlchemy and pydantic echo input.
    """
    try:
        settings = MigrationSettings()
    except ValidationError:
        raise ConfigError(f"{MIGRATION_URL_VAR} is not set") from None

    raw = settings.database_url_direct.get_secret_value().strip()
    if not raw:
        raise ConfigError(f"{MIGRATION_URL_VAR} is empty")
    try:
        url = make_url(raw)
    except _URL_PARSE_ERRORS:
        raise ConfigError(f"{MIGRATION_URL_VAR} is not a valid database URL") from None
    if url.drivername.split("+")[0] not in _POSTGRES_BACKENDS:
        raise ConfigError(f"{MIGRATION_URL_VAR} must be a PostgreSQL URL (postgresql://...)")
    if url.port is not None and not 1 <= url.port <= _MAX_PORT:
        raise ConfigError(f"{MIGRATION_URL_VAR} has a port outside 1-{_MAX_PORT}")
    if "-pooler" in (url.host or "").lower():  # hostnames are case-insensitive
        raise ConfigError(
            f"{MIGRATION_URL_VAR} points at a pooled endpoint; migrations must use the "
            "direct (non-pooled) Neon endpoint (NFR-REL-04)"
        )
    return settings


def migration_url(settings: MigrationSettings) -> URL:
    """Build the SQLAlchemy URL for Alembic, using the synchronous psycopg driver.

    Any driver suffix in the URL (e.g. ``postgresql+asyncpg://``) is rewritten to psycopg.

    The secret is unwrapped here and nowhere else. ``URL.__repr__``/``__str__`` mask the
    password, but never call ``render_as_string(hide_password=False)`` on the result.
    """
    return make_url(settings.database_url_direct.get_secret_value().strip()).set(
        drivername=MIGRATION_DRIVER
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the app's settings, loaded once from the shipped config.yaml.

    Suitable as a FastAPI dependency. Tests call ``get_settings.cache_clear()``.
    """
    return load_settings()
