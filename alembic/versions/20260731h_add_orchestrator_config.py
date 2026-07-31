"""Add orchestrator_configs table.

Revision ID: 20260731h_add_orchestrator_config
Revises: 20260731g_add_course_boost_to_retrieval_tuning
Create Date: 2026-07-31 23:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260731h_add_orchestrator_config"
down_revision: Union[str, None] = "20260731g_add_course_boost_to_retrieval_tuning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orchestrator_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intent_rules", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("default_intent", sa.String(length=50), nullable=False),
        sa.Column("intent_source_map", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("non_course_starters", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("max_lms_contents", sa.Integer(), nullable=False),
        sa.Column("max_lms_deadlines", sa.Integer(), nullable=False),
        sa.Column("intent_max_tokens", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("fallback_messages", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orchestrator_configs")),
    )
    op.create_index(op.f("ix_orchestrator_configs_id"), "orchestrator_configs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orchestrator_configs_id"), table_name="orchestrator_configs")
    op.drop_table("orchestrator_configs")
