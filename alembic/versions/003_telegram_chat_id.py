"""003 — Replace push_subscription_id with telegram_chat_id in user_settings."""

from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_settings") as batch_op:
        batch_op.drop_column("push_subscription_id")
        batch_op.add_column(sa.Column("telegram_chat_id", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_settings") as batch_op:
        batch_op.drop_column("telegram_chat_id")
        batch_op.add_column(sa.Column("push_subscription_id", sa.Integer(), nullable=True))
