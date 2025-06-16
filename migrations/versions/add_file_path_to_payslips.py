"""Add file_path to payslips table

Revision ID: 1234abcd5678
Revises: <previous_migration_id>
Create Date: 2025-03-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1234abcd5678'
down_revision = None  # Replace with the previous migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Add the file_path column to store the relative path of the PDF file
    op.add_column(
        'payslips',
        sa.Column('file_path', sa.String(512), nullable=True, comment='Relative path to the PDF file')
    )
    
    # Create an index on the file_path column for faster lookups
    op.create_index('idx_payslip_file_path', 'payslips', ['file_path'])


def downgrade():
    # Drop the index and column when rolling back
    op.drop_index('idx_payslip_file_path', table_name='payslips')
    op.drop_column('payslips', 'file_path')
