"""Add used_at column to magic_tokens table - fix

Revision ID: 20250614_1636_add_used_at_to_magic_tokens_fix
Revises: 20250614_add_auth_tables
Create Date: 2025-06-14 16:36:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '20250614_1636_add_used_at_to_magic_tokens_fix'
down_revision = '20250614_add_auth_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Get database connection
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if the column already exists
    columns = [col['name'] for col in inspector.get_columns('magic_tokens')]
    
    if 'used_at' not in columns:
        # Add the used_at column
        op.add_column('magic_tokens', 
                     sa.Column('used_at', sa.DateTime(), nullable=True, 
                              comment='When this token was used (UTC)'))
        print("Added 'used_at' column to 'magic_tokens' table")
    else:
        print("'used_at' column already exists in 'magic_tokens' table")


def downgrade():
    # Get database connection
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if the column exists before trying to drop it
    columns = [col['name'] for col in inspector.get_columns('magic_tokens')]
    
    if 'used_at' in columns:
        with op.batch_alter_table('magic_tokens') as batch_op:
            batch_op.drop_column('used_at')
        print("Dropped 'used_at' column from 'magic_tokens' table")
    else:
        print("'used_at' column does not exist in 'magic_tokens' table")
