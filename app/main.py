from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from contextlib import asynccontextmanager
from app.routes.student_routes import router as student_router
from app.routes.auth_routes import router as auth_router
from app.utils.database import connect_to_mongo, close_mongo_connection
from app.utils.error_handlers import AppError
from app.utils.security import verify_api_key, get_security_headers
from app.utils.rate_limiter import rate_limit_middleware
import os
from dotenv import load_dotenv
from fastapi.openapi.utils import get_openapi
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# CORS configuration - allows frontend applications on specified origins to interact with the API
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    try:
        # Application startup event: connect to the database
        logger.info("Starting application...")
        logger.info("Connecting to MongoDB...")
        await connect_to_mongo()
        logger.info("Successfully connected to MongoDB!")
        yield  # Application runs
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise e
    finally:
        # Application shutdown event: close the database connection
        logger.info("Shutting down application...")
        await close_mongo_connection()
        logger.info("Application shutdown complete.")

# Initialize FastAPI application with metadata and documentation URLs
app = FastAPI(
    title="Student Management API",
    description="A CRUD API for managing student records",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
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
                    "tokenUrl": "/api/v1/auth/login",
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

# Add rate limiting middleware to control request rate from clients
app.middleware("http")(rate_limit_middleware)

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
    prefix="/api/v1",
)

app.include_router(
    student_router,
    prefix="/api/v1",
    dependencies=[Depends(verify_api_key)]
)

# Root endpoint - redirects to API documentation
@app.get("/", tags=["Root"])
async def read_root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/api/v1/docs")