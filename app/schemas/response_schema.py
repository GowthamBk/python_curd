from pydantic import BaseModel
from typing import Any, Optional, List, Dict

class ErrorDetail(BaseModel):
    type: str
    loc: List[str]
    msg: str
    input: Any
    ctx: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    details: Optional[Dict[str, Any]] = None
    errors: Optional[List[ErrorDetail]] = None

class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
    message: Optional[str] = None 