from typing import Generator, Optional, Dict, Any, List
from fastapi import Depends, HTTPException, status, Header, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import ValidationError
from pymongo.database import Database
from pymongo.collection import Collection
from datetime import datetime

from app.db.mongodb import get_database, get_collection, get_jwt_collection
from app.core.config import settings
from app.models.token import TokenData, UserRole
from app.core.security import decode_token

# Use HTTPBearer for authentication
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
        
        if not jti:
            raise credentials_exception
        
        # Check if token exists in database and is not revoked
        jwt_collection = get_jwt_collection()
        stored_token = jwt_collection.find_one({"jti": jti})
        
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
            
        return stored_token
    except Exception as e:
        print(f"Error validating token: {str(e)}")
        raise credentials_exception


async def get_current_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> TokenData:
    """
    Get token data from JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Get token from credentials
        token = credentials.credentials
        
        # Decode token without verification to get the JTI
        payload = decode_token(token)
        
        # Extract JTI
        jti = payload.get("jti")
        
        if not jti:
            raise credentials_exception
        
        # Get token data from database
        jwt_collection = get_jwt_collection()
        stored_token = jwt_collection.find_one({"jti": jti})
        
        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not found in database",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract claims from stored token instead of payload
        tenant_ids = stored_token.get("tenant_ids", [])
        roles = stored_token.get("roles", [])
        
        token_data = TokenData(
            tenant_ids=tenant_ids,
            roles=roles
        )
        
    except (JWTError, ValidationError) as e:
        print(f"Token validation error: {str(e)}")
        raise credentials_exception
    
    return token_data


async def check_tenant_access(
    tenant_id: str = Depends(get_tenant_id),
    token_data: TokenData = Depends(get_current_token),
) -> bool:
    """
    Check if the token has access to the specified tenant.
    """
    if not token_data.tenant_ids or tenant_id not in token_data.tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token does not have access to tenant {tenant_id}",
        )
    return True


def check_role_permissions(required_roles: List[str]):
    """
    Dependency factory to check if the user has the required role(s).
    
    Args:
        required_roles: List of roles that are allowed to access the endpoint
        
    Returns:
        Dependency function that checks if the user has one of the required roles
    """
    async def _check_roles(token_data: TokenData = Depends(get_current_token)):
        # Convert roles to strings for consistent comparison
        user_roles = [role if isinstance(role, str) else role.value for role in token_data.roles]
        required_role_values = [role if isinstance(role, str) else role.value for role in required_roles]
        
        # Admin role has access to everything
        if "admin" in user_roles:
            return True
            
        # Check if any of the user's roles are in the required roles list
        if not any(user_role in required_role_values for user_role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(required_role_values)}",
            )
        return True
        
    return _check_roles


# Role-based permission dependencies
require_admin = check_role_permissions(["admin"])
require_writer = check_role_permissions(["admin", "writer"])
require_reader = check_role_permissions(["admin", "writer", "reader"]) 