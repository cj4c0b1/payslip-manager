"""
Application configuration settings.

This module contains configuration settings for the application,
including database connection, security settings, and other options.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

class Settings:
    """Application settings class."""
    
    def __init__(self):
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        # Base directory of the project
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        
        # Initialize all settings
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Load all settings from environment variables."""
        # Database configuration
        self.DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{self.BASE_DIR}/data/payslips.db')
        
        # Security settings
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        self.MAGIC_LINK_EXPIRE_MINUTES = 15
        
        # Email settings
        self.SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.example.com')
        self.SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
        self.SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
        self.SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
        self.EMAIL_FROM = os.getenv('EMAIL_FROM', 'noreply@example.com')
        self.EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
        
        # Application settings
        self.APP_NAME = os.getenv('APP_NAME', 'Payslip Manager')
        self.APP_URL = os.getenv('APP_URL', 'http://localhost:8501')
        self.DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Rate limiting settings
        self.RATE_LIMIT = {
            'login_attempt': {
                'max_attempts': 5,
                'window_seconds': 300  # 5 minutes
            },
            'magic_link': {
                'max_attempts': 3,
                'window_seconds': 600  # 10 minutes
            }
        }
        
        # Security headers configuration
        self.SECURE_HEADERS = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': """
                default-src 'self';
                script-src 'self' 'unsafe-inline' 'unsafe-eval';
                style-src 'self' 'unsafe-inline';
                img-src 'self' data:;
                font-src 'self' data:;
                connect-src 'self';
            """
        }
        
        # Create logs directory if it doesn't exist
        self.LOGS_DIR = os.path.join(self.BASE_DIR, 'logs')
        os.makedirs(self.LOGS_DIR, exist_ok=True)
        
        # Logging configuration
        self.LOGGING_CONFIG = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                },
            },
            'handlers': {
                'console': {
                    'level': 'INFO',
                    'class': 'logging.StreamHandler',
                    'formatter': 'standard'
                },
                'file': {
                    'level': 'DEBUG',
                    'class': 'logging.FileHandler',
                    'filename': os.path.join(self.LOGS_DIR, 'app.log'),
                    'formatter': 'standard'
                },
            },
            'loggers': {
                '': {  # root logger
                    'handlers': ['console', 'file'],
                    'level': 'DEBUG',
                    'propagate': True
                },
                'sqlalchemy': {
                    'level': 'WARNING',
                    'propagate': False,
                    'handlers': ['console', 'file']
                },
            }
        }

# Create settings instance
settings = Settings()
