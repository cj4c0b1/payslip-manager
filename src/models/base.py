"""
SQLAlchemy Base and common model mixins.
"""
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr

# Create a base class for all models
Base = declarative_base()

class TimestampMixin:
    """Mixin that adds timestamp fields to models."""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @declared_attr
    def __tablename__(cls):
        """
        Generate __tablename__ automatically.
        Convert CamelCase class name to snake_case table name.
        """
        return ''.join(['_'+i.lower() if i.isupper() else i for i in cls.__name__]).lstrip('_') + 's'
