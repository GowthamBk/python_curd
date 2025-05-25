import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Security settings
    SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    API_KEY = os.getenv("API_KEY", "your-api-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    ALGORITHM = "HS256"
    TOKEN_URL = "token"
    
    # SMTP settings
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your_mail_id@gmail.com")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "16_digit_smtp_password")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Database settings
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://node_curd:node_curd@cluster0.ahupn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    MONGODB_DB = os.getenv("DATABASE_NAME", "student_db")
    
    # CORS settings
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    
    # Rate Limiting
    REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", "60"))
    
    # Security Headers
    CSP_POLICY = os.getenv("CSP_POLICY", "default-src 'self'")
    HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", "31536000"))
    
    # API settings
    API_V1_PREFIX = "/api/v1"
    PROJECT_NAME = "Student Management API"
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

settings = Settings() 