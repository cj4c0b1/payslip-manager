"""Change default currency to BRL

Revision ID: change_default_currency_to_brl
Revises: 6db5380a8dae
Create Date: 2025-06-17 12:11:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'change_default_currency_to_brl'
down_revision = '6db5380a8dae'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite doesn't support ALTER COLUMN with DEFAULT values directly
    # So we need to create a new table, copy data, drop old table, and rename
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if the column already has the correct default
    cursor = conn.execute(text("PRAGMA table_info('payslips')"))
    columns = {col[1]: col for col in cursor.fetchall()}
    
    # Check if currency column already has the correct default
    if 'currency' in columns and columns['currency'][4] == 'BRL':
        print("Currency column already has default value 'BRL'. Skipping migration.")
        return
        
    # Drop any existing temporary tables and indexes
    conn.execute(text("DROP TABLE IF EXISTS payslips_new"))
    conn.execute(text("DROP TABLE IF EXISTS payslips_old"))
    
    # Drop any existing indexes on the payslips table
    cursor = conn.execute(text("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name LIKE 'idx_payslips_%' AND tbl_name = 'payslips'
    """))
    existing_indexes = [row[0] for row in cursor.fetchall()]
    
    for index_name in existing_indexes:
        conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
    
    conn.commit()  # Commit after DROP statements
    
    # Get the current table info
    columns = inspector.get_columns('payslips')
    
    # Create a new table with the updated schema
    op.create_table(
        'payslips_new',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('reference_month', sa.Date(), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('bank_account', sa.String(50), nullable=True),
        sa.Column('payment_method', sa.String(20), nullable=False, server_default='bank_transfer'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='BRL'),
        sa.Column('gross_salary', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('net_salary', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('total_earnings', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('total_deductions', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(10, 6), nullable=True),
        sa.Column('gross_salary_eur', sa.Numeric(12, 2), nullable=True),
        sa.Column('net_salary_eur', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_earnings_eur', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_deductions_eur', sa.Numeric(12, 2), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.Index('idx_payslips_employee_id', 'employee_id'),
        sa.Index('idx_payslips_reference_month', 'reference_month'),
        sa.Index('idx_payslips_employee_month', 'employee_id', 'reference_month', unique=True),
    )
    
    # Get the list of columns in the source table
    cursor = conn.execute(text("PRAGMA table_info('payslips')"))
    source_columns = {col[1] for col in cursor.fetchall()}
    
    # Build the column lists for the INSERT and SELECT statements
    common_columns = [
        'id', 'employee_id', 'reference_month', 'issue_date', 'payment_date', 
        'bank_account', 'payment_method', 'currency', 'gross_salary', 
        'net_salary', 'total_earnings', 'total_deductions', 'created_at', 
        'updated_at', 'original_filename'
    ]
    
    # Only include columns that exist in the source table
    insert_columns = []
    select_columns = []
    
    for col in common_columns:
        if col in source_columns:
            insert_columns.append(col)
            if col == 'payment_method':
                select_columns.append(f"COALESCE({col}, 'bank_transfer')")
            elif col == 'currency':
                select_columns.append(f"COALESCE({col}, 'BRL')")
            elif col in ['gross_salary', 'net_salary', 'total_earnings', 'total_deductions']:
                select_columns.append(f"COALESCE({col}, 0.00)")
            else:
                select_columns.append(col)
    
    # Add the new EUR columns with NULL as default
    eur_columns = ['exchange_rate', 'gross_salary_eur', 'net_salary_eur', 'total_earnings_eur', 'total_deductions_eur']
    for col in eur_columns:
        insert_columns.append(col)
        select_columns.append('NULL')
    
    # Build and execute the dynamic SQL
    insert_sql = f"""
        INSERT INTO payslips_new (
            {', '.join(insert_columns)}
        )
        SELECT 
            {', '.join(select_columns)}
        FROM payslips
    """
    
    conn.execute(text(insert_sql))
    conn.commit()
    # Drop old table and rename new one
    op.drop_table('payslips')
    op.rename_table('payslips_new', 'payslips')
    
    # Drop any existing indexes on the payslips table
    cursor = conn.execute(text("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name LIKE 'idx_payslips_%' AND tbl_name = 'payslips'
    """))
    existing_indexes = [row[0] for row in cursor.fetchall()]
    
    for index_name in existing_indexes:
        conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
    
    conn.commit()  # Commit after DROP statements
    
    # Recreate necessary indexes
    with op.batch_alter_table('payslips') as batch_op:
        batch_op.create_index('idx_payslips_employee_id', ['employee_id'])
        batch_op.create_index('idx_payslips_reference_month', ['reference_month'])
        batch_op.create_index('idx_payslips_employee_month', 
                            ['employee_id', 'reference_month'], 
                            unique=True)


def downgrade():
    # Similar process to revert the changes
    conn = op.get_bind()
    
    # Check if we need to downgrade
    cursor = conn.execute(text("PRAGMA table_info('payslips')"))
    columns = {col[1]: col for col in cursor.fetchall()}
    
    # If currency column doesn't exist or already has default 'USD', no need to downgrade
    if 'currency' not in columns or (len(columns['currency']) > 4 and columns['currency'][4] == 'USD'):
        print("Currency column already has default value 'USD' or doesn't exist. Skipping downgrade.")
        return
        
    # Drop any existing temporary tables
    conn.execute(text("DROP TABLE IF EXISTS payslips_old"))
    conn.execute(text("DROP TABLE IF EXISTS payslips_new"))
    conn.commit()  # Commit after DROP statements
    
    # Create old table structure
    op.create_table(
        'payslips_old',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('reference_month', sa.Date(), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('bank_account', sa.String(50), nullable=True),
        sa.Column('payment_method', sa.String(20), nullable=False, server_default='bank_transfer'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),  # Reverting to USD
        sa.Column('gross_salary', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('net_salary', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('total_earnings', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('total_deductions', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(10, 6), nullable=True),
        sa.Column('gross_salary_eur', sa.Numeric(12, 2), nullable=True),
        sa.Column('net_salary_eur', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_earnings_eur', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_deductions_eur', sa.Numeric(12, 2), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
    )
    
    # For downgrade, only copy back columns that exist in the target table
    cursor = conn.execute(text("PRAGMA table_info('payslips_old')"))
    target_columns = {col[1] for col in cursor.fetchall()}
    
    # Build the column lists for the INSERT and SELECT statements
    common_columns = [
        'id', 'employee_id', 'reference_month', 'issue_date', 'payment_date', 
        'bank_account', 'payment_method', 'currency', 'gross_salary', 
        'net_salary', 'total_earnings', 'total_deductions', 'created_at', 
        'updated_at', 'original_filename', 'exchange_rate', 'gross_salary_eur', 
        'net_salary_eur', 'total_earnings_eur', 'total_deductions_eur'
    ]
    
    # Only include columns that exist in the target table
    insert_columns = []
    select_columns = []
    
    for col in common_columns:
        if col in target_columns:
            insert_columns.append(col)
            if col == 'currency':
                select_columns.append("CASE WHEN currency = 'BRL' THEN 'USD' ELSE currency END")
            else:
                select_columns.append(col)
    
    # Build and execute the dynamic SQL
    insert_sql = f"""
        INSERT INTO payslips_old (
            {', '.join(insert_columns)}
        )
        SELECT 
            {', '.join(select_columns)}
        FROM payslips
    """
    
    conn.execute(text(insert_sql))
    conn.commit()
    # Drop current table and rename old one back
    op.drop_table('payslips')
    op.rename_table('payslips_old', 'payslips')
    
    # Recreate indexes
    op.create_index('idx_payslips_employee_id', 'payslips', ['employee_id'])
    op.create_index('idx_payslips_reference_month', 'payslips', ['reference_month'])
    op.create_index('idx_payslips_employee_month', 'payslips', ['employee_id', 'reference_month'], unique=True)
