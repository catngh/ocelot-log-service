from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
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


class LogAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VIEW = "VIEW"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    READ = "READ"


class LogSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogBase(BaseModel):
    session_id: Optional[str] = None
    action: LogAction
    resource_type: str
    resource_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    severity: LogSeverity = LogSeverity.INFO
    message: str
    request_id: Optional[str] = None


class LogCreate(LogBase):
    pass


class LogBulkCreate(BaseModel):
    logs: List[LogCreate]


class LogInDB(LogBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}


class Log(LogBase):
    id: str
    timestamp: datetime
    tenant_id: str

    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "session_id": "session456",
                "action": "CREATE",
                "resource_type": "user",
                "resource_id": "user789",
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "before_state": None,
                "after_state": {"name": "John Doe", "email": "john@example.com"},
                "metadata": {"source": "web"},
                "severity": "INFO",
                "message": "User created",
                "request_id": "req123",
                "timestamp": "2023-01-01T00:00:00",
                "tenant_id": "tenant1"
            }
        }


class LogQueryParams(BaseModel):
    # Basic filters
    action: Optional[LogAction] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    severity: Optional[LogSeverity] = None
    
    # Time range filters
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Additional common filters
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    
    # Full-text search
    search: Optional[str] = None
    
    # Pagination
    skip: int = 0
    limit: int = 100 