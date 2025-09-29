"""Add image variant storage paths

Revision ID: f27bd10b7ec4
Revises: 5b09ebe23c76
Create Date: 2025-09-29 17:52:08.280054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f27bd10b7ec4'
down_revision: Union[str, Sequence[str], None] = '5b09ebe23c76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add variant path columns to files table."""
    op.add_column('files', sa.Column('thumb_path', sa.String(500), nullable=True))
    op.add_column('files', sa.Column('medium_path', sa.String(500), nullable=True))


def downgrade() -> None:
    """Remove variant path columns from files table."""
    op.drop_column('files', 'medium_path')
    op.drop_column('files', 'thumb_path')
