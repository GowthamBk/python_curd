from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables for database configuration
load_dotenv()

# Retrieve MongoDB connection URL and database name from environment variables
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

# Global variables to hold the MongoDB client and database instances
client: Optional[AsyncIOMotorClient] = None
db = None

async def connect_to_mongo():
    """Create database connection."""
    global client, db
    try:
        # Initialize MongoDB client
        client = AsyncIOMotorClient(MONGODB_URL)
        # Access the specified database
        db = client[DATABASE_NAME]
        # Verify the connection by sending a ping command
        await db.command('ping')
        print("Successfully connected to MongoDB!")
    except Exception as e:
        # Print error and re-raise if connection fails
        print(f"Error connecting to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    """Close database connection."""
    global client
    # Close the client connection if it exists
    if client is not None:
        client.close()
        print("MongoDB connection closed.")

async def get_db():
    """Get database instance."""
    global db
    # Connect to MongoDB if the database instance is not yet created
    if db is None:
        await connect_to_mongo()
    return db # Return the database instance