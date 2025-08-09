# app/intelligence/email_analyzer.py
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import dateparser

class EmailCategory(Enum):
    """Email categories for auto-classification"""
    URGENT = "urgent"
    MEETING = "meeting"
    PAYMENT = "payment"
    TASK = "task"
    SOCIAL = "social"
    PROMOTIONAL = "promotional"
    NOTIFICATION = "notification"
    PERSONAL = "personal"
    WORK = "work"
    NEWSLETTER = "newsletter"
    SPAM = "spam"
    OTHER = "other"

class ImportanceLevel(Enum):
    """Email importance levels"""
    CRITICAL = 5  # Requires immediate attention
    HIGH = 4      # Important, should be addressed soon
    MEDIUM = 3    # Normal importance
    LOW = 2       # Can wait
    MINIMAL = 1   # FYI only

@dataclass
class EmailInsights:
    """Container for email analysis results"""
    importance_score: int
    importance_level: ImportanceLevel
    categories: List[EmailCategory]
    urgency_indicators: List[str]
    action_items: List[str]
    key_dates: List[Dict[str, Any]]
    financial_amounts: List[str]
    people_mentioned: List[str]
    sentiment_score: float
    estimated_response_time: Optional[str]

class EmailIntelligenceAnalyzer:
    """Advanced email analysis and intelligence system"""
    
    def __init__(self):
        # Patterns for importance scoring
        self.urgent_keywords = [
            'urgent', 'asap', 'immediate', 'emergency', 'critical', 'deadline',
            'overdue', 'final notice', 'last chance', 'expires today', 'action required'
        ]
        
        self.meeting_keywords = [
            'meeting', 'conference', 'call', 'zoom', 'teams', 'appointment',
            'schedule', 'calendar', 'invite', 'agenda', 'reschedule'
        ]
        
        self.payment_keywords = [
            'payment', 'invoice', 'bill', 'fee', 'charge', 'cost', 'price',
            'money', 'pay', 'due', 'amount', 'balance', 'refund'
        ]
        
        self.task_keywords = [
            'task', 'todo', 'action', 'complete', 'finish', 'submit', 'review',
            'approve', 'sign', 'return', 'bring', 'prepare', 'homework'
        ]
        
        # Patterns for entity extraction
        self.money_pattern = re.compile(r'[£$€¥]?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?', re.IGNORECASE)
        self.phone_pattern = re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.time_pattern = re.compile(r'\b(?:1[0-2]|0?[1-9]):[0-5][0-9]\s?(?:AM|PM|am|pm)\b')
        
        # Sender importance patterns
        self.important_domains = [
            'school', 'education', 'gov', 'bank', 'official', 'admin',
            'noreply', 'system', 'security', 'support'
        ]
        
        self.promotional_indicators = [
            'unsubscribe', 'promotional', 'newsletter', 'marketing', 'offer',
            'sale', 'discount', 'deal', 'free', 'limited time', 'exclusive'
        ]
    
    def analyze_email(self, email_data: Dict[str, Any]) -> EmailInsights:
        """Perform comprehensive analysis of an email"""
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        sender = email_data.get('from', '').lower()
        date_str = email_data.get('date', '')
        
        # Combine text for analysis
        full_text = f"{subject} {body}"
        
        # Calculate importance score
        importance_score = self._calculate_importance_score(subject, body, sender)
        importance_level = self._score_to_level(importance_score)
        
        # Categorize email
        categories = self._categorize_email(subject, body, sender)
        
        # Extract urgency indicators
        urgency_indicators = self._extract_urgency_indicators(full_text)
        
        # Extract action items
        action_items = self._extract_action_items(body)
        
        # Extract key dates
        key_dates = self._extract_key_dates(full_text, date_str)
        
        # Extract financial amounts
        financial_amounts = self._extract_financial_amounts(full_text)
        
        # Extract people mentioned
        people_mentioned = self._extract_people_mentions(body)
        
        # Calculate sentiment score
        sentiment_score = self._calculate_sentiment(full_text)
        
        # Estimate response time
        estimated_response_time = self._estimate_response_time(importance_level, categories)
        
        return EmailInsights(
            importance_score=importance_score,
            importance_level=importance_level,
            categories=categories,
            urgency_indicators=urgency_indicators,
            action_items=action_items,
            key_dates=key_dates,
            financial_amounts=financial_amounts,
            people_mentioned=people_mentioned,
            sentiment_score=sentiment_score,
            estimated_response_time=estimated_response_time
        )
    
    def _calculate_importance_score(self, subject: str, body: str, sender: str) -> int:
        """Calculate importance score from 1-5"""
        score = 3  # Start with medium importance
        
        # Urgent keywords boost
        urgent_count = sum(1 for keyword in self.urgent_keywords if keyword in subject or keyword in body)
        score += min(urgent_count * 0.5, 2)
        
        # Subject line indicators
        if any(word in subject for word in ['urgent', 'asap', 'important', 'deadline']):
            score += 1
        
        if subject.endswith('!') or '!!!' in subject:
            score += 0.5
        
        if subject.isupper():  # ALL CAPS subject
            score += 0.5
        
        # Sender importance
        sender_domain = sender.split('@')[-1] if '@' in sender else ''
        if any(domain in sender_domain for domain in self.important_domains):
            score += 1
        
        # Meeting/appointment indicators
        if any(word in subject or word in body for word in self.meeting_keywords):
            score += 0.5
        
        # Payment/financial indicators
        if any(word in subject or word in body for word in self.payment_keywords):
            score += 0.5
        
        # Promotional indicators (reduce importance)
        if any(indicator in body for indicator in self.promotional_indicators):
            score -= 1
        
        # Clamp score between 1 and 5
        return max(1, min(5, int(score)))
    
    def _score_to_level(self, score: int) -> ImportanceLevel:
        """Convert numeric score to importance level"""
        if score >= 5:
            return ImportanceLevel.CRITICAL
        elif score >= 4:
            return ImportanceLevel.HIGH
        elif score >= 3:
            return ImportanceLevel.MEDIUM
        elif score >= 2:
            return ImportanceLevel.LOW
        else:
            return ImportanceLevel.MINIMAL
    
    def _categorize_email(self, subject: str, body: str, sender: str) -> List[EmailCategory]:
        """Automatically categorize email based on content"""
        categories = []
        full_text = f"{subject} {body}"
        
        # Check for urgent indicators
        if any(word in full_text for word in self.urgent_keywords):
            categories.append(EmailCategory.URGENT)
        
        # Check for meeting indicators
        if any(word in full_text for word in self.meeting_keywords):
            categories.append(EmailCategory.MEETING)
        
        # Check for payment indicators
        if any(word in full_text for word in self.payment_keywords) or self.money_pattern.search(full_text):
            categories.append(EmailCategory.PAYMENT)
        
        # Check for task indicators
        if any(word in full_text for word in self.task_keywords):
            categories.append(EmailCategory.TASK)
        
        # Check for promotional content
        if any(indicator in full_text for indicator in self.promotional_indicators):
            categories.append(EmailCategory.PROMOTIONAL)
        
        # Check for notifications (automated emails)
        if 'noreply' in sender or 'no-reply' in sender or 'system' in sender:
            categories.append(EmailCategory.NOTIFICATION)
        
        # Check for newsletters
        if 'newsletter' in subject or 'unsubscribe' in body:
            categories.append(EmailCategory.NEWSLETTER)
        
        # Default category if no specific category found
        if not categories:
            categories.append(EmailCategory.OTHER)
        
        return categories
    
    def _extract_urgency_indicators(self, text: str) -> List[str]:
        """Extract specific urgency indicators from text"""
        indicators = []
        
        for keyword in self.urgent_keywords:
            if keyword in text:
                # Find the context around the keyword
                pattern = rf'.{{0,30}}{re.escape(keyword)}.{{0,30}}'
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    context = match.group().strip()
                    if context not in indicators:
                        indicators.append(context)
        
        return indicators[:5]  # Limit to top 5
    
    def _extract_action_items(self, body: str) -> List[str]:
        """Extract action items from email body"""
        action_items = []
        
        # Action verb patterns
        action_patterns = [
            r'please\s+(\w+(?:\s+\w+){1,10})',
            r'need\s+to\s+(\w+(?:\s+\w+){1,10})',
            r'must\s+(\w+(?:\s+\w+){1,10})',
            r'should\s+(\w+(?:\s+\w+){1,10})',
            r'remember\s+to\s+(\w+(?:\s+\w+){1,10})',
            r'don\'t\s+forget\s+to\s+(\w+(?:\s+\w+){1,10})'
        ]
        
        for pattern in action_patterns:
            matches = re.finditer(pattern, body, re.IGNORECASE)
            for match in matches:
                action = match.group(1).strip()
                if len(action) > 10 and action not in action_items:
                    action_items.append(action)
        
        return action_items[:10]  # Limit to top 10
    
    def _extract_key_dates(self, text: str, email_date: str) -> List[Dict[str, Any]]:
        """Extract important dates from email text"""
        key_dates = []
        
        # Date patterns to look for
        date_patterns = [
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(?:tomorrow|today|next\s+week|this\s+week)\b',
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\b'
        ]
        
        # Extract potential dates
        potential_dates = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                potential_dates.append(match.group())
        
        # Parse dates
        reference_date = datetime.now()
        if email_date:
            try:
                reference_date = dateparser.parse(email_date) or reference_date
            except:
                pass
        
        for date_text in potential_dates:
            try:
                parsed_date = dateparser.parse(
                    date_text, 
                    settings={
                        "RELATIVE_BASE": reference_date,
                        "PREFER_DATES_FROM": "future"
                    }
                )
                if parsed_date:
                    key_dates.append({
                        'date': parsed_date.isoformat(),
                        'text': date_text,
                        'days_from_now': (parsed_date - datetime.now()).days
                    })
            except:
                continue
        
        # Remove duplicates and sort by date
        unique_dates = {}
        for date_info in key_dates:
            date_key = date_info['date'][:10]  # Just the date part
            if date_key not in unique_dates:
                unique_dates[date_key] = date_info
        
        sorted_dates = sorted(unique_dates.values(), key=lambda x: x['date'])
        return sorted_dates[:5]  # Return top 5 dates
    
    def _extract_financial_amounts(self, text: str) -> List[str]:
        """Extract monetary amounts from text"""
        amounts = []
        matches = self.money_pattern.finditer(text)
        
        for match in matches:
            amount = match.group().strip()
            if amount not in amounts:
                amounts.append(amount)
        
        return amounts[:5]  # Limit to 5 amounts
    
    def _extract_people_mentions(self, body: str) -> List[str]:
        """Extract people's names mentioned in the email"""
        # Simple name extraction - could be enhanced with NER
        people = []
        
        # Look for "From:" patterns
        from_pattern = r'from\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
        matches = re.finditer(from_pattern, body, re.IGNORECASE)
        for match in matches:
            name = match.group(1)
            if name not in people:
                people.append(name)
        
        # Look for capitalized words that might be names (simple heuristic)
        name_pattern = r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b'
        matches = re.finditer(name_pattern, body)
        for match in matches:
            name = match.group()
            # Filter out common non-names
            if not any(word in name.lower() for word in ['Dear', 'Best', 'Kind', 'Thank']):
                if name not in people:
                    people.append(name)
        
        return people[:5]  # Limit to 5 names
    
    def _calculate_sentiment(self, text: str) -> float:
        """Simple sentiment analysis (could be enhanced with ML)"""
        positive_words = [
            'great', 'excellent', 'wonderful', 'fantastic', 'amazing', 'love',
            'happy', 'pleased', 'excited', 'congratulations', 'success', 'good'
        ]
        
        negative_words = [
            'urgent', 'problem', 'issue', 'concern', 'worried', 'disappointed',
            'failed', 'error', 'wrong', 'bad', 'terrible', 'awful', 'hate'
        ]
        
        words = text.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        total_words = len(words)
        if total_words == 0:
            return 0.0
        
        # Return sentiment score between -1 and 1
        sentiment = (positive_count - negative_count) / total_words * 10
        return max(-1.0, min(1.0, sentiment))
    
    def _estimate_response_time(self, importance: ImportanceLevel, categories: List[EmailCategory]) -> Optional[str]:
        """Estimate appropriate response time based on importance and categories"""
        if importance == ImportanceLevel.CRITICAL:
            return "Within 1 hour"
        elif importance == ImportanceLevel.HIGH:
            return "Within 4 hours"
        elif EmailCategory.URGENT in categories:
            return "Within 2 hours"
        elif EmailCategory.MEETING in categories:
            return "Within 1 day"
        elif importance == ImportanceLevel.MEDIUM:
            return "Within 2 days"
        elif importance == ImportanceLevel.LOW:
            return "Within 1 week"
        else:
            return "No response needed"

# Global analyzer instance
email_analyzer = EmailIntelligenceAnalyzer()