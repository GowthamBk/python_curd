from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class StudentBase(BaseModel):
    """
    Base schema for student data with common fields.
    
    Attributes:
        name (str): Student's name (2-50 characters)
        age (int): Student's age
        grade (str): Student's grade (1-10 characters)
        email (str): Student's email address
    """
    name: str = Field(..., min_length=2, max_length=50)
    age: int = Field(...)
    grade: str = Field(..., min_length=1, max_length=10)
    email: str = Field(...)

class StudentCreate(StudentBase):
    """
    Schema for creating a new student.
    Extends StudentBase with additional validation for age and email.
    
    Attributes:
        age (int): Student's age (must be between 1 and 149)
        email (EmailStr): Valid email address
    """
    age: int = Field(..., gt=0, lt=150)
    email: EmailStr

class StudentUpdate(BaseModel):
    """
    Schema for updating an existing student.
    All fields are optional.
    
    Attributes:
        name (Optional[str]): Student's name (2-50 characters)
        age (Optional[int]): Student's age (must be between 1 and 149)
        grade (Optional[str]): Student's grade (1-10 characters)
        email (Optional[EmailStr]): Valid email address
    """
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    age: Optional[int] = Field(None, gt=0, lt=150)
    grade: Optional[str] = Field(None, min_length=1, max_length=10)
    email: Optional[EmailStr] = None

class StudentResponse(StudentBase):
    """
    Schema for student response data.
    Extends StudentBase with additional fields for response.
    
    Attributes:
        id (str): Student's unique identifier
        createdAt (datetime): Timestamp when the student was created
    """
    id: str
    createdAt: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "682d9a1b7943cd79b2fae99d",
                "name": "gowtham",
                "age": 23,
                "grade": "A",
                "email": "gowtham@gmail.com",
                "createdAt": "2025-05-21T09:17:15.814+00:00"
            }
        }

class PaginationInfo(BaseModel):
    """
    Schema for pagination metadata.
    
    Attributes:
        total (int): Total number of items
        page (int): Current page number
        page_size (int): Number of items per page
        total_pages (int): Total number of pages
        has_next (bool): Whether there is a next page
        has_prev (bool): Whether there is a previous page
    """
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "page": 1,
                "page_size": 10,
                "total_pages": 10,
                "has_next": True,
                "has_prev": False
            }
        }

class SearchInfo(BaseModel):
    """
    Schema for search metadata.
    
    Attributes:
        term (str): Search term used
    """
    term: str = Field(..., description="Search term used")

    class Config:
        json_schema_extra = {
            "example": {
                "term": "john"
            }
        }

class StudentListResponse(BaseModel):
    """
    Schema for paginated list of students response.
    
    Attributes:
        data (List[StudentResponse]): List of student records
        pagination (PaginationInfo): Pagination metadata
        search (Optional[SearchInfo]): Search metadata if search was performed
    """
    data: List[StudentResponse] = Field(..., description="List of students")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    search: Optional[SearchInfo] = Field(None, description="Search information if search was performed")
    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "id": "682d9a1b7943cd79b2fae99d",
                        "name": "gowtham",
                        "age": 23,
                        "grade": "A",
                        "email": "gowtham@gmail.com",
                        "createdAt": "2025-05-21T09:17:15.814+00:00"
                    }
                ],
                "pagination": {
                    "total": 100,
                    "page": 1,
                    "page_size": 10,
                    "total_pages": 10,
                    "has_next": True,
                    "has_prev": False
                },
                "search": {
                    "term": "gowtham"
                }
            }
        }
