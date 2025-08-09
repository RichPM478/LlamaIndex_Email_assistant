# app/ingest/email_parser.py
import re
import html
from typing import Dict, Any, List, Optional
from email.header import decode_header
from bs4 import BeautifulSoup

class CleanEmailParser:
    """Clean email parser that extracts only essential text content"""
    
    def __init__(self):
        # Regex patterns for cleaning
        self.email_pattern = re.compile(r'<([^>]+)>')
        self.whitespace_pattern = re.compile(r'\s+')
        self.quote_pattern = re.compile(r'^["\']|["\']$')
        
    def clean_sender(self, sender_field: str) -> str:
        """Extract clean sender name without email formatting"""
        if not sender_field:
            return "Unknown"
        
        # Remove surrounding quotes
        sender = self.quote_pattern.sub('', sender_field.strip())
        
        # Extract name part before email address
        if '<' in sender and '>' in sender:
            # Format: "Name" <email@domain.com>
            name_part = sender.split('<')[0].strip()
            email_part = self.email_pattern.findall(sender)
            
            if name_part:
                # Remove quotes from name
                name = self.quote_pattern.sub('', name_part).strip()
                return name if name else (email_part[0].split('@')[0] if email_part else "Unknown")
            elif email_part:
                # Just email, use part before @
                return email_part[0].split('@')[0]
        elif '@' in sender:
            # Just email address
            return sender.split('@')[0]
        else:
            # Just name
            return sender
    
    def clean_subject(self, subject_field: str) -> str:
        """Clean email subject line"""
        if not subject_field:
            return "No Subject"
        
        # Remove common prefixes
        subject = subject_field.strip()
        prefixes = ['Re:', 'RE:', 'Fwd:', 'FWD:', 'Fw:']
        
        for prefix in prefixes:
            if subject.startswith(prefix):
                subject = subject[len(prefix):].strip()
        
        # Remove excessive whitespace
        subject = self.whitespace_pattern.sub(' ', subject)
        
        return subject if subject else "No Subject"
    
    def extract_cc_recipients(self, cc_field: str) -> List[str]:
        """Extract clean CC recipient names"""
        if not cc_field:
            return []
        
        recipients = []
        # Split by comma
        cc_list = cc_field.split(',')
        
        for recipient in cc_list:
            clean_recipient = self.clean_sender(recipient)
            if clean_recipient and clean_recipient != "Unknown":
                recipients.append(clean_recipient)
        
        return recipients[:5]  # Limit to 5 recipients
    
    def clean_email_body(self, body_content: str, content_type: str = "text/plain") -> str:
        """Extract clean text from email body"""
        if not body_content:
            return ""
        
        # Handle HTML content
        if content_type.lower().startswith('text/html') or '<html' in body_content.lower():
            return self._extract_text_from_html(body_content)
        else:
            return self._clean_plain_text(body_content)
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML email"""
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up the text
            return self._clean_plain_text(text)
            
        except Exception as e:
            print(f"Warning: HTML parsing failed, using fallback: {e}")
            # Fallback: remove HTML tags with regex
            text = re.sub(r'<[^>]+>', '', html_content)
            return self._clean_plain_text(text)
    
    def _clean_plain_text(self, text: str) -> str:
        """Clean plain text content"""
        if not text:
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove excessive whitespace and normalize line breaks
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                # Remove excessive spaces within line
                line = self.whitespace_pattern.sub(' ', line)
                lines.append(line)
        
        # Join lines and limit length
        clean_text = '\n'.join(lines)
        
        # Remove common email signature patterns
        clean_text = self._remove_signatures(clean_text)
        
        # Remove excessive line breaks
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
        
        # Truncate if too long (keep first 5000 chars)
        if len(clean_text) > 5000:
            clean_text = clean_text[:5000] + "\n\n[Content truncated for processing...]"
        
        return clean_text.strip()
    
    def _remove_signatures(self, text: str) -> str:
        """Remove common email signatures and footers"""
        signature_indicators = [
            'unsubscribe',
            'privacy policy',
            'terms of service',
            'this email was sent to',
            'you received this email because',
            'to stop receiving emails',
            'update your preferences',
            '© 20',  # Copyright notices
            'all rights reserved',
        ]
        
        lines = text.split('\n')
        clean_lines = []
        signature_started = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Check if this line indicates start of signature/footer
            if any(indicator in line_lower for indicator in signature_indicators):
                signature_started = True
                continue
            
            # Skip lines that are just URLs or very short
            if not signature_started:
                if (line.startswith('http') or 
                    len(line.strip()) < 3 or 
                    line.count('|') > 2):  # Navigation-like lines
                    continue
                clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    def parse_email(self, email_msg) -> Dict[str, Any]:
        """Parse email message and return clean structured data"""
        try:
            # Extract and clean basic fields
            raw_from = self._decode_header_safe(email_msg.get("From"))
            raw_subject = self._decode_header_safe(email_msg.get("Subject"))
            raw_cc = self._decode_header_safe(email_msg.get("CC"))
            raw_date = email_msg.get("Date", "")
            message_id = email_msg.get("Message-ID", "")
            
            # Clean the fields
            clean_sender = self.clean_sender(raw_from)
            clean_subject = self.clean_subject(raw_subject)
            cc_recipients = self.extract_cc_recipients(raw_cc) if raw_cc else []
            
            # Extract body content
            body_text = self._extract_body_content(email_msg)
            
            return {
                "sender": clean_sender,
                "subject": clean_subject, 
                "cc_recipients": cc_recipients,
                "body": body_text,
                "date": raw_date,
                "message_id": message_id,
                # Keep original fields for compatibility
                "from": raw_from,
                "raw_subject": raw_subject
            }
            
        except Exception as e:
            print(f"Error parsing email: {e}")
            return {
                "sender": "Unknown",
                "subject": "No Subject",
                "cc_recipients": [],
                "body": "",
                "date": "",
                "message_id": "",
                "from": "",
                "raw_subject": ""
            }
    
    def _decode_header_safe(self, header_value) -> str:
        """Safely decode email header"""
        if header_value is None:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            result = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    try:
                        result.append(part.decode(encoding or 'utf-8', errors='ignore'))
                    except:
                        result.append(part.decode('utf-8', errors='ignore'))
                else:
                    result.append(str(part))
            return ' '.join(result)
        except Exception:
            return str(header_value) if header_value else ""
    
    def _extract_body_content(self, email_msg) -> str:
        """Extract body content from email message"""
        body_text = ""
        
        try:
            if email_msg.is_multipart():
                for part in email_msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    # Skip attachments
                    if "attachment" in content_disposition:
                        continue
                    
                    # Process text parts
                    if content_type in ["text/plain", "text/html"]:
                        try:
                            charset = part.get_content_charset() or 'utf-8'
                            payload = part.get_payload(decode=True)
                            if payload:
                                part_text = payload.decode(charset, errors='ignore')
                                clean_text = self.clean_email_body(part_text, content_type)
                                
                                if clean_text:
                                    # Prefer plain text over HTML
                                    if content_type == "text/plain" or not body_text:
                                        body_text = clean_text
                                    
                        except Exception as e:
                            print(f"Warning: Error decoding email part: {e}")
                            continue
            else:
                # Single part message
                try:
                    charset = email_msg.get_content_charset() or 'utf-8'
                    payload = email_msg.get_payload(decode=True)
                    if payload:
                        content_type = email_msg.get_content_type()
                        raw_text = payload.decode(charset, errors='ignore')
                        body_text = self.clean_email_body(raw_text, content_type)
                except Exception as e:
                    print(f"Warning: Error decoding single-part email: {e}")
                    body_text = ""
            
        except Exception as e:
            print(f"Warning: Error extracting email body: {e}")
            body_text = ""
        
        return body_text

# Global parser instance
email_parser = CleanEmailParser()