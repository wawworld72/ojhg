import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def encrypt_token(plaintext: str) -> str:
    """AES-256-GCM encrypt a token string. Returns hex-encoded nonce+ciphertext."""
    aesgcm = AESGCM(settings.encryption_key_bytes)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return (nonce + ciphertext).hex()


def decrypt_token(encrypted_hex: str) -> str:
    """Decrypt an AES-256-GCM encrypted token. Raises ValueError on failure."""
    try:
        data = bytes.fromhex(encrypted_hex)
        nonce, ciphertext = data[:12], data[12:]
        aesgcm = AESGCM(settings.encryption_key_bytes)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception as exc:
        raise ValueError("Token decryption failed") from exc


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)
