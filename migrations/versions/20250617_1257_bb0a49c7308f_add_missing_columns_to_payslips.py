"""add_missing_columns_to_payslips

Revision ID: bb0a49c7308f
Revises: change_default_currency_to_brl
Create Date: 2025-06-17 12:57:08.444484

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'bb0a49c7308f'
down_revision = 'change_default_currency_to_brl'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to the payslips table
    with op.batch_alter_table('payslips') as batch_op:
        # Add tax_deductions column
        batch_op.add_column(sa.Column('tax_deductions', sa.Numeric(precision=12, scale=2), 
                                     server_default='0.00', nullable=True))
        
        # Add other_deductions column
        batch_op.add_column(sa.Column('other_deductions', sa.Numeric(precision=12, scale=2), 
                                     server_default='0.00', nullable=True))
        
        # Add notes column
        batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))
        
        # Add status column with default 'draft'
        batch_op.add_column(sa.Column('status', sa.String(length=20), 
                                     server_default='draft', nullable=False))
        
        # Add file_path column
        batch_op.add_column(sa.Column('file_path', sa.String(length=512), nullable=True))
        
        # Add file_hash column with index
        batch_op.add_column(sa.Column('file_hash', sa.String(length=64), nullable=True))
        batch_op.create_index('idx_payslips_file_hash', ['file_hash'], unique=True)
        
        # Rename columns to match the model
        batch_op.alter_column('gross_salary_eur', new_column_name='gross_amount_eur', 
                             existing_type=sa.Numeric(precision=12, scale=2),
                             existing_nullable=True)
        batch_op.alter_column('net_salary_eur', new_column_name='net_amount_eur',
                             existing_type=sa.Numeric(precision=12, scale=2),
                             existing_nullable=True)
        
        # Add exchange_rate_date column
        batch_op.add_column(sa.Column('exchange_rate_date', sa.Date(), nullable=True))
        
        # Add exchange_rate_source column
        batch_op.add_column(sa.Column('exchange_rate_source', sa.String(length=50), nullable=True))
        
        # Add index on status column
        batch_op.create_index('idx_payslips_status', ['status'])


def downgrade():
    with op.batch_alter_table('payslips') as batch_op:
        # Drop the index first
        batch_op.drop_index('idx_payslips_status')
        
        # Drop the file_hash index
        batch_op.drop_index('idx_payslips_file_hash')
        
        # Rename columns back to original
        batch_op.alter_column('gross_amount_eur', new_column_name='gross_salary_eur',
                             existing_type=sa.Numeric(precision=12, scale=2),
                             existing_nullable=True)
        batch_op.alter_column('net_amount_eur', new_column_name='net_salary_eur',
                             existing_type=sa.Numeric(precision=12, scale=2),
                             existing_nullable=True)
        
        # Drop the added columns
        batch_op.drop_column('exchange_rate_source')
        batch_op.drop_column('exchange_rate_date')
        batch_op.drop_column('file_hash')
        batch_op.drop_column('file_path')
        batch_op.drop_column('status')
        batch_op.drop_column('notes')
        batch_op.drop_column('other_deductions')
        batch_op.drop_column('tax_deductions')
