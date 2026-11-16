"""Unit tests for the Alembic autogenerate filters (ADR-0014, NFR-REL-04).

ADK's DatabaseSessionService owns the ``adk`` schema, so autogenerate must never see it.
No network: the behavioural proof uses an in-memory SQLite database with an attached
database named ``adk``, which SQLAlchemy reflects as a schema called ``adk``.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import (
    Column,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Table,
    create_engine,
    text,
)
from sqlalchemy.engine import Connection

from app.db.migration_filters import (
    ADK_SCHEMA,
    AUTOGENERATE_OPTIONS,
    include_name,
    include_object,
)

pytestmark = pytest.mark.unit


def _table(schema: str | None) -> Table:
    metadata = MetaData(schema=schema)
    parent = Table("parent", metadata, Column("id", Integer, primary_key=True))
    child = Table(
        "child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer),
        ForeignKeyConstraint(["parent_id"], [f"{parent.fullname}.id"], name="fk_child_parent"),
    )
    Index("ix_child_parent", child.c.parent_id)
    return child


def test_adk_schema_name_is_adk() -> None:
    assert ADK_SCHEMA == "adk"


def test_nfr_rel_04_include_name_excludes_adk_schema() -> None:
    assert include_name("adk", "schema", {}) is False


@pytest.mark.parametrize("schema", [None, "kb", "convo", "audit", "app", "public"])
def test_nfr_rel_04_include_name_keeps_other_schemas(schema: str | None) -> None:
    """``None`` is how Alembic names the connection's default schema."""
    assert include_name(schema, "schema", {}) is True


@pytest.mark.parametrize("type_", ["table", "column", "index", "unique_constraint"])
def test_nfr_rel_04_include_name_excludes_children_of_adk(type_: str) -> None:
    assert include_name("sessions", type_, {"schema_name": "adk"}) is False


def test_nfr_rel_04_include_name_keeps_children_of_other_schemas() -> None:
    assert include_name("notes", "table", {"schema_name": "kb"}) is True
    assert include_name("notes", "table", {"schema_name": None}) is True
    assert include_name("notes", "table", {}) is True


def test_nfr_rel_04_include_object_excludes_every_object_kind_in_adk() -> None:
    table = _table("adk")
    (index,) = table.indexes
    (foreign_key,) = table.foreign_key_constraints

    assert include_object(table, "child", "table", True, None) is False
    assert include_object(table.c.id, "id", "column", True, None) is False
    assert include_object(index, "ix_child_parent", "index", True, None) is False
    assert (
        include_object(foreign_key, "fk_child_parent", "foreign_key_constraint", True, None)
        is False
    )


@pytest.mark.parametrize("schema", [None, "kb", "app"])
def test_nfr_rel_04_include_object_keeps_objects_outside_adk(schema: str | None) -> None:
    table = _table(schema)
    (index,) = table.indexes

    assert include_object(table, "child", "table", True, None) is True
    assert include_object(table.c.id, "id", "column", True, None) is True
    assert include_object(index, "ix_child_parent", "index", True, None) is True


def test_nfr_rel_04_autogenerate_options_wire_the_filters() -> None:
    assert AUTOGENERATE_OPTIONS["include_schemas"] is True
    assert AUTOGENERATE_OPTIONS["include_name"] is include_name
    assert AUTOGENERATE_OPTIONS["include_object"] is include_object


@pytest.fixture
def connection() -> Iterator[Connection]:
    """SQLite with a ``main`` table and an attached ``adk`` database holding ADK-like tables."""
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.execute(text("ATTACH DATABASE ':memory:' AS adk"))
        conn.execute(text("CREATE TABLE adk.sessions (id INTEGER PRIMARY KEY, state TEXT)"))
        conn.execute(text("CREATE INDEX adk.ix_sessions_state ON sessions (state)"))
        conn.execute(text("CREATE TABLE main.notes (id INTEGER PRIMARY KEY)"))
        yield conn
    engine.dispose()


def _diff_text(connection: Connection, options: dict[str, Any]) -> str:
    context = MigrationContext.configure(connection, opts=options)
    return repr(compare_metadata(context, MetaData()))


def test_nfr_rel_04_autogenerate_never_proposes_changes_to_adk(connection: Connection) -> None:
    """Empty target metadata means "drop everything it can see"; ADK tables must not be seen."""
    diff = _diff_text(connection, dict(AUTOGENERATE_OPTIONS))

    assert "adk" not in diff
    assert "sessions" not in diff
    # Control: the comparison really ran and still sees non-ADK objects.
    assert "notes" in diff


def test_nfr_rel_04_control_without_filters_autogenerate_sees_adk(connection: Connection) -> None:
    """Proves the test above is not vacuous: without our options the ADK table is reported."""
    diff = _diff_text(connection, {"include_schemas": True})

    assert "sessions" in diff
