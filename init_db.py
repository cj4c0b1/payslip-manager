"""Initialize the database with the latest schema."""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

from src.database import init_db, engine, Base
from src.models.employee import Employee

def main():
    """Initialize the database with the latest schema."""
    print("Initializing database...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    main()
