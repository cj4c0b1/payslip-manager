"""add_exchange_rate_fields_to_payslips

Revision ID: 6db5380a8dae
Revises: c3203258fefe
Create Date: 2025-06-16 23:35:15.694211

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6db5380a8dae'
down_revision = 'c3203258fefe'
branch_labels = None
depends_on = None


def upgrade():
    # Add exchange rate fields to payslips table
    op.add_column('payslips', sa.Column('exchange_rate', sa.Numeric(precision=10, scale=6), 
                  nullable=True, comment='Exchange rate: 1 BRL = X EUR'))
    op.add_column('payslips', sa.Column('gross_amount_eur', sa.Numeric(12, 2), 
                  nullable=True, comment='Gross salary in EUR'))
    op.add_column('payslips', sa.Column('net_amount_eur', sa.Numeric(12, 2), 
                  nullable=True, comment='Net salary in EUR'))
    op.add_column('payslips', sa.Column('exchange_rate_date', sa.Date(), 
                  nullable=True, comment='Date when exchange rate was fetched'))
    op.add_column('payslips', sa.Column('exchange_rate_source', sa.String(50), 
                  nullable=True, comment='Source of the exchange rate (e.g., BCB, ECB)'))
    
    # Add index for exchange rate date for faster lookups
    op.create_index('idx_payslip_exchange_rate_date', 'payslips', ['exchange_rate_date'])


def downgrade():
    # Drop the index first
    op.drop_index('idx_payslip_exchange_rate_date', table_name='payslips')
    
    # Drop the added columns
    op.drop_column('payslips', 'exchange_rate_source')
    op.drop_column('payslips', 'exchange_rate_date')
    op.drop_column('payslips', 'net_amount_eur')
    op.drop_column('payslips', 'gross_amount_eur')
    op.drop_column('payslips', 'exchange_rate')
