"""Add course_boost_enabled and course_boost_factor to retrieval_tuning.

Revision ID: 20260731g_add_course_boost_to_retrieval_tuning
Revises: 20260731f_add_version_raw_cleaned_meta
Create Date: 2026-07-31 21:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731g_add_course_boost_to_retrieval_tuning"
down_revision: Union[str, None] = "20260731f_add_version_raw_cleaned_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "retrieval_tuning",
        sa.Column("course_boost_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "retrieval_tuning",
        sa.Column("course_boost_factor", sa.Float(), nullable=False, server_default="0.15"),
    )


def downgrade() -> None:
    op.drop_column("retrieval_tuning", "course_boost_factor")
    op.drop_column("retrieval_tuning", "course_boost_enabled")
