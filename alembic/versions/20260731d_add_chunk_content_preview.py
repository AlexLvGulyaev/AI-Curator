"""Add content_preview to kb_document_chunks.

Revision ID: 20260731d_add_chunk_content_preview
Revises: 20260731c_add_kb_version_git_meta
Create Date: 2026-07-31 14:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731d_add_chunk_content_preview"
down_revision: Union[str, None] = "20260731c_add_kb_version_git_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "kb_document_chunks",
        sa.Column("content_preview", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kb_document_chunks", "content_preview")
