from datetime import datetime
from pymongo import IndexModel, ASCENDING
from app.utils.database import get_db
from app.utils.error_handlers import DatabaseError, ERROR_MESSAGES
from typing import List, Dict, Optional

from pydantic import BaseModel, Field
from pydantic import field_validator

# Pydantic model for student data
class Student(BaseModel):
    # MongoDB ObjectId for the student, optional for creation
    id: Optional[str] = Field(default=None, alias="_id") # Use alias to map Pydantic field to MongoDB's _id
    # Name of the student, required field
    name: str = Field(...)
    # Age of the student, required field with constraints
    age: int = Field(..., gt=0, lt=150)
    # Address of the student, optional field
    address: Optional[dict] = None # Using dict for flexible address structure
    # Email address of the student, required field with format validation
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    # Timestamp of student creation, default is current time
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Timestamp of student update, default is current time
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Configuration for Pydantic model
    class Config:
        # Allow population by field name (e.g., _id instead of id)
        populate_by_name = True
        # Allow arbitrary types for flexibility (e.g., ObjectId)
        arbitrary_types_allowed = True
        # JSON schema example for documentation
        json_schema_extra = {
            "example": {
                "name": "Jane Doe",
                "age": 23,
                "address": {
                    "street": "5th Avenue",
                    "city": "New York"
                },
                "email": "jane.doe@example.com"
            }
        }

# Pydantic model for updating student data
class UpdateStudent(BaseModel):
    # Optional fields for updating student data
    name: Optional[str] = None
    age: Optional[int] = Field(None, gt=0, lt=150)
    address: Optional[dict] = None
    email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    # Configuration for Pydantic model
    class Config:
        # Allow arbitrary types for flexibility
        arbitrary_types_allowed = True
        # JSON schema example for documentation
        json_schema_extra = {
            "example": {
                "name": "Jane Doe",
                "age": 24
            }
        }

# Pydantic model for listing multiple students
class ListStudents(BaseModel):
    # List of Student models
    students: List[Student]

# Student model for database interactions
class StudentModel:
    def __init__(self):
        # Initialize collection attribute, will be set after connection
        self.collection = None
    
    async def init_collection(self):
        """Initialize the collection asynchronously."""
        # Get database instance if not already connected
        if self.collection is None:
            db = await get_db()
            self.collection = db.students # Access the 'students' collection
            # Create unique index on email field for efficient lookups and to prevent duplicates
            await self.collection.create_indexes([
                IndexModel([('email', ASCENDING)], unique=True)
            ])
    
    async def create(self, student_data):
        """Create a new student record."""
        try:
            await self.init_collection() # Ensure collection is initialized
            # print(f"Creating student with data: {student_data}")  # Debug log
            
            # Add creation timestamp before inserting
            student_data['createdAt'] = datetime.utcnow()
            
            # Insert the new student document into the collection
            result = await self.collection.insert_one(student_data)
            # print(f"Insert result: {result}")  # Debug log
            
            # Return the newly created student document
            if result.inserted_id:
                created_student = await self.get_by_id(result.inserted_id)
                # print(f"Created student: {created_student}")  # Debug log
                return created_student
            return None # Return None if insertion failed
        except Exception as e:
            # print(f"Error in create method: {str(e)}")  # Debug log
            # Re-raise the exception after logging (or handle differently if needed)
            raise e
    
    async def get_by_id(self, student_id):
        """Get a student by ID."""
        try:
            await self.init_collection() # Ensure collection is initialized
            # Find and return a single student document by its MongoDB ObjectId
            student = await self.collection.find_one({'_id': student_id})
            return student
        except Exception as e:
            # print(f"Error in get_by_id method: {str(e)}")  # Debug log
            # Re-raise the exception
            raise e
    
    async def get_by_email(self, email):
        """Get a student by email."""
        try:
            await self.init_collection() # Ensure collection is initialized
            # Find and return a single student document by email
            student = await self.collection.find_one({'email': email})
            return student
        except Exception as e:
            # print(f"Error in get_by_email method: {str(e)}")  # Debug log
            # Re-raise the exception
            raise e
    
    async def get_all(self, skip: int = 0, limit: int = 10, search_query: Dict = None) -> List[Dict]:
        """Get all students with pagination and search"""
        try:
            await self.init_collection() # Ensure collection is initialized
            query = search_query or {} # Use search query if provided, otherwise empty query
            # Find documents with pagination and search criteria
            cursor = self.collection.find(query).skip(skip).limit(limit)
            # Convert the cursor to a list of dictionaries
            return await cursor.to_list(length=limit)
        except Exception as e:
            # print(f"Error getting all students: {str(e)}")
            # Raise a DatabaseError for errors during retrieval
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": str(e)}
            )
    
    async def update(self, student_id, update_data):
        """Update a student record."""
        try:
            await self.init_collection() # Ensure collection is initialized
            # Update a single student document by ID
            result = await self.collection.update_one(
                {'_id': student_id},
                {'$set': update_data} # Use $set to update specified fields
            )
            # Return True if document was modified, False otherwise
            return result.modified_count > 0
        except Exception as e:
            # print(f"Error in update method: {str(e)}")  # Debug log
            # Re-raise the exception
            raise e
    
    async def delete(self, student_id):
        """Delete a student record."""
        try:
            await self.init_collection() # Ensure collection is initialized
            # Delete a single student document by ID
            result = await self.collection.delete_one({'_id': student_id})
            # Return True if document was deleted, False otherwise
            return result.deleted_count > 0
        except Exception as e:
            # print(f"Error in delete method: {str(e)}")  # Debug log
            # Re-raise the exception
            raise e
    
    async def count(self, search_query: Dict = None) -> int:
        """Count total students with optional search query"""
        try:
            await self.init_collection() # Ensure collection is initialized
            query = search_query or {} # Use search query if provided, otherwise empty query
            # Count documents matching the query
            return await self.collection.count_documents(query)
        except Exception as e:
            # print(f"Error in count method: {str(e)}")
            # Raise a DatabaseError for errors during counting
            raise DatabaseError(
                ERROR_MESSAGES["DATABASE_ERROR"],
                {"error": str(e)}
            )

# Example usage (for demonstration, not to be included in the final code)
# if __name__ == "__main__":
#     # Example of creating a Student instance
#     student_data = {
#         "name": "John Doe",
#         "age": 30,
#         "address": {"street": "123 Main St", "city": "Anytown"},
#         "email": "john.doe@example.com"
#     }
#     student = Student(**student_data)
#     print(student)

#     # Example of creating an UpdateStudent instance
#     update_data = {"age": 31}
#     update_student = UpdateStudent(**update_data)
#     print(update_student)