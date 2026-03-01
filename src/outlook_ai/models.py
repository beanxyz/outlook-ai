"""Data models for email processing."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Email priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EmailCategory(str, Enum):
    """Email categories."""
    IMPORTANT = "important"
    WORK = "work"
    PERSONAL = "personal"
    SCHOOL = "school"
    SUBSCRIPTION = "subscription"
    PROMOTION = "promotion"
    SPAM = "spam"
    BILL = "bill"
    NOTIFICATION = "notification"


class Email(BaseModel):
    """Email model."""
    uid: str
    subject: str
    sender: str
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    to: List[str] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    date: datetime
    body_text: str = ""
    body_html: str = ""
    body_preview: str = ""
    is_read: bool = True
    is_flagged: bool = False
    has_attachments: bool = False
    attachments: List[str] = Field(default_factory=list)
    
    # AI processing results
    vip_match: Optional["VIPMatch"] = None
    ai_category: str = ""
    ai_priority: str = ""

    @property
    def from_email_subject(self) -> str:
        """Get sender and subject for identification."""
        return f"{self.sender}: {self.subject}"


class EmailClassification(BaseModel):
    """Email classification result."""
    category: EmailCategory
    priority: Priority
    reason: str


class VIPMatch(BaseModel):
    """VIP rule match result."""
    rule_name: str           # e.g., "Oakhill Drive Public School"
    category: str           # "school" / "payment"
    push_emoji: str         # "🏫" / "💰"
    matched_by: str         # "sender" / "keyword"
    matched_pattern: str     # The actual matched pattern


class ActionItem(BaseModel):
    """Action item extracted from email."""
    title: str = ""                       # Task title
    description: str = ""                 # Detailed description
    deadline: Optional[str] = None         # "2026-03-05" or "2026-03-05T17:00:00"
    priority: str = "medium"              # high / medium / low
    source_email_uid: str = ""             # Source email UID
    source_email_subject: str = ""         # Source email subject
    category: str = "task"                # meeting / reply / payment / task / reminder / school
    calendar_event: bool = False           # Whether to create calendar event
    notion_task: bool = False              # Whether to create Notion task
    
    @property
    def task(self) -> str:
        """Compatibility alias for title."""
        return self.title


# Update forward references
Email.model_rebuild()
