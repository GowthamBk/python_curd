# Student Management API

A CRUD API for managing student records with MongoDB and FastAPI.

## Features

- Create, Read, Update, Delete student records
- MongoDB database integration
- Swagger/OpenAPI documentation
- Proper error handling
- Data validation

## Setup

1. Install Python 3.8+
2. Install MongoDB and make sure it's running
3. Create and activate a virtual environment
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file with your MongoDB connection details
6. Run the application: `uvicorn app.main:app --reload`

## API Documentation

After starting the server, access the API documentation at:

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc