from datetime import datetime, timedelta
from app.utils.error_handlers import DatabaseError, ERROR_MESSAGES
from typing import Dict, Optional, Any
from bson import ObjectId
from app.utils.database import get_db
from app.core.config import settings
from app.utils.security import get_password_hash, verify_password
import jwt
import logging
import traceback

logger = logging.getLogger(__name__)

# User model for database interactions
class User:
    def __init__(self):
        # Initialize collection reference
        self.collection = None
        logger.info("User model initialized")
    
    async def _get_collection(self):
        """Get the users collection."""
        try:
            if self.collection is None:
                logger.info("Getting database connection...")
                db = await get_db()
                logger.info("Getting users collection...")
                self.collection = db.users
            return self.collection
        except Exception as e:
            error_msg = f"Error getting users collection: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": error_msg}
            )
    
    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user."""
        try:
            logger.info("Creating new user...")
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
            logger.info("Getting users collection...")
            collection = await self._get_collection()
            logger.info("Inserting new user document...")
            result = await collection.insert_one(user_data)
            
            # Fetch and return the newly created user document
            logger.info(f"Fetching created user with ID: {result.inserted_id}")
            created_user = await self.get_by_id(result.inserted_id)
            logger.info("User created successfully")
            return created_user
        except Exception as e:
            error_msg = f"Error creating user: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise DatabaseError(
                ERROR_MESSAGES["CREATE_FAILED"],
                {"error": error_msg}
            )
    
    async def get_by_id(self, user_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            logger.info(f"Getting user by ID: {user_id}")
            collection = await self._get_collection()
            user = await collection.find_one({"_id": user_id})
            if user:
                logger.info(f"User found: {user_id}")
            else:
                logger.info(f"User not found: {user_id}")
            return user
        except Exception as e:
            error_msg = f"Error getting user by ID: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": error_msg}
            )
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            logger.info(f"Getting user by email: {email}")
            collection = await self._get_collection()
            user = await collection.find_one({"email": email})
            if user:
                logger.info(f"User found with email: {email}")
            else:
                logger.info(f"User not found with email: {email}")
            return user
        except Exception as e:
            error_msg = f"Error getting user by email: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": error_msg}
            )
    
    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            logger.info(f"Getting user by username: {username}")
            collection = await self._get_collection()
            user = await collection.find_one({"username": username})
            if user:
                logger.info(f"User found with username: {username}")
            else:
                logger.info(f"User not found with username: {username}")
            return user
        except Exception as e:
            error_msg = f"Error getting user by username: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": error_msg}
            )
    
    async def update(self, user_id, update_data: Dict) -> bool:
        """Update user data."""
        try:
            logger.info(f"Updating user: {user_id}")
            collection = await self._get_collection()
            result = await collection.update_one(
                {'_id': user_id},
                {'$set': update_data}
            )
            success = result.modified_count > 0
            logger.info(f"User update {'successful' if success else 'failed'}: {user_id}")
            return success
        except Exception as e:
            error_msg = f"Error updating user: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise DatabaseError(
                ERROR_MESSAGES["UPDATE_FAILED"],
                {"error": error_msg}
            )

    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user."""
        try:
            logger.info(f"Authenticating user: {username}")
            user = await self.get_by_username(username)
            if not user:
                logger.info(f"Authentication failed: User not found - {username}")
                return None
            if not verify_password(password, user["password"]):
                logger.info(f"Authentication failed: Invalid password - {username}")
                return None
            logger.info(f"Authentication successful: {username}")
            return user
        except Exception as e:
            error_msg = f"Error authenticating user: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise DatabaseError(
                ERROR_MESSAGES["AUTHENTICATION_FAILED"],
                {"error": error_msg}
            )

    async def create_reset_token(self, email: str) -> Optional[str]:
        """Create a password reset token."""
        try:
            logger.info(f"Creating reset token for email: {email}")
            user = await self.get_by_email(email)
            if not user:
                logger.info(f"No user found for email: {email}")
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

            logger.info(f"Reset token created for email: {email}")
            return reset_token
        except Exception as e:
            error_msg = f"Error creating reset token: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise DatabaseError(
                ERROR_MESSAGES["TOKEN_CREATION_FAILED"],
                {"error": error_msg}
            )

    async def verify_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify password reset token."""
        try:
            logger.info("Verifying reset token...")
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("user_id")
            if not user_id:
                logger.info("Token verification failed: No user_id in token")
                return None

            user = await self.get_by_id(ObjectId(user_id))
            if not user or user.get("reset_token") != token:
                logger.info("Token verification failed: Invalid token or user not found")
                return None

            if user.get("reset_token_expires") < datetime.utcnow():
                logger.info("Token verification failed: Token expired")
                return None

            logger.info(f"Token verified successfully for user: {user_id}")
            return user
        except jwt.PyJWTError as e:
            error_msg = f"Error verifying reset token: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return None

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset user password."""
        try:
            logger.info("Attempting to reset password...")
            user = await self.verify_reset_token(token)
            if not user:
                logger.info("Password reset failed: Invalid token")
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

            success = result.modified_count > 0
            logger.info(f"Password reset {'successful' if success else 'failed'} for user: {user['_id']}")
            return success
        except Exception as e:
            error_msg = f"Error resetting password: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise DatabaseError(
                ERROR_MESSAGES["PASSWORD_RESET_FAILED"],
                {"error": error_msg}
            ) 