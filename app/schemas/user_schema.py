from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

# Base schema for user data with common fields
class UserBase(BaseModel):
    """Base schema for user data."""
    username: str = Field(..., min_length=3, max_length=50) # User's unique username
    email: EmailStr # User's email address (validated format)
    full_name: str = Field(..., min_length=1, max_length=100) # User's full name

# Schema for creating a new user, extends UserBase
class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8) # User's password
    
    # Field validator for password strength
    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        # Checks for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        # Checks for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        # Checks for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        # Checks for at least one special character
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

# Schema for updating user data (all fields are optional)
class UserUpdate(BaseModel):
    """Schema for updating user data."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    password: Optional[str] = Field(None, min_length=8)

# Schema for user response data, extends UserBase
class UserResponse(UserBase):
    """Schema for user response data."""
    id: str # User's unique identifier (as string)
    created_at: datetime # Timestamp of user creation
    updated_at: datetime # Timestamp of last user update
    is_active: bool = True # User's active status
    is_superuser: bool = False # User's superuser status
    
    class Config:
        from_attributes = True # Enable mapping from ORM attributes (like MongoDB _id)
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "username": "johndoe",
                "email": "john@example.com",
                "full_name": "John Doe",
                "createdAt": "2024-03-21T10:00:00Z"
            }
        }

# Schema for JWT token response
class Token(BaseModel):
    access_token: str # The JWT access token string
    token_type: str = "bearer" # The type of token (conventionally "bearer")

# Schema for data contained within the JWT token
class TokenData(BaseModel):
    username: Optional[str] = None # The username encoded in the token

# Schema for forgot password request
class ForgotPasswordRequest(BaseModel):
    email: EmailStr # The email to send the reset link to

# Schema for reset password request
class ResetPasswordRequest(BaseModel):
    token: str # The reset token received via email
    new_password: str = Field(..., min_length=8) # The new password
    
    # Field validator for new password strength
    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v):
        # Checks for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        # Checks for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        # Checks for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        # Checks for at least one special character
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

# Schema for password reset response message
class PasswordResetResponse(BaseModel):
    message: str # A message indicating the result of the reset request

# Schema for login request (used by OAuth2PasswordRequestForm)
class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "password": "strongpassword123"
            }
        } 