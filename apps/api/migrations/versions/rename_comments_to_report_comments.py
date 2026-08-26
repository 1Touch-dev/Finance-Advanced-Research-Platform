"""rename comments table to report_comments to avoid collision with entity comments service

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-26 12:00:00.000000

The 'comments' table (created in initial_schema) is a report-level editorial
comment model from app.models.review.Comment.  The comments_service.py uses
the same table name but expects a completely different schema (user_id,
entity_type, entity_id, etc.) for entity-level threaded comments.  Renaming
the report-editorial table to 'report_comments' frees 'comments' for the
entity-comment service's CREATE TABLE IF NOT EXISTS, which carries the correct
schema.  Existing data (if any) is preserved in report_comments.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch mode (required for SQLite ALTER TABLE operations).
    # Rename the old editorial-comments table so its name no longer conflicts
    # with the entity-comments table created by comments_service._ensure_tables.
    with op.batch_alter_table('comments', schema=None) as batch_op:
        pass  # triggers a copy under the new name via recreate

    # SQLite doesn't support RENAME TABLE via Alembic batch; use raw SQL.
    op.execute("ALTER TABLE comments RENAME TO report_comments")


def downgrade() -> None:
    op.execute("ALTER TABLE report_comments RENAME TO comments")
