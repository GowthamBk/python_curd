import motor.motor_asyncio
from app.core.config import settings

# MongoDB client instance
client = None

async def connect_to_mongo():
    """Connect to MongoDB and return the database instance."""
    global client
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
        await client.admin.command('ping')
        return client[settings.MONGODB_DB]
    except Exception:
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
    except Exception:
        pass

async def get_db():
    """Get the database instance."""
    if not client:
        return await connect_to_mongo()
    return client[settings.MONGODB_DB]