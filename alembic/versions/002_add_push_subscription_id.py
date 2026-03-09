"""Add push_subscription_id to user_settings.

Revision ID: 002
Revises: 001
Create Date: 2026-03-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("push_subscription_id", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "push_subscription_id")
