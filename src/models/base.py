"""
Base model configuration for SQLAlchemy.
This module contains the Base class that all models should inherit from.
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import event
from datetime import datetime

# Create declarative base
Base = declarative_base()

# Set up event listeners for timestamps
@event.listens_for(Base, 'before_insert', propagate=True)
def set_created_at(mapper, connection, target):
    """Set created_at and updated_at timestamps on insert."""
    if hasattr(target, 'created_at'):
        target.created_at = datetime.utcnow()
    if hasattr(target, 'updated_at'):
        target.updated_at = datetime.utcnow()

@event.listens_for(Base, 'before_update', propagate=True)
def set_updated_at(mapper, connection, target):
    """Set updated_at timestamp on update."""
    if hasattr(target, 'updated_at'):
        target.updated_at = datetime.utcnow()
