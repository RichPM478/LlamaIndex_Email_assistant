# app/security/sanitizer.py
import html
import re
from typing import Any, Dict, List, Optional

class SecuritySanitizer:
    """Comprehensive security sanitizer for user inputs and outputs"""
    
    def __init__(self):
        # Allowed HTML tags for safe rendering (very restrictive)
        self.allowed_tags = {'b', 'i', 'em', 'strong', 'p', 'br'}
        
        # Safe CSS properties for styling
        self.safe_css_properties = {
            'color', 'background-color', 'font-size', 'font-weight', 
            'text-align', 'padding', 'margin'
        }
        
        # Maximum input lengths to prevent DoS
        self.max_query_length = 1000
        self.max_field_length = 500
    
    def sanitize_html(self, content: str) -> str:
        """Escape HTML content to prevent XSS attacks"""
        if not isinstance(content, str):
            content = str(content)
        
        # HTML escape the content
        escaped = html.escape(content, quote=True)
        
        # Replace newlines with <br> for display
        escaped = escaped.replace('\n', '<br>')
        
        return escaped
    
    def sanitize_query_input(self, query: str) -> str:
        """Sanitize user query input"""
        if not isinstance(query, str):
            query = str(query)
        
        # Length check
        if len(query) > self.max_query_length:
            raise ValueError(f"Query too long. Maximum {self.max_query_length} characters.")
        
        # Remove potential script tags and dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'data:text/html',
            r'on\w+\s*=',  # Event handlers like onclick=
        ]
        
        sanitized = query
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        return sanitized.strip()
    
    def sanitize_field_input(self, field_value: str, field_name: str = "input") -> str:
        """Sanitize general field inputs"""
        if not isinstance(field_value, str):
            field_value = str(field_value)
        
        if len(field_value) > self.max_field_length:
            raise ValueError(f"{field_name} too long. Maximum {self.max_field_length} characters.")
        
        # Basic sanitization
        sanitized = field_value.strip()
        sanitized = re.sub(r'[<>"\']', '', sanitized)  # Remove potentially dangerous chars
        
        return sanitized
    
    def sanitize_email_content(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize email content for safe storage and display"""
        if not isinstance(email_data, dict):
            return {}
        
        sanitized = {}
        
        # Safe fields to include
        safe_fields = ['from', 'subject', 'date', 'message_id', 'uid']
        
        for field in safe_fields:
            if field in email_data:
                value = email_data[field]
                if isinstance(value, str):
                    # Sanitize string fields
                    sanitized[field] = self.sanitize_field_input(value, field)
                else:
                    sanitized[field] = str(value)
        
        # Special handling for email body
        if 'body' in email_data:
            body = email_data['body']
            if isinstance(body, str):
                # Remove scripts and dangerous content from email body
                body = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.IGNORECASE | re.DOTALL)
                body = re.sub(r'javascript:[^"\'>\s]*', '', body, flags=re.IGNORECASE)
                # Truncate very long bodies
                if len(body) > 10000:
                    body = body[:10000] + "... [truncated for security]"
                sanitized['body'] = body
        
        return sanitized
    
    def create_safe_markdown(self, content: str) -> str:
        """Create safe markdown content without unsafe_allow_html"""
        if not isinstance(content, str):
            content = str(content)
        
        # Escape HTML first
        safe_content = self.sanitize_html(content)
        
        # Convert common markdown-like patterns safely
        safe_content = re.sub(r'\*\*(.*?)\*\*', r'**\1**', safe_content)  # Bold
        safe_content = re.sub(r'\*(.*?)\*', r'*\1*', safe_content)        # Italic
        
        return safe_content
    
    def validate_json_structure(self, data: Any, max_depth: int = 10, current_depth: int = 0) -> bool:
        """Validate JSON structure to prevent malicious nested objects"""
        if current_depth > max_depth:
            return False
        
        if isinstance(data, dict):
            if len(data) > 100:  # Limit object size
                return False
            for key, value in data.items():
                if not isinstance(key, str) or len(key) > 100:
                    return False
                if not self.validate_json_structure(value, max_depth, current_depth + 1):
                    return False
        elif isinstance(data, list):
            if len(data) > 1000:  # Limit array size
                return False
            for item in data:
                if not self.validate_json_structure(item, max_depth, current_depth + 1):
                    return False
        elif isinstance(data, str):
            if len(data) > 10000:  # Limit string size
                return False
        
        return True

# Global sanitizer instance
sanitizer = SecuritySanitizer()