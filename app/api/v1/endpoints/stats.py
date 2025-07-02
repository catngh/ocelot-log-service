from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.collection import Collection
from datetime import datetime, timedelta

from app.api.deps import (
    get_logs_collection, 
    get_current_token, 
    require_admin, 
    require_reader
)
from app.models.token import TokenData
from app.models.log import LogAction, LogSeverity
from app.models.response import ResponseWrapper

router = APIRouter()


@router.get("/count", response_model=ResponseWrapper[Dict[str, int]])
async def get_log_count(
    collection: Collection = Depends(get_logs_collection),
    token_data: TokenData = Depends(get_current_token),
    _: bool = Depends(require_reader),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """
    Get total log count with optional date range filter.
    
    Requires reader role only. Writers cannot access stats unless they also have the reader role.
    """
    query = {}
    
    # Date range filter
    date_query = {}
    if start_time:
        date_query["$gte"] = start_time
    
    if end_time:
        date_query["$lte"] = end_time
    
    if date_query:
        query["timestamp"] = date_query
    
    # Count logs
    log_count = collection.count_documents(query)
    
    # Wrap the response in a data field
    return ResponseWrapper(data={"count": log_count})


@router.get("/by-severity", response_model=ResponseWrapper[Dict[str, int]])
async def get_logs_by_severity(
    collection: Collection = Depends(get_logs_collection),
    token_data: TokenData = Depends(get_current_token),
    _: bool = Depends(require_reader),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """
    Get log counts grouped by severity level.
    
    Requires reader role only. Writers cannot access stats unless they also have the reader role.
    """
    pipeline = []
    
    # Date range filter
    match_stage = {}
    if start_time or end_time:
        date_query = {}
        if start_time:
            date_query["$gte"] = start_time
        if end_time:
            date_query["$lte"] = end_time
        match_stage["timestamp"] = date_query
    
    if match_stage:
        pipeline.append({"$match": match_stage})
    
    # Group by severity
    pipeline.append({
        "$group": {
            "_id": "$severity",
            "count": {"$sum": 1}
        }
    })
    
    # Execute aggregation
    results = list(collection.aggregate(pipeline))
    
    # Format result
    stats = {severity.value: 0 for severity in LogSeverity}
    for result in results:
        severity = result["_id"]
        if severity in stats:
            stats[severity] = result["count"]
    
    # Wrap the response in a data field
    return ResponseWrapper(data=stats)


@router.get("/by-action", response_model=ResponseWrapper[Dict[str, int]])
async def get_logs_by_action(
    collection: Collection = Depends(get_logs_collection),
    token_data: TokenData = Depends(get_current_token),
    _: bool = Depends(require_reader),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """
    Get log counts grouped by action type.
    
    Requires reader role only. Writers cannot access stats unless they also have the reader role.
    """
    pipeline = []
    
    # Date range filter
    match_stage = {}
    if start_time or end_time:
        date_query = {}
        if start_time:
            date_query["$gte"] = start_time
        if end_time:
            date_query["$lte"] = end_time
        match_stage["timestamp"] = date_query
    
    if match_stage:
        pipeline.append({"$match": match_stage})
    
    # Group by action
    pipeline.append({
        "$group": {
            "_id": "$action",
            "count": {"$sum": 1}
        }
    })
    
    # Execute aggregation
    results = list(collection.aggregate(pipeline))
    
    # Format result
    stats = {action.value: 0 for action in LogAction}
    for result in results:
        action = result["_id"]
        if action in stats:
            stats[action] = result["count"]
    
    # Wrap the response in a data field
    return ResponseWrapper(data=stats)


@router.get("/daily", response_model=ResponseWrapper[List[Dict[str, Any]]])
async def get_daily_log_counts(
    collection: Collection = Depends(get_logs_collection),
    token_data: TokenData = Depends(get_current_token),
    _: bool = Depends(require_reader),
    days: int = Query(7, ge=1, le=30),
):
    """
    Get daily log counts for the specified number of days.
    
    Requires reader role only. Writers cannot access stats unless they also have the reader role.
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # Aggregation pipeline
    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": start_time, "$lte": end_time}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}
                },
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    
    # Execute aggregation
    results = list(collection.aggregate(pipeline))
    
    # Format result
    current_date = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_counts = []
    
    # Initialize dict of dates
    date_dict = {}
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        date_dict[date_str] = 0
        current_date += timedelta(days=1)
    
    # Fill dict with actual counts
    for result in results:
        date_str = result["_id"]
        date_dict[date_str] = result["count"]
    
    # Convert to list of dicts
    for date_str, count in date_dict.items():
        daily_counts.append({"date": date_str, "count": count})
    
    # Wrap the response in a data field
    return ResponseWrapper(data=daily_counts) 