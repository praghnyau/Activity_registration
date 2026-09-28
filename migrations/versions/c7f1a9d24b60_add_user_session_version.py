"""add user.session_version

Phase 6 needs to "end other sessions" when a password changes. Sessions here
are signed cookies, so there is no server-side session store to delete from.
A version column stored in both the row and the cookie gives us revocation:
bumping the row invalidates every cookie minted before the change.

Revision ID: c7f1a9d24b60
Revises: 9e44e6ab46b2
Create Date: 2026-09-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7f1a9d24b60"
down_revision: Union[str, None] = "9e44e6ab46b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("users", "session_version")
