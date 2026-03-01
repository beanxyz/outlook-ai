"""Tests for VIP rule engine."""

import pytest
from datetime import datetime
from outlook_ai.models import Email
from outlook_ai.vip import VIPRuleEngine


class TestVIPRuleEngine:
    """Test VIP rule matching."""

    def test_match_school_sender(self, tmp_path):
        """Test matching school sender."""
        # Create a temporary config file
        config_file = tmp_path / "vip_rules.yaml"
        config_file.write_text("""
vip_senders:
  - name: Test School
    patterns: ["testschool"]
    category: school
    push_emoji: "🏫"
vip_keywords: {}
dedup_hours: 24
""")
        
        engine = VIPRuleEngine(config_path=str(config_file))
        
        email = Email(
            uid="1",
            subject="Test Email",
            sender="Principal <office@testschool.edu.au>",
            sender_name="Principal",
            sender_email="office@testschool.edu.au",
            date=datetime.now(),
        )
        
        match = engine.check(email)
        
        assert match is not None
        assert match.category == "school"
        assert match.push_emoji == "🏫"
        assert match.matched_by == "sender"

    def test_match_payment_sender(self, tmp_path):
        """Test matching payment sender."""
        config_file = tmp_path / "vip_rules.yaml"
        config_file.write_text("""
vip_senders:
  - name: Flexischools
    patterns: ["flexischools"]
    category: payment
    push_emoji: "💰"
vip_keywords: {}
dedup_hours: 24
""")
        
        engine = VIPRuleEngine(config_path=str(config_file))
        
        email = Email(
            uid="1",
            subject="Invoice",
            sender="Flexischools <info@flexischools.com.au>",
            sender_name="Flexischools",
            sender_email="info@flexischools.com.au",
            date=datetime.now(),
        )
        
        match = engine.check(email)
        
        assert match is not None
        assert match.category == "payment"
        assert match.push_emoji == "💰"

    def test_match_keyword_in_subject(self, tmp_path):
        """Test matching keyword in subject."""
        config_file = tmp_path / "vip_rules.yaml"
        config_file.write_text("""
vip_senders: []
vip_keywords:
  school:
    - "excursion"
  payment:
    - "invoice"
dedup_hours: 24
""")
        
        engine = VIPRuleEngine(config_path=str(config_file))
        
        email = Email(
            uid="1",
            subject="School Excursion Permission Form",
            sender="teacher@school.edu.au",
            sender_name="Teacher",
            sender_email="teacher@school.edu.au",
            body_text="Please sign the permission form",
            date=datetime.now(),
        )
        
        match = engine.check(email)
        
        assert match is not None
        assert match.category == "school"
        assert match.matched_by == "keyword"
        assert match.matched_pattern == "excursion"

    def test_no_match_regular_email(self, tmp_path):
        """Test no match for regular email."""
        config_file = tmp_path / "vip_rules.yaml"
        config_file.write_text("""
vip_senders: []
vip_keywords: {}
dedup_hours: 24
""")
        
        engine = VIPRuleEngine(config_path=str(config_file))
        
        email = Email(
            uid="1",
            subject="Hello",
            sender="friend@gmail.com",
            sender_name="Friend",
            sender_email="friend@gmail.com",
            date=datetime.now(),
        )
        
        match = engine.check(email)
        
        assert match is None

    def test_default_config_creation(self, tmp_path, monkeypatch):
        """Test default config is created."""
        # Mock home directory
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        
        # This should create default config
        engine = VIPRuleEngine(config_path=str(tmp_path / ".outlook-ai" / "vip_rules.yaml"))
        
        # Check default config was loaded
        assert engine.config is not None
        assert len(engine.config.get("vip_senders", [])) > 0
