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
        
        # SMTP Configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        # Email settings
        self.sender_email = os.getenv("EMAIL_SENDER", self.smtp_username)
        self.app_name = os.getenv("APP_NAME", "Payslip Manager")
        self.base_url = os.getenv("BASE_URL", "http://localhost:8501")
        
        # Token settings
        self.token_expiry_hours = int(os.getenv("TOKEN_EXPIRY_HOURS", 1))


class EmailService:
    """Service for sending authentication emails with magic links."""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
    
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
        if not all([self.config.smtp_server, self.config.smtp_username, self.config.smtp_password]):
            logger.error("SMTP configuration is incomplete. Email not sent.")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg["From"] = f"{self.config.app_name} <{self.config.sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Add HTML content
        msg.attach(MIMEText(html_content, "html"))
        
        try:
            # Create secure connection with server and send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls(context=context)
                
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)
                
            logger.info(f"Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
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
        # Generate the magic link
        magic_link = f"{self.config.base_url}/auth/verify?token={token}"
        
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
