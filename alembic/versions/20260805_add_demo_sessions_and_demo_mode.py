"""Add demo_sessions table and demo_mode flag to chat tables.

Revision ID: 20260805_add_demo_sessions_and_demo_mode
Revises: 20260803_add_llm_provider_settings
Create Date: 2026-08-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260805_add_demo_sessions_and_demo_mode"
down_revision: Union[str, None] = "9c51255b_add_provider_settings_to_ai_configs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "demo_sessions",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("requests_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requests_limit", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_demo_sessions_token", "demo_sessions", ["token"], unique=True)
    op.create_index("ix_demo_sessions_session_id", "demo_sessions", ["session_id"])
    op.create_index("ix_demo_sessions_client_ip", "demo_sessions", ["client_ip"])

    op.add_column(
        "chat_sessions",
        sa.Column(
            "demo_mode",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "chat_requests",
        sa.Column(
            "demo_mode",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_requests", "demo_mode")
    op.drop_column("chat_sessions", "demo_mode")

    op.drop_index("ix_demo_sessions_client_ip", table_name="demo_sessions")
    op.drop_index("ix_demo_sessions_session_id", table_name="demo_sessions")
    op.drop_index("ix_demo_sessions_token", table_name="demo_sessions")
    op.drop_table("demo_sessions")
