"""Add source information fields to credit card model

Revision ID: 9f3d5e7a2d4c
Revises: 6ba8de124c23
Create Date: 2023-04-20 22:58:36.773518

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f3d5e7a2d4c'
down_revision = '6ba8de124c23'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to the credit_cards table
    op.add_column('credit_cards', sa.Column('source', sa.String(length=50), nullable=True))
    op.add_column('credit_cards', sa.Column('source_url', sa.String(length=255), nullable=True))
    op.add_column('credit_cards', sa.Column('import_date', sa.DateTime(), nullable=True))


def downgrade():
    # Remove the columns if downgrading
    op.drop_column('credit_cards', 'source')
    op.drop_column('credit_cards', 'source_url')
    op.drop_column('credit_cards', 'import_date') 