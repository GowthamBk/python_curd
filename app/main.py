from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from contextlib import asynccontextmanager
from app.routes.student_routes import router as student_router
from app.routes.auth_routes import router as auth_router
from app.utils.database import connect_to_mongo, close_mongo_connection, get_db
from app.utils.error_handlers import AppError
from app.utils.security import verify_api_key, get_security_headers
from app.core.config import settings
import os
from dotenv import load_dotenv
from fastapi.openapi.utils import get_openapi
import logging
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# CORS configuration - allows frontend applications on specified origins to interact with the API
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    try:
        # Connect to MongoDB
        logger.info("Attempting to connect to MongoDB...")
        db = await connect_to_mongo()
        if db is None:
            logger.error("Failed to connect to MongoDB. Application will start but database operations will fail.")
        else:
            logger.info("Successfully connected to MongoDB!")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        logger.error("Application will start but database operations may fail.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    try:
        await close_mongo_connection()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    logger.info("Application shutdown complete.")

# Initialize FastAPI application with metadata and documentation URLs
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A CRUD API for managing student records",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
    servers=[
        {"url": "http://localhost:8000", "description": "Local Development Server"},
        {"url": "https://api.example.com", "description": "Production Server"}
    ]
)

# Add custom openapi schema definition for correct security scheme display in docs
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
        servers=app.servers
    )
    
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": f"{settings.API_V1_PREFIX}/auth/login",
                    "scopes": {}
                }
            }
        },
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Assign the custom openapi generator
app.openapi = custom_openapi

# Add rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Get client IP
    client_ip = request.client.host
    
    # Check if IP is in rate limit dictionary
    if client_ip in settings.RATE_LIMIT_DICT:
        # Check if time difference is less than 1 minute
        if time.time() - settings.RATE_LIMIT_DICT[client_ip] < 60:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again in a minute."}
            )
    
    # Update rate limit dictionary
    settings.RATE_LIMIT_DICT[client_ip] = time.time()
    
    # Process request
    response = await call_next(request)
    return response

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Add API key middleware
@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    # Skip API key verification for documentation endpoints
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Get API key from header
    api_key = request.headers.get("X-API-Key")
    
    # Verify API key
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return await call_next(request)

# Configure CORS middleware with allowed origins, methods, headers, etc.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-API-Key"],
    max_age=3600,
)

# Global exception handler for custom AppError instances
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    error_detail = {
        "loc": ["body"],
        "msg": exc.message,
        "type": "validation_error"
    }
    
    if exc.details:
        for key, value in exc.details.items():
            error_detail["loc"].append(key)
            if isinstance(value, (str, int, float, bool)):
                error_detail["input"] = value
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": [error_detail]},
        headers=get_security_headers()
    )

# Include authentication and student routers with their respective prefixes and dependencies
app.include_router(
    auth_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    student_router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(verify_api_key)]
)

# Root endpoint - redirects to API documentation
@app.get("/", tags=["Root"])
async def read_root():
    """Redirect to API documentation"""
    return RedirectResponse(url=f"{settings.API_V1_PREFIX}/docs")