class Settings:
    # Security settings
    SECRET_KEY = "your-super-secret-key-change-in-production"
    API_KEY = "your-api-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    ALGORITHM = "HS256"
    TOKEN_URL = "token"
    
    # SMTP settings
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "your_mail_id@gmail.com"
    SMTP_PASSWORD = "16_digit_smtp_password"
    FRONTEND_URL = "http://localhost:3000"
    
    # Database settings
    MONGODB_URL = "mongodb://localhost:27017"
    MONGODB_DB = "student_db"
    
    # CORS settings
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"]
    
    # Rate Limiting
    REQUESTS_PER_MINUTE = 60
    
    # Security Headers
    CSP_POLICY = "default-src 'self'"
    HSTS_MAX_AGE = 31536000
    
    # API settings
    API_V1_PREFIX = "/api/v1"
    PROJECT_NAME = "Student Management API"
    DEBUG = True

settings = Settings() 