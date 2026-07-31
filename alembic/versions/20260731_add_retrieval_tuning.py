"""Add retrieval_tuning table and remove retrieval params from ai_configs.

Revision ID: 20260731_add_retrieval_tuning
Revises: 20260730202611
Create Date: 2026-07-31 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731_add_retrieval_tuning"
down_revision: Union[str, None] = "20260730202611"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create retrieval_tuning table.
    op.create_table(
        "retrieval_tuning",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("rag_distance_threshold", sa.Float(), nullable=False, server_default="1.35"),
        sa.Column("chunk_size", sa.Integer(), nullable=False, server_default="512"),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False, server_default="128"),
        sa.Column("cache_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("retrieval_timeout_ms", sa.Integer(), nullable=False, server_default="5000"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed default row.
    op.execute(
        "INSERT INTO retrieval_tuning (top_k, rag_distance_threshold, chunk_size, chunk_overlap, "
        "cache_enabled, retrieval_timeout_ms) VALUES (5, 1.35, 512, 128, true, 5000)"
    )

    # Remove retrieval columns from ai_configs.
    op.drop_column("ai_configs", "top_k_retrieval")
    op.drop_column("ai_configs", "rag_distance_threshold")


def downgrade() -> None:
    op.add_column(
        "ai_configs",
        sa.Column("rag_distance_threshold", sa.Float(), nullable=True),
    )
    op.add_column(
        "ai_configs",
        sa.Column("top_k_retrieval", sa.Integer(), nullable=True),
    )
    op.drop_table("retrieval_tuning")
