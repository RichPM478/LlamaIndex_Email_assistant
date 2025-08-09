# app/reminders/follow_up_system.py
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ReminderType(Enum):
    ACTION_REQUIRED = "action_required"
    FOLLOW_UP = "follow_up"
    DEADLINE = "deadline"
    PAYMENT = "payment"
    MEETING = "meeting"

class ReminderPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

@dataclass
class Reminder:
    id: str
    email_id: str
    type: ReminderType
    priority: ReminderPriority
    title: str
    description: str
    due_date: datetime
    created_at: datetime
    completed: bool = False
    snoozed_until: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'email_id': self.email_id,
            'type': self.type.value,
            'priority': self.priority.value,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat(),
            'created_at': self.created_at.isoformat(),
            'completed': self.completed,
            'snoozed_until': self.snoozed_until.isoformat() if self.snoozed_until else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reminder':
        return cls(
            id=data['id'],
            email_id=data['email_id'],
            type=ReminderType(data['type']),
            priority=ReminderPriority(data['priority']),
            title=data['title'],
            description=data['description'],
            due_date=datetime.fromisoformat(data['due_date']),
            created_at=datetime.fromisoformat(data['created_at']),
            completed=data.get('completed', False),
            snoozed_until=datetime.fromisoformat(data['snoozed_until']) if data.get('snoozed_until') else None
        )

