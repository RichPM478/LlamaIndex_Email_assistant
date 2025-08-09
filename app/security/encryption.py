# app/security/encryption.py
import os
import base64
import secrets
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecureCredentialManager:
    """Secure credential management with encryption"""
    
    def __init__(self):
        self.key_derivation_iterations = 100000
        self._encryption_key = None
        self._master_password = None
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.key_derivation_iterations,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key"""
        if self._encryption_key is None:
            # In production, use proper key management (HSM, Azure Key Vault, etc.)
            master_password = os.environ.get('MASTER_PASSWORD', 'default_secure_password_2025!')
            salt = os.environ.get('ENCRYPTION_SALT', base64.urlsafe_b64encode(os.urandom(32)).decode())
            
            if isinstance(salt, str):
                salt = base64.urlsafe_b64decode(salt)
            
            self._encryption_key = self._derive_key(master_password, salt)
        
        return self._encryption_key
    
    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential string"""
        if not isinstance(credential, str):
            raise ValueError("Credential must be a string")
        
        if len(credential) > 10000:
            raise ValueError("Credential too long")
        
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted = fernet.encrypt(credential.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            raise RuntimeError(f"Encryption failed: {e}")
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential string"""
        if not isinstance(encrypted_credential, str):
            raise ValueError("Encrypted credential must be a string")
        
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_credential)
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise RuntimeError(f"Decryption failed: {e}")
    
    def secure_get_credential(self, credential_name: str, default: str = "") -> str:
        """Securely get credential from environment or encrypted storage"""
        # Try environment variable first
        env_value = os.environ.get(credential_name)
        if env_value:
            # Check if it's encrypted (our encrypted values have specific format)
            if env_value.startswith("ENC:"):
                try:
                    return self.decrypt_credential(env_value[4:])  # Remove "ENC:" prefix
                except RuntimeError:
                    print(f"Failed to decrypt credential {credential_name}")
                    return default
            return env_value
        
        return default
    
    def store_encrypted_credential(self, credential_name: str, credential_value: str) -> str:
        """Store credential in encrypted format (returns encrypted string for storage)"""
        encrypted = self.encrypt_credential(credential_value)
        return f"ENC:{encrypted}"

class SecureSettingsManager:
    """Secure settings management with credential protection"""
    
    def __init__(self):
        self.credential_manager = SecureCredentialManager()
    
    def get_secure_imap_password(self) -> str:
        """Get IMAP password securely"""
        return self.credential_manager.secure_get_credential("IMAP_PASSWORD", "")
    
    def get_secure_api_key(self, provider: str) -> str:
        """Get API key for specified provider securely"""
        key_name = f"{provider.upper()}_API_KEY"
        return self.credential_manager.secure_get_credential(key_name, "")
    
    def validate_credentials(self) -> Dict[str, bool]:
        """Validate that required credentials are available"""
        validation = {}
        
        # Check IMAP credentials
        imap_host = os.environ.get("IMAP_HOST", "")
        imap_user = os.environ.get("IMAP_USER", "")
        imap_password = self.get_secure_imap_password()
        
        validation["imap"] = bool(imap_host and imap_user and imap_password)
        
        # Check API keys
        providers = ["openai", "anthropic", "azure_openai"]
        for provider in providers:
            api_key = self.get_secure_api_key(provider)
            validation[f"{provider}_api"] = bool(api_key)
        
        return validation
    
    def secure_environment_setup(self) -> Dict[str, str]:
        """Setup secure environment variables without exposing credentials"""
        secure_env = {}
        
        # Get credentials securely
        openai_key = self.get_secure_api_key("openai")
        if openai_key:
            # Set temporarily for the session only
            os.environ["OPENAI_API_KEY"] = openai_key
            secure_env["OPENAI_API_KEY"] = "[SECURED]"  # Don't expose actual key
        
        anthropic_key = self.get_secure_api_key("anthropic")
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key
            secure_env["ANTHROPIC_API_KEY"] = "[SECURED]"
        
        return secure_env
    
    def cleanup_environment(self):
        """Clean up sensitive environment variables"""
        sensitive_vars = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY", 
            "AZURE_OPENAI_API_KEY"
        ]
        
        for var in sensitive_vars:
            if var in os.environ:
                del os.environ[var]

# Global instances
credential_manager = SecureCredentialManager()
settings_manager = SecureSettingsManager()