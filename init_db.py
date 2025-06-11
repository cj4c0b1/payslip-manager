#!/usr/bin/env python3
"""
Initialize the database and create an admin user.
"""
import os
import sys
import logging
from pathlib import Path
from getpass import getpass

# Add the project root to the Python path
project_root = str(Path(__file__).parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('init_db.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Initialize the database and create an admin user."""
    from src.database import init_db, Session, Employee, get_session
    from passlib.context import CryptContext
    
    # Initialize password hashing
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Initialize the database (drop and recreate to ensure schema is up to date)
    logger.info("Initializing database...")
    init_db(drop_existing=True)
    
    # Create a new database session
    db = Session()
    
    try:
        # Check if admin user already exists
        admin = db.query(Employee).filter(Employee.email == "admin@example.com").first()
        
        if admin:
            logger.warning("Admin user already exists. Skipping creation.")
            print("\nAdmin user already exists in the database.")
        else:
            # Create admin user
            print("\n=== Create Admin User ===")
            name = input("Full Name [Admin User]: ") or "Admin User"
            email = input("Email [admin@example.com]: ") or "admin@example.com"
            
            while True:
                password = getpass("Password: ")
                if not password:
                    print("Password cannot be empty!")
                    continue
                confirm = getpass("Confirm Password: ")
                if password == confirm:
                    break
                print("Passwords do not match!")
            
            # Create admin user with hashed password
            admin = Employee(
                employee_id="ADMIN",
                name=name,
                email=email,
                department="Administration",
                position="System Administrator",
                is_admin=True,
                is_active=True
            )
            admin.password = password  # This will hash the password
            
            db.add(admin)
            db.commit()
            logger.info(f"Created admin user: {email}")
            print("\n✅ Admin user created successfully!")
        
        # Show database info
        db_path = os.path.abspath("data/payslips.db")
        print(f"\nDatabase Location: {db_path}")
        print(f"Database Size: {os.path.getsize(db_path) / 1024:.2f} KB")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1
    finally:
        if 'session' in locals():
            session.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
