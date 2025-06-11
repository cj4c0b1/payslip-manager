"""Add magic link authentication

Revision ID: 0002
Revises: 0001
Create Date: 2025-06-11 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade database schema."""
    # Create magic_links table
    op.create_table(
        'magic_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False, index=True),
        sa.Column('email', sa.String(length=255), nullable=False, index=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='f'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for magic_links
    op.create_index('idx_magic_link_token_valid', 'magic_links', ['token', 'is_used', 'expires_at'])
    op.create_index('idx_magic_link_expiry', 'magic_links', ['expires_at'])
    
    # Add columns to employees table
    op.add_column('employees', sa.Column('is_email_verified', sa.Boolean(), server_default='f', nullable=False))
    op.add_column('employees', sa.Column('email_verified_at', sa.DateTime(), nullable=True))
    
    # Create index on email_verified
    op.create_index('idx_employees_email_verified', 'employees', ['is_email_verified'])

def downgrade():
    """Downgrade database schema."""
    # Drop indexes first
    op.drop_index('idx_employees_email_verified', table_name='employees')
    op.drop_index('idx_magic_link_expiry', table_name='magic_links')
    op.drop_index('idx_magic_link_token_valid', table_name='magic_links')
    
    # Drop columns from employees
    op.drop_column('employees', 'email_verified_at')
    op.drop_column('employees', 'is_email_verified')
    
    # Finally drop the magic_links table
    op.drop_table('magic_links')
