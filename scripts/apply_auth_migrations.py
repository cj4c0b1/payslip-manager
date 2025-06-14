"""
Script to apply authentication-related database migrations directly.
This is used as an alternative to Alembic for applying schema changes.
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database import DATABASE_URL

def apply_migrations():
    """Apply database migrations for authentication system."""
    print("Applying authentication database migrations...")
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if magic_tokens table already exists
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='magic_tokens'")
        ).fetchone()
        
        if result is None:
            print("Creating magic_tokens table...")
            # Create magic_tokens table
            session.execute(text("""
                CREATE TABLE magic_tokens (
                    id INTEGER NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    token_hash VARCHAR(64) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    used BOOLEAN NOT NULL DEFAULT '0',
                    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
                    user_agent VARCHAR(255),
                    ip_address VARCHAR(45),
                    PRIMARY KEY (id),
                    UNIQUE (token_hash)
                )
            """))
            
            # Create indexes
            session.execute(text("""
                CREATE INDEX idx_magic_token_email ON magic_tokens (email)
            
            """))
            session.execute(text("""
                CREATE INDEX idx_magic_token_expires ON magic_tokens (expires_at)
            """))
            session.execute(text("""
                CREATE INDEX idx_magic_token_used ON magic_tokens (used)
            """))
            
            print("magic_tokens table created successfully.")
        
        # Check if auth columns exist in employees table
        result = session.execute(
            text("PRAGMA table_info(employees)")
        ).fetchall()
        
        column_names = [row[1] for row in result]
        
        # Add missing columns to employees table
        if 'is_active' not in column_names:
            print("Adding is_active column to employees table...")
            session.execute(text("""
                ALTER TABLE employees ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1
            """))
        
        if 'last_login_at' not in column_names:
            print("Adding last_login_at column to employees table...")
            session.execute(text("""
                ALTER TABLE employees ADD COLUMN last_login_at DATETIME
            """))
        
        if 'failed_login_attempts' not in column_names:
            print("Adding failed_login_attempts column to employees table...")
            session.execute(text("""
                ALTER TABLE employees 
                ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0
            """))
        
        if 'account_locked_until' not in column_names:
            print("Adding account_locked_until column to employees table...")
            session.execute(text("""
                ALTER TABLE employees ADD COLUMN account_locked_until DATETIME
            """))
        
        if 'password_reset_token' not in column_names:
            print("Adding password_reset_token column to employees table...")
            session.execute(text("""
                ALTER TABLE employees ADD COLUMN password_reset_token VARCHAR(100)
            """))
        
        if 'password_reset_token_expires' not in column_names:
            print("Adding password_reset_token_expires column to employees table...")
            session.execute(text("""
                ALTER TABLE employees ADD COLUMN password_reset_token_expires DATETIME
            """))
        
        # Create indexes on employees table if they don't exist
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_employee_email'")
        ).fetchone()
        
        if result is None:
            print("Creating index on email column...")
            session.execute(text("""
                CREATE INDEX idx_employee_email ON employees (email)
            """))
        
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_employee_is_active'")
        ).fetchone()
        
        if result is None:
            print("Creating index on is_active column...")
            session.execute(text("""
                CREATE INDEX idx_employee_is_active ON employees (is_active)
            """))
        
        session.commit()
        print("Database migrations applied successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"Error applying migrations: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    apply_migrations()
