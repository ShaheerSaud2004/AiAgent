"""
Authentication and authorization for multi-tenant SaaS.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_pool

# Security
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    # Truncate password to 72 bytes if needed (bcrypt limit)
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        truncated = password_bytes[:72]
        # Remove incomplete UTF-8 sequences
        while truncated and (truncated[-1] & 0xC0) == 0x80:
            truncated = truncated[:-1]
        plain_password = truncated.decode('utf-8', errors='ignore')
    
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt directly.
    
    Bcrypt has a 72-byte limit. This function ensures the password
    is truncated to 72 bytes before hashing, handling UTF-8 boundaries correctly.
    """
    # Convert to bytes to check actual byte length
    password_bytes = password.encode('utf-8')
    
    # If password exceeds 72 bytes, truncate it
    if len(password_bytes) > 72:
        # Truncate to 72 bytes
        truncated_bytes = password_bytes[:72]
        
        # Remove any incomplete UTF-8 sequences at the end
        # UTF-8 continuation bytes have pattern 10xxxxxx (0x80-0xBF)
        while truncated_bytes:
            last_byte = truncated_bytes[-1]
            # If it's a continuation byte, remove it to avoid breaking UTF-8
            if (last_byte & 0xC0) == 0x80:
                truncated_bytes = truncated_bytes[:-1]
            else:
                break
        
        # Use truncated bytes directly for hashing
        password_bytes = truncated_bytes
    
    # Hash using bcrypt directly (bypasses passlib's validation)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
        return dict(row) if row else None


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return dict(row) if row else None


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate a user."""
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_organization(user: dict = Depends(get_current_user)) -> int:
    """Get current user's organization ID."""
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with an organization"
        )
    return org_id
