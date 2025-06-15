"""
Slash command handlers for the application.
"""
import streamlit as st
from typing import Dict, Callable, Optional, Any, List
import logging
import logging
import sys
from typing import Dict, Any, Optional, List
import re
import json
from pathlib import Path

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True, mode=0o777)

# Create file handler which logs debug messages
log_file = log_dir / 'commands.log'
try:
    fh = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    
    # Create console handler with a higher log level
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    # Add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    logger.debug("Commands module logger configured successfully")
    logger.debug("Debug log file: %s", str(log_file.absolute()))
    
except Exception as e:
    print(f"Failed to configure logging in commands module: {e}", file=sys.stderr)
    raise

# Dictionary to store command handlers
COMMAND_HANDLERS: Dict[str, Callable] = {}

# Default issue templates
ISSUE_TEMPLATES = {
    "feature": {
        "title": "Feature: ",
        "labels": ["enhancement"],
        "template": """## Description

## Acceptance Criteria
- [ ] 

## Technical Notes
"""
    },
    "bug": {
        "title": "Bug: ",
        "labels": ["bug"],
        "template": """## Description

## Steps to Reproduce
1. 
2. 
3. 

## Expected Behavior

## Actual Behavior

## Environment
- OS: 
- Browser: 
- Version: 
"""
    },
    "task": {
        "title": "Task: ",
        "labels": ["task"],
        "template": """## Description

## Acceptance Criteria
- [ ] 

## Notes
"""
    }
}

def command(name: str):
    """Decorator to register a slash command handler."""
    def decorator(func):
        COMMAND_HANDLERS[name.lower()] = func
        return func
    return decorator

def handle_command(cmd_input: str) -> Optional[str]:
    """Handle a slash command and return a response message."""
    if not cmd_input.startswith('/'):
        return None
        
    parts = cmd_input[1:].split(maxsplit=1)
    cmd_name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    handler = COMMAND_HANDLERS.get(cmd_name)
    if not handler:
        return f"Unknown command: /{cmd_name}"
    
    try:
        return handler(args)
    except Exception as e:
        logger.exception(f"Error executing command /{cmd_name}")
        return f"Error executing command: {str(e)}"

def _parse_issue_command(args: str) -> dict:
    """Parse the /issue command arguments."""
    # Match pattern like: /issue type:feature title:Add dark mode
    type_match = re.search(r'type:(\w+)', args, re.IGNORECASE)
    title_match = re.search(r'title:(.+)', args, re.IGNORECASE)
    
    issue_type = (type_match.group(1) if type_match else "task").lower()
    title = title_match.group(1).strip() if title_match else ""
    
    return {
        "type": issue_type,
        "title": title,
        "body": ""
    }

def _get_issue_template(issue_type: str) -> dict:
    """Get the template for the specified issue type."""
    return ISSUE_TEMPLATES.get(issue_type, ISSUE_TEMPLATES["task"])

@command("issue")
def create_issue(args: str) -> str:
    """Create a GitHub issue with the specified type and title.
    
    Usage: /issue type:<feature|bug|task> title:<title>
    
    Example: /issue type:feature title:Add dark mode
    """
    # If no arguments, show help
    if not args.strip():
        return (
            "Usage: /issue type:<feature|bug|task> title:<title>\n\n"
            "Example: /issue type:feature title:Add dark mode"
        )
    
    # Parse command arguments
    try:
        issue_data = _parse_issue_command(args)
        issue_type = issue_data["type"]
        
        # Get template for the issue type
        template = _get_issue_template(issue_type)
        
        # If title wasn't provided, show a form
        if not issue_data["title"]:
            with st.form("create_issue_form"):
                st.subheader("Create New Issue")
                
                # Issue type selection
                issue_type = st.selectbox(
                    "Issue Type",
                    list(ISSUE_TEMPLATES.keys()),
                    index=list(ISSUE_TEMPLATES.keys()).index(issue_type) if issue_type in ISSUE_TEMPLATES else 0
                )
                
                # Title input
                title = st.text_input("Title", value=template["title"])
                
                # Description text area with template
                body = st.text_area("Description", value=template["template"], height=300)
                
                # Submit button
                submitted = st.form_submit_button("Create Issue")
                
                if submitted and title:
                    # Create the issue
                    github = get_github_client()
                    if not github:
                        return "GitHub integration is not configured. Please set GITHUB_TOKEN in your environment or Streamlit secrets."
                    
                    try:
                        issue = github.create_issue(
                            title=title,
                            body=body,
                            labels=template["labels"]
                        )
                        
                        # Clear the form
                        st.session_state.clear()
                        
                        return f"✅ Issue created: {issue.get('html_url')}"
                    except Exception as e:
                        logger.error(f"Failed to create issue: {str(e)}")
                        return f"❌ Failed to create issue: {str(e)}"
            
            # Return None to indicate the form is being displayed
            return None
        
        # If title was provided in the command, create the issue directly
        title = issue_data["title"]
        if not title.startswith(template["title"]):
            title = f"{template['title']}{title}"
        
        logger.info("Creating GitHub issue with title: %s", title)
        github = get_github_client()
        if not github:
            error_msg = "GitHub integration is not available. Please ensure GitHub CLI is installed and authenticated."
            logger.error(error_msg)
            return f"❌ {error_msg}"
        
        try:
            issue = github.create_issue(
                title=title,
                body=template["template"],
                labels=template["labels"]
            )
            
            issue_url = issue.get('url', 'URL not available')
            logger.info("Successfully created issue: %s", issue_url)
            
            return (
                f"✅ **Issue created successfully!**\n\n"
                f"View and edit your issue here: [{issue_url}]({issue_url})\n\n"
                "You can close this message and continue using the app."
            )
            
        except RuntimeError as e:
            logger.error("Failed to create GitHub issue: %s", str(e))
            return (
                f"❌ **Failed to create issue**\n\n"
                f"Error: {str(e)}\n\n"
                "Please check your GitHub CLI configuration and try again."
            )
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(error_msg)
        return f"❌ {error_msg}\n\nPlease check the logs for more details."

# Register help command
@command("help")
def show_help(args: str = "") -> str:
    """Show available commands and their usage."""
    help_text = [
        "Available commands:",
        "",
        "/help - Show this help message",
        "/issue type:<feature|bug|task> title:<title> - Create a new GitHub issue",
        "  Example: /issue type:feature title:Add dark mode",
        ""
    ]
    
    return "\n".join(help_text)
