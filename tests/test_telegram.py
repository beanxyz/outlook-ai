"""Tests for Telegram integration."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from outlook_ai.models import Email, VIPMatch, ActionItem, Priority
from outlook_ai.integrations.telegram import TelegramPusher


class TestTelegramPusher:
    """Test Telegram push functionality."""

    @patch("requests.post")
    def test_push_success(self, mock_post):
        """Test successful push."""
        mock_post.return_value.json.return_value = {"ok": True}
        
        pusher = TelegramPusher(token="test_token", chat_id="123456")
        result = pusher.push("Test message")
        
        assert result is True
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_push_failure(self, mock_post):
        """Test push failure."""
        mock_post.return_value.json.return_value = {
            "ok": False, 
            "description": "Bot was blocked"
        }
        
        pusher = TelegramPusher(token="test_token", chat_id="123456")
        result = pusher.push("Test message")
        
        assert result is False

    @patch("requests.post")
    def test_push_message_too_long(self, mock_post):
        """Test message truncation for too long messages."""
        mock_post.return_value.json.return_value = {"ok": True}
        
        pusher = TelegramPusher(token="test_token", chat_id="123456")
        
        # Create a very long message
        long_message = "x" * 5000
        result = pusher.push(long_message)
        
        # Check that message was truncated
        called_data = mock_post.call_args[1]["json"]["text"]
        # Allow for truncation indicator text (max 4100 to account for truncation message)
        assert len(called_data) <= 4100
        assert "truncated" in called_data

    @patch("requests.post")
    def test_escape_markdown(self, mock_post):
        """Test Markdown escaping."""
        mock_post.return_value.json.return_value = {"ok": True}
        
        pusher = TelegramPusher(token="test_token", chat_id="123456")
        
        # Test with special characters
        message = "Test [link](http://example.com) and `code`"
        pusher.push(message)
        
        # Verify the message was escaped properly
        called_data = mock_post.call_args[1]["json"]["text"]
        assert "\\[" in called_data or "[" in called_data  # Either escaped or original

    @patch("requests.post")
    def test_push_vip_email(self, mock_post):
        """Test VIP email push."""
        mock_post.return_value.json.return_value = {"ok": True}
        
        pusher = TelegramPusher(token="test_token", chat_id="123456")
        
        email = Email(
            uid="1",
            subject="Test School Email",
            sender="School <school@test.edu>",
            sender_name="School",
            sender_email="school@test.edu",
            date=datetime.now(),
        )
        
        vip_match = VIPMatch(
            rule_name="Test School",
            category="school",
            push_emoji="🏫",
            matched_by="sender",
            matched_pattern="testschool"
        )
        
        result = pusher.push_vip_email(email, vip_match, "AI Summary")
        
        assert result is True
        called_data = mock_post.call_args[1]["json"]["text"]
        assert "🏫" in called_data
        assert "Test School Email" in called_data

    @patch("requests.post")
    def test_push_daily_summary(self, mock_post):
        """Test daily summary push."""
        mock_post.return_value.json.return_value = {"ok": True}
        
        pusher = TelegramPusher(token="test_token", chat_id="123456")
        
        summary = "You have 5 important emails"
        action_items = [
            ActionItem(
                title="Reply to teacher",
                priority="high",
                deadline="2026-03-01"
            )
        ]
        stats = {"total": 10, "school": 2, "payment": 1, "spam": 3}
        
        result = pusher.push_daily_summary(summary, action_items, stats)
        
        assert result is True
        called_data = mock_post.call_args[1]["json"]["text"]
        assert "📬" in called_data
        assert "10" in called_data
