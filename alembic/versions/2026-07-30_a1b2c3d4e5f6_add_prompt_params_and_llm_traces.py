"""Add prompt parameters to ai_config and separate llm_call_traces table.

Revision ID: a1b2c3d4e5f6
Revises: d0e7f8a9b1c2
Create Date: 2026-07-30 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "d0e7f8a9b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add prompt/retrieval parameters to ai_configs.
    op.add_column("ai_configs", sa.Column("rag_distance_threshold", sa.Float(), nullable=True))
    op.add_column("ai_configs", sa.Column("beginner_instructions", sa.Text(), nullable=True))
    op.add_column("ai_configs", sa.Column("advanced_instructions", sa.Text(), nullable=True))
    op.add_column("ai_configs", sa.Column("few_shot_examples", sa.Text(), nullable=True))
    op.add_column("ai_configs", sa.Column("output_rules", sa.Text(), nullable=True))
    op.add_column("ai_configs", sa.Column("refusal_answer_text", sa.Text(), nullable=True))
    op.add_column("ai_configs", sa.Column("max_history_messages", sa.Integer(), nullable=True))

    # Populate defaults for existing active configs.
    op.execute(
        "UPDATE ai_configs SET rag_distance_threshold = 1.35, max_history_messages = 6 "
        "WHERE rag_distance_threshold IS NULL"
    )

    # Move full prompt/response out of llm_calls into llm_call_traces.
    op.create_table(
        "llm_call_traces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("chat_requests.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_llm_call_traces_created_at", "llm_call_traces", ["created_at"])

    op.add_column("llm_calls", sa.Column("trace_id", sa.Integer(), nullable=True))
    op.create_index("ix_llm_calls_trace_id", "llm_calls", ["trace_id"])
    op.create_foreign_key(
        "fk_llm_calls_trace_id",
        "llm_calls",
        "llm_call_traces",
        ["trace_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_llm_calls_trace_id", "llm_calls", type_="foreignkey")
    op.drop_index("ix_llm_calls_trace_id", "llm_calls")
    op.drop_column("llm_calls", "trace_id")
    op.drop_table("llm_call_traces")

    op.drop_column("ai_configs", "max_history_messages")
    op.drop_column("ai_configs", "refusal_answer_text")
    op.drop_column("ai_configs", "output_rules")
    op.drop_column("ai_configs", "few_shot_examples")
    op.drop_column("ai_configs", "advanced_instructions")
    op.drop_column("ai_configs", "beginner_instructions")
    op.drop_column("ai_configs", "rag_distance_threshold")
