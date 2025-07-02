from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime


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
    user_id: str
    tenant_ids: Optional[List[str]] = None
    roles: Optional[List[str]] = None


class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    tenant_ids: List[str] = []
    roles: List[str] = ["user"]
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}


class User(UserBase):
    id: str

    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "full_name": "John Doe",
                "tenant_ids": ["tenant1", "tenant2"],
                "roles": ["admin", "user"],
                "is_active": True,
            }
        }


class Token(BaseModel):
    access_token: str
    token_type: str


class JWTToken(BaseModel):
    """Model for storing JWT tokens in MongoDB"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    jti: str = Field(..., description="JWT Token ID - unique identifier for the token")
    user_id: str = Field(..., description="User ID the token belongs to")
    tenant_ids: List[str] = Field(default=[], description="Tenant IDs the user has access to")
    roles: List[str] = Field(default=["user"], description="User roles")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    revoked: bool = Field(default=False, description="Whether the token has been revoked")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str} 