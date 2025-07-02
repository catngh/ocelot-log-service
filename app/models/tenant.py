from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId


class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


class TenantSettings(BaseModel):
    retention_days: int = 90
    log_levels: List[str] = ["INFO", "WARNING", "ERROR", "CRITICAL"]


class TenantBase(BaseModel):
    tenant_id: str
    name: str
    settings: TenantSettings = TenantSettings()


class TenantCreate(TenantBase):
    api_key: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[TenantSettings] = None


class TenantInDB(TenantBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    api_keys: List[str] = []  # Hashed API keys

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}


class Tenant(TenantBase):
    id: str
    created_at: datetime

    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "tenant_id": "acme-corp",
                "name": "ACME Corporation",
                "settings": {
                    "retention_days": 90,
                    "log_levels": ["INFO", "WARNING", "ERROR", "CRITICAL"]
                },
                "created_at": "2023-01-01T00:00:00"
            }
        } 