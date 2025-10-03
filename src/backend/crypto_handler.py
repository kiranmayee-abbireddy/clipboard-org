# src/backend/crypto_handler.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Optional

class CryptoHandler:
    """Handle encryption/decryption for sensitive clipboard data"""
    
    def __init__(self, passkey: str = None):
        self.passkey = passkey
        self.cipher = None
        if passkey:
            self._initialize_cipher(passkey)
    
    def _initialize_cipher(self, passkey: str):
        """Initialize Fernet cipher with passkey"""
        # Generate salt (store this in database settings)
        salt = b'clipboard_organizer_salt_v1'  # In production, use random salt
        
        # Derive key from passkey
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passkey.encode()))
        self.cipher = Fernet(key)
    
    def set_passkey(self, passkey: str):
        """Set or change passkey"""
        self.passkey = passkey
        self._initialize_cipher(passkey)
    
    def encrypt(self, data: str) -> bytes:
        """Encrypt string data"""
        if not self.cipher:
            raise ValueError("Cipher not initialized. Set passkey first.")
        return self.cipher.encrypt(data.encode())
    
    def decrypt(self, encrypted_data: bytes) -> str:
        """Decrypt data back to string"""
        if not self.cipher:
            raise ValueError("Cipher not initialized. Set passkey first.")
        try:
            return self.cipher.decrypt(encrypted_data).decode()
        except Exception as e:
            raise ValueError("Failed to decrypt. Invalid passkey or corrupted data.")
    
    def verify_passkey(self, passkey: str, test_encrypted_data: bytes) -> bool:
        """Verify if passkey is correct"""
        try:
            temp_cipher = CryptoHandler(passkey)
            temp_cipher.decrypt(test_encrypted_data)
            return True
        except:
            return False
    
    @staticmethod
    def generate_key() -> str:
        """Generate a random encryption key"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
