"""
Email utilities for sending magic links and authentication emails.
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

class EmailConfig:
    """Configuration for email settings."""
    
    def __init__(self):
        load_dotenv()  # Load environment variables from .env file if it exists
        
        # Try to import streamlit for secrets
        try:
            import streamlit as st
            use_streamlit_secrets = True
        except ImportError:
            use_streamlit_secrets = False
        
        def get_setting(env_var, default=None, secret_key=None, secret_section=None):
            """Get setting from Streamlit secrets or environment variables."""
            if use_streamlit_secrets and secret_key:
                try:
                    if secret_section:
                        return st.secrets.get(secret_section, {}).get(secret_key) or os.getenv(env_var, default)
                    return st.secrets.get(secret_key) or os.getenv(env_var, default)
                except Exception as e:
                    logger.warning(f"Error accessing Streamlit secret {secret_key}: {str(e)}")
            return os.getenv(env_var, default)
        
        # SMTP Configuration - try to get from Streamlit secrets first, then environment variables
        self.smtp_server = get_setting("SMTP_SERVER", "smtp.gmail.com", "smtp_server", "email")
        self.smtp_port = int(get_setting("SMTP_PORT", "587", "smtp_port", "email"))
        self.smtp_username = get_setting("SMTP_USERNAME", None, "smtp_username", "email")
        self.smtp_password = get_setting("SMTP_PASSWORD", None, "smtp_password", "email")
        self.use_tls = get_setting("SMTP_USE_TLS", "true", "use_tls", "email").lower() == "true"
        
        # Email settings
        self.sender_email = get_setting("EMAIL_SENDER", self.smtp_username, "from_email", "email")
        self.app_name = get_setting("APP_NAME", "Payslip Manager", "app_name", "email")
        self.base_url = get_setting("BASE_URL", "http://localhost:8501", "base_url", "email")
        
        # Token settings
        self.token_expiry_hours = int(get_setting("TOKEN_EXPIRY_HOURS", "1", "token_expiry_hours", "auth"))


class EmailService:
    """Service for sending authentication emails with magic links."""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
        
        # Log configuration for debugging
        logger.info("EmailService initialized with config:")
        logger.info(f"- SMTP Server: {self.config.smtp_server}:{self.config.smtp_port}")
        logger.info(f"- SMTP Username: {self.config.smtp_username}")
        logger.info(f"- SMTP Use TLS: {self.config.use_tls}")
        logger.info(f"- Sender Email: {self.config.sender_email}")
        logger.info(f"- App Name: {self.config.app_name}")
        logger.info(f"- Base URL: {self.config.base_url}")
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email with the given content.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: Email body in HTML format
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Validate configuration
        if not all([self.config.smtp_server, self.config.smtp_username, self.config.smtp_password]):
            missing = []
            if not self.config.smtp_server:
                missing.append("SMTP_SERVER")
            if not self.config.smtp_username:
                missing.append("SMTP_USERNAME")
            if not self.config.smtp_password:
                missing.append("SMTP_PASSWORD")
                
            logger.error(f"SMTP configuration is incomplete. Missing: {', '.join(missing)}")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg["From"] = f"{self.config.app_name} <{self.config.sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Add HTML content
        msg.attach(MIMEText(html_content, "html"))
        
        # Log email details (without sensitive data)
        logger.info(f"Sending email to {to_email} with subject: {subject}")
        logger.debug(f"Email content: {html_content[:200]}...")  # Log first 200 chars of content
        
        try:
            # Enable SMTP debug output
            debug_level = 1 if logger.getEffectiveLevel() <= logging.DEBUG else 0
            
            # Create secure connection with server and send email
            context = ssl.create_default_context()
            logger.info(f"Connecting to SMTP server: {self.config.smtp_server}:{self.config.smtp_port}")
            
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.set_debuglevel(debug_level)
                
                # Log server properties
                logger.info(f"SMTP server properties: {server.ehlo()}")
                
                if self.config.use_tls:
                    logger.info("Starting TLS...")
                    server.starttls(context=context)
                    logger.info("TLS started, sending EHLO again...")
                    logger.info(f"After TLS: {server.ehlo()}")
                
                logger.info("Authenticating with SMTP server...")
                try:
                    server.login(self.config.smtp_username, self.config.smtp_password)
                    logger.info("SMTP authentication successful")
                except Exception as auth_error:
                    logger.error(f"SMTP authentication failed: {str(auth_error)}")
                    return False
                
                logger.info(f"Sending email to {to_email}...")
                try:
                    server.send_message(msg)
                    logger.info(f"Email successfully sent to {to_email}")
                    return True
                except Exception as send_error:
                    logger.error(f"Failed to send email to {to_email}: {str(send_error)}")
                    return False
            
        except Exception as e:
            logger.error(f"Error in _send_email to {to_email}: {str(e)}", exc_info=True)
            return False
    
    def send_magic_link(self, email: str, token: str, user_agent: Optional[str] = None, 
                        ip_address: Optional[str] = None) -> bool:
        """
        Send a magic login link to the user's email.
        
        Args:
            email: Recipient's email address
            token: The magic token to include in the link
            user_agent: User agent from the login request (optional)
            ip_address: IP address from the login request (optional)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Generate the magic link - using root path with token as query parameter
        magic_link = f"{self.config.base_url}/?token={token}"
        
        # Create email content
        subject = f"Your {self.config.app_name} Login Link"
        
        # Security notice about the request
        security_notice = ""
        if user_agent or ip_address:
            security_notice = "<p style='color: #666; font-size: 0.9em; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px;'>"
            if ip_address:
                security_notice += f"<strong>Location:</strong> {ip_address}<br>"
            if user_agent:
                security_notice += f"<strong>Device:</strong> {user_agent}<br>"
            security_notice += f"<strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            security_notice += "<br><br>If you did not request this, please ignore this email."
            security_notice += "</p>"
        
        # Email template
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c3e50;">Your Login Link</h2>
            <p>Hello,</p>
            <p>Click the button below to sign in to your {self.config.app_name} account:</p>
            <p style="margin: 30px 0;">
                <a href="{magic_link}" 
                   style="background-color: #4CAF50; 
                          color: white; 
                          padding: 12px 24px; 
                          text-decoration: none; 
                          border-radius: 4px;">
                    Sign In to {self.config.app_name}
                </a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #3498db;">{magic_link}</p>
            <p>This link will expire in {self.config.token_expiry_hours} hour{'s' if self.config.token_expiry_hours > 1 else ''}.</p>
            {security_notice}
            <p style="margin-top: 30px; color: #7f8c8d; font-size: 0.9em;">
                This is an automated message, please do not reply to this email.
            </p>
        </div>
        """.format(
            magic_link=magic_link,
            app_name=self.config.app_name,
            expiry_hours=self.config.token_expiry_hours,
            security_notice=security_notice
        )
        
        return self._send_email(email, subject, html_content)
    
    def send_password_reset(self, email: str, reset_token: str) -> bool:
        """
        Send a password reset link to the user's email.
        
        Args:
            email: Recipient's email address
            reset_token: The password reset token
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        reset_link = f"{self.config.base_url}/auth/reset-password?token={reset_token}"
        subject = f"{self.config.app_name} - Password Reset Request"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c3e50;">Reset Your Password</h2>
            <p>We received a request to reset your password for your {self.config.app_name} account.</p>
            <p>Click the button below to reset your password:</p>
            <p style="margin: 30px 0;">
                <a href="{reset_link}" 
                   style="background-color: #3498db; 
                          color: white; 
                          padding: 12px 24px; 
                          text-decoration: none; 
                          border-radius: 4px;">
                    Reset Password
                </a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #3498db;">{reset_link}</p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this password reset, you can safely ignore this email.</p>
            <p style="margin-top: 30px; color: #7f8c8d; font-size: 0.9em;">
                This is an automated message, please do not reply to this email.
            </p>
        </div>
        """.format(
            reset_link=reset_link,
            app_name=self.config.app_name
        )
        
        return self._send_email(email, subject, html_content)
