# app/security/auth.py
import hashlib
import secrets
import time
from typing import Optional
import streamlit as st
from datetime import datetime, timedelta

class SecureAuth:
    """Secure authentication system for admin access"""
    
    def __init__(self):
        self.session_timeout = 3600  # 1 hour
        self.max_attempts = 3
        self.lockout_duration = 900  # 15 minutes
        
    def hash_password(self, password: str, salt: str) -> str:
        """Securely hash password with salt using PBKDF2"""
        return hashlib.pbkdf2_hmac('sha256', 
                                   password.encode('utf-8'), 
                                   salt.encode('utf-8'), 
                                   100000).hex()
    
    def generate_salt(self) -> str:
        """Generate cryptographically secure salt"""
        return secrets.token_hex(32)
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        return secrets.compare_digest(
            self.hash_password(password, salt),
            stored_hash
        )
    
    def is_locked_out(self, identifier: str) -> bool:
        """Check if user is locked out due to failed attempts"""
        if f"lockout_until_{identifier}" not in st.session_state:
            return False
        
        lockout_until = st.session_state[f"lockout_until_{identifier}"]
        return time.time() < lockout_until
    
    def record_failed_attempt(self, identifier: str):
        """Record failed login attempt and implement lockout"""
        attempts_key = f"failed_attempts_{identifier}"
        
        if attempts_key not in st.session_state:
            st.session_state[attempts_key] = 0
        
        st.session_state[attempts_key] += 1
        
        if st.session_state[attempts_key] >= self.max_attempts:
            st.session_state[f"lockout_until_{identifier}"] = time.time() + self.lockout_duration
            st.session_state[attempts_key] = 0  # Reset attempts after lockout
    
    def clear_failed_attempts(self, identifier: str):
        """Clear failed attempts on successful login"""
        attempts_key = f"failed_attempts_{identifier}"
        if attempts_key in st.session_state:
            del st.session_state[attempts_key]
    
    def authenticate_admin(self, password: str) -> bool:
        """Authenticate admin user with secure password verification"""
        identifier = "admin"
        
        # Check if locked out
        if self.is_locked_out(identifier):
            remaining = st.session_state[f"lockout_until_{identifier}"] - time.time()
            st.error(f"Account locked. Try again in {int(remaining/60)} minutes.")
            return False
        
        # Get stored credentials from environment or secure config
        # In production, use proper secret management
        stored_salt = st.secrets.get("ADMIN_SALT", self.generate_salt())
        stored_hash = st.secrets.get("ADMIN_PASSWORD_HASH", 
                                     self.hash_password("secure_admin_password_2025!", stored_salt))
        
        if self.verify_password(password, stored_hash, stored_salt):
            self.clear_failed_attempts(identifier)
            st.session_state['admin_authenticated'] = True
            st.session_state['admin_session_start'] = time.time()
            return True
        else:
            self.record_failed_attempt(identifier)
            st.error("Invalid credentials")
            return False
    
    def is_admin_authenticated(self) -> bool:
        """Check if admin is currently authenticated and session is valid"""
        if 'admin_authenticated' not in st.session_state:
            return False
        
        if not st.session_state.get('admin_authenticated', False):
            return False
        
        # Check session timeout
        session_start = st.session_state.get('admin_session_start', 0)
        if time.time() - session_start > self.session_timeout:
            self.logout_admin()
            return False
        
        return True
    
    def logout_admin(self):
        """Logout admin user"""
        if 'admin_authenticated' in st.session_state:
            del st.session_state['admin_authenticated']
        if 'admin_session_start' in st.session_state:
            del st.session_state['admin_session_start']
    
    def extend_session(self):
        """Extend admin session on activity"""
        if self.is_admin_authenticated():
            st.session_state['admin_session_start'] = time.time()

# Global auth instance
auth = SecureAuth()