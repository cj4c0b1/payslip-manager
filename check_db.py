"""Check database schema and data."""
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import inspect, text
from src.database import engine, SessionLocal

def check_schema():
    """Check the database schema."""
    print("Checking database schema...")
    
    # Create an inspector
    inspector = inspect(engine)
    
    # List all tables
    tables = inspector.get_table_names()
    print("\nTables in database:")
    for table in tables:
        print(f"- {table}")
    
    # Check employees table
    if 'employees' in tables:
        print("\nEmployees table columns:")
        for column in inspector.get_columns('employees'):
            print(f"- {column['name']}: {column['type']}")
    else:
        print("\nEmployees table not found!")

def check_data():
    """Check some sample data."""
    print("\nChecking sample data...")
    
    with SessionLocal() as session:
        # Count employees
        result = session.execute(text("SELECT COUNT(*) FROM employees"))
        count = result.scalar()
        print(f"Number of employees: {count}")
        
        # Show first few employees if any exist
        if count > 0:
            result = session.execute(text("SELECT * FROM employees LIMIT 5"))
            print("\nFirst few employees:")
            for row in result:
                print(dict(row))

if __name__ == "__main__":
    check_schema()
    check_data()
