"""
Database reset script for the Renato application.
This script will drop all existing tables and recreate them with the current schema.
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database import Base, engine, init_db

def reset_database():
    """Reset the database by dropping and recreating all tables."""
    print("🔧 Resetting database...")
    
    # Import all models to ensure they're registered with SQLAlchemy
    from src.models.employee import Employee  # noqa: F401
    from src.models.payslip import Payslip  # noqa: F401
    from src.models.earning import Earning  # noqa: F401
    from src.models.deduction import Deduction  # noqa: F401
    
    # Drop all tables
    print("🗑️  Dropping existing tables...")
    Base.metadata.drop_all(engine)
    
    # Create all tables
    print("🔄 Creating new tables...")
    Base.metadata.create_all(engine)
    
    print("✅ Database reset successfully!")
    return True

if __name__ == "__main__":
    reset_database()
