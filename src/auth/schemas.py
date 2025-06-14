"""
Pydantic schemas for authentication data validation.
"""
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator

class TokenCreate(BaseModel):
    """Schema for creating a new magic link token."""
    email: EmailStr
    user_agent: Optional[str] = Field(None, description="User agent from the login request")
    ip_address: Optional[str] = Field(None, description="IP address from the login request")
    expires_in_hours: int = Field(
        1, 
        ge=1, 
        le=24, 
        description="Token expiration time in hours (1-24)"
    )

class TokenResponse(BaseModel):
    """Schema for token response."""
    token: str
    expires_at: datetime

class TokenVerify(BaseModel):
    """Schema for verifying a token."""
    token: str

class UserLogin(BaseModel):
    """Schema for user login request."""
    email: EmailStr

class UserLoginResponse(BaseModel):
    """Schema for user login response."""
    message: str
    token_sent: bool

class UserSession(BaseModel):
    """Schema for user session data."""
    user_id: int
    email: str
    is_authenticated: bool = True
    is_active: bool = True
    last_login: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class TokenData(BaseModel):
    """Schema for token payload data."""
    email: str
    exp: datetime

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str
