"""Add CPF, department, and position to Employee

Revision ID: 20250614_add_cpf_department_position_to_employee
Revises: 20250614_add_auth_tables
Create Date: 2025-06-14 17:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20250614_add_cpf_department_position_to_employee'
down_revision = '20250614_add_auth_tables'
branch_labels = None
depends_on = None

def upgrade():
    # Add the new columns to the employees table
    with op.batch_alter_table('employees') as batch_op:
        batch_op.add_column(sa.Column('cpf', sa.String(14), unique=True, index=True, nullable=True, comment='Brazilian CPF (Cadastro de Pessoas Físicas)'))
        batch_op.add_column(sa.Column('department', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('position', sa.String(100), nullable=True))
        
        # Create an index on the cpf column
        batch_op.create_index(op.f('ix_employees_cpf'), ['cpf'], unique=True)

def downgrade():
    # Drop the columns and indexes when downgrading
    with op.batch_alter_table('employees') as batch_op:
        # Drop the index first
        batch_op.drop_index(op.f('ix_employees_cpf'))
        
        # Then drop the columns
        batch_op.drop_column('position')
        batch_op.drop_column('department')
        batch_op.drop_column('cpf')
