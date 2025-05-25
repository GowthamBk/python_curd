from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables for database configuration
load_dotenv()

# Retrieve MongoDB connection URL and database name from environment variables
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "student_db")  # Default to student_db if not specified

# Log the MongoDB URL (without credentials for security)
if MONGODB_URL:
    masked_url = MONGODB_URL.split("@")[-1] if "@" in MONGODB_URL else "not set"
    logger.info(f"MongoDB URL: mongodb://***@{masked_url}")
    logger.info(f"Database Name: {DATABASE_NAME}")
else:
    logger.error("MONGODB_URL environment variable is not set!")

# Global variables to hold the MongoDB client and database instances
client: Optional[AsyncIOMotorClient] = None
db = None

async def connect_to_mongo():
    """Create database connection."""
    global client, db
    try:
        if not MONGODB_URL:
            raise ValueError("MONGODB_URL environment variable is not set")
            
        # Initialize MongoDB client
        logger.info("Attempting to connect to MongoDB...")
        client = AsyncIOMotorClient(MONGODB_URL)
        
        # Access the specified database
        db = client[DATABASE_NAME]
        
        # Verify the connection by sending a ping command
        await db.command('ping')
        logger.info("Successfully connected to MongoDB!")
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}")
        logger.error(f"Connection details - URL: {MONGODB_URL}, Database: {DATABASE_NAME}")
        raise e

async def close_mongo_connection():
    """Close database connection."""
    global client
    try:
        if client is not None:
            client.close()
            logger.info("MongoDB connection closed.")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {str(e)}")
        raise e

async def get_db():
    """Get database instance."""
    global db
    try:
        # Connect to MongoDB if the database instance is not yet created
        if db is None:
            await connect_to_mongo()
        return db
    except Exception as e:
        logger.error(f"Error getting database instance: {str(e)}")
        raise e