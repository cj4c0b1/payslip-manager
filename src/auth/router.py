"""
Authentication router for handling authentication endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.database import get_db_session
from src.auth.schemas import (
    UserLogin, 
    UserLoginResponse,
    TokenResponse,
    UserSession,
    ErrorResponse
)
from src.auth.service import auth_service, AuthService
from src.security import create_access_token, get_current_user

# Create router
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
    },
)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

@router.post("/login", response_model=UserLoginResponse, status_code=status.HTTP_200_OK)
async def request_magic_link(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db_session),
    service: AuthService = Depends(lambda: auth_service)
) -> UserLoginResponse:
    """
    Request a magic login link.
    
    This endpoint sends a magic link to the provided email address.
    The link will be valid for a limited time (default 1 hour).
    """
    # Get user agent and IP address from request
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    
    # Send magic link email
    email_sent = service.send_magic_link(
        email=login_data.email,
        user_agent=user_agent,
        ip_address=ip_address
    )
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send login email. Please try again."
        )
    
    # Always return success to prevent email enumeration
    return UserLoginResponse(
        message="If an account with this email exists, a login link has been sent.",
        token_sent=email_sent
    )

@router.post("/verify-token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def verify_magic_token(
    token: str,
    service: AuthService = Depends(lambda: auth_service)
) -> TokenResponse:
    """
    Verify a magic token and return an access token.
    
    This endpoint validates the magic token and returns a JWT access token
    that can be used for authenticating subsequent requests.
    """
    is_valid, user_data = service.verify_token(token)
    
    if not is_valid or not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please request a new login link.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token (valid for 24 hours)
    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": user_data["email"]},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_at=datetime.utcnow() + access_token_expires
    )

@router.get("/me", response_model=UserSession, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
) -> UserSession:
    """
    Get current user information.
    
    This endpoint returns the currently authenticated user's information.
    """
    from src.models.employee import Employee
    
    user = db.query(Employee).filter(Employee.email == current_user.get("sub")).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    return UserSession(
        user_id=user.id,
        email=user.email,
        is_active=user.is_active,
        last_login=user.last_login_at
    )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    token: str = Depends(oauth2_scheme)
) -> dict:
    """
    Log out the current user.
    
    This endpoint invalidates the current access token.
    Note: In a stateless JWT system, the client should discard the token.
    For enhanced security, consider implementing a token blacklist.
    """
    # In a stateless JWT system, the client should discard the token
    # For enhanced security, you could implement a token blacklist here
    return {"message": "Successfully logged out. Please discard your token."}

# Add cleanup task for expired tokens
@router.on_event("startup")
async def startup_event():
    """Clean up expired tokens on startup."""
    with next(get_db_session()) as db:
        service = AuthService(db=db)
        deleted = service.cleanup_expired_tokens()
        if deleted > 0:
            print(f"Cleaned up {deleted} expired or used tokens on startup.")
