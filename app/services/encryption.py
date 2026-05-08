# Encryption service using Fernet (AES-256)
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
import base64


_fernet = None

def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPTION_KEY
        if not key:
            # Fallback for dev if not set
            key = Fernet.generate_key().decode()
        try:
            _fernet = Fernet(key.encode())
        except Exception:
            # If the key is not a valid Fernet key, try to make it one
            import base64
            # Fernet needs 32 bytes base64 encoded
            key_bytes = key.encode()[:32].ljust(32, b'0')
            _fernet = Fernet(base64.urlsafe_b64encode(key_bytes))
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
