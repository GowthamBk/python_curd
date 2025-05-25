from datetime import datetime, timedelta
from app.utils.error_handlers import DatabaseError, ERROR_MESSAGES
from typing import Dict, Optional, Any
from bson import ObjectId
from app.utils.database import get_db
from app.core.config import settings
from app.utils.security import get_password_hash, verify_password
import jwt
import logging

logger = logging.getLogger(__name__)

# User model for database interactions
class User:
    def __init__(self):
        # Initialize collection reference
        self.collection = None
    
    async def _get_collection(self):
        """Get the users collection."""
        if self.collection is None:
            db = await get_db()
            self.collection = db.users
        return self.collection
    
    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user."""
        try:
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
            
            # Get collection and insert the new user document
            collection = await self._get_collection()
            result = await collection.insert_one(user_data)
            
            # Fetch and return the newly created user document
            created_user = await self.get_by_id(result.inserted_id)
            return created_user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise DatabaseError(
                ERROR_MESSAGES["CREATE_FAILED"],
                {"error": str(e)}
            )
    
    async def get_by_id(self, user_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            collection = await self._get_collection()
            return await collection.find_one({"_id": user_id})
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": str(e)}
            )
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            collection = await self._get_collection()
            return await collection.find_one({"email": email})
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": str(e)}
            )
    
    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            collection = await self._get_collection()
            return await collection.find_one({"username": username})
        except Exception as e:
            logger.error(f"Error getting user by username: {str(e)}")
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": str(e)}
            )
    
    async def update(self, user_id, update_data: Dict) -> bool:
        """Update user data."""
        try:
            collection = await self._get_collection()
            result = await collection.update_one(
                {'_id': user_id},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise DatabaseError(
                ERROR_MESSAGES["UPDATE_FAILED"],
                {"error": str(e)}
            )

    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user."""
        try:
            user = await self.get_by_username(username)
            if not user:
                return None
            if not verify_password(password, user["password"]):
                return None
            return user
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            raise DatabaseError(
                ERROR_MESSAGES["AUTHENTICATION_FAILED"],
                {"error": str(e)}
            )

    async def create_reset_token(self, email: str) -> Optional[str]:
        """Create a password reset token."""
        try:
            user = await self.get_by_email(email)
            if not user:
                return None

            reset_token = jwt.encode(
                {
                    "user_id": str(user["_id"]),
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM
            )

            collection = await self._get_collection()
            await collection.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "reset_token": reset_token,
                        "reset_token_expires": datetime.utcnow() + timedelta(hours=1)
                    }
                }
            )

            return reset_token
        except Exception as e:
            logger.error(f"Error creating reset token: {str(e)}")
            raise DatabaseError(
                ERROR_MESSAGES["TOKEN_CREATION_FAILED"],
                {"error": str(e)}
            )

    async def verify_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify password reset token."""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("user_id")
            if not user_id:
                return None

            user = await self.get_by_id(ObjectId(user_id))
            if not user or user.get("reset_token") != token:
                return None

            if user.get("reset_token_expires") < datetime.utcnow():
                return None

            return user
        except jwt.PyJWTError as e:
            logger.error(f"Error verifying reset token: {str(e)}")
            return None

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset user password."""
        try:
            user = await self.verify_reset_token(token)
            if not user:
                return False

            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "password": get_password_hash(new_password),
                        "updated_at": datetime.utcnow()
                    },
                    "$unset": {
                        "reset_token": "",
                        "reset_token_expires": ""
                    }
                }
            )

            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            raise DatabaseError(
                ERROR_MESSAGES["PASSWORD_RESET_FAILED"],
                {"error": str(e)}
            ) 