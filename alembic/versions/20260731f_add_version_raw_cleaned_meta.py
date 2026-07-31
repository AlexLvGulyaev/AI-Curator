"""Add raw/cleaned storage and technical metadata to KB versions, plus event timing.

Revision ID: 20260731f_add_version_raw_cleaned_meta
Revises: 20260731e_add_kb_document_events
Create Date: 2026-07-31 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731f_add_version_raw_cleaned_meta"
down_revision: Union[str, None] = "20260731e_add_kb_document_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # KB version technical metadata and raw/cleaned storage paths.
    op.add_column(
        "kb_document_versions",
        sa.Column("raw_storage_path", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "kb_document_versions",
        sa.Column("cleaned_storage_path", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "kb_document_versions",
        sa.Column("sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "kb_document_versions",
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "kb_document_versions",
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
    )

    # Lifecycle event timing for the operational console timeline.
    op.add_column(
        "kb_document_events",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "kb_document_events",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "kb_document_events",
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kb_document_events", "duration_ms")
    op.drop_column("kb_document_events", "finished_at")
    op.drop_column("kb_document_events", "started_at")

    op.drop_column("kb_document_versions", "embedding_model")
    op.drop_column("kb_document_versions", "indexed_at")
    op.drop_column("kb_document_versions", "sha256")
    op.drop_column("kb_document_versions", "cleaned_storage_path")
    op.drop_column("kb_document_versions", "raw_storage_path")
