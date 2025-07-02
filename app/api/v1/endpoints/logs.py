from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, status
from pymongo.collection import Collection
from datetime import datetime
from bson import ObjectId

from app.api.deps import get_logs_collection, get_current_user, get_tenant_id
from app.models.user import TokenData
from app.models.log import Log, LogCreate, LogBulkCreate, LogQueryParams, LogInDB

router = APIRouter()


@router.post("", response_model=Log, status_code=status.HTTP_201_CREATED)
async def create_log(
    log: LogCreate,
    collection: Collection = Depends(get_logs_collection),
    current_user: TokenData = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Create a new log entry.
    """
    # Create a LogInDB object with timestamp and tenant_id
    log_dict = log.dict()
    log_dict["timestamp"] = datetime.utcnow()
    log_dict["tenant_id"] = tenant_id  # Add tenant_id for tenant isolation
    
    # Insert into MongoDB
    result = collection.insert_one(log_dict)
    
    # Get the created log
    created_log = collection.find_one({"_id": result.inserted_id})
    
    if created_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Log not found"
        )
    
    # Convert MongoDB _id to id for response
    created_log["id"] = str(created_log["_id"])
    
    return created_log


@router.post("/bulk", response_model=List[Log], status_code=status.HTTP_201_CREATED)
async def create_logs_bulk(
    logs_data: LogBulkCreate,
    collection: Collection = Depends(get_logs_collection),
    current_user: TokenData = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Create multiple log entries in bulk.
    """
    # Add timestamp and tenant_id to each log
    logs_dict = []
    for log in logs_data.logs:
        log_dict = log.dict()
        log_dict["timestamp"] = datetime.utcnow()
        log_dict["tenant_id"] = tenant_id  # Add tenant_id for tenant isolation
        logs_dict.append(log_dict)
    
    result = collection.insert_many(logs_dict)
    
    # Get the created logs
    created_logs = list(collection.find(
        {"_id": {"$in": list(result.inserted_ids)}}
    ))
    
    # Convert MongoDB _id to id for response
    for log in created_logs:
        log["id"] = str(log["_id"])
    
    return created_logs


@router.get("", response_model=List[Log])
async def get_logs(
    query_params: LogQueryParams = Depends(),
    collection: Collection = Depends(get_logs_collection),
    current_user: TokenData = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get logs with filtering and pagination.
    """
    # Start with tenant_id filter for tenant isolation
    query = {"tenant_id": tenant_id}
    
    # Apply filters
    if query_params.user_id:
        query["user_id"] = query_params.user_id
    
    if query_params.action:
        query["action"] = query_params.action
    
    if query_params.resource_type:
        query["resource_type"] = query_params.resource_type
    
    if query_params.resource_id:
        query["resource_id"] = query_params.resource_id
    
    if query_params.severity:
        query["severity"] = query_params.severity
    
    # Date range filter
    date_query = {}
    if query_params.start_time:
        date_query["$gte"] = query_params.start_time
    
    if query_params.end_time:
        date_query["$lte"] = query_params.end_time
    
    if date_query:
        query["timestamp"] = date_query
    
    # Text search
    if query_params.search:
        query["$text"] = {"$search": query_params.search}
    
    # Execute query with pagination
    logs = list(collection.find(query).skip(query_params.skip).limit(query_params.limit))
    
    # Convert MongoDB _id to id for response
    for log in logs:
        log["id"] = str(log["_id"])
    
    return logs


@router.get("/{log_id}", response_model=Log)
async def get_log(
    log_id: str = Path(..., title="The ID of the log to get"),
    collection: Collection = Depends(get_logs_collection),
    current_user: TokenData = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get a specific log by ID.
    """
    if not ObjectId.is_valid(log_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid log ID"
        )
    
    # Query with tenant_id for tenant isolation
    log = collection.find_one({"_id": ObjectId(log_id), "tenant_id": tenant_id})
    
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Log not found"
        )
    
    # Convert MongoDB _id to id for response
    log["id"] = str(log["_id"])
    
    return log 