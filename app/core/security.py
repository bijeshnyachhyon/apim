# Security utilities: JWT, API key hashing, password hashing
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# API Key hashing
def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate API key. Returns (full_key, prefix, hash)
    Full key is only shown once at creation.
    """
    random_part = secrets.token_hex(24)  # 48 hex chars
    full_key = f"{settings.API_KEY_PREFIX}{random_part}"
    prefix = full_key[:len(settings.API_KEY_PREFIX) + 8]
    key_hash = hash_api_key(full_key)
    return full_key, prefix, key_hash

def verify_api_key(plain_key: str, stored_hash: str) -> bool:
    return hash_api_key(plain_key) == stored_hash

# JWT tokens
def load_jwt_keys():
    if settings.JWT_PRIVATE_KEY_PATH and settings.JWT_PUBLIC_KEY_PATH:
        try:
            with open(settings.JWT_PRIVATE_KEY_PATH, "r") as f:
                private_key = serialization.load_pem_private_key(
                    f.read().encode(), password=None, backend=default_backend()
                )
            with open(settings.JWT_PUBLIC_KEY_PATH, "r") as f:
                public_key = serialization.load_pem_public_key(
                    f.read().encode(), backend=default_backend()
                )
            return private_key, public_key
        except Exception:
            pass
    # Fallback: generate ephemeral RSA key pair for dev
    from cryptography.hazmat.primitives.asymmetric import rsa
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    public_key = private_key.public_key()
    return private_key, public_key

_jwt_private_key = None
_jwt_public_key = None

def get_jwt_private_key():
    global _jwt_private_key
    if _jwt_private_key is None:
        _jwt_private_key, _ = load_jwt_keys()
    return _jwt_private_key

def get_jwt_public_key():
    global _jwt_public_key
    if _jwt_public_key is None:
        _, _jwt_public_key = load_jwt_keys()
    return _jwt_public_key

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    private_key = get_jwt_private_key()
    return jwt.encode(to_encode, private_key, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    private_key = get_jwt_private_key()
    return jwt.encode(to_encode, private_key, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        public_key = get_jwt_public_key()
        payload = jwt.decode(token, public_key, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
