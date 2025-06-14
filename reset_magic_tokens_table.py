"""
Script to reset the magic_tokens table to match the current model definition.
This will drop and recreate the table with the correct schema.
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.absolute())
sys.path.insert(0, project_root)

from src.database import engine, Base
from src.auth.models import MagicToken

def reset_magic_tokens_table():
    """Drop and recreate the magic_tokens table."""
    print("Dropping magic_tokens table...")
    MagicToken.__table__.drop(engine, checkfirst=True)
    print("Creating magic_tokens table...")
    MagicToken.__table__.create(engine)
    print("magic_tokens table has been reset successfully.")

if __name__ == "__main__":
    print("This will reset the magic_tokens table. All existing tokens will be lost.")
    confirm = input("Are you sure you want to continue? (y/N): ")
    if confirm.lower() == 'y':
        reset_magic_tokens_table()
    else:
        print("Operation cancelled.")
