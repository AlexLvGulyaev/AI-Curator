"""Add Git provenance fields to kb_document_versions.

Revision ID: 20260731c_add_kb_version_git_meta
Revises: 20260731b_add_retrieval_extra
Create Date: 2026-07-31 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731c_add_kb_version_git_meta"
down_revision: Union[str, None] = "20260731b_add_retrieval_extra"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen alembic_version.version_num so longer revision names fit.
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)")

    op.add_column(
        "kb_document_versions",
        sa.Column("git_commit_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "kb_document_versions",
        sa.Column("git_blob_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "kb_document_versions",
        sa.Column("git_author", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "kb_document_versions",
        sa.Column("git_commit_message", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "kb_document_versions",
        sa.Column("git_committed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kb_document_versions", "git_committed_at")
    op.drop_column("kb_document_versions", "git_commit_message")
    op.drop_column("kb_document_versions", "git_author")
    op.drop_column("kb_document_versions", "git_blob_hash")
    op.drop_column("kb_document_versions", "git_commit_hash")
