"""Security utilities for authentication and authorization."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from schedora.config import get_settings

settings = get_settings()

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token (typically {"sub": user_id})
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token({"sub": str(user_id)})
        >>> # Token expires in 24 hours (default)
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded payload dictionary

    Raises:
        JWTError: If token is invalid, expired, or malformed

    Example:
        >>> payload = decode_access_token(token)
        >>> user_id = payload.get("sub")
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return payload


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key pair.

    Returns:
        Tuple of (plaintext_key, key_hash, key_prefix)
        - plaintext_key: The full API key (show only once to user)
        - key_hash: Hashed version to store in database
        - key_prefix: First characters for display purposes

    Example:
        >>> key, key_hash, prefix = generate_api_key()
        >>> # key = "sk_live_abc123..."
        >>> # prefix = "sk_live_abc"
        >>> # Store key_hash in database, show key to user once
    """
    # Generate secure random key
    random_part = secrets.token_urlsafe(32)
    plaintext_key = f"sk_live_{random_part}"

    # Hash the key for storage (same as password hashing)
    key_hash = hash_password(plaintext_key)

    # Extract prefix for display (first 11 characters: sk_live_xxx)
    key_prefix = plaintext_key[:11]

    return plaintext_key, key_hash, key_prefix


def verify_api_key(plaintext_key: str, key_hash: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        plaintext_key: The API key provided by the user
        key_hash: The hashed key stored in the database

    Returns:
        True if key matches, False otherwise
    """
    return verify_password(plaintext_key, key_hash)
