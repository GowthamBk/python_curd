import motor.motor_asyncio
from app.core.config import settings
import logging
import traceback

logger = logging.getLogger(__name__)

# MongoDB client instance
client = None

async def connect_to_mongo():
    """Connect to MongoDB and return the database instance."""
    global client
    try:
        # Log connection attempt
        logger.info("Attempting to connect to MongoDB...")
        logger.info(f"Connection URL: {settings.MONGODB_URL}")
        logger.info(f"Database Name: {settings.MONGODB_DB}")
        
        # Create client
        client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
        
        # Verify connection
        logger.info("Sending ping command to verify connection...")
        await client.admin.command('ping')
        
        # Get database
        db = client[settings.MONGODB_DB]
        
        logger.info("Successfully connected to MongoDB!")
        return db
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        if client:
            client.close()
            client = None
        return None

async def close_mongo_connection():
    """Close the MongoDB connection."""
    global client
    try:
        if client:
            client.close()
            client = None
            logger.info("MongoDB connection closed.")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

async def get_db():
    """Get the database instance."""
    if not client:
        return await connect_to_mongo()
    return client[settings.MONGODB_DB]