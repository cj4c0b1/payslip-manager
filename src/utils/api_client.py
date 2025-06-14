"""
API client utilities for making HTTP requests to the backend.
"""
import json
import logging
from typing import Dict, Any, Optional
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class APIClientError(Exception):
    """Custom exception for API client errors."""
    pass

def make_api_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    base_url: str = "http://localhost:8501"
) -> Dict[str, Any]:
    """
    Make an HTTP request to the API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint (e.g., "/api/auth/login")
        data: Request payload
        headers: Request headers
        base_url: Base URL of the API
        
    Returns:
        dict: Parsed JSON response
        
    Raises:
        APIClientError: If the request fails or returns an error
    """
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = headers or {}
    
    # Ensure JSON content type
    if 'Content-Type' not in headers and data is not None:
        headers['Content-Type'] = 'application/json'
    
    try:
        logger.debug(f"Making {method} request to {url}")
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=headers,
            timeout=10
        )
        
        # Parse JSON response
        try:
            response_data = response.json()
        except ValueError:
            response_data = {}
        
        # Check for error status codes
        if not response.ok:
            error_msg = response_data.get('detail', response.text)
            logger.error(f"API request failed: {response.status_code} - {error_msg}")
            raise APIClientError(f"{response.status_code} - {error_msg}")
            
        return response_data
        
    except RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        raise APIClientError(f"Failed to connect to the server: {str(e)}")

def send_magic_link(email: str, base_url: str = "http://localhost:8501") -> bool:
    """
    Send a magic login link to the specified email.
    
    Args:
        email: User's email address
        base_url: Base URL of the API
        
    Returns:
        bool: True if the request was successful, False otherwise
    """
    try:
        response = make_api_request(
            method="POST",
            endpoint="/api/auth/login",
            data={"email": email},
            base_url=base_url
        )
        return response.get("success", False)
    except APIClientError as e:
        logger.error(f"Failed to send magic link: {str(e)}")
        return False
