"""Add monitoring indexes for dashboard queries.

Revision ID: 20260730202611
Revises: a1b2c3d4e5f6
Create Date: 2026-07-30 20:26:11.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260730202611"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Indexes for 24h dashboard aggregations.
    op.create_index("ix_chat_requests_created_at", "chat_requests", ["created_at"])
    op.create_index("ix_chat_logs_created_at", "chat_logs", ["created_at"])
    op.create_index("ix_chat_logs_error", "chat_logs", ["error"])
    op.create_index("ix_llm_calls_created_at", "llm_calls", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_calls_created_at", table_name="llm_calls")
    op.drop_index("ix_chat_logs_error", table_name="chat_logs")
    op.drop_index("ix_chat_logs_created_at", table_name="chat_logs")
    op.drop_index("ix_chat_requests_created_at", table_name="chat_requests")
