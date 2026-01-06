"""
Authentication and authorization for multi-tenant SaaS.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_pool

# Security
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # Bcrypt has a 72-byte limit, so truncate if necessary
    # Convert to bytes to check length properly
    password_bytes = password.encode('utf-8')
    
    # If password is too long, truncate to exactly 72 bytes
    # We need to be careful not to break UTF-8 sequences
    if len(password_bytes) > 72:
        # Truncate to 72 bytes
        truncated = password_bytes[:72]
        
        # Remove any incomplete UTF-8 sequences at the end
        # UTF-8 continuation bytes start with 10xxxxxx (0x80-0xBF)
        # We need to find the last byte that starts a character
        while truncated:
            last_byte = truncated[-1]
            # If it's a continuation byte (10xxxxxx), remove it
            if (last_byte & 0xC0) == 0x80:
                truncated = truncated[:-1]
            else:
                break
        
        # Decode the truncated bytes - this is safe now
        password = truncated.decode('utf-8', errors='ignore')
        
        # Final safety check: ensure the decoded password, when re-encoded, is <= 72 bytes
        # If not, truncate the string character by character until it fits
        while True:
            test_bytes = password.encode('utf-8')
            if len(test_bytes) <= 72:
                break
            # Remove last character and try again
            if len(password) > 0:
                password = password[:-1]
            else:
                # Edge case: empty string somehow encodes to > 72 bytes (shouldn't happen)
                password = ""
                break
    
    # Now hash - password is guaranteed to be <= 72 bytes when encoded
    # But passlib might check the original string, so let's pass the truncated version
    # Actually, passlib checks the byte length of what we pass, so we're good
    return pwd_context.hash(password)


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
