"""Add provider_settings to ai_configs.

Revision ID: 20260803b_add_provider_settings_to_ai_configs
Revises: 20260803_add_llm_provider_settings
Create Date: 2026-08-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c51255b_add_provider_settings_to_ai_configs"
down_revision: Union[str, None] = "20260803_add_llm_provider_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_configs",
        sa.Column(
            "provider_settings",
            sa.JSON(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_configs", "provider_settings")
