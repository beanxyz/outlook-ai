"""Tests for AI module."""

import pytest
from outlook_ai.models import Email, Priority, EmailCategory
from outlook_ai.ai import OllamaEmailAI


def test_truncate_string():
    """Test string truncation."""
    from outlook_ai.utils import truncate_string
    
    assert truncate_string("hello", 10) == "hello"
    assert truncate_string("hello world", 8) == "hello..."


def test_email_model():
    """Test Email model."""
    from datetime import datetime
    
    email = Email(
        uid="123",
        subject="Test",
        sender="test@example.com",
        date=datetime.now(),
    )
    assert email.uid == "123"
    assert email.subject == "Test"


def test_classify_spam():
    """Test spam classification."""
    ai = OllamaEmailAI()
    
    # Test with casino email
    email = Email(
        uid="1",
        subject="🎰 Win big money!",
        sender="casino@spam.com",
        date=None,
    )
    
    classification = ai.classify(email)
    assert classification.category == EmailCategory.SPAM
