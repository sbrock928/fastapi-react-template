"""Add dependent calculation columns

Revision ID: 0821dc47d72c
Revises: c0f950ba152a
Create Date: 2025-06-24 19:29:46.940646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0821dc47d72c'
down_revision: Union[str, Sequence[str], None] = 'c0f950ba152a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add dependent calculation columns to user_calculations table
    op.add_column('user_calculations', sa.Column('calculation_dependencies', sa.JSON(), nullable=True))
    op.add_column('user_calculations', sa.Column('calculation_expression', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove dependent calculation columns
    op.drop_column('user_calculations', 'calculation_expression')
    op.drop_column('user_calculations', 'calculation_dependencies')
