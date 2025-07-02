from datetime import datetime, timedelta
from typing import Any, Union, Optional, List, Dict
from passlib.context import CryptContext
from jose import jwt
import uuid
from app.core.config import settings
from app.models.token import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    tenant_ids: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None
) -> Dict[str, Any]:
    """
    Create a JWT access token with tenant and role claims.
    
    Returns:
        Dict containing the token and its metadata
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Generate a unique token ID (jti)
    jti = generate_jti()
    
    to_encode = {
        "exp": expire,
        "jti": jti,
        "iat": datetime.utcnow()
    }
    
    # Add tenant IDs if provided
    if tenant_ids:
        to_encode["tenant_ids"] = tenant_ids
        
    # Add roles if provided
    if roles:
        to_encode["roles"] = roles
    
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    
    # Return both the token and its metadata
    return {
        "token": encoded_jwt,
        "jti": jti,
        "tenant_ids": tenant_ids or [],
        "roles": roles or [UserRole.READER],
        "expires_at": expire
    }


def generate_jti() -> str:
    """
    Generate a unique JWT ID (jti) for token tracking.
    """
    return str(uuid.uuid4())


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    """
    return pwd_context.hash(password)

def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token and return its payload.
    
    Raises:
        JWTError: If the token is invalid
    """
    return jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    ) 