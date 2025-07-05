from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, status
from pymongo.collection import Collection
from datetime import datetime
from bson import ObjectId

from app.api.deps import (
    get_logs_collection, 
    get_current_token, 
    get_tenant_id, 
    require_admin,
    require_writer,
    require_reader
)
from app.models.token import TokenData
from app.models.log import Log, LogCreate, LogBulkCreate, LogQueryParams, LogInDB
from app.models.response import ResponseWrapper, PaginatedResponseWrapper
from app.services.sqs_service import get_sqs_service, SQSService
from app.services.opensearch_service import get_opensearch_service, OpenSearchService
from app.core.config import settings

router = APIRouter()

@router.get("", response_model=PaginatedResponseWrapper[Log])
async def get_logs(
    query_params: LogQueryParams = Depends(),
    opensearch_service: OpenSearchService = Depends(get_opensearch_service),
    token_data: TokenData = Depends(get_current_token),
    tenant_id: str = Depends(get_tenant_id),
    _: bool = Depends(require_reader),
):
    """
    Get logs with filtering and pagination.
    Uses OpenSearch for improved search capabilities.
    
    Requires reader role only. Writers cannot read logs unless they also have the reader role.
    """
    try:
        # Search logs in OpenSearch
        results = opensearch_service.search_logs(tenant_id, query_params)
        return PaginatedResponseWrapper(**results)
    except Exception as e:
        print(f"OpenSearch error: {str(e)}. Falling back to MongoDB.")
        # Fall back to MongoDB if OpenSearch fails
    
    # MongoDB fallback
    collection = get_logs_collection()
    
    # Start with tenant_id filter for tenant isolation
    query = {"tenant_id": tenant_id}
    
    # Apply filters
    if query_params.action:
        query["action"] = query_params.action
    
    if query_params.resource_type:
        query["resource_type"] = query_params.resource_type
    
    if query_params.resource_id:
        query["resource_id"] = query_params.resource_id
    
    if query_params.severity:
        query["severity"] = query_params.severity
    
    # Additional filters
    if query_params.session_id:
        query["session_id"] = query_params.session_id
    
    if query_params.ip_address:
        query["ip_address"] = query_params.ip_address
    
    if query_params.request_id:
        query["request_id"] = query_params.request_id
    
    if query_params.user_id:
        query["metadata.user_id"] = query_params.user_id
    
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
    
    # Get total count for pagination
    total_count = collection.count_documents(query)
    
    # Execute query with pagination
    logs = list(collection.find(query).skip(query_params.skip).limit(query_params.limit))
    
    # Convert MongoDB _id to id for response
    for log in logs:
        log["id"] = str(log["_id"])
    
    # Calculate pagination metadata
    page = query_params.skip // query_params.limit + 1 if query_params.limit > 0 else 1
    
    # Wrap the response in a data field with pagination metadata
    return PaginatedResponseWrapper(
        data=logs,
        meta={
            "pagination": {
                "total": total_count,
                "page": page,
                "size": query_params.limit
            }
        }
    )


@router.get("/{log_id}", response_model=ResponseWrapper[Log])
async def get_log(
    log_id: str = Path(..., title="The ID of the log to get"),
    opensearch_service: OpenSearchService = Depends(get_opensearch_service),
    token_data: TokenData = Depends(get_current_token),
    tenant_id: str = Depends(get_tenant_id),
    _: bool = Depends(require_reader),
):
    """
    Get a specific log by ID.
    Uses OpenSearch when enabled, otherwise falls back to MongoDB.
    
    Requires reader role only. Writers cannot read logs unless they also have the reader role.
    """
    if not ObjectId.is_valid(log_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid log ID"
        )
    
    log = None
    
    try:
        log = opensearch_service.get_log_by_id(log_id, tenant_id)
    except Exception as e:
        print(f"OpenSearch error: {str(e)}. Falling back to MongoDB")
    
    # Fall back to MongoDB if log not found in OpenSearch or OpenSearch is disabled
    if log is None:
        collection = get_logs_collection()
        # Query with tenant_id for tenant isolation
        mongo_log = collection.find_one({"_id": ObjectId(log_id), "tenant_id": tenant_id})
        
        if mongo_log is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Log not found"
            )
        
        # Convert MongoDB _id to id for response
        mongo_log["id"] = str(mongo_log["_id"])
        log = mongo_log
    
    # Wrap the response in a data field
    return ResponseWrapper(data=log)

