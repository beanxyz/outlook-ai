"""Microsoft Graph API client for Outlook."""

from datetime import date, datetime
from typing import List, Optional
import logging
import os
import pathlib

import msal
import requests

from outlook_ai.models import Email


logger = logging.getLogger(__name__)

# MSAL cache file location (default location)
CACHE_DIR = pathlib.Path.home() / ".outlook-ai"
MSAL_CACHE_FILE = CACHE_DIR / "msal_cache.json"


class OutlookGraphClient:
    """Microsoft Graph API client for Outlook."""
    
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
    SCOPES = ["Mail.Read", "Mail.ReadWrite", "User.Read"]
    
    def __init__(
        self,
        client_id: str,
        authority: str = "https://login.microsoftonline.com/consumers",
    ):
        """Initialize Graph API client.
        
        Args:
            client_id: Azure AD application client ID
            authority: OAuth authority URL
        """
        self.client_id = client_id
        self.authority = authority
        
        # Use SerializableTokenCache for serialization support
        cache = msal.SerializableTokenCache()
        if MSAL_CACHE_FILE.exists():
            try:
                cache.deserialize(open(MSAL_CACHE_FILE, "r").read())
                logger.info("Loaded MSAL cache from %s", MSAL_CACHE_FILE)
            except Exception as e:
                logger.warning("Failed to load MSAL cache: %s", e)
        
        self._app = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority,
            token_cache=cache,
        )
        self._token: Optional[str] = None
    
    def _save_cache(self) -> None:
        """Save MSAL cache to disk."""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_data = self._app.token_cache.serialize()
            # serialize() returns str, need to encode to bytes
            open(MSAL_CACHE_FILE, "w").write(cache_data)
            logger.info("Saved MSAL cache to %s", MSAL_CACHE_FILE)
        except Exception as e:
            logger.warning("Failed to save MSAL cache: %s", e)
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self._token = None
        return False
    
    def get_token(self) -> str:
        """Get token silently first, then interactively if needed."""
        # Try silent token acquisition first
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(
                scopes=self.scopes,
                account=accounts[0]
            )
            if result and "access_token" in result:
                self._token = result["access_token"]
                return self._token
        
        # If silent fails, use interactive
        return self.get_token_interactive()
    
    def get_token_interactive(self) -> str:
        """Get token interactively (opens browser)."""
        result = self._app.acquire_token_interactive(scopes=self.scopes)
        if result and "access_token" in result:
            self._token = result["access_token"]
            # Save cache after new token acquired
            self._save_cache()
            return self._token
        error_msg = result.get("error") if result else "Unknown"
        raise RuntimeError(f"Failed to get token: {error_msg}")
    
    @property
    def scopes(self) -> List[str]:
        """Get OAuth scopes."""
        return [f"https://graph.microsoft.com/{s}" for s in self.SCOPES]
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """Make API request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response JSON
        """
        if not self._token:
            self.get_token()
        
        url = f"{self.GRAPH_API_BASE}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"
        
        response = requests.request(
            method,
            url,
            headers=headers,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()
    
    def fetch_recent(self, count: int = 20, folder: str = "INBOX") -> List[Email]:
        """Fetch recent emails.
        
        Args:
            count: Number of emails
            folder: Folder name
            
        Returns:
            List of Email objects
        """
        # Validate folder name
        safe_folder = self._validate_folder(folder)
        
        try:
            result = self._make_request(
                "GET",
                f"/me/mailFolders/{safe_folder}/messages",
                params={
                    "$top": count,
                    "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,isRead,hasAttachments",
                    "$orderby": "receivedDateTime desc",
                },
            )
            
            emails = []
            for msg in result.get("value", []):
                email_obj = self._parse_message(msg)
                emails.append(email_obj)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def fetch_unread(self, folder: str = "INBOX") -> List[Email]:
        """Fetch unread emails.
        
        Args:
            folder: Folder name
            
        Returns:
            List of Email objects
        """
        try:
            result = self._make_request(
                "GET",
                f"/me/mailFolders/{folder}/messages",
                params={
                    "$filter": "isRead eq false",
                    "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,isRead,hasAttachments",
                    "$orderby": "receivedDateTime desc",
                },
            )
            
            emails = []
            for msg in result.get("value", []):
                email_obj = self._parse_message(msg)
                emails.append(email_obj)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching unread emails: {e}")
            return []
    
    def fetch_by_date_range(self, since: date, folder: str = "INBOX") -> List[Email]:
        """Fetch emails by date range.
        
        Args:
            since: Start date
            folder: Folder name
            
        Returns:
            List of Email objects
        """
        # Format date as ISO 8601 with time
        since_str = since.isoformat() + "T00:00:00Z"
        
        try:
            result = self._make_request(
                "GET",
                f"/me/mailFolders/{folder}/messages",
                params={
                    "$filter": f"receivedDateTime ge {since_str}",
                    "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,isRead,hasAttachments",
                    "$orderby": "receivedDateTime desc",
                },
            )
            
            if not result:
                logger.warning("Empty response from Graph API")
                return []
            
            emails = []
            for msg in result.get("value", []):
                email_obj = self._parse_message(msg)
                emails.append(email_obj)
            
            return emails
            
        except Exception as e:
            logger.error("Error fetching emails by date: %s", e)
            return []
    
    def _parse_message(self, msg: dict) -> Email:
        """Parse Graph API message to Email model.
        
        Args:
            msg: Graph API message
            
        Returns:
            Email object
        """
        # Parse sender
        from_addr = msg.get("from", {})
        sender_email = from_addr.get("emailAddress", {})
        sender_name = sender_email.get("name", "")
        sender_addr = sender_email.get("address", "")
        
        # Parse recipients
        to_list = []
        for r in msg.get("toRecipients", []):
            to_list.append(r.get("emailAddress", {}).get("address", ""))
        
        cc_list = []
        for r in msg.get("ccRecipients", []):
            cc_list.append(r.get("emailAddress", {}).get("address", ""))
        
        # Parse date
        date_str = msg.get("receivedDateTime", "")
        try:
            email_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            email_date = datetime.now()
        
        # Get body
        body = msg.get("body", {})
        body_text = body.get("contentText", "")
        
        return Email(
            uid=msg.get("id", ""),
            subject=msg.get("subject", ""),
            sender=f"{sender_name} <{sender_addr}>" if sender_name else sender_addr,
            sender_name=sender_name,
            sender_email=sender_addr,
            to=to_list,
            cc=cc_list,
            date=email_date,
            body_text=body_text,
            is_read=msg.get("isRead", True),
            has_attachments=msg.get("hasAttachments", False),
        )
    
    def _escape_odata_string(self, value: str) -> str:
        """Escape string for OData filter to prevent injection.
        
        Args:
            value: String to escape
            
        Returns:
            Escaped string
        """
        # Escape single quotes by doubling them
        return value.replace("'", "''")
    
    def _validate_folder(self, folder: str) -> str:
        """Validate folder name to prevent path traversal.
        
        Args:
            folder: Folder name
            
        Returns:
            Validated folder name
            
        Raises:
            ValueError: If folder name is invalid
        """
        # Block path traversal attempts
        if ".." in folder or "/" in folder or "\\" in folder:
            raise ValueError("Invalid folder name")
        # Block other dangerous characters
        if any(c in folder for c in ["<", ">", "|", "&", ";", "`", "$", "(", ")"]):
            raise ValueError("Invalid folder name")
        return folder
    
    def _validate_uid(self, uid: str) -> str:
        """Validate email UID to prevent injection.
        
        Args:
            uid: Email UID
            
        Returns:
            Validated UID
            
        Raises:
            ValueError: If UID is invalid
        """
        # Block dangerous characters
        if any(c in uid for c in ["<", ">", "|", "&", ";", "`", "$", "(", ")", "/", "\\", " "]):
            raise ValueError("Invalid email UID")
        return uid
    
    def search(self, query: str, folder: str = "INBOX") -> List[Email]:
        """Search emails.
        
        Args:
            query: Search query
            folder: Folder name
            
        Returns:
            List of Email objects
        """
        # Escape query to prevent OData injection
        escaped_query = self._escape_odata_string(query)
        
        try:
            result = self._make_request(
                "GET",
                f"/me/mailFolders/{folder}/messages",
                params={
                    "$filter": f"contains(subject,'{escaped_query}') or contains(body/content,'{escaped_query}')",
                    "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,isRead,hasAttachments",
                    "$orderby": "receivedDateTime desc",
                },
            )
            
            emails = []
            for msg in result.get("value", []):
                email_obj = self._parse_message(msg)
                emails.append(email_obj)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def get_folders(self) -> List[str]:
        """Get list of folders.
        
        Returns:
            List of folder names
        """
        try:
            result = self._make_request(
                "GET",
                "/me/mailFolders",
            )
            
            folders = []
            for folder in result.get("value", []):
                folders.append(folder.get("displayName", ""))
            
            return folders
            
        except Exception as e:
            logger.error(f"Error getting folders: {e}")
            return []
    
    def mark_as_read(self, uid: str, folder: str = "INBOX") -> bool:
        """Mark email as read.
        
        Args:
            uid: Email ID
            folder: Folder name
            
        Returns:
            True if successful
        """
        try:
            self._make_request(
                "PATCH",
                f"/me/mailFolders/{folder}/messages/{uid}",
                json={"isRead": True},
            )
            return True
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
