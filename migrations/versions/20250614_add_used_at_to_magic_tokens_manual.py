"""Add used_at column to magic_tokens table - manual migration

Revision ID: 20250614_add_used_at_to_magic_tokens_manual
Revises: 20250614_add_cpf_department_position_to_employee
Create Date: 2025-06-14 16:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250614_add_used_at_to_magic_tokens_manual'
down_revision = '20250614_add_cpf_department_position_to_employee'
branch_labels = None
depends_on = None


def upgrade():
    # Add used_at column to magic_tokens table if it doesn't exist
    with op.batch_alter_table('magic_tokens') as batch_op:
        # Check if the column already exists (for idempotency)
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('magic_tokens')]
        
        if 'used_at' not in columns:
            batch_op.add_column(
                sa.Column('used_at', sa.DateTime(), nullable=True, comment='When this token was used (UTC)')
            )
            print("Added 'used_at' column to 'magic_tokens' table")
        else:
            print("'used_at' column already exists in 'magic_tokens' table")


def downgrade():
    # Remove used_at column from magic_tokens table if it exists
    with op.batch_alter_table('magic_tokens') as batch_op:
        # Check if the column exists before trying to drop it
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('magic_tokens')]
        
        if 'used_at' in columns:
            batch_op.drop_column('used_at')
            print("Dropped 'used_at' column from 'magic_tokens' table")
        else:
            print("'used_at' column does not exist in 'magic_tokens' table")
