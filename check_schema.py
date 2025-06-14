"""
Check the database schema to ensure all tables are created correctly.
"""
import sqlite3
from pathlib import Path

def check_schema():
    db_path = Path("data/payslips.db")
    
    if not db_path.exists():
        print("❌ Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("📋 Database schema check:")
        print(f"Found {len(tables)} tables:")
        
        for table in sorted(tables):
            # Get table info
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            
            print(f"\nTable: {table}")
            print("Columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
        # Check for required tables
        required_tables = {'employees', 'payslips', 'earnings', 'deductions'}
        missing_tables = required_tables - set(tables)
        
        if missing_tables:
            print("\n❌ Missing tables:", ", ".join(missing_tables))
            return False
        
        print("\n✅ Database schema looks good!")
        return True
        
    except Exception as e:
        print(f"❌ Error checking database schema: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_schema()
