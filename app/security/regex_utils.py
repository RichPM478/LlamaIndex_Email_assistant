# app/security/regex_utils.py
import re
import signal
from typing import Optional, List
from contextlib import contextmanager

class RegexTimeoutError(Exception):
    """Raised when regex execution times out"""
    pass

@contextmanager
def regex_timeout(seconds: int = 1):
    """Context manager to limit regex execution time"""
    def timeout_handler(signum, frame):
        raise RegexTimeoutError("Regex execution timed out")
    
    # Set the signal handler and alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restore the old signal handler and cancel the alarm
        signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)

class SecureRegexMatcher:
    """Secure regex pattern matcher with DoS protection"""
    
    def __init__(self):
        # Pre-compiled secure patterns for sender extraction
        self.sender_patterns = [
            re.compile(r"from\s+([a-zA-Z0-9\s\-_\.]{1,50})", re.IGNORECASE),
            re.compile(r"sent\s+by\s+([a-zA-Z0-9\s\-_\.]{1,50})", re.IGNORECASE),
            re.compile(r"([a-zA-Z0-9\s\-_\.]{1,50})\s+emails?", re.IGNORECASE)
        ]
    
    def extract_sender_from_query(self, query: str, max_length: int = 500) -> Optional[str]:
        """Safely extract sender name from queries with DoS protection"""
        if not isinstance(query, str):
            return None
        
        # Input validation
        if len(query) > max_length:
            query = query[:max_length]  # Truncate long inputs
        
        # Clean the query
        query = query.strip()
        if not query:
            return None
        
        # Try each pattern with timeout protection
        for pattern in self.sender_patterns:
            try:
                with regex_timeout(1):  # 1 second timeout
                    match = pattern.search(query)
                    if match:
                        sender = match.group(1).strip()
                        # Clean up the sender name
                        sender = re.sub(r'\s+', ' ', sender)  # Normalize whitespace
                        sender = sender.replace("emails", "").replace("email", "").strip()
                        
                        # Validate sender name
                        if self._is_valid_sender_name(sender):
                            return sender
            except RegexTimeoutError:
                # Log the timeout but continue with other patterns
                print(f"Regex timeout for pattern: {pattern.pattern}")
                continue
            except Exception as e:
                # Log unexpected errors but continue
                print(f"Regex error: {e}")
                continue
        
        return None
    
    def _is_valid_sender_name(self, name: str) -> bool:
        """Validate extracted sender name"""
        if not name or len(name) < 2 or len(name) > 50:
            return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'[<>"\']',  # HTML/script injection
            r'javascript:',  # JavaScript injection
            r'\.\.',  # Directory traversal
            r'[{}[\]]',  # Brackets that might indicate code
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                return False
        
        return True
    
    def safe_search(self, pattern: str, text: str, timeout_seconds: int = 1) -> Optional[re.Match]:
        """Perform a safe regex search with timeout protection"""
        if not isinstance(text, str) or not isinstance(pattern, str):
            return None
        
        # Limit input size
        if len(text) > 10000:
            text = text[:10000]
        
        try:
            compiled_pattern = re.compile(pattern)
            with regex_timeout(timeout_seconds):
                return compiled_pattern.search(text)
        except (RegexTimeoutError, re.error) as e:
            print(f"Safe regex search failed: {e}")
            return None
    
    def validate_email_address(self, email: str) -> bool:
        """Validate email address with secure pattern"""
        if not isinstance(email, str) or len(email) > 254:
            return False
        
        # Simple but secure email validation
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        try:
            with regex_timeout(1):
                return bool(email_pattern.match(email))
        except RegexTimeoutError:
            return False

# Global instance
secure_regex = SecureRegexMatcher()