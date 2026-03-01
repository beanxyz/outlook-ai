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
    is_read: bool = True
    is_flagged: bool = False
    has_attachments: bool = False
    attachments: List[str] = Field(default_factory=list)

    @property
    def from_email_subject(self) -> str:
        """Get sender and subject for identification."""
        return f"{self.sender}: {self.subject}"


class EmailClassification(BaseModel):
    """Email classification result."""
    category: EmailCategory
    priority: Priority
    reason: str


class ActionItem(BaseModel):
    """Action item extracted from email."""
    task: str
    deadline: Optional[str] = None
    from_email_subject: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    email_uid: Optional[str] = None
