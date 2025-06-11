import os
import sys
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.database import get_db_session, init_db
from src.pdf_parser import process_military_payslip
from src.database import Employee, Payslip, Earning, Deduction

def get_or_create_employee(session: Session, employee_data: dict) -> Employee:
    """Get or create an employee record based on CPF."""
    if not employee_data.get('cpf'):
        raise ValueError("Employee CPF is required")
    
    # Try to find existing employee by CPF
    employee = session.query(Employee).filter(
        Employee.employee_id == employee_data['cpf']
    ).first()
    
    if not employee:
        # Create new employee
        employee = Employee(
            employee_id=employee_data['cpf'],
            name=employee_data.get('name', 'Unknown'),
            email=f"{employee_data.get('cpf', '')}@military.gov.br",
            department="Military",
            position=employee_data.get('rank', 'Military Personnel'),
            is_active=True
        )
        session.add(employee)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            # Try to get the employee again in case of race condition
            employee = session.query(Employee).filter(
                Employee.employee_id == employee_data['cpf']
            ).first()
    
    return employee

def create_payslip_record(session: Session, employee: Employee, payslip_data: dict, filename: str) -> Payslip:
    """Create a new payslip record in the database."""
    # Parse reference month (format: YYYY-MM)
    period = payslip_data.get('period', '')
    if not period:
        raise ValueError("Payslip period is required")
    
    try:
        reference_date = datetime.strptime(period + "-01", "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid period format: {period}. Expected YYYY-MM") from e
    
    # Check if payslip already exists for this employee and period
    existing = session.query(Payslip).filter(
        Payslip.employee_id == employee.id,
        Payslip.reference_month == reference_date
    ).first()
    
    if existing:
        print(f"Payslip for {employee.name} for {period} already exists (ID: {existing.id})")
        return existing
    
    # Create new payslip
    payslip = Payslip(
        employee_id=employee.id,
        reference_month=reference_date,
        issue_date=datetime.now().date(),
        payment_date=datetime.now().date(),
        bank_account=payslip_data.get('employee', {}).get('bank', ''),
        payment_method='bank_transfer',
        currency='BRL',
        gross_salary=float(payslip_data['totals']['gross']),
        net_salary=float(payslip_data['totals']['net']),
        total_earnings=float(payslip_data['totals']['gross']),
        total_deductions=float(payslip_data['totals']['deductions']),
        tax_deductions=sum(d.get('amount', 0) for d in payslip_data['deductions'] 
                          if d.get('code', '').startswith(('Z01', 'Z02'))),
        other_deductions=sum(d.get('amount', 0) for d in payslip_data['deductions'] 
                           if not d.get('code', '').startswith(('Z01', 'Z02'))),
        status='approved',
        original_filename=filename,
        notes=f"Imported from {filename} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    session.add(payslip)
    session.flush()  # Get the payslip ID for the relationships
    
    # Add earnings
    for item in payslip_data.get('earnings', []):
        earning = Earning(
            payslip_id=payslip.id,
            category=_get_earning_category(item.get('code', '')),  # Removed self. reference
            description=item.get('description', ''),
            reference=item.get('code', ''),
            amount=float(item.get('amount', 0)),
            is_taxable=not item.get('code', '').startswith('B')  # Assuming B-codes are non-taxable
        )
        session.add(earning)
    
    # Add deductions
    for item in payslip_data.get('deductions', []):
        deduction = Deduction(
            payslip_id=payslip.id,
            category=_get_deduction_category(item.get('code', '')),  # Removed self. reference
            description=item.get('description', ''),
            reference=item.get('code', ''),
            amount=float(item.get('amount', 0)),
            is_tax=item.get('code', '').startswith(('Z01', 'Z02')),  # Assuming tax-related codes
            is_pretax=False,
            tax_year=reference_date.year
        )
        session.add(deduction)
    
    try:
        session.commit()
        print(f"Successfully imported payslip for {employee.name} for {period}")
        return payslip
    except Exception as e:
        session.rollback()
        print(f"Error saving payslip: {str(e)}")
        raise

def _get_earning_category(code: str) -> str:
    """Map earning code to category."""
    if not code:
        return 'other'
    
    code_prefix = code[0] if code else ''
    category_map = {
        'B': 'salary',
        'A': 'allowance',
        'G': 'bonus',
        'H': 'overtime'
    }
    return category_map.get(code_prefix, 'other')

def _get_deduction_category(code: str) -> str:
    """Map deduction code to category."""
    if not code:
        return 'other'
    
    if code.startswith(('Z01', 'Z02')):
        return 'tax'
    elif code.startswith('Z35'):
        return 'retirement'
    elif code.startswith(('ZQ', 'ZR')):
        return 'insurance'
    return 'other'

def import_payslip(pdf_path: str):
    """Process a payslip PDF and import it into the database."""
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        return None
    
    try:
        # Initialize database if needed
        init_db()
        
        # Parse the PDF
        print(f"Processing {os.path.basename(pdf_path)}...")
        payslip_data = process_military_payslip(pdf_path)
        
        if not payslip_data or 'employee' not in payslip_data:
            print("Error: Could not parse payslip data")
            return None
        
        # Get database session
        with get_db_session() as session:
            # Get or create employee
            employee = get_or_create_employee(session, payslip_data['employee'])
            
            # Create payslip record
            payslip = create_payslip_record(
                session=session,
                employee=employee,
                payslip_data=payslip_data,
                filename=os.path.basename(pdf_path)
            )
            
            return payslip
            
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_payslip.py <path_to_pdf>")
        return 1
    
    pdf_path = sys.argv[1]
    
    # Initialize database and get a session
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'payslips.db')
    db_url = f"sqlite:///{db_path}"
    
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Initialize the database
    from src.database import init_db, get_db, get_db_session
    init_db()
    
    # Use the context manager for database sessions
    with get_db_session() as session:
        try:
            # Process the payslip
            print(f"Processing {os.path.basename(pdf_path)}...")
            payslip = import_payslip(pdf_path)
            
            if not payslip:
                print("Failed to import payslip: No data returned")
                return 1
                
            # Ensure the payslip is in the session
            session.add(payslip)
            session.commit()
            
            # Refresh the object to ensure we have all attributes
            session.refresh(payslip)
            
            # Access the ID while the session is still active
            print(f"Successfully imported payslip with ID: {payslip.id}")
            return 0
            
        except Exception as e:
            session.rollback()
            print(f"Failed to import payslip: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    sys.exit(main())
