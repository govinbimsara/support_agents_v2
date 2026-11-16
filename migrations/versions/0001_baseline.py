"""baseline

Empty on purpose (ADR-0014). It only gives Alembic a starting revision to stamp. Schemas
(kb, convo, audit, app), tables and the pgvector extension are added by later, hand-reviewed
migrations. The ``adk`` schema is never migrated by us.

Revision ID: 0001
Revises:
Create Date: 2026-11-16 07:05:17.468529
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: nothing to do."""


def downgrade() -> None:
    """Downgrade schema: nothing to do."""
