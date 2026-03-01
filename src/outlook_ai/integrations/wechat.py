"""WeChat push integration using PushPlus."""

import requests
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from outlook_ai.models import Email, VIPMatch, ActionItem


class WeChatPusher:
    """WeChat push notification using PushPlus."""

    URL = "http://www.pushplus.plus/send"

    def __init__(self, token: str):
        """Initialize PushPlus client.
        
        Args:
            token: PushPlus token
        """
        self.token = token

    def push(self, title: str, content: str) -> bool:
        """Send push notification.
        
        Args:
            title: Notification title
            content: Notification content (markdown supported)
            
        Returns:
            True if successful
        """
        data = {
            "token": self.token,
            "title": title[:40],  # PushPlus title limit
            "content": content,
            "template": "markdown"
        }
        try:
            resp = requests.post(self.URL, json=data, timeout=10)
            result = resp.json()
            if result.get("code") != 200:
                print(f"⚠️ Push failed: {result.get('msg')}")
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
        """Push VIP email notification (school/payment alerts).
        
        Args:
            email: Email object
            vip_match: VIP match result
            ai_summary: AI summary text
            
        Returns:
            True if successful
        """
        content = f"""## {vip_match.push_emoji} {vip_match.category.upper()} 通知

**发件人**：{email.sender_name}
**主题**：{email.subject}
**时间**：{email.date.strftime("%Y-%m-%d %H:%M")}
**匹配规则**：{vip_match.rule_name}

---

### AI 摘要
{ai_summary if ai_summary else email.body_text[:300]}
"""
        return self.push(
            f"{vip_match.push_emoji} {email.subject[:30]}", 
            content
        )

    def push_payment_alert(
        self, 
        email: "Email", 
        payment_info: dict
    ) -> bool:
        """Push payment reminder with amount and due date.
        
        Args:
            email: Email object
            payment_info: Payment info extracted by AI
            
        Returns:
            True if successful
        """
        content = f"""## 💰 缴费提醒

**来源**：{email.sender_name}
**主题**：{email.subject}

| 项目 | 详情 |
|------|------|
| 金额 | {payment_info.get("amount", "未知")} |
| 截止日期 | {payment_info.get("due_date", "未知")} |
| 收款方 | {payment_info.get("payee", "未知")} |
| 说明 | {payment_info.get("description", "")} |

⚡ **请及时处理！**
"""
        return self.push(
            f"💰 缴费: {payment_info.get('payee', email.subject[:20])}", 
            content
        )

    def push_daily_summary(
        self, 
        summary: str, 
        action_items: list, 
        stats: dict
    ) -> bool:
        """Push daily email summary.
        
        Args:
            summary: AI generated summary
            action_items: List of action items
            stats: Statistics dict
            
        Returns:
            True if successful
        """
        now = datetime.now().strftime("%m-%d %H:%M")

        content = f"""## 📬 邮件摘要 ({now})

**统计**：共 {stats.get("total", 0)} 封未读 | 🏫 学校 {stats.get("school", 0)} | 💰 缴费 {stats.get("payment", 0)} | 🚫 垃圾 {stats.get("spam", 0)}

---

### 概览
{summary}
"""

        if action_items:
            content += "\n---\n\n### ✅ 待办事项\n\n"
            for item in action_items:
                emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item.priority, "⚪")
                content += f"- {emoji} **{item.title}**"
                if item.deadline:
                    content += f"（截止 {item.deadline}）"
                content += "\n"

        return self.push(f"📬 邮件摘要 {now}", content)
