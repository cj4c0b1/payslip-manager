"""Add authentication tables

Revision ID: 20250614_add_auth_tables
Revises: 
Create Date: 2025-06-14 11:52:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20250614_add_auth_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create magic_tokens table
    op.create_table(
        'magic_tokens',
        sa.Column('id', sa.Integer(), nullable=False, comment='Primary key'),
        sa.Column('email', sa.String(length=100), nullable=False, comment='Email address the token was sent to'),
        sa.Column('token_hash', sa.String(length=64), nullable=False, comment='Hashed token value for security'),
        sa.Column('expires_at', sa.DateTime(), nullable=False, comment='When this token expires (UTC)'),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.text('0'), comment='Whether this token has been used'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='When this token was created (UTC)'),
        sa.Column('user_agent', sa.String(length=255), nullable=True, comment='User agent from the login request'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='IP address from the login request'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    
    # Add indexes for magic_tokens
    op.create_index('idx_magic_token_email', 'magic_tokens', ['email'], unique=False)
    op.create_index('idx_magic_token_expires', 'magic_tokens', ['expires_at'], unique=False)
    op.create_index('idx_magic_token_used', 'magic_tokens', ['used'], unique=False)
    
    # Add authentication columns to employees table
    with op.batch_alter_table('employees') as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1'), comment='Whether the user account is active'))
        batch_op.add_column(sa.Column('last_login_at', sa.DateTime(), nullable=True, comment='Timestamp of last successful login'))
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default=sa.text('0'), comment='Number of consecutive failed login attempts'))
        batch_op.add_column(sa.Column('account_locked_until', sa.DateTime(), nullable=True, comment='Timestamp until which the account is locked'))
        batch_op.add_column(sa.Column('password_reset_token', sa.String(length=100), nullable=True, comment='Password reset token'))
        batch_op.add_column(sa.Column('password_reset_token_expires', sa.DateTime(), nullable=True, comment='When the password reset token expires'))
        
        # Add indexes for authentication fields
        batch_op.create_index('idx_employee_email', ['email'], unique=True)
        batch_op.create_index('idx_employee_is_active', ['is_active'], unique=False)


def downgrade():
    # Remove indexes
    op.drop_index('idx_magic_token_email', table_name='magic_tokens')
    op.drop_index('idx_magic_token_expires', table_name='magic_tokens')
    op.drop_index('idx_magic_token_used', table_name='magic_tokens')
    
    with op.batch_alter_table('employees') as batch_op:
        batch_op.drop_index('idx_employee_email')
        batch_op.drop_index('idx_employee_is_active')
        
        # Remove columns
        batch_op.drop_column('password_reset_token_expires')
        batch_op.drop_column('password_reset_token')
        batch_op.drop_column('account_locked_until')
        batch_op.drop_column('failed_login_attempts')
        batch_op.drop_column('last_login_at')
        batch_op.drop_column('is_active')
    
    # Drop magic_tokens table
    op.drop_table('magic_tokens')
