"""Add R2 storage fields

Revision ID: 5b09ebe23c76
Revises: 71dda59686db
Create Date: 2025-09-25 14:05:10.238517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b09ebe23c76'
down_revision: Union[str, Sequence[str], None] = '71dda59686db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add R2 storage support fields to files table."""
    # Add new columns for R2 storage support
    op.add_column('files', sa.Column('storage_backend', sa.String(20), default='local'))
    op.add_column('files', sa.Column('metadata_json', sa.Text(), nullable=True))

    # Add indexes for performance
    op.create_index('ix_files_storage_backend', 'files', ['storage_backend'])

    # Update existing files to have storage_backend = 'local'
    # This ensures backward compatibility
    op.execute("UPDATE files SET storage_backend = 'local' WHERE storage_backend IS NULL")


def downgrade() -> None:
    """Remove R2 storage fields."""
    # Remove indexes
    op.drop_index('ix_files_storage_backend', table_name='files')

    # Remove columns
    op.drop_column('files', 'metadata_json')
    op.drop_column('files', 'storage_backend')
