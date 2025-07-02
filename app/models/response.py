from typing import Generic, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel, Field

# Define a generic type variable
T = TypeVar('T')

class ResponseWrapper(BaseModel, Generic[T]):
    """
    Generic response wrapper model to provide a consistent API response format.
    All API responses will be wrapped in a "data" field.
    """
    data: T
    meta: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "data": {},
                "meta": {
                    "pagination": {
                        "total": 100,
                        "page": 1,
                        "size": 10
                    }
                }
            }
        }


class PaginatedResponseWrapper(ResponseWrapper[List[T]]):
    """
    Response wrapper for paginated list responses.
    Includes pagination metadata.
    """
    meta: Dict[str, Any] = Field(default_factory=lambda: {
        "pagination": {
            "total": 0,
            "page": 1,
            "size": 10
        }
    })
    
    class Config:
        schema_extra = {
            "example": {
                "data": [],
                "meta": {
                    "pagination": {
                        "total": 100,
                        "page": 1,
                        "size": 10
                    }
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    """
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "error": "Not Found",
                "detail": "The requested resource was not found",
                "code": "RESOURCE_NOT_FOUND"
            }
        } 