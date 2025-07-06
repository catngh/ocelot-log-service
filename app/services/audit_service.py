import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient

from app.models.audit import AuditTrail
from app.models.token import TokenData
from app.core.config import settings

logger = logging.getLogger(__name__)

class AuditService:
    """Service for recording audit trail events asynchronously."""
    
    def __init__(self):
        """Initialize the audit service."""
        self.client = None
        self.db = None
        self.collection = None
        
    async def initialize(self):
        """Initialize MongoDB connection."""
        if self.client is None:
            try:
                # Connect to MongoDB
                self.client = AsyncIOMotorClient(settings.MONGODB_URL)
                self.db = self.client[settings.MONGODB_DB]
                self.collection = self.db["audit_trail"]
                
                # Create index on tenant_id and timestamp
                await self.collection.create_index([("tenant_id", 1), ("timestamp", -1)])
                
                logger.info("Initialized audit trail service")
            except Exception as e:
                logger.error(f"Error initializing audit service: {str(e)}")
                raise
    
    async def record_log_access(
        self,
        tenant_id: str,
        token_data: TokenData,
        action: str,
        resource_path: str,
        query_params: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """
        Record an audit trail entry for log access.
        
        Args:
            tenant_id: The ID of the tenant
            token_data: The token data of the user
            action: The action being performed (e.g., "get_logs")
            resource_path: The API path being accessed
            query_params: Optional query parameters used in the request
            request: Optional FastAPI request object
        """
        await self.initialize()
        
        try:
            # Build the audit entry
            audit_entry = AuditTrail(
                tenant_id=tenant_id,
                user_id=token_data.sub if token_data else None,
                token_id=token_data.jti if token_data else None,
                action=action,
                resource_path=resource_path,
                query_params=query_params,
                timestamp=datetime.utcnow()
            )
            
            # Add request info if available
            if request:
                audit_entry.ip_address = request.client.host if request.client else None
                audit_entry.request_id = request.headers.get("X-Request-ID")
            
            # Insert into database asynchronously
            await self.collection.insert_one(audit_entry.dict(by_alias=True))
            
            logger.debug(f"Recorded audit trail: {tenant_id} - {action}")
        except Exception as e:
            # Log error but don't fail the request
            logger.error(f"Error recording audit trail: {str(e)}")

# Singleton instance
_audit_service = AuditService()

async def get_audit_service():
    """Get the audit service singleton."""
    await _audit_service.initialize()
    return _audit_service

def create_audit_log_task(
    tenant_id: str,
    token_data: TokenData,
    action: str,
    resource_path: str,
    query_params: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Create a function that will record an audit log entry.
    This function is designed to be used with FastAPI's BackgroundTasks.
    
    Returns:
        A function that can be called with no arguments to record the audit log
    """
    async def _record():
        service = await get_audit_service()
        await service.record_log_access(
            tenant_id=tenant_id,
            token_data=token_data,
            action=action,
            resource_path=resource_path,
            query_params=query_params,
            request=request
        )
    
    # Return the function - don't create a task here
    # FastAPI's background_tasks.add_task will handle this
    return _record 