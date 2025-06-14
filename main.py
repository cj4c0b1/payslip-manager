import os
import base64
import hashlib
import hmac
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Payslip Manager",
    page_icon="💰",
    layout="centered"
)

import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from pathlib import Path
import shutil
from io import BytesIO
import logging
from typing import Optional, Tuple, Dict, Any

# Security imports
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('payslip_manager.log')
    ]
)
logger = logging.getLogger(__name__)

# Security configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Get secrets from Streamlit's secrets
SECRET_KEY = st.secrets.get("SECRET_KEY", "default-insecure-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hashed password."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user."""
    try:
        logger.debug(f"Attempting to authenticate user: {username}")
        
        # Get user from secrets (in production, use a database)
        stored_username = st.secrets.get("authentication", {}).get("username")
        stored_password = st.secrets.get("authentication", {}).get("password")
        
        if not stored_username or not stored_password:
            logger.error("Authentication credentials not configured in secrets.toml")
            return False
            
        logger.debug(f"Stored username: {stored_username}")
        logger.debug(f"Stored password hash: {'*' * 10}{stored_password[-4:] if stored_password else 'None'}")
        
        if not hmac.compare_digest(username, stored_username):
            logger.warning(f"Username mismatch: '{username}' != '{stored_username}'")
            return False
        
        logger.debug("Username matches, verifying password...")
        is_valid = verify_password(password, stored_password)
        
        if is_valid:
            logger.info(f"User '{username}' authenticated successfully")
        else:
            logger.warning(f"Invalid password for user: {username}")
            
        return is_valid
    except Exception as e:
        logger.error(f"Authentication error for user '{username}': {str(e)}", exc_info=True)
        return False

def check_authentication() -> bool:
    """Check if user is authenticated."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    return st.session_state.authenticated

def login_form() -> bool:
    """Display login form and handle authentication."""
    logger.debug("Rendering login form")
    
    # Set page title and header
    st.title("🔒 Payslip Manager Login")
    st.markdown("Please sign in with your credentials or request a magic link.")
    
    # Create tabs for different login methods
    tab1, tab2 = st.tabs(["Sign In with Password", "Sign In with Magic Link"])
    
    with tab1:
        with st.form("password_login_form", clear_on_submit=True):
            st.subheader("Sign In with Password")
            
            # Username and password fields
            col1, col2 = st.columns([1, 1])
            with col1:
                username = st.text_input("Username", key="login_username", placeholder="Enter your username")
            with col2:
                password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
            
            # Login button
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            
            # Handle form submission
            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password")
                    logger.warning("Login attempt with empty username or password")
                    return False
                    
                logger.info(f"Password login attempt for user: {username}")
                
                if authenticate_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    logger.info(f"User {username} authenticated successfully")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
                    logger.warning(f"Failed password login attempt for user: {username}")
    
    with tab2:
        with st.form("magic_link_form", clear_on_submit=True):
            st.subheader("Sign In with Magic Link")
            st.info("Enter your email address and we'll send you a secure login link.")
            
            email = st.text_input("Email Address", key="magic_link_email", 
                                placeholder="your.email@example.com")
            
            submitted = st.form_submit_button("Send Magic Link", type="secondary", use_container_width=True)
            
            if submitted:
                if not email:
                    st.error("Please enter your email address")
                    return False
                    
                logger.info(f"Magic link requested for email: {email}")
                
                try:
                    # Import the auth service context manager
                    from src.auth.service import auth_service_scope
                    from fastapi import Request
                    
                    # Get user agent and IP address
                    user_agent = st.query_params.get("user_agent", [""])[0]
                    ip_address = st.query_params.get("ip", [""])[0]
                    
                    # Use the auth service within a context manager for proper session handling
                    with auth_service_scope() as auth_service:
                        # Send magic link
                        email_sent = auth_service.send_magic_link(
                            email=email,
                            user_agent=user_agent,
                            ip_address=ip_address
                        )
                    
                    if email_sent:
                        st.success("✅ A magic link has been sent to your email!")
                        st.info("Please check your inbox and click the link to sign in.")
                        logger.info(f"Magic link sent to {email}")
                    else:
                        st.error("❌ Failed to send magic link. Please try again later.")
                        logger.error(f"Failed to send magic link to {email}")
                        
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
                    logger.error(f"Error sending magic link to {email}: {str(e)}", exc_info=True)
    
    # Add some spacing and a divider
    st.markdown("---")
    
    # Add a note about secure login
    st.markdown("""
    <div style='font-size: 0.9em; color: #666; text-align: center;'>
        For security reasons, please log out when you're done.
    </div>
    """, unsafe_allow_html=True)
    
    # Add some spacing and a divider
    st.markdown("---")
    
    # Add a note about secure login
    st.markdown("""
    <div style='font-size: 0.9em; color: #666; text-align: center;'>
        For security reasons, please log out when you're done.
    </div>
    """, unsafe_allow_html=True)
    
    return False

def require_auth():
    """Decorator to require authentication for a Streamlit page."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not check_authentication():
                if login_form():
                    return func(*args, **kwargs)
                return
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Import local modules
from src.database import (
    init_db, get_session, get_db_session, get_db, Base, engine, Session
)
from src.models.employee import Employee
from src.models.payslip import Payslip
from src.models.earning import Earning
from src.models.deduction import Deduction
from src.pdf_parser import process_payslip, process_military_payslip, MilitaryPayslipParser
from sqlalchemy import func

# Initialize database if not exists
if not Path("data/payslips.db").exists():
    init_db()

# Custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .stAlert {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

class PayslipManager:
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
        self.Session = Session  # Use the scoped session factory
        
    def get_session(self):
        """
        Get a new database session context manager.
        
        Returns:
            context manager that yields a database session
        """
        return get_db_session()
        
    def get_db(self):
        """
        Get a database session generator for FastAPI-style dependency injection.
        
        Yields:
            Session: A database session
            
        Note:
            This is intended for use with FastAPI's Depends()
        """
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()
        
    def _get_or_create_employee(self, session, employee_info):
        """
        Get an existing employee or create a new one if they don't exist.
        Matches the behavior of import_payslip.py for consistency.
        
        Args:
            session: SQLAlchemy session for database operations
            employee_info: Dictionary containing employee information
                - cpf: The employee's CPF (Brazilian ID)
                - employee_id: The employee ID (if available)
                - name: The employee's name
                - department: The employee's department (optional)
                - position: The employee's position (optional)
                
        Returns:
            Employee: The existing or newly created employee
            
        Raises:
            ValueError: If no valid employee ID or CPF is provided
        """
        logger = logging.getLogger(__name__)
        
        # Get CPF and employee_id from the employee info
        cpf = employee_info.get('cpf')
        employee_id = employee_info.get('employee_id')
        
        # Log the input for debugging
        logger.debug(f"Looking up employee with CPF: {cpf}, employee_id: {employee_id}")
        
        # If we have a CPF, use that as the primary identifier
        if cpf:
            # Try exact CPF match first
            employee = session.query(Employee).filter(
                Employee.cpf == cpf
            ).first()
            
            if employee:
                logger.debug(f"Found employee by CPF: {cpf}")
                return employee
                
            # Try with CPF_ prefix for backward compatibility
            prefixed_cpf = f"CPF_{cpf}"
            employee = session.query(Employee).filter(
                Employee.cpf == prefixed_cpf
            ).first()
            
            if employee:
                logger.debug(f"Found employee by prefixed CPF: {prefixed_cpf}")
                return employee
        
        # If we have an employee_id but no CPF match, try that
        if employee_id and employee_id != cpf and employee_id != f"CPF_{cpf}":
            employee = session.query(Employee).filter(
                Employee.id == employee_id
            ).first()
            
            if employee:
                logger.debug(f"Found employee by ID: {employee_id}")
                return employee
        
        # If we get here, we need to create a new employee
        # Use CPF as the identifier if available
        new_employee_cpf = cpf if cpf else employee_id
        
        if not new_employee_cpf:
            raise ValueError(
                "Could not determine employee identifier. "
                f"CPF: {cpf}, employee_id: {employee_id}"
            )
        
        # Create new employee
        logger.info(f"Creating new employee with CPF: {new_employee_cpf}")
        
        # Split name into first and last name if available
        name = employee_info.get('name', 'Unknown')
        if name == 'Unknown' and 'email' in employee_info:
            # Try to get name from email if name is not provided
            name = employee_info['email'].split('@')[0].replace('.', ' ').title()
            
        name_parts = name.split(' ', 1)
        first_name = name_parts[0] if name_parts else 'Unknown'
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Create the employee with the correct fields
        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            email=employee_info.get('email', f"{new_employee_cpf}@example.com"),
            cpf=new_employee_cpf,
            is_active=True
        )
        
        # Add department and position if they exist in employee_info
        if 'department' in employee_info:
            employee.department = employee_info['department']
        if 'position' in employee_info:
            employee.position = employee_info['position']
        
        try:
            session.add(employee)
            session.flush()
            logger.info(f"Created new employee: {employee.id} - {employee.first_name} {employee.last_name}")
            return employee
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating employee: {str(e)}", exc_info=True)
            raise

    def _is_safe_filename(self, filename: str) -> bool:
        """Check if the filename is safe to use.
        
        Args:
            filename: The filename to check
            
        Returns:
            bool: True if the filename is safe, False otherwise
        """
        # Check for path traversal attempts
        if '..' in filename or filename.startswith('/') or '~' in filename:
            logger.warning(f"Rejected filename with path traversal attempt: {filename}")
            return False
            
        # Check for allowed extensions (only PDF)
        if not filename.lower().endswith('.pdf'):
            logger.warning(f"Rejected file with invalid extension: {filename}")
            return False
            
        # Check for suspicious characters
        if any(c in filename for c in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']):
            logger.warning(f"Rejected filename with suspicious characters: {filename}")
            return False
            
        # Check filename length
        if len(filename) > 255:
            logger.warning(f"Rejected filename that's too long: {filename}")
            return False
            
        return True
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename to be safe for storage.
        
        Args:
            filename: The original filename
            
        Returns:
            str: A sanitized version of the filename
        """
        # Remove any path information
        basename = os.path.basename(filename)
        
        # Replace or remove unsafe characters
        safe_name = "".join(c if c.isalnum() or c in ' ._-' else '_' for c in basename)
        
        # Add timestamp to prevent overwrites and add some randomness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(os.urandom(8)).hexdigest()[:8]
        name, ext = os.path.splitext(safe_name)
        return f"{name}_{timestamp}_{random_suffix}{ext}"
    
    def save_uploaded_files(self, uploaded_files) -> list:
        """Securely save uploaded files to the upload directory.
        
        Args:
            uploaded_files: List of uploaded file objects from Streamlit
            
        Returns:
            list: List of paths to the saved files
            
        Raises:
            ValueError: If a file is not safe to save
        """
        saved_files = []
        
        # Ensure upload directory exists with secure permissions (0o700 = owner-only rwx)
        self.upload_dir.mkdir(mode=0o700, exist_ok=True, parents=True)
        
        for uploaded_file in uploaded_files:
            original_name = uploaded_file.name
            
            # Validate the filename
            if not self._is_safe_filename(original_name):
                logger.warning(f"Rejected potentially unsafe filename: {original_name}")
                st.warning(f"Skipping file with invalid name: {original_name}")
                continue
            
            # Sanitize the filename
            safe_name = self._sanitize_filename(original_name)
            file_path = self.upload_dir / safe_name
            
            try:
                # Read the file content first to check size
                file_content = uploaded_file.getvalue()
                
                # Check file size (max 10MB)
                max_size = 10 * 1024 * 1024  # 10MB
                if len(file_content) > max_size:
                    raise ValueError(f"File {original_name} exceeds maximum size of 10MB")
                
                # Check if the content looks like a PDF (first 4 bytes should be '%PDF')
                if len(file_content) > 4 and not file_content.startswith(b'%PDF'):
                    raise ValueError(f"File {original_name} does not appear to be a valid PDF")
                
                # Write the file with secure permissions (0o600 = owner-only rw-)
                with open(file_path, "wb") as f:
                    f.write(file_content)
                
                # Set secure file permissions
                os.chmod(file_path, 0o600)
                
                # Verify the file was written and is not empty
                if not file_path.is_file() or file_path.stat().st_size == 0:
                    raise IOError(f"Failed to save file: {safe_name}")
                
                saved_files.append(str(file_path))
                logger.info(f"Saved uploaded file: {file_path}")
                
            except Exception as e:
                # Clean up partially written files on error
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception as cleanup_error:
                        logger.error(f"Failed to clean up file after error: {cleanup_error}")
                logger.error(f"Error saving file {original_name}: {e}")
                st.error(f"❌ Error saving file {original_name}: {str(e)}")
                
        return saved_files

    def _is_military_payslip(self, file_path):
        """Check if the PDF is a military payslip by looking for military-specific patterns."""
        try:
            with open(file_path, 'rb') as f:
                # Look for military-specific keywords in the first few KB of the file
                content = f.read(4096).decode('latin-1', errors='ignore')
                military_keywords = ['EXÉRCITO BRASILEIRO', 'MINISTÉRIO DA DEFESA', 'PAGAMENTO DE PESSOAL']
                return any(keyword in content for keyword in military_keywords)
        except Exception:
            return False

    def _process_uploaded_file(self, uploaded_file):
        """Process an uploaded PDF file and extract payslip data."""
        temp_path = None
        try:
            # Save the uploaded file temporarily
            temp_path = self.upload_dir / uploaded_file.name
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Process the payslip
            with get_db_session() as session:
                if self._is_military_payslip(temp_path):
                    st.info("Detected military payslip. Processing with military parser...")
                    result = process_military_payslip(temp_path)
                    
                    # Convert the result to match the expected format
                    if result and 'employee' in result and 'payslip' in result:
                        # Create or update employee
                        employee = session.query(Employee).filter_by(
                            employee_id=result['employee'].get('employee_id')
                        ).first()
                        
                        if not employee:
                            employee = Employee(
                                employee_id=result['employee'].get('employee_id'),
                                name=result['employee'].get('name'),
                                cpf=result['employee'].get('cpf')
                            )
                            session.add(employee)
                            session.commit()
                        
                        # Create payslip
                        payslip = Payslip(
                            employee_id=employee.id,
                            reference_period=result['payslip'].get('reference_period'),
                            gross_amount=result['payslip'].get('totals', {}).get('gross', 0),
                            deductions_amount=abs(result['payslip'].get('totals', {}).get('deductions', 0)),
                            net_amount=result['payslip'].get('totals', {}).get('net', 0),
                            file_name=uploaded_file.name,
                            file_hash=hash(temp_path.read_bytes())  # Simple hash for deduplication
                        )
                        session.add(payslip)
                        session.commit()
                        
                        # Add earnings and deductions
                        for earning in result['payslip'].get('earnings', []):
                            e = Earning(
                                payslip_id=payslip.id,
                                code=earning.get('code'),
                                description=earning.get('description'),
                                amount=earning.get('amount', 0),
                                reference=earning.get('reference')
                            )
                            session.add(e)
                        
                        for deduction in result['payslip'].get('deductions', []):
                            d = Deduction(
                                payslip_id=payslip.id,
                                code=deduction.get('code'),
                                description=deduction.get('description'),
                                amount=abs(deduction.get('amount', 0)),  # Store as positive
                                reference=deduction.get('reference')
                            )
                            session.add(d)
                        
                        session.commit()
                        result = {
                            'success': True,
                            'employee': f"{employee.first_name} {employee.last_name}".strip(),
                            'period': payslip.reference_period,
                            'net_amount': payslip.net_amount
                        }
                else:
                    result = process_payslip(temp_path, session)
            
            return result
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            raise
            
        finally:
            # Clean up the temporary file
            if temp_path and temp_path.exists():
                temp_path.unlink()

    def process_payslips(self, file_paths):
        """
        Process multiple payslip files and save them to the database.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            dict: Results of the processing operation with counts and status
        """
        results = {
            'total': len(file_paths),
            'processed': 0,
            'skipped': [],
            'success': []
        }

        if not file_paths:
            st.warning("No files to process")
            return results

        # Create a progress bar
        progress_bar = st.progress(0)
        total_files = len(file_paths)

        for idx, file_path in enumerate(file_paths):
            file_name = os.path.basename(file_path)
            progress = (idx + 1) / total_files
            progress_bar.progress(progress)
            
            try:
                # Process the payslip
                with st.spinner(f"Processing {file_name}..."):
                    payslip_data = process_payslip(file_path)
                    if not payslip_data:
                        results['skipped'].append((file_name, "Failed to parse payslip"))
                        st.warning(f"⚠️ Could not parse {file_name}")
                        continue

                    # Save to database using a new session
                    with self.get_session() as session:
                        try:
                            success = self._save_to_database(session, payslip_data)
                            if not success:
                                results['skipped'].append((file_name, "Database save failed"))
                                st.error(f"❌ Failed to save {file_name} to database")
                                continue
                                
                            # Commit the transaction
                            session.commit()
                            results['success'].append(file_name)
                            results['processed'] += 1
                            
                            # Move processed file to archive
                            archive_dir = self.upload_dir / "processed"
                            archive_dir.mkdir(exist_ok=True)
                            
                            # Create a timestamped subdirectory for better organization
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            timestamp_dir = archive_dir / timestamp
                            timestamp_dir.mkdir(exist_ok=True)
                            
                            # Move the file
                            dest_path = timestamp_dir / os.path.basename(file_path)
                            shutil.move(file_path, dest_path)
                            
                            st.success(f"✅ Successfully processed {file_name}")
                            
                        except Exception as db_error:
                            # Rollback on error
                            session.rollback()
                            error_msg = str(db_error)
                            results['skipped'].append((file_name, f"Database error: {error_msg}"))
                            st.error(f"❌ Database error processing {file_name}: {error_msg}")
                            # Log the full error for debugging
                            import traceback
                            st.error(f"Error details: {traceback.format_exc()}")
                            continue
                            
            except Exception as e:
                error_msg = str(e)
                results['skipped'].append((file_name, f"Processing error: {error_msg}"))
                st.error(f"❌ Error processing {file_name}: {error_msg}")
                # Log the full error for debugging
                import traceback
                st.error(f"Error details: {traceback.format_exc()}")
                continue

        return results

    def cleanup_database(self, session, days_old=30, confirm=False):
        """
        Clean up old database records and optimize the database.
        
        Args:
            session: SQLAlchemy session
            days_old: Number of days to keep (records older than this will be deleted)
            confirm: If False, will only show what would be deleted
            
        Returns:
            dict: Results of the cleanup operation
        """
        from datetime import datetime, timedelta
        import os
        
        results = {
            'backup_created': False,
            'records_deleted': 0,
            'tables_optimized': [],
            'database_size_before': 0,
            'database_size_after': 0,
            'error': None
        }
        
        try:
            # Get database file size before cleanup
            db_path = "data/payslips.db"
            if os.path.exists(db_path):
                results['database_size_before'] = os.path.getsize(db_path)
            
            if not confirm:
                # Just show what would be deleted
                cutoff_date = datetime.now().date() - timedelta(days=days_old)
                old_payslips = session.query(Payslip).filter(
                    Payslip.reference_month < cutoff_date
                ).count()
                
                results['records_to_delete'] = old_payslips
                return results
                
            # Create a backup
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(db_path):
                import shutil
                shutil.copy2(db_path, backup_path)
                results['backup_created'] = True
                results['backup_path'] = backup_path
            
            # Delete old records
            cutoff_date = datetime.now().date() - timedelta(days=days_old)
            
            # Delete related records first (earnings, deductions)
            old_payslips = session.query(Payslip).filter(
                Payslip.reference_month < cutoff_date
            ).all()
            
            for payslip in old_payslips:
                # Delete related records
                session.query(Earning).filter(Earning.payslip_id == payslip.id).delete()
                session.query(Deduction).filter(Deduction.payslip_id == payslip.id).delete()
                # Delete the payslip
                session.delete(payslip)
            
            results['records_deleted'] = len(old_payslips)
            
            # Optimize the database
            if session.bind.dialect.name == 'sqlite':
                session.execute('VACUUM')
                results['tables_optimized'].append('VACUUM executed')
            
            # Get database file size after cleanup
            if os.path.exists(db_path):
                results['database_size_after'] = os.path.getsize(db_path)
            
            session.commit()
            return results
            
        except Exception as e:
            session.rollback()
            results['error'] = str(e)
            return results
        
    def _save_to_database(self, session, payslip_data):
        """
        Save parsed payslip data to the database.
        
        Args:
            session: SQLAlchemy session
            payslip_data: Dictionary containing payslip data with 'employee' and 'payment' keys
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            if not payslip_data:
                raise ValueError("No payslip data provided")
                
            employee_info = payslip_data.get('employee', {})
            payment_info = payslip_data.get('payment', {})
            
            # Validate required fields with more detailed error messages
            if not employee_info:
                raise ValueError("No employee information found in the payslip")
                
            # Log the employee info for debugging
            logger = logging.getLogger(__name__)
            logger.debug(f"Raw employee info: {employee_info}")
            
            # Try to get employee_id, fallback to CPF if not available
            employee_id = employee_info.get('employee_id')
            cpf = employee_info.get('cpf')
            
            if not employee_id and not cpf:
                # Try to extract CPF from the raw text as a last resort
                cpf_match = re.search(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', str(payslip_data))
                if cpf_match:
                    cpf = cpf_match.group(1)
                    logger.warning(f"Extracted CPF from raw text as fallback: {cpf}")
            
            if not employee_id and not cpf:
                raise ValueError(
                    "Could not extract employee ID or CPF from the payslip. "
                    f"Employee info available: {dict(employee_info)}. "
                    "Please ensure the payslip contains a valid employee ID or CPF."
                )
                
            # Use CPF as employee_id if employee_id is not available
            identifier = employee_id if employee_id else f"CPF_{cpf}"
            employee_info['employee_id'] = identifier  # Update with the identifier we'll use
            logger.info(f"Using employee identifier: {identifier}")
            
            # Get reference period from the main payslip data (not payment_info)
            reference_period = payslip_data.get('period') or payment_info.get('reference_month')
            
            if not reference_period:
                raise ValueError(
                    "Could not determine the reference month from the payslip. "
                    "Please ensure the payslip contains a valid reference date."
                )
            
            logger.info(f"Processing reference period: {reference_period} (type: {type(reference_period)})")
                
            # Convert reference_period to datetime.date if it's a string
            if isinstance(reference_period, str):
                try:
                    # Clean the string (remove any whitespace or quotes)
                    ref_str = reference_period.strip().strip('"\'')
                    
                    # Try different date formats
                    for fmt in ["%Y-%m-%d", "%Y-%m", "%m/%Y"]:
                        try:
                            reference_date = datetime.strptime(ref_str, fmt).date()
                            # If format was YYYY-MM or MM/YYYY, set day to 1
                            if fmt in ["%Y-%m", "%m/%Y"]:
                                reference_date = reference_date.replace(day=1)
                            logger.info(f"Successfully parsed date '{ref_str}' with format '{fmt}': {reference_date}")
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format matched, try to extract date parts from the string
                        month_year_match = re.search(r'(?P<month>\d{1,2})/(?P<year>\d{4})', ref_str)
                        if month_year_match:
                            month = int(month_year_match.group('month'))
                            year = int(month_year_match.group('year'))
                            reference_date = date(year, month, 1)
                            logger.info(f"Extracted date from pattern MM/YYYY: {reference_date}")
                        else:
                            raise ValueError(f"Date format not recognized: {ref_str}")
                            
                except Exception as e:
                    logger.error(f"Error parsing reference period '{reference_period}': {e}")
                    raise ValueError(
                        f"Invalid reference period format: {reference_period}. "
                        "Expected formats: MM/YYYY, YYYY-MM, or YYYY-MM-DD"
                    ) from e
            elif hasattr(reference_period, 'date'):
                # If it's already a datetime or date object
                reference_date = reference_period.date() if hasattr(reference_period, 'date') else reference_period
                logger.info(f"Using existing date object: {reference_date}")
            else:
                raise ValueError(f"Unexpected reference period type: {type(reference_period)}")
            
            # Ensure we have a valid date object
            if not isinstance(reference_date, date):
                raise ValueError(f"Failed to parse a valid date from: {reference_period}")
                
            # Get or create employee
            employee = self._get_or_create_employee(session, employee_info)
            
            # Check for duplicate payslip using the formatted reference date
            existing_payslip = session.query(Payslip).filter(
                Payslip.employee_id == employee.id,
                func.strftime('%Y-%m', Payslip.reference_month) == reference_date.strftime('%Y-%m')
            ).first()
            
            if existing_payslip:
                st.warning(
                    f"⚠️ Payslip for {employee.first_name} {employee.last_name} "
                    f"({payment_info['reference_month'].strftime('%B %Y')}) already exists. Skipping..."
                )
                return False

            # Helper function to parse dates from various formats
            def parse_date(date_str):
                if not date_str:
                    return None
                if isinstance(date_str, date):
                    return date_str
                if isinstance(date_str, datetime):
                    return date_str.date()
                    
                # Try common date formats
                date_formats = [
                    '%Y-%m-%d',  # YYYY-MM-DD
                    '%d/%m/%Y',  # DD/MM/YYYY
                    '%m/%d/%Y',  # MM/DD/YYYY
                    '%Y%m%d',    # YYYYMMDD
                    '%d-%m-%Y',  # DD-MM-YYYY
                    '%m-%d-%Y'   # MM-DD-YYYY
                ]
                
                for fmt in date_formats:
                    try:
                        return datetime.strptime(str(date_str).strip(), fmt).date()
                    except (ValueError, AttributeError):
                        continue
                
                logger.warning(f"Could not parse date: {date_str}")
                return None
            
            # Parse issue_date and payment_date
            issue_date = parse_date(payment_info.get('issue_date')) or datetime.now().date()
            payment_date = parse_date(payment_info.get('payment_date')) or datetime.now().date()
            
            # Log the dates being used
            logger.info(f"Using dates - issue_date: {issue_date} (type: {type(issue_date)}), "
                      f"payment_date: {payment_date} (type: {type(payment_date)})")
            
            # Create payslip with the parsed dates
            payslip = Payslip(
                employee_id=employee.id,
                reference_month=reference_date,  # Already parsed as date
                issue_date=issue_date,
                payment_date=payment_date,
                bank_account=payment_info.get('bank_account') or employee_info.get('bank', ''),
                gross_salary=float(payment_info.get('gross_salary', 0)),
                net_salary=float(payment_info.get('net_salary', 0)),
                total_earnings=float(payment_info.get('total_earnings', 0)),
                total_deductions=float(payment_info.get('total_deductions', 0)),
                original_filename=payslip_data.get('filename', 'unknown.pdf')
            )
            session.add(payslip)
            session.flush()  # Flush to get the payslip ID

            # Add earnings with validation
            total_earnings = 0
            for earning in payslip_data.get('earnings', []):
                if not isinstance(earning, dict) or 'description' not in earning or 'amount' not in earning:
                    continue
                    
                try:
                    amount = float(earning['amount'])
                    total_earnings += amount
                    
                    # Get category and tax status from earning data or use defaults
                    category = earning.get('category', 'salary')
                    is_taxable = earning.get('is_taxable', True)
                    quantity = earning.get('quantity', 1.0)
                    rate = earning.get('rate')
                    
                    earn = Earning(
                        payslip_id=payslip.id,
                        category=category,
                        description=earning['description'].strip(),
                        reference=earning.get('reference', '').strip(),
                        amount=amount,
                        is_taxable=is_taxable,
                        quantity=quantity,
                        rate=rate
                    )
                    session.add(earn)
                except (ValueError, TypeError) as e:
                    st.warning(f"⚠️ Invalid earning data: {earning}. Error: {str(e)}")
                    continue

            # Add deductions with validation
            total_deductions = 0
            for deduction in payslip_data.get('deductions', []):
                if not isinstance(deduction, dict) or 'description' not in deduction or 'amount' not in deduction:
                    continue
                    
                try:
                    amount = float(deduction['amount'])
                    total_deductions += amount
                    
                    # Get category and tax status from deduction data or use defaults
                    category = deduction.get('category', 'other')
                    is_tax = deduction.get('is_tax', False)
                    is_pretax = deduction.get('is_pretax', False)
                    
                    ded = Deduction(
                        payslip_id=payslip.id,
                        category=category,
                        description=deduction['description'].strip(),
                        reference=deduction.get('reference', '').strip(),
                        amount=amount,
                        is_tax=is_tax,
                        is_pretax=is_pretax,
                        tax_year=deduction.get('tax_year')
                    )
                    session.add(ded)
                except (ValueError, TypeError) as e:
                    st.warning(f"⚠️ Invalid deduction data: {deduction}. Error: {str(e)}")
                    continue

            # Update totals if they weren't provided or don't match the sum
            if not payment_info.get('total_earnings') or abs(total_earnings - float(payment_info.get('total_earnings', 0))) > 0.01:
                payslip.total_earnings = total_earnings
                
            if not payment_info.get('total_deductions') or abs(total_deductions - float(payment_info.get('total_deductions', 0))) > 0.01:
                payslip.total_deductions = total_deductions
                
            # Recalculate net salary if needed and ensure it's never negative
            calculated_net = float(payslip.gross_salary) - float(payslip.total_deductions)
            if calculated_net < 0:
                logger.warning(
                    f"Net salary would be negative (${calculated_net:.2f}) for employee {employee.id} "
                    f"in {reference_date.strftime('%Y-%m')}. Setting to 0."
                )
                calculated_net = 0.0
                
            if payslip.net_salary != calculated_net:
                payslip.net_salary = calculated_net

            session.commit()
            return True

        except Exception as e:
            session.rollback()
            st.error(f"❌ Error saving to database: {str(e)}")
            import traceback
            st.error(f"Error details: {traceback.format_exc()}")
            return False

def show_upload_page(manager):
    """
    Display the upload page for processing payslip PDF files.
    
    Args:
        manager: Instance of PayslipManager for handling file processing
    """
    st.title("📤 Upload Payslips")
    st.write("Upload one or more payslip PDF files for processing.")
    
    # Add a section for database status
    db_status_expander = st.expander("ℹ️ Database Status", expanded=False)
    with db_status_expander:
        try:
            with manager.get_session() as session:
                # Get counts from database
                employee_count = session.query(Employee).count()
                payslip_count = session.query(Payslip).count()
                
                st.write(f"📊 **Database Stats:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Employees", employee_count)
                with col2:
                    st.metric("Payslips", payslip_count)
                    
        except Exception as e:
            st.error(f"❌ Error connecting to database: {str(e)}")

    # File upload section
    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select one or more PDF files containing payslips"
    )
    
    # Database cleanup section
    with st.expander("🧹 Database Cleanup", expanded=False):
        st.write("Clean up old records and optimize the database.")
        
        # Get current database stats
        with manager.get_session() as session:
            total_payslips = session.query(Payslip).count()
            oldest_record = session.query(func.min(Payslip.reference_month)).scalar()
            
            if oldest_record:
                days_old = (datetime.now().date() - oldest_record).days
                st.info(f"Database contains {total_payslips} payslips. "
                       f"Oldest record is from {oldest_record.strftime('%Y-%m-%d')} ({days_old} days ago).")
            
            # Cleanup options
            col1, col2 = st.columns([2, 1])
            with col1:
                days_to_keep = st.number_input(
                    "Keep records from the last (days):",
                    min_value=30,
                    max_value=3650,  # ~10 years
                    value=365,  # Default to 1 year
                    step=30,
                    help="Records older than this many days will be deleted"
                )
            
            with col2:
                st.write("")
                st.write("")
                if st.button("🔍 Preview Cleanup"):
                    with st.spinner("Analyzing database..."):
                        results = manager.cleanup_database(session, days_old=days_to_keep, confirm=False)
                        
                        if 'records_to_delete' in results:
                            if results['records_to_delete'] > 0:
                                st.warning(
                                    f"⚠️ {results['records_to_delete']} payslips would be deleted. "
                                    f"This operation cannot be undone!"
                                )
                                
                                if st.button("🧹 Confirm Cleanup", type="primary"):
                                    with st.spinner("Cleaning up database..."):
                                        results = manager.cleanup_database(
                                            session, 
                                            days_old=days_to_keep, 
                                            confirm=True
                                        )
                                        
                                        if results.get('error'):
                                            st.error(f"❌ Error during cleanup: {results['error']}")
                                        else:
                                            st.success("✅ Database cleanup completed successfully!")
                                            st.json({
                                                "Records deleted": results['records_deleted'],
                                                "Backup created": "Yes" if results['backup_created'] else "No",
                                                "Database optimization": ", ".join(results['tables_optimized']),
                                                "Space saved": f"{(results['database_size_before'] - results['database_size_after']) / (1024*1024):.2f} MB"
                                            })
                                            st.rerun()
                            else:
                                st.info("No records would be deleted with the current settings.")
                        else:
                            st.error(f"❌ Could not analyze database: {results.get('error', 'Unknown error')}")

    if uploaded_files:
        st.write(f"📄 **{len(uploaded_files)} files selected for processing**")
        
        # Show a preview of selected files
        with st.expander("📋 Selected Files"):
            for i, uploaded_file in enumerate(uploaded_files, 1):
                st.write(f"{i}. {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
        
        if st.button("🚀 Process Files", type="primary"):
            # Create a status container outside the try block to ensure it's in scope for the except block
            status = st.status("Processing files...")
            try:
                with status:
                    # Save uploaded files
                    saved_files = manager.save_uploaded_files(uploaded_files)
                    
                    if not saved_files:
                        st.warning("No valid PDF files were saved for processing")
                        return
                        
                    st.write(f"💾 Saved {len(saved_files)} files for processing...")
                    
                    # Process the saved files
                    results = manager.process_payslips(saved_files)
                    
                    # Show results
                    if results['success']:
                        status.update(label="✅ Processing complete!", state="complete")
                        st.success(f"Successfully processed {len(results['success'])} of {results['total']} files")
                    
                    if results['skipped']:
                        st.warning(f"⚠️ {len(results['skipped'])} files were skipped. See details below.")
                        skipped_files = "\n".join([f"- **{file_name}**: {reason}" for file_name, reason in results['skipped']])
                        st.markdown(skipped_files)
                    
                    # Show a summary
                    st.balloons()
                    
            except Exception as e:
                status.update(label="❌ Processing failed", state="error")
                st.error(f"An error occurred: {str(e)}")
                st.exception(e)  # Show full traceback for debugging
    
    # Add a section for database maintenance (collapsed by default)
    db_expander = st.expander("⚙️ Database Tools", expanded=False)
    with db_expander:
        st.warning("⚠️ Use these tools with caution!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh Database Stats"):
                st.rerun()
        
        with col2:
            if st.button("🧹 Clear All Data", type="secondary"):
                st.session_state.show_reset_confirm = True
                
            # Show the reset confirmation outside the button's scope
            if st.session_state.get('show_reset_confirm', False):
                st.warning("⚠️ This will delete ALL data!")
                confirm = st.checkbox("❌ I understand this will delete ALL data and cannot be undone!")
                
                if confirm:
                    if st.button("✅ Confirm Reset", type="primary"):
                        with st.spinner("Resetting database..."):
                            try:
                                with manager.get_session() as session:
                                    # Drop all tables and recreate them
                                    Base.metadata.drop_all(bind=engine)
                                    session.commit()
                                    
                                    # Recreate all tables
                                    Base.metadata.create_all(bind=engine)
                                    session.commit()
                                    
                                    st.success("✅ Database has been reset successfully")
                                    st.session_state.show_reset_confirm = False
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error resetting database: {str(e)}")
                                st.exception(e)
                                st.session_state.show_reset_confirm = False
                            st.exception(e)

def show_payslip_details(payslip, session):
    """
    Display detailed information about a specific payslip.
    
    Args:
        payslip: The Payslip object to display
        session: SQLAlchemy session for database operations
    """
    employee = session.get(Employee, payslip.employee_id)
    
    employee_name = f"{employee.first_name} {employee.last_name}".strip() if employee else 'Unknown'
    with st.expander(f"📄 Payslip Details - {employee_name} - {payslip.reference_month.strftime('%B %Y') if payslip.reference_month else 'N/A'}", expanded=True):
        # Basic information
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Employee Information")
            employee_name = f"{employee.first_name} {employee.last_name}".strip() if employee else 'N/A'
            st.write(f"**Name:** {employee_name}")
            st.write(f"**Employee ID:** {employee.id if employee else 'N/A'}")
            st.write(f"**Department:** {employee.department if employee and employee.department else 'N/A'}")
            st.write(f"**Position:** {employee.position if employee and employee.position else 'N/A'}")
        
        with col2:
            st.subheader("Payment Details")
            st.write(f"**Reference Month:** {payslip.reference_month.strftime('%B %Y') if payslip.reference_month else 'N/A'}")
            st.write(f"**Issue Date:** {payslip.issue_date.strftime('%Y-%m-%d') if payslip.issue_date else 'N/A'}")
            st.write(f"**Payment Date:** {payslip.payment_date.strftime('%Y-%m-%d') if payslip.payment_date else 'N/A'}")
            st.write(f"**Status:** {payslip.status.capitalize() if payslip.status else 'N/A'}")
        
        # Earnings and Deductions
        st.subheader("Earnings & Deductions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Earnings")
            earnings = payslip.earnings.all() if hasattr(payslip, 'earnings') else []
            if earnings:
                earnings_data = []
                for earning in earnings:
                    earnings_data.append({
                        "Description": earning.description,
                        "Reference": earning.reference or "-",
                        "Amount": f"${float(earning.amount):,.2f}",
                        "Taxable": "Yes" if earning.is_taxable else "No"
                    })
                st.table(earnings_data)
            else:
                st.info("No earnings recorded for this payslip.")
        
        with col2:
            st.markdown("#### Deductions")
            deductions = payslip.deductions.all() if hasattr(payslip, 'deductions') else []
            if deductions:
                deductions_data = []
                for deduction in deductions:
                    deductions_data.append({
                        "Description": deduction.description,
                        "Reference": deduction.reference or "-",
                        "Amount": f"${float(deduction.amount):,.2f}",
                        "Type": deduction.category.capitalize() if deduction.category else "-"
                    })
                st.table(deductions_data)
            else:
                st.info("No deductions recorded for this payslip.")
        
        # Summary
        st.subheader("Summary")
        
        summary_cols = st.columns(3)
        
        with summary_cols[0]:
            st.metric("Gross Salary", f"${float(payslip.gross_salary):,.2f}" if payslip.gross_salary else "N/A")
        
        with summary_cols[1]:
            st.metric("Total Deductions", f"${float(payslip.total_deductions):,.2f}" if payslip.total_deductions else "N/A")
        
        with summary_cols[2]:
            st.metric("Net Salary", f"${float(payslip.net_salary):,.2f}" if payslip.net_salary else "N/A")
        
        # Add action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🖨️ Print Payslip", key=f"print_{payslip.id}"):
                st.session_state['print_payslip_id'] = payslip.id
        
        with col2:
            if st.button("📥 Download PDF", key=f"download_{payslip.id}"):
                st.session_state['download_payslip_id'] = payslip.id
        
        with col3:
            if st.button("✏️ Edit", key=f"edit_{payslip.id}"):
                st.session_state['edit_payslip_id'] = payslip.id

def show_view_page(manager):
    """
    Display the view page with a table of all payslips and filtering options.
    
    Args:
        manager: Instance of PayslipManager for database operations
    """
    st.title("📋 View Payslips")
    
    # Add filters
    with st.expander("🔍 Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Employee filter
            with manager.get_session() as session:
                employees = session.query(Employee).order_by(Employee.first_name, Employee.last_name).all()
                employee_options = ["All Employees"] + [f"{emp.first_name} {emp.last_name or ''} ({emp.id})".strip() for emp in employees]
                
        selected_employee = col1.selectbox(
            "Employee",
            options=employee_options,
            index=0
        )
        
        # Year filter
        with manager.get_session() as session:
            years = sorted(list({p.reference_month.year for p in session.query(Payslip).all() if p.reference_month}), reverse=True)
            year_options = ["All Years"] + [str(year) for year in years]
            
        selected_year = col2.selectbox(
            "Year",
            options=year_options,
            index=0
        )
        
        # Month filter
        month_options = ["All Months"] + [datetime(2000, i, 1).strftime('%B') for i in range(1, 13)]
        selected_month = col3.selectbox(
            "Month",
            options=month_options,
            index=0
        )
    
    # Get filtered data
    with manager.get_session() as session:
        # Start with base query
        query = session.query(Payslip).join(Employee)
        
        # Apply filters
        if selected_employee != "All Employees":
            employee_id = int(selected_employee.split('(')[-1].rstrip(')'))
            query = query.filter(Employee.id == employee_id)
            
        if selected_year != "All Years":
            query = query.filter(func.strftime('%Y', Payslip.reference_month) == selected_year)
            
        if selected_month != "All Months":
            month_num = datetime.strptime(selected_month, '%B').month
            query = query.filter(func.strftime('%m', Payslip.reference_month) == f"{month_num:02d}")
        
        # Execute query
        payslips = query.order_by(Payslip.reference_month.desc()).all()
        
        if not payslips:
            st.info("No payslips found matching the selected filters.")
            return
            
        # Create a DataFrame for display
        data = []
        for payslip in payslips:
            employee = session.get(Employee, payslip.employee_id)
            data.append({
                "ID": payslip.id,
                "Employee": f"{employee.first_name} {employee.last_name}" if employee else "Unknown",
                "Employee ID": employee.id if employee else "N/A",
                "Reference Month": payslip.reference_month.strftime("%B %Y") if payslip.reference_month else "N/A",
                "Gross Salary": float(payslip.gross_salary) if payslip.gross_salary else 0.0,
                "Net Salary": float(payslip.net_salary) if payslip.net_salary else 0.0,
                "Payment Date": payslip.payment_date.strftime("%Y-%m-%d") if payslip.payment_date else "N/A",
                "Status": payslip.status.capitalize() if payslip.status else "N/A"
            })
        
        # Display the table with enhanced features
        if data:
            df = pd.DataFrame(data)
            
            # Create a table using st.columns for layout
            col_widths = [50, 150, 100, 120, 120, 120, 110, 100, 100]
            col_names = ["ID", "Employee", "Employee ID", "Reference Month", 
                        "Gross Salary", "Net Salary", "Payment Date", "Status", "Actions"]
            
            # Display headers
            cols = st.columns(col_widths)
            for i, col in enumerate(cols):
                col.markdown(f"**{col_names[i]}**")
            
            # Display data rows
            for idx, row in df.iterrows():
                cols = st.columns(col_widths)
                with cols[0]:
                    st.write(row["ID"])
                with cols[1]:
                    st.write(row["Employee"])
                with cols[2]:
                    st.write(row["Employee ID"])
                with cols[3]:
                    st.write(row["Reference Month"])
                with cols[4]:
                    st.write(f"${row['Gross Salary']:,.2f}")
                with cols[5]:
                    st.write(f"${row['Net Salary']:,.2f}")
                with cols[6]:
                    st.write(row["Payment Date"])
                with cols[7]:
                    st.write(row["Status"])
                # Color code status
                status = row["Status"].lower()
                status_color = {
                    "paid": "green",
                    "approved": "blue",
                    "draft": "orange",
                    "cancelled": "red"
                }.get(status, "gray")
                
                cols[7].markdown(f"<span style='color: {status_color}'>{status.title()}</span>", unsafe_allow_html=True)
                
                # Add view button
                if cols[8].button("View", key=f"view_{row['ID']}"):
                    st.session_state['selected_payslip_id'] = row['ID']
                    
            # Show details when a row is selected
            if 'selected_payslip_id' in st.session_state:
                selected_payslip = session.get(Payslip, st.session_state['selected_payslip_id'])
                if selected_payslip:
                    show_payslip_details(selected_payslip, session)
                    
        else:
            st.info("No payslip data available to display.")

def show_reports_page(manager):
    """
    Display the reports page with various analytics and visualizations.
    
    Args:
        manager: Instance of PayslipManager for database operations
    """
    st.title("📊 Reports & Analytics")
    
    # Add a date range filter
    st.sidebar.header("Filters")
    
    with manager.get_session() as session:
        # Get date range from data
        min_date = session.query(func.min(Payslip.reference_month)).scalar()
        max_date = session.query(func.max(Payslip.reference_month)).scalar()
        
        if min_date and max_date:
            # Convert to datetime for the date_input widget
            min_date = datetime(min_date.year, min_date.month, 1)
            max_date = datetime(max_date.year, max_date.month, 1)
            
            # Add date range filter
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="date_range"
            )
            
            # Ensure we have a valid date range
            if len(date_range) == 2 and date_range[0] and date_range[1]:
                start_date, end_date = date_range
            else:
                start_date, end_date = min_date, max_date
        else:
            st.info("No payslip data available for reporting.")
            return
        
        # Get employee options for the filter
        employees = session.query(Employee).order_by(Employee.last_name, Employee.first_name).all()
        employee_options = ["All Employees"] + [f"{emp.last_name}, {emp.first_name} ({emp.id})" for emp in employees]
        
        selected_employee = st.sidebar.selectbox(
            "Employee",
            options=employee_options,
            index=0
        )
        
        # Build the base query
        query = session.query(Payslip, Employee).join(Employee)
        
        # Apply filters
        if selected_employee != "All Employees":
            employee_id = int(selected_employee.split('(')[-1].rstrip(')'))
            query = query.filter(Employee.id == employee_id)
        
        # Apply date range filter
        query = query.filter(
            func.date(Payslip.reference_month) >= start_date,
            func.date(Payslip.reference_month) <= end_date
        )
        
        # Execute the query
        results = query.all()
        
        if not results:
            st.warning("No data found matching the selected filters.")
            return
            
        # Convert to DataFrame for easier manipulation
        data = []
        for payslip, employee in results:
            data.append({
                "Employee": f"{employee.first_name} {employee.last_name}".strip(),
                "Employee ID": employee.id,
                "Department": (employee.department or "N/A") if hasattr(employee, 'department') else "N/A",
                "Position": (employee.position or "N/A") if hasattr(employee, 'position') else "N/A",
                "Reference Month": payslip.reference_month,
                "Year": payslip.reference_month.year,
                "Month": payslip.reference_month.month,
                "Month Name": payslip.reference_month.strftime("%B"),
                "Gross Salary": float(payslip.gross_salary) if payslip.gross_salary else 0.0,
                "Net Salary": float(payslip.net_salary) if payslip.net_salary else 0.0,
                "Total Deductions": float(payslip.total_deductions) if payslip.total_deductions else 0.0,
                "Status": payslip.status.capitalize() if payslip.status else "N/A"
            })
        
        df = pd.DataFrame(data)
        
        # Show summary statistics
        st.subheader("📊 Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Employees", df['Employee'].nunique())
        
        with col2:
            st.metric("Total Payslips", len(df))
            
        with col3:
            st.metric("Total Gross Pay", f"${df['Gross Salary'].sum():,.2f}")
            
        with col4:
            st.metric("Average Net Pay", f"${df['Net Salary'].mean():,.2f}")
        
        # Time series of gross and net pay
        st.subheader("💵 Salary Trends Over Time")
        
        # Group by month and calculate sums
        monthly_data = df.groupby(['Year', 'Month', 'Month Name']).agg({
            'Gross Salary': 'sum',
            'Net Salary': 'sum',
            'Total Deductions': 'sum'
        }).reset_index()
        
        # Create a proper date column for sorting
        monthly_data['Date'] = pd.to_datetime(monthly_data['Year'].astype(str) + '-' + monthly_data['Month'].astype(str) + '-01')
        monthly_data = monthly_data.sort_values('Date')
        
        # Create the line chart
        fig = px.line(
            monthly_data,
            x='Date',
            y=['Gross Salary', 'Net Salary', 'Total Deductions'],
            title='Salary Trends Over Time',
            labels={'value': 'Amount ($)', 'variable': 'Type'},
            height=400
        )
        
        # Update layout
        fig.update_layout(
            xaxis_title='Month',
            yaxis_title='Amount ($)',
            legend_title='Salary Type',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Department-wise analysis
        st.subheader("🏢 Department-wise Analysis")
        
        if 'Department' in df.columns and df['Department'].nunique() > 1:
            dept_data = df.groupby('Department').agg({
                'Employee': 'nunique',
                'Gross Salary': 'sum',
                'Net Salary': 'sum',
                'Total Deductions': 'sum'
            }).reset_index()
            
            # Calculate averages
            dept_data['Avg Gross'] = dept_data['Gross Salary'] / dept_data['Employee']
            dept_data['Avg Net'] = dept_data['Net Salary'] / dept_data['Employee']
            
            # Display department metrics
            cols = st.columns(2)
            
            with cols[0]:
                st.markdown("#### Total Pay by Department")
                fig1 = px.pie(
                    dept_data,
                    names='Department',
                    values='Gross Salary',
                    title='Total Gross Pay by Department'
                )
                st.plotly_chart(fig1, use_container_width=True)
                
            with cols[1]:
                st.markdown("#### Average Pay by Department")
                fig2 = px.bar(
                    dept_data,
                    x='Department',
                    y='Avg Gross',
                    title='Average Gross Pay by Department',
                    labels={'Avg Gross': 'Average Gross Pay ($)'}
                )
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Insufficient department data for analysis.")
        
        # Export options
        st.subheader("📤 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export to CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="💾 Download as CSV",
                data=csv,
                file_name=f"payslip_report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
        with col2:
            # Export to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Payslips')
                
                # Add summary sheet
                if 'Department' in df.columns and df['Department'].nunique() > 1:
                    dept_data.to_excel(writer, sheet_name='Department Summary', index=False)
                
                # Add monthly summary
                monthly_data.to_excel(writer, sheet_name='Monthly Summary', index=False)
            
            excel_data = output.getvalue()
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"payslip_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        payslips = session.query(Payslip).join(Employee).all()
        
        if not payslips:
            st.info("No payslips found in the database.")
            return
        
        # Create a DataFrame for analysis
        data = []
        for payslip in payslips:
            employee = session.get(Employee, payslip.employee_id)
            data.append({
                "Employee": f"{employee.first_name} {employee.last_name}".strip() if employee else "Unknown",
                "Employee ID": employee.id if employee else "N/A",
                "Department": employee.department if employee and hasattr(employee, 'department') else "N/A",
                "Position": employee.position if employee and hasattr(employee, 'position') else "N/A",
                "Reference Month": payslip.reference_month,
                "Gross Salary": payslip.gross_salary,
                "Net Salary": payslip.net_salary,
                "Payment Date": payslip.payment_date
            })
        
        if not data:
            st.warning("No data available for reports.")
            return
            
        df = pd.DataFrame(data)
        
        # Convert date columns to datetime, handling None values
        df['Reference Month'] = pd.to_datetime(df['Reference Month'], errors='coerce')
        df['Payment Date'] = pd.to_datetime(df['Payment Date'], errors='coerce')
        
        # Add a month-year column for grouping, handling None values
        df['Month'] = df['Reference Month'].dt.strftime('%Y-%m')
        
        # Display summary statistics
        st.subheader("Summary Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Employees", df['Employee'].nunique() if not df.empty else 0)
        with col2:
            avg_gross = df['Gross Salary'].mean() if not df.empty and 'Gross Salary' in df else 0
            st.metric("Average Gross Salary", f"R$ {avg_gross:,.2f}" if avg_gross > 0 else "N/A")
        with col3:
            avg_net = df['Net Salary'].mean() if not df.empty and 'Net Salary' in df else 0
            st.metric("Average Net Salary", f"R$ {avg_net:,.2f}" if avg_net > 0 else "N/A")
        
        # Monthly salary trend (only if we have valid dates)
        if not df['Month'].isnull().all():
            st.subheader("Monthly Salary Trend")
            monthly_avg = df.groupby('Month').agg({
                'Gross Salary': 'mean',
                'Net Salary': 'mean'
            }).reset_index()
            
            if not monthly_avg.empty:
                fig = px.line(
                    monthly_avg,
                    x='Month',
                    y=['Gross Salary', 'Net Salary'],
                    title="Average Monthly Salary Trend",
                    labels={'value': 'Amount (R$)', 'variable': 'Salary Type'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Department-wise analysis (only if we have department data)
        if 'Department' in df.columns and not df['Department'].isnull().all():
            st.subheader("Department-wise Analysis")
            dept_avg = df.groupby('Department').agg({
                'Gross Salary': 'mean',
                'Net Salary': 'mean',
                'Employee': 'count'
            }).rename(columns={'Employee': 'Employee Count'}).reset_index()
            
            if not dept_avg.empty:
                fig = px.bar(
                    dept_avg,
                    x='Department',
                    y=['Gross Salary', 'Net Salary'],
                    barmode='group',
                    title="Average Salary by Department",
                    labels={'value': 'Amount (R$)'}
                )
                st.plotly_chart(fig, use_container_width=True)

def init_database():
    """Initialize the database and create tables"""
    try:
        # Import models to ensure they're registered with SQLAlchemy
        from src.models import Base
        from src.database import engine
        
        # Import all models to ensure they're registered
        from src.models.employee import Employee  # noqa: F401
        from src.models.payslip import Payslip  # noqa: F401
        from src.models.earning import Earning  # noqa: F401
        from src.models.deduction import Deduction  # noqa: F401
        
        # Create all tables
        Base.metadata.create_all(engine)
        st.sidebar.success("✅ Database initialized successfully!")
    except Exception as e:
        st.sidebar.error(f"❌ Error initializing database: {str(e)}")
        import traceback
        st.sidebar.error(f"Error details: {traceback.format_exc()}")

def reset_database():
    """Safely reset the database by dropping and recreating all tables."""
    import shutil
    from pathlib import Path
    
    db_path = Path("data/payslips.db")
    backup_path = Path("data/payslips.db.backup")
    
    # Create a backup of the existing database
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
        print(f"Created backup at {backup_path}")
    
    try:
        # Import models to ensure they're registered with SQLAlchemy
        from src.models import Base
        from src.database import engine
        
        # Import all models to ensure they're registered
        from src.models.employee import Employee  # noqa: F401
        from src.models.payslip import Payslip  # noqa: F401
        from src.models.earning import Earning  # noqa: F401
        from src.models.deduction import Deduction  # noqa: F401
        
        # Drop and recreate all tables
        print("Dropping existing tables...")
        Base.metadata.drop_all(engine)
        
        print("Creating new tables...")
        Base.metadata.create_all(engine)
        
        print("✅ Database reset successfully!")
        return True
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        import traceback
        traceback.print_exc()
        # Restore from backup if possible
        if backup_path.exists():
            shutil.copy2(backup_path, db_path)
            print("Restored database from backup")
        return False

def main_app():
    """Main application layout and routing."""
    # Check if we need to reset the database
    if Path("data/payslips.db").exists():
        with get_db_session() as session:
            try:
                # Try a simple query to check if the schema is up to date
                session.query(Employee).first()
            except Exception as e:
                if "no such column: employees.email" in str(e):
                    st.warning("Database schema is out of date. Resetting database...")
                    if reset_database():
                        st.success("Database reset successfully! Please refresh the page.")
                    else:
                        st.error("Failed to reset database. Please check the logs.")
                    return
                else:
                    raise
    
    # Security-focused styles and custom CSS
    st.markdown("""
    <style>
        /* Security-focused styles */
        html {
            scroll-behavior: smooth;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }
        
        /* Custom styles */
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .stButton>button {
            width: 100%;
        }
        .stProgress > div > div > div > div {
            background-color: #1f77b4;
        }
        .stAlert {
            padding: 1em;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Add logout button to sidebar
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Upload", "View", "Reports", "Employees"],
        index=0,
        format_func=lambda x: {
            "Upload": "📤 Upload", 
            "View": "👀 View", 
            "Reports": "📊 Reports",
            "Employees": "👥 Employees"
        }[x]
    )
    
    # Main app logic
    manager = PayslipManager()
    
    if page == "Upload":
        show_upload_page(manager)
    elif page == "View":
        show_view_page(manager)
    elif page == "Reports":
        show_reports_page(manager)
    elif page == "Employees":
        show_employee_management_page(manager)

def show_employee_management_page(manager):
    """Display the employee management page."""
    st.title("👥 Employee Management")
    
    # Initialize session state for form visibility
    if 'show_employee_form' not in st.session_state:
        st.session_state.show_employee_form = False
    if 'editing_employee_id' not in st.session_state:
        st.session_state.editing_employee_id = None
    
    # Add new employee button
    if st.button("➕ Add New Employee") and not st.session_state.show_employee_form:
        st.session_state.show_employee_form = True
        st.session_state.editing_employee_id = None
    
    # Employee form
    if st.session_state.show_employee_form:
        with st.form("employee_form"):
            st.subheader("Employee Details")
            
            # Form fields
            first_name = st.text_input("First Name", key="emp_first_name")
            last_name = st.text_input("Last Name", key="emp_last_name")
            email = st.text_input("Email", key="emp_email")
            cpf = st.text_input("CPF", key="emp_cpf", 
                             help="Brazilian CPF (format: 000.000.000-00)")
            department = st.text_input("Department", key="emp_dept")
            position = st.text_input("Position", key="emp_position")
            is_active = st.checkbox("Active", value=True, key="emp_active")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save"):
                    try:
                        with manager.get_session() as session:
                            employee_data = {
                                'first_name': first_name,
                                'last_name': last_name,
                                'email': email,
                                'cpf': cpf,
                                'department': department,
                                'position': position,
                                'is_active': is_active
                            }
                            
                            if st.session_state.editing_employee_id:
                                # Update existing employee
                                employee = session.get(Employee, st.session_state.editing_employee_id)
                                if employee:
                                    for key, value in employee_data.items():
                                        setattr(employee, key, value)
                                    session.commit()
                                    st.success("Employee updated successfully!")
                            else:
                                # Create new employee
                                employee = Employee(**employee_data)
                                session.add(employee)
                                session.commit()
                                st.success("Employee created successfully!")
                            
                            # Reset form
                            st.session_state.show_employee_form = False
                            st.session_state.editing_employee_id = None
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Error saving employee: {str(e)}")
            
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    st.session_state.show_employee_form = False
                    st.session_state.editing_employee_id = None
                    st.rerun()
    
    # Employees list
    st.subheader("Employees")
    
    with manager.get_session() as session:
        employees = session.query(Employee).order_by(Employee.last_name, Employee.first_name).all()
        
        if not employees:
            st.info("No employees found. Add a new employee to get started.")
            return
        
        # Create a DataFrame for display
        data = []
        for emp in employees:
            data.append({
                "ID": emp.id,
                "Name": f"{emp.last_name}, {emp.first_name}" if emp.first_name or emp.last_name else "N/A",
                "Email": emp.email or "N/A",
                "CPF": emp.cpf or "N/A",
                "Department": emp.department or "N/A",
                "Position": emp.position or "N/A",
                "Status": "Active" if emp.is_active else "Inactive"
            })
        
        if data:
            # Display as a table with action buttons
            for idx, emp in enumerate(data):
                cols = st.columns([1, 3, 3, 2, 2, 2, 1, 1])
                with cols[0]:
                    st.write(emp["ID"])
                with cols[1]:
                    st.write(emp["Name"])
                with cols[2]:
                    st.write(emp["Email"])
                with cols[3]:
                    st.write(emp["Department"])
                with cols[4]:
                    st.write(emp["Position"])
                with cols[5]:
                    status_color = "green" if emp["Status"] == "Active" else "red"
                    st.markdown(f"<span style='color: {status_color}'>{emp['Status']}</span>", 
                                unsafe_allow_html=True)
                with cols[6]:
                    if st.button("✏️", key=f"edit_{emp['ID']}"):
                        st.session_state.show_employee_form = True
                        st.session_state.editing_employee_id = emp["ID"]
                        st.rerun()
                with cols[7]:
                    if st.button("🗑️", key=f"delete_{emp['ID']}"):
                        try:
                            with manager.get_session() as sess:
                                employee = sess.get(Employee, emp["ID"])
                                if employee:
                                    sess.delete(employee)
                                    sess.commit()
                                    st.success(f"Employee {emp['Name']} deleted successfully!")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting employee: {str(e)}")

def verify_magic_link(token: str) -> bool:
    """Verify a magic link token and log the user in if valid."""
    try:
        logger.info(f"Verifying magic link token: {token[:8]}...")
        from src.auth.service import auth_service_scope
        
        with auth_service_scope() as auth_service:
            logger.info("Auth service scope entered successfully")
            is_valid, user_data = auth_service.verify_token(token)
            logger.info(f"Token verification result: is_valid={is_valid}, user_data={user_data}")
            
            if is_valid and user_data:
                st.session_state.authenticated = True
                st.session_state.username = user_data.get('email', 'user')
                logger.info(f"User {st.session_state.username} authenticated successfully via magic link")
                st.toast("✅ Successfully logged in with magic link!")
                st.rerun()
                return True
            else:
                error_msg = "Invalid or expired magic link. Please request a new one."
                logger.warning(error_msg)
                st.error(f"❌ {error_msg}")
                return False
                
    except Exception as e:
        error_msg = f"Error verifying magic link: {str(e)}"
        logger.error(error_msg, exc_info=True)
        st.error(f"❌ {error_msg}")
        return False

def main():
    """Main entry point with authentication check."""
    # Initialize session state for authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Check for magic link token in URL
    token = st.query_params.get("token")
    if token and not st.session_state.authenticated:
        verify_magic_link(token)
        return  # Wait for rerun
    
    # Show login form if not authenticated
    if not st.session_state.authenticated:
        st.title("🔒 Payslip Manager")
        login_form()
    else:
        main_app()
    
    # Sidebar info
    st.sidebar.info(
        "ℹ️ **Payslip Management System**\n\n"
        "Upload, view, and analyze your payslips in one place."
    )
    
    # Add version info to sidebar
    st.sidebar.caption(f"v1.0.0 | {datetime.now().year}")

if __name__ == "__main__":
    main()
