"""Telegram push integration."""

import re
import requests
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from outlook_ai.models import Email, VIPMatch, ActionItem

TELEGRAM_API_URL = "https://api.telegram.org/bot"

# Telegram Markdown reserved characters that need escaping
MARKDOWN_RESERVED = re.compile(r'([_*\[\]()~`>#+\-=|{}.!])')


class TelegramPusher:
    """Telegram bot push notification."""

    def __init__(self, token: str, chat_id: str):
        """Initialize Telegram client.
        
        Args:
            token: Telegram Bot Token
            chat_id: Telegram Chat ID
        """
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"{TELEGRAM_API_URL}{token}"

    def _escape_markdown(self, text: str) -> str:
        """Escape reserved Markdown characters to prevent injection.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        # Escape Markdown special characters
        # Note: We escape but preserve our emoji and basic formatting
        def _escape_char(match):
            char = match.group(1)
            # Don't escape our formatting markers
            if char in ['_', '*']:  # Keep emphasis markers
                return char
            return f'\\{char}'
        
        # Only escape potentially dangerous characters
        return MARKDOWN_RESERVED.sub(r'\\\1', text)

    def push(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send push notification.
        
        Args:
            text: Message text
            parse_mode: Parse mode (Markdown or HTML)
            
        Returns:
            True if successful
        """
        # Limit message length (Telegram max is 4096 chars)
        if len(text) > 4000:
            text = text[:4000] + "\n\n... (truncated)"
        
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        try:
            resp = requests.post(f"{self.api_url}/sendMessage", json=data, timeout=10)
            result = resp.json()
            if not result.get("ok"):
                print(f"⚠️ Push failed: {result.get('description')}")
                return False
            return True
        except Exception as e:
            print(f"⚠️ Push error: {e}")
            return False

    def push_vip_email(
        self, 
        email: "Email", 
        vip_match: "VIPMatch", 
        ai_summary: str = ""
    ) -> bool:
        """Push VIP email notification (school/payment alerts)."""
        text = f"""📌 **{vip_match.category.upper()} 通知**

👤 发件人：{email.sender_name}
📧 主题：{email.subject}
🕐 时间：{email.date.strftime("%Y-%m-%d %H:%M")}
🔍 匹配规则：{vip_match.rule_name}

---
{ai_summary if ai_summary else email.body_text[:300]}"""
        
        return self.push(f"{vip_match.push_emoji} {email.subject[:30]}\n\n{text}")

    def push_payment_alert(
        self, 
        email: "Email", 
        payment_info: dict
    ) -> bool:
        """Push payment reminder with amount and due date."""
        text = f"""💰 *缴费提醒*

📤 来源：{email.sender_name}
📧 主题：{email.subject}

💵 金额：{payment_info.get("amount", "未知")}
📅 截止日期：{payment_info.get("due_date", "未知")}
🏦 收款方：{payment_info.get("payee", "未知")}
📝 说明：{payment_info.get("description", "")}

⚡ 请及时处理！"""
        
        return self.push(f"💰 缴费: {payment_info.get('payee', email.subject[:20])}\n\n{text}")

    def push_daily_summary(
        self, 
        summary: str, 
        action_items: list, 
        stats: dict
    ) -> bool:
        """Push daily email summary."""
        now = datetime.now().strftime("%m-%d %H:%M")

        text = f"""📬 *邮件摘要* ({now})

📊 统计：共 {stats.get("total", 0)} 封未读 | 🏫 学校 {stats.get("school", 0)} | 💰 缴费 {stats.get("payment", 0)} | 🚫 垃圾 {stats.get("spam", 0)}

---
📝 概览：
{summary}
"""

        if action_items:
            text += "\n---\n\n✅ 待办事项\n\n"
            for item in action_items:
                emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item.priority, "⚪")
                text += f"- {emoji} **{item.title}**"
                if item.deadline:
                    text += f"（截止 {item.deadline}）"
                text += "\n"

        return self.push(f"📬 邮件摘要 {now}\n\n{text}")
