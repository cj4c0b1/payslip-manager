"""Add used_at column to magic_tokens table

Revision ID: 20250614_add_used_at_to_magic_tokens
Revises: 20250614_add_cpf_department_position_to_employee
Create Date: 2025-06-14 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20250614_add_used_at_to_magic_tokens'
down_revision = '20250614_add_cpf_department_position_to_employee'
branch_labels = None
depends_on = None


def upgrade():
    # Add used_at column to magic_tokens table
    with op.batch_alter_table('magic_tokens') as batch_op:
        batch_op.add_column(
            sa.Column('used_at', sa.DateTime(), nullable=True, comment='When this token was used (UTC)')
        )


def downgrade():
    # Remove used_at column from magic_tokens table
    with op.batch_alter_table('magic_tokens') as batch_op:
        batch_op.drop_column('used_at')
