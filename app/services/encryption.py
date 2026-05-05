# Encryption service using Fernet (AES-256)
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
import base64

def get_fernet_key() -> bytes:
    # Ensure the key is URL-safe base64 encoded 32 bytes
    key = settings.ENCRYPTION_KEY.encode()
    # Pad or trim to correct length
    if len(key) < 32:
        key = key.ljust(32, b'0')
    return base64.urlsafe_b64encode(key[:32])

_fernet = None

def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_fernet_key())
    return _fernet

def encrypt_password(password: str) -> str:
    """Encrypt a password for storage."""
    f = get_fernet()
    encrypted = f.encrypt(password.encode())
    return base64.b64encode(encrypted).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a stored password."""
    f = get_fernet()
    try:
        decoded = base64.b64decode(encrypted_password.encode())
        decrypted = f.decrypt(decoded)
        return decrypted.decode()
    except InvalidToken:
        raise ValueError("Invalid encryption key or corrupted password")
