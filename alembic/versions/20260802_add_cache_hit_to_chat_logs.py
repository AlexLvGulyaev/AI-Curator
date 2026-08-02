"""Add cache_hit to chat_logs.

Revision ID: 20260802_add_cache_hit_to_chat_logs
Revises: 20260801_add_chat_sessions_execution_steps
Create Date: 2026-08-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260802_add_cache_hit_to_chat_logs"
down_revision: Union[str, None] = "20260801_add_chat_sessions_execution_steps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_logs",
        sa.Column(
            "cache_hit",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_logs", "cache_hit")
