from datetime import datetime, timedelta
from app.utils.error_handlers import DatabaseError, ERROR_MESSAGES
from typing import Dict, Optional, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.utils.security import get_password_hash, verify_password
import jwt

# User model for database interactions
class User:
    def __init__(self):
        # Initialize MongoDB client and access the 'users' collection
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB]
        self.collection = self.db.users
    
    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user."""
        # Hash the user's password before storing
        user_data["password"] = get_password_hash(user_data["password"])
        # Add creation and update timestamps
        user_data["created_at"] = datetime.utcnow()
        user_data["updated_at"] = datetime.utcnow()
        # Set default active and superuser status
        user_data["is_active"] = True
        user_data["is_superuser"] = False
        # Initialize reset token fields
        user_data["reset_token"] = None
        user_data["reset_token_expires"] = None
        
        # Insert the new user document into the collection
        result = await self.collection.insert_one(user_data)
        # Fetch and return the newly created user document
        created_user = await self.get_by_id(result.inserted_id)
        return created_user
    
    async def get_by_id(self, user_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            # Find and return a single user document by its MongoDB ObjectId
            return await self.collection.find_one({"_id": user_id})
        except Exception as e:
            # Raise a DatabaseError for errors during retrieval
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": str(e)}
            )
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            # Find and return a single user document by email
            return await self.collection.find_one({"email": email})
        except Exception as e:
            # Raise a DatabaseError for errors during retrieval
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": str(e)}
            )
    
    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            # Find and return a single user document by username
            return await self.collection.find_one({"username": username})
        except Exception as e:
            # Raise a DatabaseError for errors during retrieval
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": str(e)}
            )
    
    async def update(self, user_id, update_data: Dict) -> bool:
        """Update user data."""
        try:
            # Update a single user document by ID
            result = await self.collection.update_one(
                {'_id': user_id},
                {'$set': update_data} # Use $set to update specified fields
            )
            # Return True if document was modified, False otherwise
            return result.modified_count > 0
        except Exception as e:
            # Raise a DatabaseError for errors during update
            raise DatabaseError(
                ERROR_MESSAGES["UPDATE_FAILED"],
                {"error": str(e)}
            )

    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user."""
        # Get user by username
        user = await self.get_by_username(username)
        # If user not found or password incorrect, return None
        if not user:
            return None
        if not verify_password(password, user["password"]):
            return None
        return user # Return user dictionary if authentication is successful

    async def create_reset_token(self, email: str) -> Optional[str]:
        """Create a password reset token."""
        # Find user by email
        user = await self.get_by_email(email)
        # Return None if user not found
        if not user:
            return None

        # Generate JWT reset token with user_id and expiration time
        reset_token = jwt.encode(
            {
                "user_id": str(user["_id"]),
                "exp": datetime.utcnow() + timedelta(hours=1) # Token expires in 1 hour
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        # Store the reset token and its expiration time in the user's document
        await self.collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "reset_token": reset_token,
                    "reset_token_expires": datetime.utcnow() + timedelta(hours=1)
                }
            }
        )

        return reset_token # Return the generated token

    async def verify_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify password reset token."""
        try:
            # Decode the JWT token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            # Get user_id from the token payload
            user_id = payload.get("user_id")
            if not user_id:
                return None # Return None if user_id is missing in token

            # Fetch the user from database and check if the token matches and is not expired
            user = await self.get_by_id(ObjectId(user_id))
            if not user or user.get("reset_token") != token:
                return None # Return None if user not found or token mismatch

            if user.get("reset_token_expires") < datetime.utcnow():
                return None # Return None if token has expired

            return user # Return user dictionary if token is valid
        except jwt.PyJWTError:
            return None # Return None for any JWT decoding errors

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset user password."""
        # Verify the reset token
        user = await self.verify_reset_token(token)
        # Return False if token is invalid
        if not user:
            return False

        # Update password and clear the reset token fields in the user's document
        result = await self.collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "password": get_password_hash(new_password),
                    "updated_at": datetime.utcnow()
                },
                "$unset": { # Use $unset to remove fields
                    "reset_token": "",
                    "reset_token_expires": ""
                }
            }
        )

        # Return True if the document was modified, False otherwise
        return result.modified_count > 0 