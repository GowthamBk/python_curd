from fastapi import APIRouter, status, Query, Depends
from bson import ObjectId

from app.models.student import Student, StudentModel
from app.schemas.student_schema import (
    StudentCreate, StudentUpdate, StudentResponse,
    StudentListResponse, PaginationInfo, SearchInfo
)
from app.utils.error_handlers import (
    AppError, ValidationError, NotFoundError, DatabaseError,
    handle_app_error, ERROR_MESSAGES
)
from app.utils.security import verify_token
from app.models.user import User

# APIRouter instance for student endpoints
router = APIRouter(
    prefix="/students",
    tags=["students"],
    responses={404: {"description": "Not found"}}, # Default response for Not Found errors
)

# Student and User model instances for database interactions
student_model = StudentModel()
user_model = User()

# Dependency to get the current authenticated user based on JWT token
async def get_current_user(token_data: dict = Depends(verify_token)):
    """Get current user and verify authentication."""
    # Fetch user details from database using username from token
    user = await user_model.get_by_username(token_data.username)
    if not user:
        # Raise validation error if user is not found (should ideally not happen with valid token)
        raise ValidationError(ERROR_MESSAGES["USER_NOT_FOUND"])
    return user # Return user dictionary

# Endpoint to create a new student record (requires authentication)
@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student: StudentCreate, # Request body with student data
    current_user: dict = Depends(get_current_user) # Dependency to get authenticated user
):
    """
    Create a new student record.
    
    Args:
        student (StudentCreate): Student data to create
        current_user (dict): Current authenticated user
        
    Returns:
        StudentResponse: Created student data
        
    Raises:
        ValidationError: If email already exists
        DatabaseError: If creation fails
    """
    try:
        # Check if a student with the same email already exists
        existing_student = await student_model.get_by_email(student.email)
        if existing_student:
            # Raise validation error if email is already in use
            raise ValidationError(
                ERROR_MESSAGES["EMAIL_EXISTS"],
                {"email": student.email}
            )
        
        # Convert student schema to dictionary and create student in the database
        student_data = student.model_dump()
        created_student = await student_model.create(student_data)
        
        if created_student is None:
            # Raise database error if student creation failed
            raise DatabaseError(ERROR_MESSAGES["CREATE_FAILED"])
        
        # Prepare and return the created student data in the response format
        response_data = {
            "id": str(created_student["_id"]),
            "name": created_student["name"],
            "age": created_student["age"],
            "grade": created_student["grade"],
            "email": created_student["email"],
            "createdAt": created_student["createdAt"]
        }
        
        return StudentResponse(**response_data)
    except AppError as e:
        # Handle application-specific errors and return appropriate HTTP responses
        raise handle_app_error(e)
    except Exception as e:
        # Catch any other unexpected exceptions during creation
        raise DatabaseError(
            ERROR_MESSAGES["CREATE_FAILED"],
            {"error": str(e)}
        )

