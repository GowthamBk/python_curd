from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.models.user import User
from app.schemas.user_schema import (
    UserCreate, UserResponse, Token, ForgotPasswordRequest,
    ResetPasswordRequest, PasswordResetResponse
)
from app.utils.error_handlers import (
    AppError, ValidationError, NotFoundError, DatabaseError,
    handle_app_error, ERROR_MESSAGES
)
from app.utils.security import verify_token, create_access_token, verify_api_key
from app.core.config import settings
import smtplib
from email.mime.text import MIMEText

# APIRouter instance for authentication endpoints
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}}, # Default response for Not Found errors
)

# OAuth2PasswordBearer for JWT token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login") # The URL where clients can obtain a token

# User model instance for database operations
user_model = User()

# Helper function to send password reset emails
def send_reset_email(email: str, reset_token: str):
    """Send password reset email."""
    # Create a plain text email message
    msg = MIMEText("", 'plain') # Modified to use MIMEText directly
    msg['From'] = settings.SMTP_USERNAME
    msg['To'] = email
    msg['Subject'] = "Password Reset Request"
    
    # Construct the password reset link
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    body = f"""
    Hello,
    
    You have requested to reset your password. Please click the link below to reset your password:
    
    {reset_link}
    
    This link will expire in 1 hour.
    
    If you did not request this password reset, please ignore this email.
    
    Best regards,
    Your App Team
    """
    
    # Set the email body
    msg.set_payload(body) # Modified to set payload directly on MIMEText
    
    try:
        # Connect to the SMTP server and send the email
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls() # Secure the connection
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        # Raise a DatabaseError if email sending fails
        raise DatabaseError(
            ERROR_MESSAGES["EMAIL_SEND_FAILED"],
            {"error": str(e)}
        )

# Endpoint for user registration
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """Register a new user."""
    try:
        # Check if username exists in the database
        existing_user = await user_model.get_by_username(user.username)
        if existing_user:
            # Raise validation error if username is taken
            raise ValidationError(
                ERROR_MESSAGES["USERNAME_EXISTS"],
                {"username": user.username}
            )
        
        # Check if email exists in the database
        existing_email = await user_model.get_by_email(user.email)
        if existing_email:
            # Raise validation error if email is taken
            raise ValidationError(
                ERROR_MESSAGES["EMAIL_EXISTS"],
                {"email": user.email}
            )
        
        # Convert user schema to dictionary and create user in the database
        user_data = user.model_dump()
        created_user = await user_model.create(user_data)
        
        if not created_user:
            # Raise database error if user creation failed
            raise DatabaseError(ERROR_MESSAGES["CREATE_FAILED"])
        
        # Return the created user data
        return UserResponse(
            id=str(created_user["_id"]),
            username=created_user["username"],
            email=created_user["email"],
            full_name=created_user["full_name"],
            created_at=created_user["created_at"],
            updated_at=created_user["updated_at"],
            is_active=created_user["is_active"],
            is_superuser=created_user["is_superuser"]
        )
    except AppError as e:
        # Handle application-specific errors
        raise handle_app_error(e)

# Endpoint for user login
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user and return JWT token."""
    try:
        # Authenticate the user using username and password
        user = await user_model.authenticate(form_data.username, form_data.password)
        if not user:
            # Raise validation error for invalid credentials
            raise ValidationError(ERROR_MESSAGES["INVALID_CREDENTIALS"])
        
        # Create a JWT access token
        access_token = create_access_token(data={"sub": user["username"]})
        # Return the access token
        return Token(access_token=access_token)
    except AppError as e:
        # Handle application-specific errors
        raise handle_app_error(e)

# Endpoint to request a password reset email (requires API Key)
@router.post("/forgot-password", response_model=PasswordResetResponse, dependencies=[Depends(verify_api_key)])
async def forgot_password(request: ForgotPasswordRequest):
    """Send password reset email."""
    try:
        # Create a password reset token for the provided email
        reset_token = await user_model.create_reset_token(request.email)
        
        # Check if a reset token was generated (email exists)
        if not reset_token:
            # Return a generic message for security (don't reveal if email exists)
            return PasswordResetResponse(
                message="If your email is registered, you will receive a password reset link."
            )
        
        # Send the password reset email
        send_reset_email(request.email, reset_token)
        
        # Return a success message
        return PasswordResetResponse(
            message="If your email is registered, you will receive a password reset link."
        )
    except AppError as e:
        # Handle application-specific errors
        raise handle_app_error(e)

# Endpoint to reset the password using a reset token (requires API Key)
@router.post("/reset-password", response_model=PasswordResetResponse, dependencies=[Depends(verify_api_key)])
async def reset_password(request: ResetPasswordRequest):
    """Reset user password."""
    try:
        # Attempt to reset the password using the token and new password
        success = await user_model.reset_password(request.token, request.new_password)
        
        # Check if the password reset was successful
        if not success:
            # Raise validation error if the token is invalid or expired
            raise ValidationError(ERROR_MESSAGES["INVALID_RESET_TOKEN"])
        
        # Return a success message
        return PasswordResetResponse(
            message="Password has been reset successfully."
        )
    except AppError as e:
        # Handle application-specific errors
        raise handle_app_error(e)

# Endpoint to get the current authenticated user
@router.get("/me", response_model=UserResponse, dependencies=[Depends(verify_api_key), Depends(verify_token)])
async def get_current_user(current_user: dict = Depends(verify_token)):
    """Get current user data."""
    try:
        # Get the user data from the database using the username from the verified token
        user = await user_model.get_by_username(current_user.username)
        
        # Check if the user exists (should not happen if token is valid, but as a safeguard)
        if not user:
            # Raise not found error if user is not found
            raise NotFoundError(ERROR_MESSAGES["USER_NOT_FOUND"])
        
        # Return the current user's data
        return UserResponse(
            id=str(user["_id"]),
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            created_at=user["created_at"],
            updated_at=user["updated_at"],
            is_active=user["is_active"],
            is_superuser=user["is_superuser"]
        )
    except AppError as e:
        # Handle application-specific errors
        raise handle_app_error(e) 