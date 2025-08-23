# app/ingest/mailparser_adapter.py
"""
Production-Grade Email Parser using mail-parser Library

Replaces our custom email parsing with the battle-tested mail-parser library:
- Used by SpamScope (major email analysis platform)
- Proper RFC 2047 header decoding
- HTML entity handling
- Attachment extraction
- Built-in error handling
- .msg file support
"""

import mailparser
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re
import html
from datetime import datetime
from email.header import decode_header
import langdetect
from langdetect.lang_detect_exception import LangDetectException

@dataclass
class ContentQualityScore:
    """Content quality assessment results"""
    overall_score: float  # 0-100
    content_ratio: float  # Useful content vs noise ratio
    marketing_score: float  # How promotional (0=not promotional, 100=pure marketing)
    template_score: float  # How template-like (0=unique, 100=template)
    readability_score: float  # How readable (0=unreadable, 100=perfect)
    language_confidence: float  # English language confidence
    issues: List[str]  # List of quality issues found

class MailParserAdapter:
    """
    Professional email parser adapter using mail-parser library
    Maintains compatibility with existing quality scoring system
    """
    
    def __init__(self):
        # Marketing content patterns for quality scoring
        self.marketing_patterns = [
            r'\[SHOP\s+NOW\]', r'LIMITED\s+TIME', r'EXCLUSIVE\s+OFFER', r'SALE\s+ENDS',
            r'BUY\s+NOW', r'ORDER\s+TODAY', r'DISCOUNT', r'% OFF', r'FREE\s+SHIPPING',
            r'CLEARANCE', r'DEALS?', r'PROMO(TION)?', r'SAVE\s+\$', r'SPECIAL\s+OFFER'
        ]
        self.marketing_regex = re.compile('|'.join(self.marketing_patterns), re.IGNORECASE)
        
        # Template content indicators
        self.template_patterns = [
            r'your\s+(job\s+alert|daily\s+digest|weekly\s+summary)',
            r'new\s+(jobs?\s+match|opportunities|listings)',
            r'(hi|hello|dear)\s+{{?[^}]+}}?',  # Template variables
            r'{{[^}]+}}',  # Any template variables
            r'dear\s+(valued\s+)?(customer|subscriber|member)',
        ]
        self.template_regex = re.compile('|'.join(self.template_patterns), re.IGNORECASE)
        
        # Signature/footer patterns
        self.signature_patterns = [
            r'unsubscribe', r'privacy\s+policy', r'terms\s+of\s+service',
            r'you\s+received\s+this\s+email\s+because', r'to\s+stop\s+receiving',
            r'©\s*20\d{2}', r'all\s+rights\s+reserved', r'confidential'
        ]
        self.signature_regex = re.compile('|'.join(self.signature_patterns), re.IGNORECASE)
        
        # English language indicators
        self.english_patterns = [
            r'\b(the|and|or|but|in|on|at|to|for|of|with|by)\b',
            r'\b(this|that|these|those|here|there|where|when|what|who|how|why)\b',
            r'\b(is|are|was|were|be|been|being|have|has|had|do|does|did)\b'
        ]
        self.english_regex = re.compile('|'.join(self.english_patterns), re.IGNORECASE)
    
    def parse_email_advanced(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse email using mail-parser library with quality assessment
        
        Args:
            email_data: Dict with keys 'from', 'subject', 'body', 'date', etc.
            
        Returns:
            Dict with cleaned content and quality metrics
        """
        try:
            # Step 1: Create mail-parser compatible input
            raw_email = self._create_raw_email_string(email_data)
            
            # Step 2: Parse with mail-parser
            mail = mailparser.parse_from_string(raw_email)
            
            # Step 3: Extract and clean content
            clean_sender = self._extract_sender(mail)
            clean_subject = self._extract_subject(mail)
            clean_body = self._extract_body(mail)
            
            # Step 4: Language filtering and quality assessment
            is_english = self._is_english_content(clean_body + " " + clean_subject)
            language_detected = self._detect_language(clean_body)
            
            quality = self._assess_content_quality(clean_body, clean_subject, clean_sender, is_english, language_detected)
            
            # Step 5: Calculate derived metrics
            importance_score = self._calculate_importance_score(clean_sender, clean_subject, clean_body, quality)
            email_type = self._detect_email_type(clean_sender, clean_subject, clean_body)
            
            # Step 6: Extract additional metadata
            attachments = self._extract_attachments(mail)
            headers = self._extract_headers(mail)
            
            # Step 7: Combine attachment content for enhanced analysis
            attachment_text = self._combine_attachment_text(attachments)
            combined_content = clean_body + "\n\n" + attachment_text if attachment_text else clean_body
            
            # Step 8: Recalculate quality and importance with attachment content
            if attachment_text:
                enhanced_quality = self._assess_content_quality(combined_content, clean_subject, clean_sender, is_english, language_detected)
                enhanced_importance = self._calculate_importance_score(clean_sender, clean_subject, combined_content, enhanced_quality, has_attachments=True)
            else:
                enhanced_quality = quality
                enhanced_importance = importance_score
            
            return {
                # Cleaned content (mail-parser handles all encoding automatically)
                'clean_sender': clean_sender,
                'clean_subject': clean_subject,
                'clean_body': clean_body,
                
                # Original content
                'raw_sender': email_data.get('from', ''),
                'raw_subject': email_data.get('subject', ''),
                'raw_body': email_data.get('body', ''),
                'date': email_data.get('date', ''),
                
                # Quality metrics (maintain compatibility)
                'quality_score': enhanced_quality.overall_score,
                'marketing_score': enhanced_quality.marketing_score,
                'template_score': enhanced_quality.template_score,
                'readability_score': enhanced_quality.readability_score,
                'content_ratio': enhanced_quality.content_ratio,
                'language_confidence': enhanced_quality.language_confidence,
                'quality_issues': enhanced_quality.issues,
                
                # Derived metrics
                'importance_score': enhanced_importance,
                'email_type': email_type,
                'content_length': len(clean_body),
                
                # Enhanced metadata from mail-parser
                'attachments': attachments,
                'headers': headers,
                'has_attachments': len(attachments) > 0,
                'has_document_attachments': any(att.get('extracted_content') for att in attachments),
                'attachment_word_count': sum(att.get('extracted_content', {}).get('word_count', 0) for att in attachments if att.get('extracted_content')),
                'total_content_length': len(combined_content),
                
                # Language detection metadata
                'is_english': is_english,
                'detected_language': language_detected,
                'language_confidence': 1.0 if is_english else 0.0,
                
                # Parser metadata
                'parsed_by': 'mail-parser',
                'parser_version': mailparser.__version__ if hasattr(mailparser, '__version__') else '4.1.4',
                'encoding_issues_fixed': True,  # mail-parser handles all encoding
                'was_encoded': self._check_if_encoded(email_data),
            }
            
        except Exception as e:
            print(f"mail-parser error: {e}")
            # Fallback: return basic parsed data
            return self._create_fallback_result(email_data, str(e))
    
    def _decode_header_field(self, header_value: str) -> str:
        """Explicitly decode RFC 2047 encoded headers"""
        if not header_value:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            result_parts = []
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        try:
                            decoded_part = part.decode(encoding)
                        except (UnicodeDecodeError, LookupError):
                            try:
                                decoded_part = part.decode('utf-8')
                            except UnicodeDecodeError:
                                decoded_part = part.decode('latin-1', errors='ignore')
                    else:
                        try:
                            decoded_part = part.decode('utf-8')
                        except UnicodeDecodeError:
                            decoded_part = part.decode('latin-1', errors='ignore')
                else:
                    decoded_part = str(part)
                
                result_parts.append(decoded_part)
            
            return ''.join(result_parts).strip()
            
        except Exception as e:
            print(f"Header decoding error: {e}")
            return header_value
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of text content"""
        if not text or len(text.strip()) < 10:
            return "unknown"
        
        try:
            # Clean text for language detection
            clean_text = re.sub(r'[^\w\s]', ' ', text)
            clean_text = ' '.join(clean_text.split())
            
            if len(clean_text) < 10:
                return "unknown"
            
            detected = langdetect.detect(clean_text)
            return detected
        except LangDetectException:
            return "unknown"
        except Exception as e:
            print(f"Language detection error: {e}")
            return "unknown"
    
    def _is_english_content(self, text: str, threshold: float = 0.7) -> bool:
        """Check if content is primarily English"""
        if not text or len(text.strip()) < 20:
            return False  # Too short to determine
        
        # Quick English word check
        english_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 
            'with', 'by', 'this', 'that', 'these', 'those', 'is', 'are', 
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'can',
            'may', 'might', 'must', 'shall', 'email', 'message', 'dear',
            'hello', 'hi', 'regards', 'thanks', 'thank', 'you', 'your',
            'please', 'from', 'subject', 'date', 'sent', 'received'
        }
        
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        if len(words) < 5:
            return False
        
        english_count = sum(1 for word in words if word in english_words)
        english_ratio = english_count / len(words)
        
        # If quick check passes threshold, it's likely English
        if english_ratio >= threshold:
            return True
        
        # If ratio is very low, probably not English
        if english_ratio < 0.1:
            return False
        
        # For borderline cases, use langdetect
        detected_lang = self._detect_language(text)
        return detected_lang == "en"

    def _create_raw_email_string(self, email_data: Dict[str, Any]) -> str:
        """Create a proper email string for mail-parser with pre-decoded headers"""
        # Pre-decode headers to ensure mail-parser gets clean input
        from_field = self._decode_header_field(email_data.get('from', 'unknown@example.com'))
        subject = self._decode_header_field(email_data.get('subject', 'No Subject'))
        date = email_data.get('date', datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'))
        body = email_data.get('body', '')
        message_id = email_data.get('message_id', '<generated@example.com>')
        
        # Create RFC 5322 compliant email
        raw_email = f"""From: {from_field}
Subject: {subject}
Date: {date}
Message-ID: {message_id}
Content-Type: text/html; charset=UTF-8

{body}"""
        
        return raw_email
    
    def _extract_sender(self, mail) -> str:
        """Extract clean sender from parsed mail"""
        try:
            # mail-parser provides clean from field
            from_field = mail.from_
            if isinstance(from_field, list) and len(from_field) > 0:
                return str(from_field[0]).strip()
            elif from_field:
                return str(from_field).strip()
            else:
                return "Unknown Sender"
        except:
            return "Unknown Sender"
    
    def _extract_subject(self, mail) -> str:
        """Extract clean subject from parsed mail"""
        try:
            subject = mail.subject
            if subject:
                return str(subject).strip()
            else:
                return "No Subject"
        except:
            return "No Subject"
    
    def _extract_body(self, mail) -> str:
        """Extract clean body text from parsed mail"""
        try:
            # Try text/plain first
            if hasattr(mail, 'text_plain') and mail.text_plain:
                body_text = '\n'.join(mail.text_plain)
            # Fallback to HTML
            elif hasattr(mail, 'text_html') and mail.text_html:
                html_content = '\n'.join(mail.text_html)
                body_text = self._html_to_text(html_content)
            # Last resort: try body attribute
            elif hasattr(mail, 'body') and mail.body:
                body_text = str(mail.body)
            else:
                body_text = ""
            
            # Clean up the text
            return self._clean_body_text(body_text)
            
        except Exception as e:
            print(f"Body extraction error: {e}")
            return ""
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to clean text"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except ImportError:
            # Fallback: simple HTML tag removal
            import re
            html_tag_pattern = re.compile(r'<[^>]+>')
            text = html_tag_pattern.sub('', html_content)
            return html.unescape(text)
        except Exception:
            return html_content
    
    def _clean_body_text(self, text: str) -> str:
        """Clean extracted body text"""
        if not text:
            return ""
        
        # Remove signature blocks
        lines = text.split('\n')
        cleaned_lines = []
        in_signature = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Detect signature start
            if not in_signature and (
                self.signature_regex.search(line) or
                line_lower.startswith(('--', '___', '***')) or
                'unsubscribe' in line_lower
            ):
                in_signature = True
                continue
            
            if not in_signature:
                cleaned_lines.append(line)
        
        # Rejoin and normalize whitespace
        text = '\n'.join(cleaned_lines)
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()
    
    def _extract_attachments(self, mail) -> List[Dict[str, Any]]:
        """Extract attachment information and process content with Docling"""
        from app.ingest.docling_processor import docling_processor
        
        attachments = []
        try:
            if hasattr(mail, 'attachments') and mail.attachments:
                for attachment in mail.attachments:
                    filename = getattr(attachment, 'filename', 'unknown')
                    content_type = getattr(attachment, 'content_type', 'unknown')
                    payload = getattr(attachment, 'payload', b'')
                    
                    # Basic attachment info
                    att_info = {
                        'filename': filename,
                        'content_type': content_type,
                        'size': len(payload),
                        'content_id': getattr(attachment, 'content_id', None),
                        'extracted_content': None,
                        'extraction_error': None
                    }
                    
                    # Process with Docling if it's a document
                    if payload and len(payload) > 0:
                        try:
                            processed_doc = docling_processor.process_attachment(
                                attachment_data=payload,
                                filename=filename,
                                content_type=content_type
                            )
                            
                            # Add extracted content if successful
                            if not processed_doc.error and processed_doc.text:
                                att_info['extracted_content'] = {
                                    'text': processed_doc.text[:5000],  # Limit for storage
                                    'full_text': processed_doc.text,
                                    'tables': processed_doc.tables,
                                    'metadata': processed_doc.metadata,
                                    'word_count': processed_doc.word_count,
                                    'page_count': processed_doc.page_count,
                                    'language': processed_doc.language,
                                    'extraction_method': processed_doc.extraction_method
                                }
                            elif processed_doc.error:
                                att_info['extraction_error'] = processed_doc.error
                                
                        except Exception as e:
                            att_info['extraction_error'] = str(e)
                            print(f"Docling processing error for {filename}: {e}")
                    
                    attachments.append(att_info)
        except Exception as e:
            print(f"Attachment extraction error: {e}")
        
        return attachments
    
    def _extract_headers(self, mail) -> Dict[str, str]:
        """Extract important headers"""
        headers = {}
        try:
            if hasattr(mail, 'headers') and mail.headers:
                # Extract commonly useful headers
                useful_headers = [
                    'Return-Path', 'Reply-To', 'X-Mailer', 'X-Originating-IP',
                    'Received', 'Authentication-Results', 'DKIM-Signature'
                ]
                
                for header in useful_headers:
                    if header in mail.headers:
                        headers[header] = str(mail.headers[header])
        except Exception as e:
            print(f"Header extraction error: {e}")
        
        return headers
    
    def _check_if_encoded(self, email_data: Dict[str, Any]) -> bool:
        """Check if original email had encoding issues"""
        text_to_check = str(email_data.get('from', '')) + str(email_data.get('subject', ''))
        return ('=?UTF-8?B?' in text_to_check or 
                '&amp;' in text_to_check or
                '&lt;' in text_to_check)
    
    def _assess_content_quality(self, body: str, subject: str, sender: str, is_english: bool = True, detected_language: str = "en") -> ContentQualityScore:
        """Assess content quality (maintains compatibility with existing system)"""
        issues = []
        
        # Basic quality metrics
        body_length = len(body.strip())
        if body_length < 10:
            issues.append("Very short content")
            readability_score = 0.0
        elif body_length < 50:
            issues.append("Short content")
            readability_score = 30.0
        elif body_length > 10000:
            issues.append("Very long content") 
            readability_score = 60.0
        else:
            readability_score = 80.0
        
        # Marketing score
        marketing_matches = len(self.marketing_regex.findall(body + subject))
        marketing_score = min(100.0, marketing_matches * 15.0)
        
        # Template score
        template_matches = len(self.template_regex.findall(body + subject))
        template_score = min(100.0, template_matches * 20.0)
        
        # Language confidence (enhanced with detection)
        if not is_english:
            issues.append(f"Non-English content detected ({detected_language})")
            language_confidence = 0.0
        else:
            english_matches = len(self.english_regex.findall(body))
            language_confidence = min(100.0, (english_matches / max(1, len(body.split()))) * 100)
        
        # Content ratio (useful content vs noise)
        noise_indicators = marketing_matches + template_matches
        total_words = len(body.split())
        content_ratio = max(0.0, 1.0 - (noise_indicators / max(1, total_words)))
        
        # Overall score (with English language requirement)
        base_score = (
            readability_score * 0.3 +
            (100 - marketing_score) * 0.3 +
            (100 - template_score) * 0.2 +
            language_confidence * 0.2
        )
        
        # Heavy penalty for non-English content
        if not is_english:
            overall_score = base_score * 0.1  # 90% penalty for non-English
        else:
            overall_score = base_score
        
        return ContentQualityScore(
            overall_score=overall_score,
            content_ratio=content_ratio,
            marketing_score=marketing_score,
            template_score=template_score,
            readability_score=readability_score,
            language_confidence=language_confidence,
            issues=issues
        )
    
    def _combine_attachment_text(self, attachments: List[Dict[str, Any]]) -> str:
        """Combine text from all processed attachments"""
        combined_text = ""
        
        for att in attachments:
            if att.get('extracted_content'):
                content = att['extracted_content']
                if content.get('full_text'):
                    combined_text += f"\n\n--- Attachment: {att['filename']} ---\n"
                    combined_text += content['full_text'][:10000]  # Limit per attachment
        
        return combined_text.strip()
    
    def _calculate_importance_score(self, sender: str, subject: str, body: str, quality: ContentQualityScore, has_attachments: bool = False) -> float:
        """Calculate email importance score"""
        base_score = 50.0
        
        # Quality factor
        base_score += (quality.overall_score - 50) * 0.3
        
        # Marketing penalty
        base_score -= quality.marketing_score * 0.2
        
        # Template penalty
        base_score -= quality.template_score * 0.15
        
        # Length bonus for reasonable emails
        if 100 < len(body) < 2000:
            base_score += 10
        
        # Attachment bonus for document attachments
        if has_attachments:
            base_score += 15  # Documents often indicate important content
        
        return max(0, min(100, base_score))
    
    def _detect_email_type(self, sender: str, subject: str, body: str) -> str:
        """Detect email type"""
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        if any(word in sender_lower + subject_lower for word in ['job', 'career', 'linkedin']):
            return 'job_alert'
        elif any(word in sender_lower + subject_lower for word in ['newsletter', 'digest', 'update']):
            return 'newsletter'
        elif any(word in body_lower for word in ['unsubscribe', 'marketing', 'promotion']):
            return 'promotional'
        elif any(word in subject_lower for word in ['reply', 'response', 're:']):
            return 'reply'
        else:
            return 'general'
    
    def _create_fallback_result(self, email_data: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create fallback result if mail-parser fails"""
        return {
            'clean_sender': email_data.get('from', 'Unknown'),
            'clean_subject': email_data.get('subject', 'No Subject'),
            'clean_body': email_data.get('body', '')[:1000],  # Truncated
            'raw_sender': email_data.get('from', ''),
            'raw_subject': email_data.get('subject', ''),
            'raw_body': email_data.get('body', ''),
            'date': email_data.get('date', ''),
            'quality_score': 25.0,  # Low quality due to parsing failure
            'marketing_score': 50.0,
            'template_score': 50.0,
            'readability_score': 25.0,
            'content_ratio': 0.5,
            'language_confidence': 50.0,
            'quality_issues': [f'Parser error: {error}'],
            'importance_score': 25.0,
            'email_type': 'unknown',
            'content_length': len(email_data.get('body', '')),
            'attachments': [],
            'headers': {},
            'has_attachments': False,
            'parsed_by': 'fallback',
            'parser_version': 'fallback',
            'encoding_issues_fixed': False,
            'was_encoded': False,
        }

def test_mailparser_adapter():
    """Test the mail-parser adapter with encoded content"""
    adapter = MailParserAdapter()
    
    # Test with problematic email
    test_email = {
        'from': '=?UTF-8?B?RmFtbHkg?= <family@example.com>',
        'subject': '=?UTF-8?B?VGVzdCBTdWJqZWN0?=',
        'body': '''<html><body>
        Dear Customer,
        
        This is a test email with &lt;encoded&gt; content and tracking URLs.
        
        <a href="https://clicks.example.com/track?id=12345">Click here</a>
        
        Best regards,<br>
        The Team
        
        <hr>
        <small>Unsubscribe: https://example.com/unsubscribe?id=12345</small>
        </body></html>''',
        'date': 'Thu, 31 Jul 2025 11:03:59 +0000',
        'message_id': '<test@example.com>'
    }
    
    print("MAIL-PARSER ADAPTER TEST")
    print("=" * 50)
    
    result = adapter.parse_email_advanced(test_email)
    
    print(f"Original From: {test_email['from']}")
    print(f"Cleaned From: {result['clean_sender']}")
    print()
    print(f"Original Subject: {test_email['subject']}")
    print(f"Cleaned Subject: {result['clean_subject']}")
    print()
    print(f"Cleaned Body: {result['clean_body'][:200]}...")
    print()
    print(f"Quality Score: {result['quality_score']:.1f}")
    print(f"Marketing Score: {result['marketing_score']:.1f}")
    print(f"Parser: {result['parsed_by']}")
    print(f"Encoding Fixed: {result['encoding_issues_fixed']}")

if __name__ == "__main__":
    test_mailparser_adapter()