"""Add kb_document_events lifecycle table.

Revision ID: 20260731e_add_kb_document_events
Revises: 20260731d_add_chunk_content_preview
Create Date: 2026-07-31 14:02:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731e_add_kb_document_events"
down_revision: Union[str, None] = "20260731d_add_chunk_content_preview"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kb_document_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["kb_documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["kb_document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kb_document_events_document_created",
        "kb_document_events",
        ["document_id", "created_at"],
    )
    op.create_index(
        "ix_kb_document_events_version_created",
        "kb_document_events",
        ["version_id", "created_at"],
    )
    op.create_index(
        "ix_kb_document_events_event_type",
        "kb_document_events",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_kb_document_events_event_type", table_name="kb_document_events")
    op.drop_index("ix_kb_document_events_version_created", table_name="kb_document_events")
    op.drop_index("ix_kb_document_events_document_created", table_name="kb_document_events")
    op.drop_table("kb_document_events")
