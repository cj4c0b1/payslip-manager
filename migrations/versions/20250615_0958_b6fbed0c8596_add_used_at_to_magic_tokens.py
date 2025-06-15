"""add_used_at_to_magic_tokens

Revision ID: b6fbed0c8596
Revises: af8b10a37a56
Create Date: 2025-06-15 09:58:13.844578

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b6fbed0c8596'
down_revision = 'af8b10a37a56'
branch_labels = None
depends_on = None


def upgrade():
    # Add used_at column to magic_tokens table
    op.add_column('magic_tokens',
                 sa.Column('used_at', sa.DateTime(), nullable=True, 
                          comment='When the token was used'))
    
    # Create an index on the used_at column for faster queries
    op.create_index('idx_magic_token_used_at', 'magic_tokens', ['used_at'])


def downgrade():
    # Drop the index and column when rolling back
    op.drop_index('idx_magic_token_used_at', table_name='magic_tokens')
    op.drop_column('magic_tokens', 'used_at')
