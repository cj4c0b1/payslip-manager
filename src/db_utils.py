"""
Database utility functions for the Payslip Management System.

This module provides high-level helper functions for common database operations.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from datetime import date, datetime
from decimal import Decimal
import logging

from sqlalchemy import and_, or_, func, extract
from sqlalchemy.orm import Session, Query, joinedload

from .database import (
    Session as DBSession,
    get_db_session,
    Employee,
    Payslip,
    Earning,
    Deduction,
)

# Type variables for generic functions
T = TypeVar('T')
ModelType = TypeVar('ModelType')

logger = logging.getLogger(__name__)

def get_object(
    session: Session,
    model: Type[ModelType],
    object_id: Any,
    options: Optional[list] = None
) -> Optional[ModelType]:
    """
    Get a single object by ID with optional relationship loading.
    
    Args:
        session: Database session
        model: SQLAlchemy model class
        object_id: ID of the object to retrieve
        options: List of relationship loading options (e.g., [joinedload(...)])
        
    Returns:
        The object if found, None otherwise
    """
    query = session.query(model)
    
    # Apply relationship loading options if provided
    if options:
        for option in options:
            query = query.options(option)
    
    return query.get(object_id)

def get_objects(
    session: Session,
    model: Type[ModelType],
    filters: Optional[Dict] = None,
    order_by: Optional[list] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    options: Optional[list] = None
) -> List[ModelType]:
    """
    Get multiple objects with filtering, ordering, and pagination.
    
    Args:
        session: Database session
        model: SQLAlchemy model class
        filters: Dictionary of {column: value} to filter by
        order_by: List of columns to order by (use - prefix for DESC)
        limit: Maximum number of results to return
        offset: Number of results to skip
        options: List of relationship loading options
        
    Returns:
        List of matching objects
    """
    query = session.query(model)
    
    # Apply filters if provided
    if filters:
        filter_conditions = []
        for column, value in filters.items():
            if hasattr(model, column):
                if value is None:
                    filter_conditions.append(getattr(model, column).is_(None))
                elif isinstance(value, (list, tuple, set)):
                    filter_conditions.append(getattr(model, column).in_(value))
                else:
                    filter_conditions.append(getattr(model, column) == value)
        
        if filter_conditions:
            query = query.filter(and_(*filter_conditions))
    
    # Apply ordering if provided
    if order_by:
        order_clauses = []
        for item in order_by:
            if item.startswith('-'):
                column = item[1:]
                if hasattr(model, column):
                    order_clauses.append(getattr(model, column).desc())
            else:
                if hasattr(model, item):
                    order_clauses.append(getattr(model, item).asc())
        
        if order_clauses:
            query = query.order_by(*order_clauses)
    
    # Apply relationship loading options if provided
    if options:
        for option in options:
            query = query.options(option)
    
    # Apply pagination
    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)
    
    return query.all()

def create_object(
    session: Session,
    model: Type[ModelType],
    data: Dict[str, Any],
    commit: bool = True
) -> ModelType:
    """
    Create a new object with the given data.
    
    Args:
        session: Database session
        model: SQLAlchemy model class
        data: Dictionary of {column: value} for the new object
        commit: Whether to commit the transaction
        
    Returns:
        The created object
    """
    try:
        obj = model(**data)
        session.add(obj)
        
        if commit:
            session.commit()
            session.refresh(obj)
        
        return obj
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating {model.__name__}: {str(e)}")
        raise

def update_object(
    session: Session,
    obj: ModelType,
    data: Dict[str, Any],
    commit: bool = True
) -> ModelType:
    """
    Update an existing object with the given data.
    
    Args:
        session: Database session
        obj: The object to update
        data: Dictionary of {column: value} to update
        commit: Whether to commit the transaction
        
    Returns:
        The updated object
    """
    try:
        for key, value in data.items():
            if hasattr(obj, key) and key != 'id':  # Prevent updating the ID
                setattr(obj, key, value)
        
        if commit:
            session.commit()
            session.refresh(obj)
        
        return obj
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating {obj.__class__.__name__} {obj.id}: {str(e)}")
        raise

def delete_object(
    session: Session,
    obj: ModelType,
    commit: bool = True
) -> bool:
    """
    Delete an object from the database.
    
    Args:
        session: Database session
        obj: The object to delete
        commit: Whether to commit the transaction
        
    Returns:
        True if the object was deleted, False otherwise
    """
    try:
        session.delete(obj)
        
        if commit:
            session.commit()
        
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting {obj.__class__.__name__} {obj.id}: {str(e)}")
        return False

# Employee-related functions
def get_employee_by_id(employee_id: int, session: Optional[Session] = None) -> Optional[Employee]:
    """Get an employee by ID."""
    if session is None:
        with get_db_session() as db_session:
            return db_session.query(Employee).get(employee_id)
    return session.query(Employee).get(employee_id)

def get_employee_by_cpf(cpf: str, session: Optional[Session] = None) -> Optional[Employee]:
    """Get an employee by their CPF (Brazilian ID)."""
    if session is None:
        with get_db_session() as db_session:
            return db_session.query(Employee).filter(Employee.cpf == cpf).first()
    return session.query(Employee).filter(Employee.cpf == cpf).first()

def search_employees(
    query: str,
    session: Optional[Session] = None,
    limit: int = 10
) -> List[Employee]:
    """
    Search for employees by name, email, or CPF.
    
    Args:
        query: Search term
        session: Optional database session (will create one if not provided)
        limit: Maximum number of results to return
        
    Returns:
        List of matching employees
    """
    search = f"%{query}%"
    q = Employee.query.filter(
        or_(
            Employee.first_name.ilike(search),
            Employee.last_name.ilike(search),
            Employee.email.ilike(search),
            Employee.cpf.ilike(search)
        )
    ).order_by(Employee.first_name, Employee.last_name)
    
    if limit:
        q = q.limit(limit)
    
    if session is None:
        with get_db_session() as db_session:
            return q.with_session(db_session).all()
    
    return q.all()

# Payslip-related functions
def get_payslip(
    payslip_id: int,
    session: Optional[Session] = None,
    include_relations: bool = True
) -> Optional[Payslip]:
    """
    Get a payslip by ID with optional relationship loading.
    
    Args:
        payslip_id: ID of the payslip to retrieve
        session: Optional database session
        include_relations: Whether to load related objects (employee, earnings, deductions)
        
    Returns:
        The payslip if found, None otherwise
    """
    query = Payslip.query
    
    if include_relations:
        query = query.options(
            joinedload(Payslip.employee),
            joinedload(Payslip.earnings),
            joinedload(Payslip.deductions)
        )
    
    if session is None:
        with get_db_session() as db_session:
            return query.with_session(db_session).get(payslip_id)
    
    return query.with_session(session).get(payslip_id)

def get_employee_payslips(
    employee_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None,
    session: Optional[Session] = None
) -> List[Payslip]:
    """
    Get payslips for an employee, optionally filtered by year and/or month.
    
    Args:
        employee_id: ID of the employee
        year: Optional year to filter by
        month: Optional month (1-12) to filter by
        session: Optional database session
        
    Returns:
        List of matching payslips, ordered by reference_month (newest first)
    """
    query = Payslip.query.filter(Payslip.employee_id == employee_id)
    
    if year is not None:
        query = query.filter(extract('year', Payslip.reference_month) == year)
    
    if month is not None:
        query = query.filter(extract('month', Payslip.reference_month) == month)
    
    query = query.order_by(Payslip.reference_month.desc())
    
    if session is None:
        with get_db_session() as db_session:
            return query.with_session(db_session).all()
    
    return query.all()

def get_payslips_in_date_range(
    start_date: date,
    end_date: date,
    employee_id: Optional[int] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Payslip]:
    """
    Get payslips within a date range with optional filters.
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        employee_id: Optional employee ID to filter by
        department: Optional department name to filter by
        status: Optional status to filter by
        session: Optional database session
        
    Returns:
        List of matching payslips
    """
    query = Payslip.query.join(Employee)
    
    # Apply date range filter
    query = query.filter(
        Payslip.reference_month.between(
            start_date.replace(day=1),
            end_date.replace(day=1)
        )
    )
    
    # Apply optional filters
    if employee_id is not None:
        query = query.filter(Payslip.employee_id == employee_id)
    
    if department:
        query = query.filter(Employee.department == department)
    
    if status:
        query = query.filter(Payslip.status == status)
    
    # Order by reference month (newest first) and employee name
    query = query.order_by(
        Payslip.reference_month.desc(),
        Employee.name
    )
    
    if session is None:
        with get_db_session() as db_session:
            return query.with_session(db_session).all()
    
    return query.all()

def calculate_ytd_totals(
    employee_id: int,
    as_of_date: date,
    session: Optional[Session] = None
) -> Dict[str, Decimal]:
    """
    Calculate year-to-date totals for an employee.
    
    Args:
        employee_id: ID of the employee
        as_of_date: Date to calculate YTD up to (inclusive)
        session: Optional database session
        
    Returns:
        Dictionary with YTD totals for various amounts
    """
    from sqlalchemy import func
    
    year = as_of_date.year
    
    # Create a subquery to get YTD payslips
    ytd_query = (
        Payslip.query
        .filter(
            Payslip.employee_id == employee_id,
            extract('year', Payslip.reference_month) == year,
            Payslip.reference_month <= as_of_date.replace(day=1),
            Payslip.status.in_(['approved', 'paid'])
        )
        .with_entities(
            func.coalesce(func.sum(Payslip.gross_salary), 0).label('total_gross'),
            func.coalesce(func.sum(Payslip.net_salary), 0).label('total_net'),
            func.coalesce(func.sum(Payslip.tax_deductions), 0).label('total_tax'),
            func.coalesce(func.sum(Payslip.other_deductions), 0).label('total_other_deductions')
        )
    )
    
    # Execute the query
    if session is None:
        with get_db_session() as db_session:
            result = ytd_query.with_session(db_session).first()
    else:
        result = ytd_query.with_session(session).first()
    
    # Format the results
    return {
        'gross_income': Decimal(str(result[0] or 0)),
        'net_income': Decimal(str(result[1] or 0)),
        'tax_withheld': Decimal(str(result[2] or 0)),
        'other_deductions': Decimal(str(result[3] or 0)),
        'year': year,
        'as_of_date': as_of_date
    }
