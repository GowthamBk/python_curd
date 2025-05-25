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

# Load environment variables from .env file
load_dotenv()

# CORS configuration - allows frontend applications on specified origins to interact with the API
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup event: connect to the database
    await connect_to_mongo()
    yield # Application runs
    # Application shutdown event: close the database connection
    await close_mongo_connection()

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
        {"url": "https://student-management-api-dwse.onrender.com", "description": "Test Deployment Server"},
        {"url": "http://localhost:8000", "description": "Local Development Server"},
        {"url": "https://api.example.com", "description": "Production Server"} # Example production server URL
    ]
)

# Add custom openapi schema definition for correct security scheme display in docs
def custom_openapi():
    # Check if schema is already generated
    if app.openapi_schema:
        return app.openapi_schema
    
    # Generate default openapi schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
        servers=app.servers
    )
    
    # Define security schemes explicitly for Swagger UI
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": { # Security scheme for JWT authentication
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/api/v1/auth/login", # Specify the correct login endpoint URL
                    "scopes": {} # Define scopes if your application uses them
                }
            }
        },
        "APIKeyHeader": { # Security scheme for API Key authentication via header
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key" # The name of the header for the API key
        }
    }
    
    # Store the generated schema and return it
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
    allow_methods=["GET", "POST", "PUT", "DELETE"], # Allowed HTTP methods
    allow_headers=["*"], # Allow all headers in requests
    expose_headers=["X-API-Key"], # Expose custom headers in responses
    max_age=3600, # Cache preflight requests for 1 hour
)

# Global exception handler for custom AppError instances
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    # Structure the error detail for the response
    error_detail = {
        "loc": ["body"], # Default location, can be overridden by error details
        "msg": exc.message,
        "type": "validation_error" # Default type, can be adjusted based on error class
    }
    
    # Add specific details from the AppError instance if available
    if exc.details:
        for key, value in exc.details.items():
            error_detail["loc"].append(key)
            if isinstance(value, (str, int, float, bool)):
                error_detail["input"] = value
    
    # Return a JSON response with the appropriate status code and headers
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": [error_detail]},
        headers=get_security_headers() # Include security headers in the response
    )

# Include authentication and student routers with their respective prefixes and dependencies
# Authentication router: /api/v1/auth endpoints
app.include_router(
    auth_router,
    prefix="/api/v1",
    # Note: API key dependency is applied to specific auth routes, not globally here
)

# Student router: /api/v1/students endpoints requiring API key authentication
app.include_router(
    student_router,
    prefix="/api/v1",
    dependencies=[Depends(verify_api_key)] # Apply API key dependency to student routes
)

# Root endpoint - redirects to API documentation
@app.get("/", tags=["Root"])
async def read_root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/api/v1/docs")