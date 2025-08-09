# app/analytics/email_stats.py
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re
from pathlib import Path

def load_emails_from_raw(raw_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load emails from the latest raw file"""
    if not raw_path:
        # Find the latest file in data/raw/
        raw_dir = Path("data/raw")
        if not raw_dir.exists():
            return []
        
        files = list(raw_dir.glob("*.json")) + list(raw_dir.glob("*.jsonl"))
        if not files:
            return []
        
        raw_path = max(files, key=lambda f: f.stat().st_mtime)
    
    emails = []
    if str(raw_path).endswith(".jsonl"):
        with open(raw_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    emails.append(json.loads(line))
    else:
        with open(raw_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                emails = data
    
    return emails


def extract_sender_name(from_field: str) -> str:
    """Extract clean sender name from email 'from' field"""
    if not from_field:
        return "Unknown"
    
    # Remove email address parts
    from_field = re.sub(r'<[^>]+>', '', from_field).strip()
    # Remove quotes
    from_field = from_field.replace('"', '').replace("'", '')
    # Take organization/name part
    from_field = from_field.split('@')[0] if '@' in from_field else from_field
    
    return from_field.strip() or "Unknown"


def parse_email_date(date_str: str) -> Optional[datetime]:
    """Parse email date string to datetime"""
    if not date_str:
        return None
    
    try:
        # Common email date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%d %H:%M:%S",
            "%d %b %Y %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        # Fallback: try dateutil parser
        from dateutil import parser
        return parser.parse(date_str)
    except:
        return None


def extract_key_topics(emails: List[Dict[str, Any]]) -> Dict[str, int]:
    """Extract common topics/keywords from email subjects and bodies"""
    topic_patterns = {
        "📅 Events": ["event", "meeting", "conference", "assembly", "concert", "performance", "sports day"],
        "💰 Payments": ["payment", "pay", "fee", "cost", "money", "£", "$", "invoice", "due"],
        "📝 Forms": ["form", "permission", "slip", "sign", "submit", "return", "deadline"],
        "🏫 School Info": ["closure", "closed", "holiday", "break", "term", "semester"],
        "🚌 Transport": ["bus", "transport", "pick up", "drop off", "parking"],
        "🍽️ Food": ["lunch", "menu", "meal", "food", "cafeteria", "dietary"],
        "📚 Academic": ["homework", "assignment", "test", "exam", "report", "grades"],
        "🎯 Activities": ["club", "activity", "after school", "extracurricular", "team"],
        "📢 Announcements": ["announcement", "update", "news", "important", "urgent"],
        "👕 Uniform": ["uniform", "dress code", "clothing", "wear"],
    }
    
    topic_counts = defaultdict(int)
    
    for email in emails:
        text = f"{email.get('subject', '')} {email.get('body', '')}".lower()
        
        for topic, keywords in topic_patterns.items():
            if any(keyword in text for keyword in keywords):
                topic_counts[topic] += 1
    
    return dict(topic_counts)


def get_email_analytics(emails: List[Dict[str, Any]], days_back: int = 30) -> Dict[str, Any]:
    """Generate comprehensive email analytics"""
    
    # Filter emails by date if requested
    if days_back:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        filtered_emails = []
        for email in emails:
            email_date = parse_email_date(email.get('date', ''))
            if email_date and email_date >= cutoff_date:
                filtered_emails.append(email)
        emails_to_analyze = filtered_emails
    else:
        emails_to_analyze = emails
    
    # Top senders
    senders = [extract_sender_name(e.get('from', '')) for e in emails_to_analyze]
    sender_counts = Counter(senders)
    
    # Email volume by date
    dates = []
    for email in emails_to_analyze:
        email_date = parse_email_date(email.get('date', ''))
        if email_date:
            dates.append(email_date.date())
    date_counts = Counter(dates)
    
    # Key topics
    topics = extract_key_topics(emails_to_analyze)
    
    # Time distribution (hour of day)
    hours = []
    for email in emails_to_analyze:
        email_date = parse_email_date(email.get('date', ''))
        if email_date:
            hours.append(email_date.hour)
    hour_counts = Counter(hours)
    
    # Day of week distribution
    weekdays = []
    for email in emails_to_analyze:
        email_date = parse_email_date(email.get('date', ''))
        if email_date:
            weekdays.append(email_date.strftime('%A'))
    weekday_counts = Counter(weekdays)
    
    # Subject length analysis
    subject_lengths = [len(e.get('subject', '')) for e in emails_to_analyze if e.get('subject')]
    avg_subject_length = sum(subject_lengths) / len(subject_lengths) if subject_lengths else 0
    
    # Urgent/important emails
    urgent_count = sum(1 for e in emails_to_analyze 
                      if any(word in str(e.get('subject', '')).lower() 
                            for word in ['urgent', 'important', 'asap', 'deadline', 'tomorrow']))
    
    return {
        'total_emails': len(emails_to_analyze),
        'original_total': len(emails),
        'top_senders': sender_counts.most_common(10),
        'topics': sorted(topics.items(), key=lambda x: x[1], reverse=True),
        'daily_volume': sorted(date_counts.items()),
        'hour_distribution': dict(hour_counts),
        'weekday_distribution': dict(weekday_counts),
        'avg_subject_length': round(avg_subject_length, 1),
        'urgent_count': urgent_count,
        'date_range': {
            'start': min(dates).isoformat() if dates else None,
            'end': max(dates).isoformat() if dates else None
        }
    }


def get_email_trends(emails: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze email trends over time"""
    
    # Weekly volume trend
    weekly_volumes = defaultdict(int)
    for email in emails:
        email_date = parse_email_date(email.get('date', ''))
        if email_date:
            week = email_date.isocalendar()[1]
            year = email_date.year
            weekly_volumes[f"{year}-W{week:02d}"] += 1
    
    # Calculate trend (increasing/decreasing)
    if len(weekly_volumes) >= 2:
        recent_weeks = sorted(weekly_volumes.keys())[-4:]
        older_weeks = sorted(weekly_volumes.keys())[-8:-4] if len(weekly_volumes) >= 8 else sorted(weekly_volumes.keys())[:4]
        
        recent_avg = sum(weekly_volumes[w] for w in recent_weeks) / len(recent_weeks)
        older_avg = sum(weekly_volumes[w] for w in older_weeks) / len(older_weeks)
        
        if recent_avg > older_avg * 1.2:
            trend = "increasing"
        elif recent_avg < older_avg * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"
    
    return {
        'weekly_volumes': dict(weekly_volumes),
        'trend': trend,
        'recent_average': recent_avg if 'recent_avg' in locals() else None
    }


def find_important_emails(emails: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    """Identify potentially important emails based on keywords and patterns"""
    
    importance_keywords = {
        'deadline': 5,
        'urgent': 5,
        'important': 4,
        'required': 4,
        'mandatory': 4,
        'must': 3,
        'payment due': 5,
        'tomorrow': 4,
        'today': 4,
        'asap': 5,
        'action required': 5,
        'reminder': 3,
        'final': 3
    }
    
    scored_emails = []
    
    for email in emails:
        score = 0
        text = f"{email.get('subject', '')} {email.get('body', '')}".lower()
        
        for keyword, weight in importance_keywords.items():
            if keyword in text:
                score += weight
        
        # Recent emails get a bonus
        email_date = parse_email_date(email.get('date', ''))
        if email_date:
            days_old = (datetime.now() - email_date).days
            if days_old <= 7:
                score += 3
            elif days_old <= 14:
                score += 1
        
        if score > 0:
            scored_emails.append({
                'email': email,
                'score': score,
                'date': email_date
            })
    
    # Sort by score and return top N
    scored_emails.sort(key=lambda x: x['score'], reverse=True)
    
    return [
        {
            'subject': e['email'].get('subject', 'No subject'),
            'from': extract_sender_name(e['email'].get('from', '')),
            'date': e['date'].isoformat() if e['date'] else 'Unknown',
            'importance_score': e['score']
        }
        for e in scored_emails[:limit]
    ]