# Endpoint to get a paginated list of students with optional search (requires authentication)
@router.get("/", response_model=StudentListResponse)
async def get_students(
    page: int = Query(1, ge=1, description="Page number"), # Query parameter for page number
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"), # Query parameter for page size
    search: str = Query(None, description="Search term for name or email"), # Optional query parameter for search
    current_user: dict = Depends(get_current_user) # Dependency to get authenticated user
):
    """
    Get a paginated list of students with optional search.
    
    Args:
        page (int): Page number (starts from 1)
        page_size (int): Number of items per page (1-100)
        search (str, optional): Search term for name or email
        current_user (dict): Current authenticated user
        
    Returns:
        StudentListResponse: Paginated list of students with metadata
        
    Raises:
        NotFoundError: If no students found
        DatabaseError: If database operation fails
    """
    try:
        # Calculate the number of documents to skip for pagination
        skip = (page - 1) * page_size
        
        # Build search query for MongoDB if a search term is provided
        search_query = {}
        if search:
            search_query = {
                "$or": [
                    {"name": {"$regex": search, "$options": "i"}}, # Case-insensitive regex search on name
                    {"email": {"$regex": search, "$options": "i"}} # Case-insensitive regex search on email
                ]
            }
        
        # Get total number of students matching the search query
        total_students = await student_model.count(search_query)
        # Get students for the current page with pagination and search
        students = await student_model.get_all(skip=skip, limit=page_size, search_query=search_query)
        
        # Raise not found error if no students are returned after filtering
        if not students:
            raise NotFoundError(ERROR_MESSAGES["NO_VALID_STUDENTS"])
        
        # Manually validate each student document against the response schema
        response_students = []
        for student in students:
            try:
                # Prepare student data for the response schema
                response_data = {
                    "id": str(student["_id"]),
                    "name": student["name"],
                    "age": student["age"],
                    "grade": student["grade"],
                    "email": student["email"],
                    "createdAt": student["createdAt"]
                }
                # Validate and append to the response list
                response_student = StudentResponse.model_validate(response_data)
                response_students.append(response_student)
            except Exception as e:
                # Optionally log validation errors for individual students
                # print(f"Error validating student data: {e} for student: {student}")
                continue # Skip students that fail validation
        
        # If after validation no students are left, raise not found error
        if not response_students:
            raise NotFoundError(ERROR_MESSAGES["NO_VALID_STUDENTS"])
        
        # Calculate pagination metadata
        total_pages = (total_students + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        # Create pagination info object
        pagination_info = PaginationInfo(
            total=total_students,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
        # Create search info object if search was performed
        search_info = SearchInfo(term=search) if search else None
        
        # Return the paginated list of students with metadata
        return StudentListResponse(
            data=response_students,
            pagination=pagination_info,
            search=search_info
        )
    except AppError as e:
        # Handle application-specific errors
        raise handle_app_error(e)
    except Exception as e:
        # Catch any other unexpected exceptions during retrieval
        raise DatabaseError(
            ERROR_MESSAGES["DATABASE_ERROR"],
            {"error": str(e)}
        )

# Endpoint to get a single student by ID (requires authentication)
@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str, # Path parameter for student ID
    current_user: dict = Depends(get_current_user) # Dependency to get authenticated user
):
    """
    Get a student by ID.
    
    Args:
        student_id (str): Student ID
        current_user (dict): Current authenticated user
        
    Returns:
        StudentResponse: Student data
        
    Raises:
        ValidationError: If ID is invalid
        NotFoundError: If student not found
    """
    try:
        # Validate if the provided student_id is a valid MongoDB ObjectId format
        if not ObjectId.is_valid(student_id):
            # Raise validation error for invalid ID format
            raise ValidationError(
                ERROR_MESSAGES["INVALID_ID"],
                {"student_id": student_id}
            )
        
        # Fetch the student from the database by ID
        student = await student_model.get_by_id(ObjectId(student_id))
        
        if not student:
            # Raise not found error if student does not exist
            raise NotFoundError(
                ERROR_MESSAGES["STUDENT_NOT_FOUND"],
                {"student_id": student_id}
            )
        
        # Add 'id' field as string representation of _id for the response schema
        student['id'] = str(student['_id'])
        
        # Return the student data
        return StudentResponse(**student)
    except AppError as e:
        # Handle application-specific errors
        raise handle_app_error(e)

# Endpoint to update an existing student record (requires authentication)
@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str, # Path parameter for student ID
    student_data: StudentUpdate, # Request body with updated student data
    current_user: dict = Depends(get_current_user) # Dependency to get authenticated user
):
    """
    Update a student record.
    
    Args:
        student_id (str): Student ID
        student_data (StudentUpdate): Updated student data
        current_user (dict): Current authenticated user
        
    Returns:
        StudentResponse: Updated student data
        
    Raises:
        ValidationError: If ID is invalid or data is invalid
        NotFoundError: If student not found
    """
    try:
        # Validate if the provided student_id is a valid MongoDB ObjectId format
        if not ObjectId.is_valid(student_id):
            # Raise validation error for invalid ID format
            raise ValidationError(
                ERROR_MESSAGES["INVALID_ID"],
                {"student_id": student_id}
            )
        
        # Check if the student exists
        student = await student_model.get_by_id(ObjectId(student_id))
        if not student:
            # Raise not found error if student does not exist
            raise NotFoundError(
                ERROR_MESSAGES["STUDENT_NOT_FOUND"],
                {"student_id": student_id}
            )
        
        # Convert update data schema to dictionary, excluding unset fields
        update_data = student_data.model_dump(exclude_unset=True)
        
        # Raise validation error if no data is provided for update
        if not update_data:
            raise ValidationError(ERROR_MESSAGES["NO_UPDATE_DATA"])
        
        # If email is being updated, check for email existence among other students
        if "email" in update_data:
            existing_student = await student_model.get_by_email(update_data["email"])
            # Ensure the existing student with the same email is not the current student being updated
            if existing_student and str(existing_student["_id"]) != student_id:
                # Raise validation error if email is already used by another student
                raise ValidationError(
                    ERROR_MESSAGES["EMAIL_EXISTS"],
                    {"email": update_data["email"]}
                )
        
        # Update the student record in the database
        updated = await student_model.update(ObjectId(student_id), update_data)
        
        if not updated:
            # Raise database error if update failed
            raise DatabaseError(ERROR_MESSAGES["UPDATE_FAILED"])
        
        # Fetch the updated student record to return in the response
        updated_student = await student_model.get_by_id(ObjectId(student_id))
        # Add 'id' field as string representation of _id for the response schema
        updated_student['id'] = str(updated_student['_id'])
        
        # Return the updated student data
        return StudentResponse(**updated_student)
    except AppError as e:
        # Handle application-specific errors
        raise handle_app_error(e)

# Endpoint to delete a student record by ID (requires authentication)
@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: str, # Path parameter for student ID
    current_user: dict = Depends(get_current_user) # Dependency to get authenticated user
):
    """
    Delete a student record.
    
    Args:
        student_id (str): Student ID
        current_user (dict): Current authenticated user
        
    Returns:
        None (204 No Content)
        
    Raises:
        ValidationError: If ID is invalid
        NotFoundError: If student not found
    """
    try:
        # Validate if the provided student_id is a valid MongoDB ObjectId format
        if not ObjectId.is_valid(student_id):
            # Raise validation error for invalid ID format
            raise ValidationError(
                ERROR_MESSAGES["INVALID_ID"],
                {"student_id": student_id}
            )
        
        # Check if the student exists
        student = await student_model.get_by_id(ObjectId(student_id))
        if not student:
            # Raise not found error if student does not exist
            raise NotFoundError(
                ERROR_MESSAGES["STUDENT_NOT_FOUND"],
                {"student_id": student_id}
            )
        
        # Delete the student record from the database
        deleted = await student_model.delete(ObjectId(student_id))
        
        if not deleted:
            # Raise database error if deletion failed
            raise DatabaseError(ERROR_MESSAGES["DELETE_FAILED"])
        
        # Return None for 204 No Content response
        return None
    except AppError as e:
        # Handle application-specific errors
        raise handle_app_error(e)