"""Add cache_ttl_seconds and embedding_timeout_ms to retrieval_tuning.

Revision ID: 20260731_2_add_retrieval_extra_fields
Revises: 20260731_add_retrieval_tuning
Create Date: 2026-07-31 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731b_add_retrieval_extra"
down_revision: Union[str, None] = "20260731_add_retrieval_tuning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "retrieval_tuning",
        sa.Column("cache_ttl_seconds", sa.Integer(), nullable=False, server_default="300"),
    )
    op.add_column(
        "retrieval_tuning",
        sa.Column("embedding_timeout_ms", sa.Integer(), nullable=False, server_default="30000"),
    )


def downgrade() -> None:
    op.drop_column("retrieval_tuning", "embedding_timeout_ms")
    op.drop_column("retrieval_tuning", "cache_ttl_seconds")
