"""Microsoft Calendar integration using Graph API."""

import requests
from datetime import datetime, timedelta
from typing import Optional

from outlook_ai.models import ActionItem, Email


class MicrosoftCalendarClient:
    """Microsoft Calendar integration via Graph API."""

    BASE_URL = "https://graph.microsoft.com/v1.0/me"

    def __init__(self, auth: "MicrosoftAuth"):
        """Initialize Calendar client.
        
        Args:
            auth: MicrosoftAuth instance (shares token with mail)
        """
        self.auth = auth

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.auth.get_token()}",
            "Content-Type": "application/json"
        }

    def create_event(
        self, 
        action: ActionItem, 
        source_email: Email
    ) -> Optional[str]:
        """Create calendar event from ActionItem.
        
        Args:
            action: ActionItem object
            source_email: Source email
            
        Returns:
            Event ID or None on failure
        """
        # Determine time
        if action.deadline:
            start_time = action.deadline
            # If only date without time, create all-day event
            if "T" not in action.deadline:
                return self._create_all_day_event(action, source_email)
        else:
            # No deadline, set to tomorrow
            start_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT09:00:00")

        end_time = (datetime.fromisoformat(start_time) + timedelta(hours=1)).isoformat()

        # Reminders based on priority
        reminders = {
            "high": [30, 60, 1440],     # 30min, 1hr, 1day before
            "medium": [30, 60],          # 30min, 1hr before
            "low": [30],                 # 30min before
        }

        event_data = {
            "subject": action.title,
            "body": {
                "contentType": "text",
                "content": f"{action.description}\n\n来源邮件：{source_email.subject}\n发件人：{source_email.sender}"
            },
            "start": {
                "dateTime": start_time,
                "timeZone": "Australia/Sydney"
            },
            "end": {
                "dateTime": end_time,
                "timeZone": "Australia/Sydney"
            },
            "isReminderOn": True,
            "reminderMinutesBeforeStart": reminders.get(action.priority, [30])[0],
        }

        # Payment events: remind 1 day before
        if action.category == "payment" and action.deadline:
            event_data["reminderMinutesBeforeStart"] = 1440  # 24 hours

        # School activities: remind 2 days before
        if action.category in ("school", "meeting") and action.deadline:
            event_data["reminderMinutesBeforeStart"] = 2880  # 48 hours

        try:
            resp = requests.post(
                f"{self.BASE_URL}/events",
                headers=self._headers(),
                json=event_data
            )
            resp.raise_for_status()
            return resp.json()["id"]
        except Exception as e:
            print(f"⚠️ Calendar create event failed: {e}")
            return None

    def _create_all_day_event(
        self, 
        action: ActionItem, 
        source_email: Email
    ) -> Optional[str]:
        """Create all-day event.
        
        Args:
            action: ActionItem object
            source_email: Source email
            
        Returns:
            Event ID or None on failure
        """
        event_data = {
            "subject": action.title,
            "body": {
                "contentType": "text",
                "content": f"{action.description}\n\n来源邮件：{source_email.subject}"
            },
            "start": {
                "dateTime": f"{action.deadline}T00:00:00",
                "timeZone": "Australia/Sydney"
            },
            "end": {
                "dateTime": f"{action.deadline}T23:59:59",
                "timeZone": "Australia/Sydney"
            },
            "isAllDay": True,
            "isReminderOn": True,
            "reminderMinutesBeforeStart": 1440,  # 1 day before
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/events",
                headers=self._headers(),
                json=event_data
            )
            resp.raise_for_status()
            return resp.json()["id"]
        except Exception as e:
            print(f"⚠️ Calendar create all-day event failed: {e}")
            return None

    def check_duplicate(self, action: ActionItem) -> bool:
        """Check if event already exists.
        
        Args:
            action: ActionItem object
            
        Returns:
            True if duplicate exists
        """
        if not action.deadline:
            return False

        params = {
            "$filter": f"subject eq '{action.title}'",
            "$top": 5
        }
        try:
            resp = requests.get(
                f"{self.BASE_URL}/events",
                headers=self._headers(),
                params=params
            )
            resp.raise_for_status()
            return len(resp.json().get("value", [])) > 0
        except Exception as e:
            print(f"⚠️ Calendar check duplicate failed: {e}")
            return False

    def get_upcoming_events(self, days: int = 7) -> list:
        """Get upcoming calendar events.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of events
        """
        start = datetime.now().isoformat()
        end = (datetime.now() + timedelta(days=days)).isoformat()
        
        params = {
            "$filter": f"start/dateTime ge '{start}' and end/dateTime le '{end}'",
            "$orderby": "start/dateTime",
            "$top": 50
        }
        
        try:
            resp = requests.get(
                f"{self.BASE_URL}/events",
                headers=self._headers(),
                params=params
            )
            resp.raise_for_status()
            return resp.json().get("value", [])
        except Exception as e:
            print(f"⚠️ Calendar get events failed: {e}")
            return []
