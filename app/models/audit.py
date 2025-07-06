from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId

class AuditTrail(BaseModel):
    """Model for audit trail entries."""
    id: Optional[str] = Field(None, alias="_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str
    user_id: Optional[str] = None
    token_id: Optional[str] = None
    action: str  # e.g., "get_logs", "get_log", etc.
    resource_path: str  # e.g., "/api/v1/logs"
    query_params: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        } 