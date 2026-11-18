# src/backend/crypto_handler.py
import base64
import os
import hashlib
from typing import Optional, Union
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Default backwards-compatible salt for existing databases
DEFAULT_SALT = b'clipboard_organizer_salt_v1'

class CryptoHandler:
    """Handle encryption/decryption for sensitive clipboard data using Fernet (AES-128-CBC + HMAC-SHA256)"""
    
    def __init__(self, passkey: Optional[str] = None, salt: bytes = DEFAULT_SALT):
        self.passkey = passkey
        self.salt = salt
        self.cipher = None
        if passkey:
            self._initialize_cipher(passkey, salt)
    
    def _initialize_cipher(self, passkey: str, salt: bytes):
        """Initialize Fernet cipher with passkey and salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passkey.encode('utf-8')))
        self.cipher = Fernet(key)
    
    def set_passkey(self, passkey: str, salt: bytes = DEFAULT_SALT):
        """Set or change passkey"""
        self.passkey = passkey
        self.salt = salt
        self._initialize_cipher(passkey, salt)
    
    def encrypt(self, data: str) -> bytes:
        """Encrypt string data and return bytes"""
        if not self.cipher:
            raise ValueError("Cipher not initialized. Set passkey first.")
        return self.cipher.encrypt(data.encode('utf-8'))
    
    def encrypt_to_b64(self, data: str) -> str:
        """Encrypt string data and return URL-safe base64 string for safe JSON serialization"""
        encrypted_bytes = self.encrypt(data)
        return base64.b64encode(encrypted_bytes).decode('ascii')
    
    def decrypt(self, encrypted_data: Union[bytes, str]) -> str:
        """Decrypt data back to string. Accepts either bytes or base64 string."""
        if not self.cipher:
            raise ValueError("Cipher not initialized. Set passkey first.")
        if not encrypted_data:
            return ""
        
        # Handle string input
        if isinstance(encrypted_data, str):
            try:
                raw_bytes = base64.b64decode(encrypted_data.encode('ascii'))
            except Exception:
                raw_bytes = encrypted_data.encode('utf-8')
        else:
            raw_bytes = encrypted_data
            
        try:
            return self.cipher.decrypt(raw_bytes).decode('utf-8')
        except InvalidToken:
            raise ValueError("Failed to decrypt. Invalid passkey or corrupted data.")
        except Exception as e:
            raise ValueError(f"Decryption error: {e}")
    
    @staticmethod
    def hash_passkey(passkey: str) -> str:
        """Hash passkey for verification"""
        return hashlib.sha256(passkey.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_random_salt(length: int = 16) -> bytes:
        """Generate a random cryptographic salt"""
        return os.urandom(length)