class FollowUpSystem:
    """Intelligent follow-up and reminder system for emails"""
    
    def __init__(self, data_dir: str = "data/reminders"):
        self.data_dir = data_dir
        self.reminders_file = os.path.join(data_dir, "reminders.json")
        os.makedirs(data_dir, exist_ok=True)
        
        self.reminders: List[Reminder] = self._load_reminders()
    
    def _load_reminders(self) -> List[Reminder]:
        """Load reminders from storage"""
        if not os.path.exists(self.reminders_file):
            return []
        
        try:
            with open(self.reminders_file, 'r') as f:
                data = json.load(f)
                return [Reminder.from_dict(item) for item in data]
        except Exception as e:
            print(f"Error loading reminders: {e}")
            return []
    
    def _save_reminders(self):
        """Save reminders to storage"""
        try:
            with open(self.reminders_file, 'w') as f:
                data = [reminder.to_dict() for reminder in self.reminders]
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving reminders: {e}")
    
    def create_reminder_from_email(self, email_data: Dict[str, Any], insights=None) -> List[Reminder]:
        """Create reminders automatically from email content"""
        reminders = []
        
        # Basic email info
        email_id = email_data.get('message_id') or email_data.get('uid', '')
        subject = email_data.get('subject', 'No Subject')
        body = email_data.get('body', '')
        sender = email_data.get('from', '')
        
        if insights:
            # Create reminders based on email intelligence
            for action_item in insights.action_items:
                reminder_id = f"action_{email_id}_{hash(action_item) % 10000}"
                
                reminder = Reminder(
                    id=reminder_id,
                    email_id=email_id,
                    type=ReminderType.ACTION_REQUIRED,
                    priority=self._determine_priority(insights.importance_level, insights.categories),
                    title=f"Action: {action_item[:50]}...",
                    description=f"From: {sender}\nSubject: {subject}\nAction: {action_item}",
                    due_date=self._calculate_due_date(insights.estimated_response_time),
                    created_at=datetime.now()
                )
                reminders.append(reminder)
            
            # Create deadline reminders from key dates
            for date_info in insights.key_dates:
                if date_info['days_from_now'] > 0:  # Only future dates
                    reminder_id = f"deadline_{email_id}_{hash(date_info['text']) % 10000}"
                    
                    reminder = Reminder(
                        id=reminder_id,
                        email_id=email_id,
                        type=ReminderType.DEADLINE,
                        priority=ReminderPriority.HIGH,
                        title=f"Deadline: {date_info['text']}",
                        description=f"From: {sender}\nSubject: {subject}\nDeadline: {date_info['text']}",
                        due_date=datetime.fromisoformat(date_info['date']) - timedelta(days=1),  # Remind 1 day before
                        created_at=datetime.now()
                    )
                    reminders.append(reminder)
            
            # Create payment reminders
            if insights.financial_amounts and any(cat.value == 'payment' for cat in insights.categories):
                amounts = ', '.join(insights.financial_amounts)
                reminder_id = f"payment_{email_id}_{hash(amounts) % 10000}"
                
                reminder = Reminder(
                    id=reminder_id,
                    email_id=email_id,
                    type=ReminderType.PAYMENT,
                    priority=ReminderPriority.HIGH,
                    title=f"Payment Due: {amounts}",
                    description=f"From: {sender}\nSubject: {subject}\nAmounts: {amounts}",
                    due_date=self._calculate_due_date("Within 1 week"),
                    created_at=datetime.now()
                )
                reminders.append(reminder)
        
        # Add reminders to the system
        for reminder in reminders:
            self.add_reminder(reminder)
        
        return reminders
    
    def _determine_priority(self, importance_level, categories) -> ReminderPriority:
        """Determine reminder priority based on email importance"""
        if importance_level.name == 'CRITICAL':
            return ReminderPriority.URGENT
        elif importance_level.name == 'HIGH':
            return ReminderPriority.HIGH
        elif any(cat.value in ['urgent', 'payment', 'deadline'] for cat in categories):
            return ReminderPriority.HIGH
        elif importance_level.name == 'MEDIUM':
            return ReminderPriority.MEDIUM
        else:
            return ReminderPriority.LOW
    
    def _calculate_due_date(self, estimated_response_time: str) -> datetime:
        """Calculate due date based on estimated response time"""
        now = datetime.now()
        
        if "1 hour" in estimated_response_time:
            return now + timedelta(hours=1)
        elif "4 hours" in estimated_response_time:
            return now + timedelta(hours=4)
        elif "1 day" in estimated_response_time:
            return now + timedelta(days=1)
        elif "2 days" in estimated_response_time:
            return now + timedelta(days=2)
        elif "1 week" in estimated_response_time:
            return now + timedelta(weeks=1)
        else:
            return now + timedelta(days=3)  # Default to 3 days
    
    def add_reminder(self, reminder: Reminder):
        """Add a new reminder"""
        # Check if reminder already exists
        existing = next((r for r in self.reminders if r.id == reminder.id), None)
        if not existing:
            self.reminders.append(reminder)
            self._save_reminders()
    
    def get_active_reminders(self) -> List[Reminder]:
        """Get all active (non-completed) reminders"""
        now = datetime.now()
        return [
            r for r in self.reminders 
            if not r.completed and (not r.snoozed_until or r.snoozed_until <= now)
        ]
    
    def get_due_reminders(self, hours_ahead: int = 24) -> List[Reminder]:
        """Get reminders due within specified hours"""
        cutoff = datetime.now() + timedelta(hours=hours_ahead)
        return [
            r for r in self.get_active_reminders()
            if r.due_date <= cutoff
        ]
    
    def get_overdue_reminders(self) -> List[Reminder]:
        """Get overdue reminders"""
        now = datetime.now()
        return [
            r for r in self.get_active_reminders()
            if r.due_date < now
        ]
    
    def complete_reminder(self, reminder_id: str):
        """Mark a reminder as completed"""
        reminder = next((r for r in self.reminders if r.id == reminder_id), None)
        if reminder:
            reminder.completed = True
            self._save_reminders()
    
    def snooze_reminder(self, reminder_id: str, snooze_hours: int = 24):
        """Snooze a reminder for specified hours"""
        reminder = next((r for r in self.reminders if r.id == reminder_id), None)
        if reminder:
            reminder.snoozed_until = datetime.now() + timedelta(hours=snooze_hours)
            self._save_reminders()
    
    def get_reminder_summary(self) -> Dict[str, Any]:
        """Get summary of all reminders"""
        active = self.get_active_reminders()
        overdue = self.get_overdue_reminders()
        due_today = self.get_due_reminders(24)
        
        by_priority = {}
        for priority in ReminderPriority:
            by_priority[priority.name.lower()] = len([
                r for r in active if r.priority == priority
            ])
        
        by_type = {}
        for reminder_type in ReminderType:
            by_type[reminder_type.name.lower()] = len([
                r for r in active if r.type == reminder_type
            ])
        
        return {
            'total_active': len(active),
            'overdue': len(overdue),
            'due_today': len(due_today),
            'completed_total': len([r for r in self.reminders if r.completed]),
            'by_priority': by_priority,
            'by_type': by_type
        }
    
    def cleanup_old_reminders(self, days_old: int = 30):
        """Clean up old completed reminders"""
        cutoff = datetime.now() - timedelta(days=days_old)
        original_count = len(self.reminders)
        
        self.reminders = [
            r for r in self.reminders
            if not (r.completed and r.created_at < cutoff)
        ]
        
        removed_count = original_count - len(self.reminders)
        if removed_count > 0:
            self._save_reminders()
        
        return removed_count

# Global follow-up system instance
follow_up_system = FollowUpSystem()