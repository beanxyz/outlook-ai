"""Notion integration for task management."""

import requests
from typing import Optional

from outlook_ai.models import ActionItem


class NotionClient:
    """Notion task management integration."""

    BASE_URL = "https://api.notion.com/v1"

    def __init__(self, token: str, database_id: str):
        """Initialize Notion client.
        
        Args:
            token: Notion API token
            database_id: Notion database ID for tasks
        """
        self.token = token
        self.database_id = database_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

    def create_task(self, action: ActionItem) -> Optional[str]:
        """Create a Notion task.
        
        Args:
            action: ActionItem object
            
        Returns:
            Page URL or None on failure
        """
        properties = {
            "Title": {"title": [{"text": {"content": action.title}}]},
            "Status": {"select": {"name": "Todo"}},
            "Priority": {"select": {"name": action.priority.capitalize()}},
            "Category": {"select": {"name": action.category.capitalize()}},
            "Source": {"rich_text": [{"text": {"content": action.source_email_subject[:100]}}]},
            "Email UID": {"rich_text": [{"text": {"content": action.source_email_uid[:100]}}]},
        }

        # Deadline (optional)
        if action.deadline:
            properties["Deadline"] = {"date": {"start": action.deadline}}

        data = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
        }

        # Add page content (detailed description)
        if action.description:
            data["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": action.description}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": f"来源邮件：{action.source_email_subject}"}}]
                    }
                }
            ]

        try:
            resp = requests.post(
                f"{self.BASE_URL}/pages",
                headers=self._headers(),
                json=data
            )
            resp.raise_for_status()
            return resp.json()["url"]
        except Exception as e:
            print(f"⚠️ Notion create task failed: {e}")
            return None

    def check_duplicate(self, email_uid: str) -> bool:
        """Check if task already exists for this email.
        
        Args:
            email_uid: Email UID
            
        Returns:
            True if duplicate exists
        """
        data = {
            "filter": {
                "property": "Email UID",
                "rich_text": {"equals": email_uid[:100]}
            }
        }
        try:
            resp = requests.post(
                f"{self.BASE_URL}/databases/{self.database_id}/query",
                headers=self._headers(),
                json=data
            )
            resp.raise_for_status()
            return len(resp.json().get("results", [])) > 0
        except Exception as e:
            print(f"⚠️ Notion check duplicate failed: {e}")
            return False

    def update_status(self, page_id: str, status: str) -> bool:
        """Update task status.
        
        Args:
            page_id: Notion page ID
            status: New status (Todo / In Progress / Done)
            
        Returns:
            True if successful
        """
        try:
            resp = requests.patch(
                f"{self.BASE_URL}/pages/{page_id}",
                headers=self._headers(),
                json={"properties": {"Status": {"select": {"name": status}}}}
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"⚠️ Notion update status failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Test Notion API connection.
        
        Returns:
            True if connection successful
        """
        try:
            resp = requests.get(
                f"{self.BASE_URL}/databases/{self.database_id}",
                headers=self._headers()
            )
            return resp.status_code == 200
        except Exception:
            return False
