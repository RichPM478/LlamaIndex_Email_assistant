# app/ingest/advanced_email_parser.py
"""
Advanced Email Parser 2.0 - Phase 3A Data Pipeline Overhaul

Features:
- Content quality scoring (0-100)
- Marketing content detection & removal
- Advanced HTML cleaning with CSS removal
- Tracking URL sanitization
- Template content deduplication
- Enhanced signature/footer detection
- Language detection & filtering
- Zero-width character removal
"""

import re
import html
from typing import Dict, Any, List, Optional, Tuple
from email.header import decode_header
from bs4 import BeautifulSoup
import urllib.parse
from dataclasses import dataclass

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

class AdvancedEmailParser:
    """Advanced email parser with content quality scoring and noise removal"""
    
    def __init__(self):
        # Compile regex patterns for performance
        self.email_pattern = re.compile(r'<([^>]+)>')
        self.whitespace_pattern = re.compile(r'\s+')
        self.quote_pattern = re.compile(r'^["\']|["\']$')
        
        # Advanced cleaning patterns
        self.zero_width_pattern = re.compile(r'[\u200b\u200c\u200d\ufeff]')  # Zero-width chars
        self.html_entity_spam = re.compile(r'(&zwnj;|&#8199;|&#847;|\s){10,}')  # Repeated entities
        self.css_pattern = re.compile(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
        self.script_pattern = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
        
        # Marketing content patterns
        self.marketing_patterns = [
            r'\[SHOP\s+NOW\]', r'LIMITED\s+TIME', r'EXCLUSIVE\s+OFFER', r'SALE\s+ENDS',
            r'BUY\s+NOW', r'ORDER\s+TODAY', r'DISCOUNT', r'% OFF', r'FREE\s+SHIPPING',
            r'CLEARANCE', r'DEALS?', r'PROMO(TION)?', r'SAVE\s+\$', r'SPECIAL\s+OFFER'
        ]
        self.marketing_regex = re.compile('|'.join(self.marketing_patterns), re.IGNORECASE)
        
        # Tracking URL patterns
        self.tracking_patterns = [
            r'utm_[a-z]+=[^&\s]+',  # UTM parameters
            r'_ri_=[^&\s]+',  # LinkedIn tracking
            r'eid=[^&\s]+',  # Email ID tracking
            r'mid=[^&\s]+',  # Message ID tracking
            r'track[^&\s]*=[^&\s]+',  # General tracking
            r'[a-z0-9]{20,}',  # Long tracking codes
        ]
        self.tracking_regex = re.compile('|'.join(self.tracking_patterns), re.IGNORECASE)
        
        # Enhanced signature patterns
        self.signature_patterns = [
            r'unsubscribe', r'privacy\s+policy', r'terms\s+of\s+service', r'legal\s+notice',
            r'this\s+email\s+was\s+sent\s+to', r'you\s+received\s+this\s+email\s+because',
            r'to\s+stop\s+receiving', r'update\s+your\s+preferences', r'manage\s+subscriptions',
            r'©\s*20\d{2}', r'all\s+rights\s+reserved', r'confidential', r'disclaimer',
            r'if\s+you\s+no\s+longer', r'remove\s+me', r'opt\s+out'
        ]
        self.signature_regex = re.compile('|'.join(self.signature_patterns), re.IGNORECASE)
        
        # Template content indicators
        self.template_patterns = [
            r'your\s+(job\s+alert|daily\s+digest|weekly\s+summary)',
            r'new\s+(jobs?\s+match|opportunities|listings)',
            r'(hi|hello|dear)\s+{{?[^}]+}}?',  # Template variables
            r'{{[^}]+}}',  # Any template variables
            r'dear\s+(valued\s+)?(customer|subscriber|member)',
        ]
        self.template_regex = re.compile('|'.join(self.template_patterns), re.IGNORECASE)
        
        # English language indicators
        self.english_patterns = [
            r'\b(the|and|or|but|in|on|at|to|for|of|with|by)\b',
            r'\b(this|that|these|those|here|there|where|when|what|who|how|why)\b',
            r'\b(is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|could|should)\b'
        ]
        self.english_regex = re.compile('|'.join(self.english_patterns), re.IGNORECASE)
    
    def assess_content_quality(self, body_text: str, subject: str = "", sender: str = "") -> ContentQualityScore:
        """Comprehensive content quality assessment"""
        issues = []
        
        if not body_text or len(body_text.strip()) < 10:
            return ContentQualityScore(
                overall_score=0.0, content_ratio=0.0, marketing_score=0.0,
                template_score=0.0, readability_score=0.0, language_confidence=0.0,
                issues=["Empty or too short content"]
            )
        
        # 1. Calculate content vs noise ratio
        total_length = len(body_text)
        
        # Identify noise
        marketing_matches = len(self.marketing_regex.findall(body_text))
        tracking_urls = len(self.tracking_regex.findall(body_text))
        signature_content = len(self.signature_regex.findall(body_text))
        html_entities = len(re.findall(r'&[a-z#0-9]+;', body_text))
        
        noise_score = min(100, (marketing_matches * 5) + (tracking_urls * 3) + 
                         (signature_content * 4) + (html_entities * 0.5))
        content_ratio = max(0, 100 - noise_score) / 100.0
        
        # 2. Marketing content score
        marketing_density = marketing_matches / max(1, len(body_text.split()) / 10)
        marketing_score = min(100, marketing_density * 20)
        
        if marketing_score > 50:
            issues.append(f"High marketing content density ({marketing_score:.1f}%)")
        
        # 3. Template content score
        template_matches = len(self.template_regex.findall(body_text))
        template_score = min(100, template_matches * 25)
        
        if template_score > 30:
            issues.append(f"Template-like content detected ({template_score:.1f}%)")
        
        # 4. Readability score
        sentences = len(re.findall(r'[.!?]+', body_text))
        words = len(body_text.split())
        avg_sentence_length = words / max(1, sentences)
        
        # Penalize very short or very long sentences
        if avg_sentence_length < 3:
            readability_score = 30
            issues.append("Content too fragmented")
        elif avg_sentence_length > 50:
            readability_score = 40
            issues.append("Sentences too long")
        else:
            readability_score = 80
        
        # Check for excessive repetition
        unique_words = len(set(body_text.lower().split()))
        repetition_ratio = unique_words / max(1, words)
        if repetition_ratio < 0.3:
            readability_score -= 30
            issues.append("Highly repetitive content")
        
        # 5. Language confidence (English)
        english_matches = len(self.english_regex.findall(body_text))
        word_count = len(body_text.split())
        language_confidence = min(100, (english_matches / max(1, word_count / 10)) * 100)
        
        if language_confidence < 50:
            issues.append(f"Low English confidence ({language_confidence:.1f}%)")
        
        # 6. Calculate overall score
        overall_score = (
            content_ratio * 0.4 +  # 40% weight on content vs noise
            (100 - marketing_score) * 0.25 / 100 +  # 25% weight on non-marketing
            (100 - template_score) * 0.15 / 100 +   # 15% weight on non-template  
            readability_score * 0.15 / 100 +        # 15% weight on readability
            language_confidence * 0.05 / 100        # 5% weight on language
        ) * 100
        
        return ContentQualityScore(
            overall_score=overall_score,
            content_ratio=content_ratio,
            marketing_score=marketing_score,
            template_score=template_score,
            readability_score=readability_score,
            language_confidence=language_confidence,
            issues=issues
        )
    
    def clean_html_advanced(self, html_content: str) -> str:
        """Advanced HTML cleaning with CSS and script removal"""
        if not html_content:
            return ""
        
        try:
            # Remove CSS styles and scripts first
            html_content = self.css_pattern.sub('', html_content)
            html_content = self.script_pattern.sub('', html_content)
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove problematic elements
            for element in soup(["script", "style", "meta", "link", "head", "title"]):
                element.decompose()
            
            # Remove elements commonly used for tracking/layout
            for element in soup.find_all(attrs={'class': re.compile(r'track|pixel|beacon|analytics', re.I)}):
                element.decompose()
            
            # Remove hidden elements
            for element in soup.find_all(attrs={'style': re.compile(r'display:\s*none|visibility:\s*hidden', re.I)}):
                element.decompose()
            
            # Get text and clean
            text = soup.get_text()
            return self.clean_text_advanced(text)
            
        except Exception as e:
            # Fallback: regex-based cleaning
            text = re.sub(r'<[^>]+>', '', html_content)
            return self.clean_text_advanced(text)
    
    def clean_text_advanced(self, text: str) -> str:
        """Advanced text cleaning with noise removal"""
        if not text:
            return ""
        
        # 1. Remove HTML entity spam (like &zwnj; &#8199; repeated)
        text = self.html_entity_spam.sub(' ', text)
        
        # 2. Decode remaining HTML entities
        text = html.unescape(text)
        
        # 3. Remove zero-width characters
        text = self.zero_width_pattern.sub('', text)
        
        # 4. Normalize whitespace and line breaks
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                # Remove excessive spaces within line
                line = self.whitespace_pattern.sub(' ', line)
                
                # Skip lines that are just URLs or tracking codes
                if (not line.startswith('http') and 
                    not re.match(r'^[A-Za-z0-9+/=]{20,}$', line) and  # Base64-like
                    len(line) > 3):
                    lines.append(line)
        
        # 5. Join lines and remove excessive line breaks
        clean_text = '\n'.join(lines)
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
        
        return clean_text.strip()
    
    def remove_marketing_content(self, text: str) -> str:
        """Remove marketing and promotional content"""
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Skip lines with heavy marketing language
            marketing_matches = len(self.marketing_regex.findall(line))
            if marketing_matches >= 2:  # Line has 2+ marketing phrases
                continue
            
            # Skip call-to-action lines
            if any(phrase in line_lower for phrase in ['shop now', 'buy now', 'order today', 'click here']):
                continue
            
            # Skip lines that are mostly uppercase (promotional)
            upper_ratio = sum(1 for c in line if c.isupper()) / max(1, len(line))
            if upper_ratio > 0.7 and len(line) > 10:
                continue
            
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    def remove_signatures_advanced(self, text: str) -> str:
        """Advanced signature and footer removal"""
        lines = text.split('\n')
        clean_lines = []
        signature_started = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Check for signature indicators
            if (any(pattern.search(line_lower) for pattern in [self.signature_regex]) or
                line_lower.startswith(('sent from', 'get outlook', 'sent via'))):
                signature_started = True
                continue
            
            # Skip if we're in signature section
            if signature_started:
                continue
            
            # Skip lines with legal/disclaimer content
            if any(word in line_lower for word in ['confidential', 'privilege', 'disclaimer', 
                                                   'copyright', 'proprietary', 'authorized']):
                continue
            
            # Skip lines that are just contact information
            if re.match(r'^[\w\s]+\|[\w\s]+\|', line):  # Format: Name | Title | Company
                continue
            
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    def sanitize_urls(self, text: str) -> str:
        """Remove tracking URLs and clean remaining ones"""
        # Find all URLs
        url_pattern = re.compile(r'https?://[^\s<>"]+')
        urls = url_pattern.findall(text)
        
        for url in urls:
            # Parse URL
            try:
                parsed = urllib.parse.urlparse(url)
                query = urllib.parse.parse_qs(parsed.query)
                
                # Remove tracking parameters
                clean_params = {}
                for key, values in query.items():
                    if not any(pattern in key.lower() for pattern in ['utm_', 'track', 'eid', 'mid', '_ri_']):
                        clean_params[key] = values
                
                # If URL is mostly tracking parameters, remove it entirely
                if len(url) > 100 and len(clean_params) == 0:
                    text = text.replace(url, '[URL removed]')
                elif clean_params != query:
                    # Rebuild cleaner URL
                    clean_query = urllib.parse.urlencode(clean_params, doseq=True)
                    clean_url = urllib.parse.urlunparse((
                        parsed.scheme, parsed.netloc, parsed.path,
                        parsed.params, clean_query, parsed.fragment
                    ))
                    text = text.replace(url, clean_url)
                    
            except Exception:
                # If URL parsing fails and it's very long, likely tracking
                if len(url) > 150:
                    text = text.replace(url, '[URL removed]')
        
        return text
    
    def parse_email_advanced(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced email parsing with quality assessment"""
        # Extract basic fields
        subject = email_data.get("subject", "")
        sender = email_data.get("from", "")
        body = email_data.get("body", "")
        
        # Clean the content
        if "<html" in body.lower() or "<body" in body.lower():
            clean_body = self.clean_html_advanced(body)
        else:
            clean_body = self.clean_text_advanced(body)
        
        # Apply advanced cleaning
        clean_body = self.remove_marketing_content(clean_body)
        clean_body = self.remove_signatures_advanced(clean_body)
        clean_body = self.sanitize_urls(clean_body)
        
        # Assess content quality
        quality = self.assess_content_quality(clean_body, subject, sender)
        
        # Clean sender and subject
        clean_sender = self.clean_sender(sender)
        clean_subject = self.clean_subject(subject)
        
        return {
            # Original fields
            **email_data,
            
            # Cleaned fields
            "clean_body": clean_body,
            "clean_sender": clean_sender,
            "clean_subject": clean_subject,
            
            # Quality assessment
            "quality_score": quality.overall_score,
            "content_ratio": quality.content_ratio,
            "marketing_score": quality.marketing_score,
            "template_score": quality.template_score,
            "readability_score": quality.readability_score,
            "language_confidence": quality.language_confidence,
            "quality_issues": quality.issues,
            
            # Processing metadata
            "parser_version": "2.0",
            "processed_length": len(clean_body),
            "original_length": len(body)
        }
    
    def clean_sender(self, sender_field: str) -> str:
        """Clean sender name (reuse from original parser)"""
        if not sender_field:
            return "Unknown"
        
        sender = self.quote_pattern.sub('', sender_field.strip())
        
        if '<' in sender and '>' in sender:
            name_part = sender.split('<')[0].strip()
            email_part = self.email_pattern.findall(sender)
            
            if name_part:
                name = self.quote_pattern.sub('', name_part).strip()
                return name if name else (email_part[0].split('@')[0] if email_part else "Unknown")
            elif email_part:
                return email_part[0].split('@')[0]
        elif '@' in sender:
            return sender.split('@')[0]
        else:
            return sender
    
    def clean_subject(self, subject_field: str) -> str:
        """Clean email subject (reuse from original parser)"""
        if not subject_field:
            return "No Subject"
        
        subject = subject_field.strip()
        prefixes = ['Re:', 'RE:', 'Fwd:', 'FWD:', 'Fw:']
        
        for prefix in prefixes:
            if subject.startswith(prefix):
                subject = subject[len(prefix):].strip()
        
        subject = self.whitespace_pattern.sub(' ', subject)
        return subject if subject else "No Subject"

# Global parser instance
advanced_email_parser = AdvancedEmailParser()