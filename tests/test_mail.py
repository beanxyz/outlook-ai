"""Tests for mail module."""

import pytest
from outlook_ai.mail import OutlookMailClient
from outlook_ai.models import Email


def test_mail_client_init():
    """Test mail client initialization."""
    client = OutlookMailClient(
        email="test@example.com",
        app_password="password",
    )
    
    assert client.email == "test@example.com"
    assert client.host == "outlook.office365.com"
