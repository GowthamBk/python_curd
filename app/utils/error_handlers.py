from fastapi import HTTPException
from typing import Any, Dict, Optional

# Base error class for application-specific exceptions
class AppError(Exception):
    """Base error class for the application"""
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

# Exception for validation failures
class ValidationError(AppError):
    """Error for validation failures"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 400, details)

# Exception for resource not found errors
class NotFoundError(AppError):
    """Error for resource not found"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 404, details)

# Exception for database operation errors
class DatabaseError(AppError):
    """Error for database operations"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 500, details)

# Handler function to convert custom AppError to FastAPI HTTPException
def handle_app_error(error: AppError) -> HTTPException:
    """Convert AppError to FastAPI HTTPException"""
    # Create a base error detail dictionary following FastAPI's error response format
    error_detail = {
        "loc": ["body"], # Default location, can be overridden by error details
        "msg": error.message,
        "type": "validation_error" # Default type, can be adjusted based on error class
    }
    
    # Include additional details from the AppError instance if available
    if error.details:
        for key, value in error.details.items():
            # Add detail location and input value if it's a basic type
            error_detail["loc"].append(key)
            if isinstance(value, (str, int, float, bool)):
                error_detail["input"] = value
    
    # Return an HTTPException with the status code and detailed error information
    return HTTPException(
        status_code=error.status_code,
        detail=[error_detail]
    )

# Dictionary of common error messages used throughout the application
ERROR_MESSAGES = {
    "INVALID_ID": "Invalid ID format",
    "STUDENT_NOT_FOUND": "Student not found",
    "NO_VALID_STUDENTS": "No valid students found",
    "INVALID_AGE": "Age must be greater than 0 and less than 150",
    "INVALID_EMAIL": "Invalid email format",
    "EMAIL_EXISTS": "Student with this email already exists",
    "NO_UPDATE_DATA": "No data provided for update",
    "UPDATE_FAILED": "Failed to update student",
    "CREATE_FAILED": "Failed to create student",
    "DELETE_FAILED": "Failed to delete student",
    "INVALID_DATA": "Invalid student data",
    "DATABASE_ERROR": "Database operation failed",
    # Authentication error messages
    "USER_NOT_FOUND": "User not found",
    "INVALID_CREDENTIALS": "Invalid username or password",
    "INVALID_TOKEN": "Invalid or expired token",
    "UNAUTHORIZED": "Not authorized to perform this action",
    "PASSWORD_TOO_SHORT": "Password must be at least 8 characters long",
    "INVALID_USERNAME": "Username must be between 3 and 50 characters",
    "INVALID_FULL_NAME": "Full name must be between 2 and 100 characters",
    "USERNAME_EXISTS": "Username already exists",
    "INVALID_RESET_TOKEN": "Invalid or expired reset token",
    "EMAIL_SEND_FAILED": "Failed to send email"
} 