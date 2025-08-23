"""Email domain entity - pure business logic, no external dependencies."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class EmailPriority(Enum):
    """Email priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailCategory(Enum):
    """Email categories for classification."""
    PERSONAL = "personal"
    WORK = "work"
    MARKETING = "marketing"
    NEWSLETTER = "newsletter"
    NOTIFICATION = "notification"
    SPAM = "spam"


@dataclass
class EmailAddress:
    """Value object for email addresses."""
    address: str
    name: Optional[str] = None
    
    def __post_init__(self):
        if not self._is_valid_email(self.address):
            raise ValueError(f"Invalid email address: {self.address}")
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Basic email validation."""
        return "@" in email and "." in email.split("@")[1]
    
    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address


@dataclass
class EmailAttachment:
    """Email attachment entity."""
    filename: str
    content_type: str
    size: int
    content: Optional[bytes] = None
    extracted_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityScore:
    """Value object for email quality scoring."""
    overall: float
    relevance: float
    completeness: float
    authenticity: float
    
    def __post_init__(self):
        scores = [self.overall, self.relevance, self.completeness, self.authenticity]
        if not all(0 <= score <= 100 for score in scores):
            raise ValueError("Quality scores must be between 0 and 100")
    
    @property
    def is_high_quality(self) -> bool:
        """Check if email meets quality threshold."""
        return self.overall >= 40.0  # Configurable threshold
    
    @property
    def weighted_score(self) -> float:
        """Calculate weighted quality score."""
        return (
            self.overall * 0.4 +
            self.relevance * 0.3 +
            self.completeness * 0.2 +
            self.authenticity * 0.1
        )


@dataclass
class Email:
    """Core email entity with business logic."""
    id: str
    message_id: str
    subject: str
    sender: EmailAddress
    recipients: List[EmailAddress]
    cc: List[EmailAddress]
    bcc: List[EmailAddress]
    date: datetime
    body_text: str
    body_html: Optional[str]
    attachments: List[EmailAttachment]
    headers: Dict[str, str]
    
    # Computed properties
    quality_score: Optional[QualityScore] = None
    category: Optional[EmailCategory] = None
    priority: Optional[EmailPriority] = None
    thread_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: List[str] = field(default_factory=list)
    
    # Metadata
    folder: str = "INBOX"
    flags: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_read(self) -> bool:
        """Check if email has been read."""
        return "\\Seen" in self.flags
    
    @property
    def is_flagged(self) -> bool:
        """Check if email is flagged/starred."""
        return "\\Flagged" in self.flags
    
    @property
    def has_attachments(self) -> bool:
        """Check if email has attachments."""
        return len(self.attachments) > 0
    
    @property
    def total_attachment_size(self) -> int:
        """Calculate total size of all attachments."""
        return sum(att.size for att in self.attachments)
    
    @property
    def is_thread(self) -> bool:
        """Check if email is part of a thread."""
        return bool(self.in_reply_to or self.references)
    
    def get_reply_chain_depth(self) -> int:
        """Calculate the depth of the reply chain."""
        return len(self.references)
    
    def extract_summary(self, max_length: int = 200) -> str:
        """Extract a summary from the email body."""
        text = self.body_text or ""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def to_document(self) -> Dict[str, Any]:
        """Convert email to document format for indexing."""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "subject": self.subject,
            "sender": str(self.sender),
            "recipients": [str(r) for r in self.recipients],
            "date": self.date.isoformat(),
            "body": self.body_text,
            "category": self.category.value if self.category else None,
            "priority": self.priority.value if self.priority else None,
            "quality_score": self.quality_score.overall if self.quality_score else None,
            "has_attachments": self.has_attachments,
            "folder": self.folder,
            "labels": self.labels,
            "metadata": self.metadata
        }