# Primary endpoint for creating logs
@router.post("/", response_model=ResponseWrapper[Dict[str, Any]], status_code=status.HTTP_202_ACCEPTED)
async def produce_log(
    log: LogCreate,
    sqs_service: SQSService = Depends(get_sqs_service),
    token_data: TokenData = Depends(get_current_token),
    tenant_id: str = Depends(get_tenant_id),
    _: bool = Depends(require_writer),
):
    """
    Send a log entry to SQS queue for asynchronous processing.
    
    Requires writer role only. Readers cannot create logs.
    """
    # Create a message with timestamp and tenant_id
    message = log.dict()
    message["timestamp"] = datetime.utcnow().isoformat()
    message["tenant_id"] = tenant_id  # Add tenant_id for tenant isolation
    
    # Send to SQS
    response = sqs_service.send_message(message)
    
    # Return the SQS message ID
    return ResponseWrapper(data={"message_id": response["MessageId"], "status": "queued"})


@router.post("/bulk", response_model=ResponseWrapper[Dict[str, Any]], status_code=status.HTTP_202_ACCEPTED)
async def produce_logs_bulk(
    logs_data: LogBulkCreate,
    sqs_service: SQSService = Depends(get_sqs_service),
    token_data: TokenData = Depends(get_current_token),
    tenant_id: str = Depends(get_tenant_id),
    _: bool = Depends(require_writer),
):
    """
    Send multiple log entries to SQS queue for asynchronous processing.
    
    Requires writer role only. Readers cannot create logs.
    """
    message_ids = []
    
    # Process each log and send to SQS
    for log in logs_data.logs:
        message = log.dict()
        message["timestamp"] = datetime.utcnow().isoformat()
        message["tenant_id"] = tenant_id
        
        # Send to SQS
        response = sqs_service.send_message(message)
        message_ids.append(response["MessageId"])
    
    # Return the SQS message IDs
    return ResponseWrapper(data={"message_ids": message_ids, "count": len(message_ids), "status": "queued"})

@router.post("/index/bulk", response_model=ResponseWrapper[Dict[str, Any]], status_code=status.HTTP_200_OK)
async def bulk_index_logs(
    start_time: Optional[datetime] = Query(None, description="Start time for logs to index"),
    end_time: Optional[datetime] = Query(None, description="End time for logs to index"),
    limit: int = Query(100, description="Maximum number of logs to index", ge=1, le=1000),
    opensearch_service: OpenSearchService = Depends(get_opensearch_service),
    token_data: TokenData = Depends(get_current_token),
    tenant_id: str = Depends(get_tenant_id),
    _: bool = Depends(require_admin),
):
    """
    Bulk index logs in OpenSearch.
    
    Requires admin role.
    """
    # Build query
    query = {"tenant_id": tenant_id}
    
    # Date range filter
    if start_time or end_time:
        date_query = {}
        if start_time:
            date_query["$gte"] = start_time
        if end_time:
            date_query["$lte"] = end_time
        query["timestamp"] = date_query
    
    # Get logs from MongoDB
    collection = get_logs_collection()
    logs = list(collection.find(query).limit(limit))
    
    if not logs:
        return ResponseWrapper(data={"message": "No logs found to index", "count": 0})
    
    # Index logs in OpenSearch
    indexed_count = 0
    errors = []
    
    for log in logs:
        try:
            # Convert ObjectId to string
            log["_id"] = str(log["_id"])
            
            # Index in OpenSearch
            opensearch_service.index_log(log)
            indexed_count += 1
        except Exception as e:
            errors.append({"log_id": str(log["_id"]), "error": str(e)})
    
    return ResponseWrapper(data={
        "message": "Bulk indexing completed",
        "total": len(logs),
        "indexed": indexed_count,
        "errors": len(errors),
        "error_details": errors[:10] if errors else []  # Return first 10 errors only
    }) 