from typing import Generator, Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header, Security
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import ValidationError
from pymongo.database import Database
from pymongo.collection import Collection
from datetime import datetime

from app.db.mongodb import get_database, get_collection, get_jwt_collection
from app.core.config import settings
from app.models.user import TokenData
from app.core.security import decode_token

# Use HTTPBearer instead of OAuth2PasswordBearer since we're not using the login flow
security = HTTPBearer(auto_error=True)


def get_db() -> Database:
    """
    Get MongoDB database dependency.
    """
    return get_database()


async def get_tenant_id(x_tenant_id: str = Header(...)) -> str:
    """
    Get tenant ID from header.
    """
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required",
        )
    return x_tenant_id


def get_logs_collection(
    tenant_id: str = Depends(get_tenant_id),
) -> Collection:
    """
    Get logs collection.
    
    Instead of creating a tenant-specific collection, we use a single logs collection
    and filter by tenant_id for tenant isolation.
    """
    db = get_database()
    return db["logs"]


def get_tenant_collection() -> Collection:
    """
    Get tenants collection.
    """
    db = get_database()
    return db["tenants"]


async def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate a JWT token against the database.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict containing the decoded token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or revoked
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode token without verification to get the JTI
        payload = decode_token(token)
        
        # Extract claims
        jti = payload.get("jti")
        user_id = payload.get("sub")
        
        if not jti or not user_id:
            raise credentials_exception
        
        # Check if token exists in database and is not revoked
        jwt_collection = get_jwt_collection()
        stored_token = jwt_collection.find_one({"jti": jti, "user_id": user_id})
        
        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not found in database",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Check if token is revoked
        if stored_token.get("revoked", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Check if token is expired
        expires_at = stored_token.get("expires_at")
        if expires_at and expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return payload
        
    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> TokenData:
    """
    Get current user from JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Get token from credentials
        token = credentials.credentials
        
        # Validate token against database
        payload = await validate_token(token)
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Extract additional claims
        tenant_ids = payload.get("tenant_ids", [])
        roles = payload.get("roles", ["user"])
        
        token_data = TokenData(
            user_id=user_id,
            tenant_ids=tenant_ids,
            roles=roles
        )
        
    except (JWTError, ValidationError):
        raise credentials_exception
    
    return token_data


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """
    Get current active user.
    """
    # Here you could check if the user is active in the database
    # For now, we'll just return the token data
    return current_user


async def check_user_tenant_access(
    tenant_id: str = Depends(get_tenant_id),
    current_user: TokenData = Depends(get_current_user),
) -> bool:
    """
    Check if the current user has access to the specified tenant.
    """
    if not current_user.tenant_ids or tenant_id not in current_user.tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have access to tenant {tenant_id}",
        )
    return True 