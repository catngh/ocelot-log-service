import logging
from typing import Dict, Set, List, Any
from fastapi import WebSocket, WebSocketDisconnect
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Connection manager for WebSocket connections.
    Handles tenant-scoped connections and message broadcasting.
    """
    
    def __init__(self):
        # Dict mapping tenant_id -> set of connected WebSockets
        self.tenant_connections: Dict[str, Set[WebSocket]] = {}
        # Dict mapping connection id -> tenant_id
        self.connection_tenants: Dict[str, str] = {}
        # Counter for unique connection IDs
        self.connection_counter = 0
    
    async def connect(self, websocket: WebSocket, tenant_id: str) -> str:
        """
        Connect a new WebSocket client for a specific tenant.
        
        Args:
            websocket: The WebSocket connection
            tenant_id: The tenant ID for isolation
            
        Returns:
            connection_id: A unique ID for this connection
        """
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = f"{tenant_id}_{self.connection_counter}"
        self.connection_counter += 1
        
        # Add to tenant connections
        if tenant_id not in self.tenant_connections:
            self.tenant_connections[tenant_id] = set()
        
        self.tenant_connections[tenant_id].add(websocket)
        self.connection_tenants[connection_id] = tenant_id
        
        logger.info(f"New WebSocket connection for tenant {tenant_id}, connection_id: {connection_id}")
        
        return connection_id
    
    def disconnect(self, websocket: WebSocket, connection_id: str):
        """
        Disconnect a WebSocket client.
        
        Args:
            websocket: The WebSocket connection to disconnect
            connection_id: The connection ID to remove
        """
        if connection_id in self.connection_tenants:
            tenant_id = self.connection_tenants[connection_id]
            
            if tenant_id in self.tenant_connections:
                self.tenant_connections[tenant_id].discard(websocket)
                
                # Clean up empty tenant sets
                if not self.tenant_connections[tenant_id]:
                    del self.tenant_connections[tenant_id]
            
            del self.connection_tenants[connection_id]
            logger.info(f"WebSocket disconnected for tenant {tenant_id}, connection_id: {connection_id}")
    
    async def broadcast_to_tenant(self, tenant_id: str, log_data: Dict[str, Any]):
        """
        Broadcast a log message to all connections for a specific tenant.
        
        Args:
            tenant_id: The tenant ID to broadcast to
            log_data: The log data to broadcast
        """
        if tenant_id not in self.tenant_connections:
            return
        
        # Format timestamp for JSON serialization if needed
        if isinstance(log_data.get("timestamp"), datetime):
            log_data["timestamp"] = log_data["timestamp"].isoformat()
        
        # Convert ObjectId to string if needed
        if log_data.get("_id"):
            log_data["id"] = str(log_data["_id"])
            del log_data["_id"]
        
        # Convert to JSON string
        message = json.dumps(log_data)
        
        # Get a copy of the connections to avoid modification during iteration
        connections = self.tenant_connections[tenant_id].copy()
        
        # Track disconnected websockets for cleanup
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except RuntimeError:
                # Connection already closed
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.tenant_connections[tenant_id].discard(websocket)
        
        logger.debug(f"Broadcasted log to {len(connections) - len(disconnected)} connections for tenant {tenant_id}")

# Singleton instance
connection_manager = ConnectionManager()

def get_connection_manager() -> ConnectionManager:
    """
    Get the connection manager singleton.
    """
    return connection_manager

def broadcast_log(tenant_id: str, log_data: Dict[str, Any]):
    """
    Broadcast a log to all connections for a specific tenant.
    This is a non-async helper for code that can't use async functions.
    
    Args:
        tenant_id: The tenant ID to broadcast to
        log_data: The log data to broadcast
    """
    import asyncio
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Create a task if we're in an async context
        asyncio.create_task(connection_manager.broadcast_to_tenant(tenant_id, log_data))
    else:
        # Create a new event loop if we're not in an async context
        new_loop = asyncio.new_event_loop()
        new_loop.run_until_complete(connection_manager.broadcast_to_tenant(tenant_id, log_data))
        new_loop.close() 