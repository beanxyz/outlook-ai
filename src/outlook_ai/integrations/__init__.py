"""Integrations module for Outlook AI."""

from outlook_ai.integrations.calendar import MicrosoftCalendarClient
from outlook_ai.integrations.notion import NotionClient
from outlook_ai.integrations.wechat import WeChatPusher

__all__ = [
    "MicrosoftCalendarClient",
    "NotionClient", 
    "WeChatPusher",
]
