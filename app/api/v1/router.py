from fastapi import APIRouter
from app.api.v1.endpoints import logs, tenants, stream

api_router = APIRouter()

# Include routers for different resources
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(stream.router, prefix="/logs", tags=["logs", "streaming"])