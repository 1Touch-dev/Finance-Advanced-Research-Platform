"""add price_alerts, alert_notifications, and portfolio user_id

Revision ID: a1b2c3d4e5f6
Revises: 3dd8a2786cc5
Create Date: 2026-08-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3dd8a2786cc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to portfolios table (idempotent — local.db may already
    # have this column if it was created via Base.metadata.create_all()).
    from sqlalchemy import inspect as sa_inspect
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    portfolios_cols = [c["name"] for c in inspector.get_columns("portfolios")]
    if "user_id" not in portfolios_cols:
        with op.batch_alter_table('portfolios', schema=None) as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.String(), nullable=True))
            batch_op.create_index(batch_op.f('ix_portfolios_user_id'), ['user_id'], unique=False)

    # Create price_alerts table (skip if already exists from create_all)
    existing_tables = inspector.get_table_names()
    if 'price_alerts' not in existing_tables:
        op.create_table('price_alerts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('alert_id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('ticker', sa.String(), nullable=False),
            sa.Column('alert_type', sa.String(), nullable=False),
            sa.Column('target_value', sa.Float(), nullable=False),
            sa.Column('current_value', sa.Float(), nullable=True),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('created_at', sa.String(), nullable=False),
            sa.Column('triggered_at', sa.String(), nullable=True),
            sa.Column('expires_at', sa.String(), nullable=True),
            sa.Column('notification_channels', sa.JSON(), nullable=True),
            sa.Column('note', sa.Text(), nullable=True),
            sa.Column('recurring', sa.Boolean(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('price_alerts', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_price_alerts_alert_id'), ['alert_id'], unique=True)
            batch_op.create_index(batch_op.f('ix_price_alerts_user_id'), ['user_id'], unique=False)

    # Create alert_notifications table
    if 'alert_notifications' not in existing_tables:
        op.create_table('alert_notifications',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('notification_id', sa.String(), nullable=False),
            sa.Column('alert_id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('ticker', sa.String(), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('sent_at', sa.String(), nullable=False),
            sa.Column('channel', sa.String(), nullable=False),
            sa.Column('read', sa.Boolean(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('alert_notifications', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_alert_notifications_notification_id'), ['notification_id'], unique=True)
            batch_op.create_index(batch_op.f('ix_alert_notifications_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    # Drop alert_notifications table
    with op.batch_alter_table('alert_notifications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alert_notifications_user_id'))
        batch_op.drop_index(batch_op.f('ix_alert_notifications_notification_id'))
    op.drop_table('alert_notifications')

    # Drop price_alerts table
    with op.batch_alter_table('price_alerts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_price_alerts_user_id'))
        batch_op.drop_index(batch_op.f('ix_price_alerts_alert_id'))
    op.drop_table('price_alerts')

    # Remove user_id column from portfolios table
    with op.batch_alter_table('portfolios', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_portfolios_user_id'))
        batch_op.drop_column('user_id')
