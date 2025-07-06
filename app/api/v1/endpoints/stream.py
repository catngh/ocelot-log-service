from typing import Optional, Dict
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, status, Header
from jose import jwt, JWTError

from app.services.stream_service import get_connection_manager
from app.api.deps import get_tenant_id, get_current_token, check_tenant_access
from app.core.security import decode_token
from app.models.token import TokenData
from app.models.log import LogQueryParams
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_token_from_header(
    websocket: WebSocket
) -> Optional[TokenData]:
    """
    Get token data from Authorization header.
    This is needed for WebSocket authentication.
    """
    try:
        # Get token from Authorization header
        auth_header = websocket.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header")
            return None
            
        token = auth_header.replace("Bearer ", "")
        payload = decode_token(token)
        
        token_data = TokenData(
            tenant_ids=payload.get("tenant_ids", []),
            roles=payload.get("roles", [])
        )
        return token_data
    except JWTError as e:
        logger.warning(f"JWT validation error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error parsing token: {str(e)}")
        return None

@router.websocket("/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    filters: Optional[str] = Query(None, description="JSON-encoded filters for log streaming")
):
    """
    WebSocket endpoint for real-time log streaming.
    
    Authentication is done via the Authorization header (Bearer token).
    Tenant ID must be provided in the X-Tenant-ID header.
    
    Optional query parameters:
    - filters: JSON-encoded filters to apply to the log stream
    """
    connection_manager = get_connection_manager()
    connection_id = None
    
    # Validate headers before accepting connection
    try:
        # Extract tenant_id from header
        tenant_id = websocket.headers.get("X-Tenant-ID")
        if not tenant_id:
            logger.warning("WebSocket connection rejected: Missing X-Tenant-ID header")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        # Get and validate token from Authorization header
        token_data = await get_token_from_header(websocket)
        if not token_data:
            logger.warning("WebSocket connection rejected: Invalid or missing token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Check tenant access
        if not token_data.tenant_ids or tenant_id not in token_data.tenant_ids:
            logger.warning(f"WebSocket connection rejected: Tenant {tenant_id} not authorized for token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Check if has at least reader role
        roles = [role.lower() for role in token_data.roles]
        if not any(role in ["admin", "reader"] for role in roles):
            logger.warning(f"WebSocket connection rejected: Insufficient permissions (requires reader role)")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        # Accept connection
        connection_id = await connection_manager.connect(websocket, tenant_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "tenant_id": tenant_id,
            "connection_id": connection_id,
            "message": "Connected to log stream"
        })
        
        # Keep connection alive until client disconnects
        while True:
            # Wait for any message from client (can be used for ping/pong or filter updates)
            data = await websocket.receive_text()
            # Just echo back for now - could be extended to update filters
            await websocket.send_json({
                "type": "echo",
                "data": data
            })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected")
        if connection_id:
            connection_manager.disconnect(websocket, connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        if connection_id:
            connection_manager.disconnect(websocket, connection_id)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass 