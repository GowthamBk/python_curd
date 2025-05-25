from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load environment variables for security configurations
load_dotenv()

# Retrieve security-related configurations from environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
API_KEY_NAME = "X-API-Key" # The name of the header for the API key
API_KEY = os.getenv("API_KEY")

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for integrating JWT authentication with FastAPI security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=os.getenv("JWT_TOKEN_URL", "token")) # Specifies the endpoint for token requests

# APIKeyHeader for extracting API key from a header
api_key_header = APIKeyHeader(name=API_KEY_NAME)

# Pydantic model for the JWT token response
class Token(BaseModel):
    access_token: str
    token_type: str # e.g., "bearer"

# Pydantic model for the data contained within the JWT token payload
class TokenData(BaseModel):
    username: Optional[str] = None # Subject of the token, typically the username

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Uses the password context to safely verify the password
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    # Uses the password context to generate a hash of the password
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    # Set expiration time for the token
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Add expiration time to the payload
    to_encode.update({"exp": expire})
    # Encode the payload into a JWT token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt # Return the encoded JWT token

async def verify_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Verify JWT token."""
    # Define credentials exception for unauthorized access
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}, # Indicates the required authentication scheme
    )
    try:
        # Decode the JWT token using the secret key and algorithm
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Extract the username (subject) from the token payload
        username: str = payload.get("sub")
        # If username is not present in the token, raise credentials exception
        if username is None:
            raise credentials_exception
        # Return TokenData containing the username
        token_data = TokenData(username=username)
        return token_data
    except JWTError:
        # Catch JWT specific errors (e.g., invalid signature, expired token)
        raise credentials_exception # Raise credentials exception for JWT errors

async def verify_api_key(api_key: str = Security(api_key_header)) -> bool:
    """Verify API key."""
    # Compare the provided API key with the configured API key
    if api_key != API_KEY:
        # Raise HTTPException if API key is invalid
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    return True # Return True if API key is valid

# Helper function to get security headers for responses
def get_security_headers():
    """Get security headers for responses."""
    # Return a dictionary of security headers
    return {
        "X-Content-Type-Options": "nosniff", # Prevents browsers from MIME-sniffing a response away from the declared content-type
        "X-Frame-Options": "DENY", # Prevents clickjacking attacks
        "X-XSS-Protection": "1; mode=block", # Enables the Cross-Site Scripting (XSS) filter built into most modern web browsers
        "Strict-Transport-Security": f"max-age={os.getenv('HSTS_MAX_AGE', '31536000')}; includeSubDomains", # Enforces secure (HTTPS) connections to the server
        "Content-Security-Policy": os.getenv("CSP_POLICY", "default-src 'self'"), # Controls resources the user agent is allowed to load
        "Referrer-Policy": "strict-origin-when-cross-origin", # Controls how much referrer information is included with requests
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()" # Allows or denies the use of browser features
    } 