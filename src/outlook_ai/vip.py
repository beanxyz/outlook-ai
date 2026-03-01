"""VIP rule engine for high-priority email matching."""

import os
import yaml
from typing import Optional, List, Dict

from outlook_ai.models import Email, VIPMatch


class VIPRuleEngine:
    """VIP rule engine - runs before AI classification.
    
    Matches emails against predefined rules (senders, keywords).
    Matched emails are marked as high priority and pushed immediately.
    """

    DEFAULT_CONFIG_PATH = "~/.outlook-ai/vip_rules.yaml"

    def __init__(self, config_path: str = None):
        """Initialize VIP rule engine.
        
        Args:
            config_path: Path to VIP rules config file
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config: Dict = {}
        self.dedup_hours: int = 24
        self._load_config()

    def _load_config(self) -> None:
        """Load VIP rules from config file."""
        config_path = os.path.expanduser(self.config_path)
        
        if not os.path.exists(config_path):
            # Use default config
            self._create_default_config()
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
            self.dedup_hours = self.config.get("dedup_hours", 24)
        except Exception as e:
            print(f"⚠️ Failed to load VIP config: {e}")
            self._create_default_config()

    def _create_default_config(self) -> None:
        """Create default VIP config."""
        self.config = {
            "vip_senders": [
                {"name": "Oakhill Drive Public School", "patterns": ["oakhill", "oakhilldrive"], "category": "school", "push_emoji": "🏫"},
                {"name": "Seesaw", "patterns": ["seesaw", "web.seesaw.me"], "category": "school", "push_emoji": "🏫"},
                {"name": "School Bytes", "patterns": ["schoolbytes", "school bytes"], "category": "school", "push_emoji": "🏫"},
                {"name": "Compass / Sentral", "patterns": ["compass", "sentral"], "category": "school", "push_emoji": "🏫"},
                {"name": "Flexischools", "patterns": ["flexischools"], "category": "payment", "push_emoji": "💰"},
                {"name": "Westpac", "patterns": ["westpac"], "category": "payment", "push_emoji": "🏦"},
                {"name": "YMCA", "patterns": ["ymca"], "category": "school", "push_emoji": "🏫"},
            ],
            "vip_keywords": {
                "school": [
                    "school fee", "payment due", "payment reminder", "overdue",
                    "excursion", "permission", "report card", "parent teacher",
                    "school event", "canteen", "assembly", "sports carnival", "book week"
                ],
                "payment": [
                    "invoice", "payment due", "amount owing", "overdue",
                    "direct debit", "final notice", "payment required", "low balance", "insufficient"
                ]
            },
            "dedup_hours": 24
        }
        
        # Save default config
        self._save_default_config()

    def _save_default_config(self) -> None:
        """Save default config to file."""
        config_path = os.path.expanduser(self.config_path)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, allow_unicode=True)
            print(f"✓ Created default VIP config: {config_path}")
        except Exception as e:
            print(f"⚠️ Failed to save default config: {e}")

    def reload(self) -> None:
        """Hot reload: reload config without restarting."""
        self._load_config()

    def check(self, email: Email) -> Optional[VIPMatch]:
        """Check if email matches VIP rules.
        
        Args:
            email: Email object
            
        Returns:
            VIPMatch if matched, None otherwise
        """
        # 1. Sender matching (priority)
        sender_text = f"{email.sender_name or ''} {email.sender_email or ''}".lower()
        
        for rule in self.config.get("vip_senders", []):
            for pattern in rule.get("patterns", []):
                if pattern.lower() in sender_text:
                    return VIPMatch(
                        rule_name=rule.get("name", "Unknown"),
                        category=rule.get("category", "other"),
                        push_emoji=rule.get("push_emoji", "📌"),
                        matched_by="sender",
                        matched_pattern=pattern
                    )

        # 2. Keyword matching (subject + body preview)
        text = f"{email.subject} {email.body_preview or email.body_text[:500]}".lower()
        
        for category, keywords in self.config.get("vip_keywords", {}).items():
            for keyword in keywords:
                if keyword.lower() in text:
                    return VIPMatch(
                        rule_name=category,
                        category=category,
                        push_emoji="🏫" if category == "school" else "💰",
                        matched_by="keyword",
                        matched_pattern=keyword
                    )

        return None
