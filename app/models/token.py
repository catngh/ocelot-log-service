from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """
    Enum for user roles in the system.
    """
    ADMIN = "admin"    # Full access to all operations
    WRITER = "writer"  # Can create logs but has limited read access
    READER = "reader"  # Can only read logs, no write access


class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


class TokenData(BaseModel):
    """
    Token data model for authentication and authorization.
    Contains tenant access information and roles.
    """
    tenant_ids: List[str] = []
    roles: List[str] = [UserRole.READER]


class Token(BaseModel):
    """
    Token response model.
    """
    access_token: str
    token_type: str


class JWTToken(BaseModel):
    """
    Model for storing JWT tokens in MongoDB.
    """
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    jti: str = Field(..., description="JWT Token ID - unique identifier for the token")
    tenant_ids: List[str] = Field(default=[], description="Tenant IDs the token has access to")
    roles: List[str] = Field(default=[UserRole.READER], description="Roles assigned to this token")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    revoked: bool = Field(default=False, description="Whether the token has been revoked")
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str} 