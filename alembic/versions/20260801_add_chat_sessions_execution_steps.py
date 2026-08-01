"""Add chat_sessions, execution_sessions, execution_steps and extend audit_logs.

Revision ID: 20260801_add_chat_sessions_execution_steps
Revises: 20260731h_add_orchestrator_config
Create Date: 2026-08-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260801_add_chat_sessions_execution_steps"
down_revision: Union[str, None] = "20260731h_add_orchestrator_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Chat sessions — canonical grouping of student dialog requests.
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_sessions")),
    )
    op.create_index(op.f("ix_chat_sessions_id"), "chat_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_chat_sessions_session_id"), "chat_sessions", ["session_id"], unique=True)
    op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_chat_sessions_role"), "chat_sessions", ["role"], unique=False)
    op.create_index(op.f("ix_chat_sessions_course_id"), "chat_sessions", ["course_id"], unique=False)
    op.create_index(op.f("ix_chat_sessions_mode"), "chat_sessions", ["mode"], unique=False)
    op.create_index(op.f("ix_chat_sessions_updated_at"), "chat_sessions", ["updated_at"], unique=False)

    # Execution sessions — one pipeline trace per chat request.
    op.create_table(
        "execution_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_session_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=True),
        sa.Column("route", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'started'")),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("provider_key", sa.String(length=50), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_metadata", sa.JSON(), nullable=True),
        sa.Column("is_backfilled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["chat_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_execution_sessions")),
    )
    op.create_index(op.f("ix_execution_sessions_id"), "execution_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_execution_sessions_chat_session_id"), "execution_sessions", ["chat_session_id"], unique=False)
    op.create_index(op.f("ix_execution_sessions_request_id"), "execution_sessions", ["request_id"], unique=False)
    op.create_index(op.f("ix_execution_sessions_status"), "execution_sessions", ["status"], unique=False)

    # Execution steps — individual stages inside an execution pipeline.
    op.create_table(
        "execution_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_session_id", sa.Integer(), nullable=False),
        sa.Column("stage_name", sa.String(length=50), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'ok'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("step_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["execution_session_id"], ["execution_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_execution_steps")),
    )
    op.create_index(op.f("ix_execution_steps_id"), "execution_steps", ["id"], unique=False)
    op.create_index(op.f("ix_execution_steps_execution_session_id"), "execution_steps", ["execution_session_id"], unique=False)
    op.create_index(op.f("ix_execution_steps_stage_name"), "execution_steps", ["stage_name"], unique=False)

    # Link chat requests to canonical chat sessions (optional, backfill-free).
    op.add_column("chat_requests", sa.Column("chat_session_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_chat_requests_chat_session_id"), "chat_requests", ["chat_session_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_chat_requests_chat_session_id"),
        "chat_requests",
        "chat_sessions",
        ["chat_session_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Extend audit_logs with client context.
    op.add_column("audit_logs", sa.Column("ip_address", sa.String(length=45), nullable=True))
    op.add_column("audit_logs", sa.Column("user_name", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_audit_logs_ip_address"), "audit_logs", ["ip_address"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_ip_address"), table_name="audit_logs")
    op.drop_column("audit_logs", "user_name")
    op.drop_column("audit_logs", "ip_address")

    op.drop_constraint(op.f("fk_chat_requests_chat_session_id"), "chat_requests", type_="foreignkey")
    op.drop_index(op.f("ix_chat_requests_chat_session_id"), table_name="chat_requests")
    op.drop_column("chat_requests", "chat_session_id")

    op.drop_index(op.f("ix_execution_steps_stage_name"), table_name="execution_steps")
    op.drop_index(op.f("ix_execution_steps_execution_session_id"), table_name="execution_steps")
    op.drop_index(op.f("ix_execution_steps_id"), table_name="execution_steps")
    op.drop_table("execution_steps")

    op.drop_index(op.f("ix_execution_sessions_status"), table_name="execution_sessions")
    op.drop_index(op.f("ix_execution_sessions_request_id"), table_name="execution_sessions")
    op.drop_index(op.f("ix_execution_sessions_chat_session_id"), table_name="execution_sessions")
    op.drop_index(op.f("ix_execution_sessions_id"), table_name="execution_sessions")
    op.drop_table("execution_sessions")

    op.drop_index(op.f("ix_chat_sessions_updated_at"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_mode"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_course_id"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_role"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_session_id"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")
