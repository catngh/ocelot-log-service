from datetime import datetime, timedelta
from typing import Any, Union, Optional, List, Dict
from passlib.context import CryptContext
from jose import jwt
import uuid
from app.core.config import settings
from app.models.token import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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