"""Add LLM provider settings to ai_configs.

Revision ID: 20260803_add_llm_provider_settings
Revises: 20260802_add_cache_hit_to_chat_logs
Create Date: 2026-08-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260803_add_llm_provider_settings"
down_revision: Union[str, None] = "20260802_add_cache_hit_to_chat_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_configs",
        sa.Column("active_provider", sa.String(length=50), nullable=False, server_default=sa.text("'openai'")),
    )
    op.add_column(
        "ai_configs",
        sa.Column("fallback_provider", sa.String(length=50), nullable=False, server_default=sa.text("'gigachat'")),
    )
    op.add_column(
        "ai_configs",
        sa.Column("openai_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "ai_configs",
        sa.Column("gigachat_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("ai_configs", "active_provider")
    op.drop_column("ai_configs", "fallback_provider")
    op.drop_column("ai_configs", "openai_enabled")
    op.drop_column("ai_configs", "gigachat_enabled")
