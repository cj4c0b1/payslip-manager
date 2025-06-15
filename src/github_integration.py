"""
GitHub integration for creating issues and managing repositories.
"""
import os
import logging
import json
import subprocess
import sys
from typing import Optional, Dict, Any, List, Union
import streamlit as st
from pathlib import Path

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True, mode=0o777)

# Create file handler which logs debug messages
log_file = log_dir / 'github_integration.log'
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
    
    logger.debug("GitHub integration logger configured successfully")
    logger.debug("Debug log file: %s", str(log_file.absolute()))
    
except Exception as e:
    print(f"Failed to configure logging: {e}", file=sys.stderr)
    raise

class GitHubIntegration:
    """Handle GitHub CLI interactions for issue creation."""
    
    def __init__(self):
        """Initialize GitHub CLI integration."""
        self.owner = "cj4c0b1"
        self.repo = "payslip-manager"
    
    def _run_gh_command(self, command_parts: List[str]) -> Dict[str, Any]:
        """
        Run a GitHub CLI command and return the parsed JSON output.
        
        Args:
            command_parts: List of command parts to execute
            
        Returns:
            dict: Parsed JSON output from the command
        """
        full_command = ["gh"] + command_parts
        logger.debug("Running command: %s", " ".join(full_command))
        
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.debug("Command stdout: %s", result.stdout)
            if result.stderr:
                logger.debug("Command stderr: %s", result.stderr)
                
            if result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse JSON output: %s", e)
                    logger.debug("Raw output: %s", result.stdout)
                    return {}
            return {}
            
        except subprocess.CalledProcessError as e:
            error_msg = f"GitHub CLI command failed with code {e.returncode}"
            if e.stderr:
                error_msg += f": {e.stderr.strip()}"
            logger.error(error_msg)
            logger.debug("Command: %s", " ".join(e.cmd) if e.cmd else "Unknown")
            logger.debug("Output: %s", e.stdout)
            raise RuntimeError(f"Failed to execute GitHub CLI: {error_msg}") from e
            
        except FileNotFoundError as e:
            error_msg = "GitHub CLI (gh) not found. Please install it from https://cli.github.com/"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def create_issue(self, title: str, body: str, labels: List[str] = None) -> Dict[str, Any]:
        """
        Create a GitHub issue using the GitHub CLI.
        
        Args:
            title: Issue title
            body: Issue body/description
            labels: List of labels to add to the issue
            
        Returns:
            dict: The created issue data
            
        Raises:
            RuntimeError: If issue creation fails
        """
        logger.info("Creating GitHub issue with title: %s", title)
        
        try:
            # Prepare the command
            cmd = [
                "issue", "create",
                "--title", title,
                "--body", body,
                "--repo", f"{self.owner}/{self.repo}",
                "--json", "number,title,url,state"
            ]
            
            # Add labels if provided
            if labels:
                logger.debug("Adding labels: %s", ", ".join(labels))
                cmd.extend(["--label", ",".join(labels)])
            
            # Create the issue
            logger.debug("Executing GitHub CLI command")
            result = self._run_gh_command(cmd)
            
            if not result:
                error_msg = "Failed to create GitHub issue: No response from GitHub CLI"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            logger.info("Successfully created issue #%s: %s", 
                      result.get('number'), result.get('url'))
            logger.debug("Issue details: %s", json.dumps(result, indent=2))
            
            return result
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to create GitHub issue: {e.stderr.strip() if e.stderr else 'Unknown error'}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Unexpected error creating GitHub issue: {str(e)}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e

def get_github_client() -> Optional[GitHubIntegration]:
    """
    Get a GitHub client instance if GitHub CLI is authenticated.
    
    Returns:
        Optional[GitHubIntegration]: A GitHub client instance or None if not authenticated
    """
    try:
        # Check if GitHub CLI is installed and authenticated
        subprocess.run(
            ["gh", "auth", "status", "--hostname", "github.com"],
            capture_output=True,
            check=True
        )
        return GitHubIntegration()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning("GitHub CLI is not installed or not authenticated: %s", str(e))
        return None
