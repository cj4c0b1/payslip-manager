"""
Email service for sending transactional emails.
"""
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import logging
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# Configure logging
logger = logging.getLogger(__name__)

class EmailServiceError(Exception):
    """Base exception for email service errors."""
    pass

class EmailService:
    """
    Service for sending emails using SMTP.
    
    Configuration is loaded from environment variables or Streamlit secrets.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the email service.
        
        Args:
            config: Optional configuration dictionary. If not provided, will use environment variables.
        """
        self.config = self._load_config(config)
        self.template_env = self._setup_templates()
    
    def _load_config(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Load email configuration from environment variables or provided config."""
        if config is None:
            try:
                import streamlit as st
                # Try to get config from Streamlit secrets
                secrets = st.secrets.get("email", {})
                config = {
                    "smtp_server": secrets.get("smtp_server"),
                    "smtp_port": int(secrets.get("smtp_port", 587)),
                    "smtp_username": secrets.get("smtp_username"),
                    "smtp_password": secrets.get("smtp_password"),
                    "default_sender": secrets.get("default_sender"),
                    "default_sender_name": secrets.get("default_sender_name", "Payslip Manager"),
                    "use_tls": secrets.get("use_tls", "true").lower() == "true",
                    "use_ssl": secrets.get("use_ssl", "false").lower() == "true",
                    "debug": secrets.get("debug", "false").lower() == "true"
                }
            except Exception as e:
                logger.warning("Could not load Streamlit secrets, falling back to environment variables")
                config = {}
        
        # Override with environment variables if not set in config
        env_config = {
            "smtp_server": os.getenv("SMTP_SERVER"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "smtp_username": os.getenv("SMTP_USERNAME"),
            "smtp_password": os.getenv("SMTP_PASSWORD"),
            "default_sender": os.getenv("EMAIL_DEFAULT_SENDER"),
            "default_sender_name": os.getenv("EMAIL_DEFAULT_SENDER_NAME", "Payslip Manager"),
            "use_tls": os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
            "use_ssl": os.getenv("EMAIL_USE_SSL", "false").lower() == "true",
            "debug": os.getenv("EMAIL_DEBUG", "false").lower() == "true",
            "from_email": os.getenv("FROM_EMAIL")
        }
        
        # Merge configs with environment variables taking precedence
        merged_config = {**config, **{k: v for k, v in env_config.items() if v is not None}}
        
        # Set default_sender from from_email if not provided
        if not merged_config.get("default_sender") and merged_config.get("from_email"):
            sender_name = merged_config.get("default_sender_name", "Payslip Manager")
            merged_config["default_sender"] = f"{sender_name} <{merged_config['from_email']}>"

        # Validate required settings
        required = ["smtp_server", "smtp_port", "smtp_username", "smtp_password"]
        missing = [key for key in required if not merged_config.get(key)]

        if missing:
            raise EmailServiceError(f"Missing required email configuration: {', '.join(missing)}")

        # Ensure we have either default_sender or from_email
        if not merged_config.get("default_sender") and not merged_config.get("from_email"):
            raise EmailServiceError("Either 'default_sender' or 'from_email' must be configured")

        # Set default_sender from from_email if still not set
        if not merged_config.get("default_sender"):
            merged_config["default_sender"] = merged_config["from_email"]

        return merged_config
    
    def _setup_templates(self):
        """Set up Jinja2 template environment."""
        # Look for templates in the 'templates/email' directory
        template_path = Path(__file__).parent.parent / "templates" / "email"
        
        # Create the directory if it doesn't exist
        template_path.mkdir(parents=True, exist_ok=True)
        
        # Create a default template if it doesn't exist
        self._ensure_default_templates(template_path)
        
        return Environment(
            loader=FileSystemLoader(template_path),
            autoescape=True
        )
    
    def _ensure_default_templates(self, template_path: Path):
        """Ensure default email templates exist."""
        # Create base template
        base_template = template_path / "base.html"
        if not base_template.exists():
            base_template.write_text("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{% block title %}{% endblock %}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #f8f9fa; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #fff; }
        .footer { margin-top: 20px; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; }
        .button { 
            display: inline-block; 
            padding: 10px 20px; 
            background-color: #007bff; 
            color: #fff; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{% block header %}{% endblock %}</h1>
        </div>
        <div class="content">
            {% block content %}{% endblock %}
        </div>
        <div class="footer">
            <p>This is an automated message, please do not reply to this email.</p>
            <p>&copy; {{ current_year }} {{ app_name }}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
""")
        
        # Create magic link email template
        magic_link_template = template_path / "magic_link.html"
        if not magic_link_template.exists():
            magic_link_template.write_text("""{% extends "base.html" %}

{% block title %}Your Login Link{% endblock %}

{% block header %}Sign in to {{ app_name }}{% endblock %}

{% block content %}
    <p>Hello,</p>
    <p>You requested a login link for {{ app_name }}. Click the button below to sign in:</p>
    
    <p style="text-align: center;">
        <a href="{{ login_url }}" class="button">Sign In</a>
    </p>
    
    <p>Or copy and paste this link into your browser:</p>
    <p style="word-break: break-all;">{{ login_url }}</p>
    
    <p>This link will expire in {{ expiration_minutes }} minutes and can only be used once.</p>
    
    <p>If you didn't request this email, you can safely ignore it.</p>
    
    <p>Best regards,<br>{{ app_name }} Team</p>
{% endblock %}
""")
    
    def send_email(
        self,
        to_emails: Union[str, List[str]],
        subject: str,
        template_name: str = None,
        template_context: Optional[Dict[str, Any]] = None,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_emails: Email address or list of email addresses to send to
            subject: Email subject
            template_name: Name of the template to use (without extension)
            template_context: Context variables for the template
            html_content: Raw HTML content (alternative to template)
            text_content: Plain text content (alternative to HTML)
            from_email: Sender email address (defaults to config)
            from_name: Sender name (defaults to config)
            cc: CC email address(es)
            bcc: BCC email address(es)
            reply_to: Reply-to email address
            
        Returns:
            bool: True if email was sent successfully, False otherwise
            
        Raises:
            EmailServiceError: If there's an error sending the email
        """
        # Prepare recipients
        if isinstance(to_emails, str):
            to_emails = [to_emails]
        
        # Prepare message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self._format_sender(from_email, from_name)
        msg['To'] = ', '.join(to_emails)
        
        if cc:
            msg['Cc'] = ', '.join([cc] if isinstance(cc, str) else cc)
        if bcc:
            msg['Bcc'] = ', '.join([bcc] if isinstance(bcc, str) else bcc)
        if reply_to:
            msg['Reply-To'] = reply_to
        
        # Prepare content
        if template_name:
            html_content = self._render_template(template_name, template_context or {})
        
        # Attach parts (plain text first, then HTML)
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        
        if html_content:
            msg.attach(MIMEText(html_content, 'html'))
        
        # Connect to SMTP server and send
        try:
            if self.config["use_ssl"]:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.config["smtp_server"],
                    self.config["smtp_port"],
                    context=context,
                    timeout=10
                ) as server:
                    if self.config["debug"]:
                        server.set_debuglevel(1)
                    self._login(server)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(
                    self.config["smtp_server"],
                    self.config["smtp_port"],
                    timeout=10
                ) as server:
                    if self.config["debug"]:
                        server.set_debuglevel(1)
                    if self.config["use_tls"]:
                        server.starttls()
                    self._login(server)
                    server.send_message(msg)
            
            logger.info(f"Email sent to {', '.join(to_emails)} with subject: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}", exc_info=True)
            raise EmailServiceError(f"Failed to send email: {str(e)}")
    
    def _login(self, server):
        """Login to the SMTP server."""
        try:
            server.login(
                self.config["smtp_username"],
                self.config["smtp_password"]
            )
        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP authentication failed")
            raise EmailServiceError("SMTP authentication failed. Please check your credentials.") from e
    
    def _format_sender(self, email: Optional[str] = None, name: Optional[str] = None) -> str:
        """Format the sender email with an optional name."""
        email = email or self.config["default_sender"]
        name = name or self.config["default_sender_name"]
        
        if name:
            return f'"{name}" <{email}>'
        return email
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render an email template with the given context."""
        try:
            # Add default context
            context.setdefault("app_name", "Payslip Manager")
            context.setdefault("current_year", datetime.now().year)
            
            template = self.template_env.get_template(f"{template_name}.html")
            return template.render(**context)
            
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}", exc_info=True)
            raise EmailServiceError(f"Failed to render template: {str(e)}") from e

# Create a singleton instance
email_service = EmailService()

def send_magic_link_email(
    email: str,
    magic_link: str,
    expiration_minutes: int = 15,
    app_name: str = "Payslip Manager"
) -> bool:
    """
    Send a magic link login email.
    
    Args:
        email: Recipient email address
        magic_link: The magic link URL
        expiration_minutes: Number of minutes until the link expires
        app_name: Name of the application
        
    Returns:
        bool: True if email was sent successfully
    """
    subject = f"Your {app_name} Login Link"
    
    # Create template context
    context = {
        "app_name": app_name,
        "login_url": magic_link,
        "expiration_minutes": expiration_minutes
    }
    
    # Send the email
    try:
        return email_service.send_email(
            to_emails=email,
            subject=subject,
            template_name="magic_link",
            template_context=context
        )
    except Exception as e:
        logger.error(f"Failed to send magic link email to {email}: {str(e)}")
        return False
