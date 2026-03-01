"""Outlook Mail client using IMAP."""

import imaplib
import email
from datetime import date, datetime, timedelta
from typing import List, Optional
import logging

from outlook_ai.models import Email


logger = logging.getLogger(__name__)


class OutlookMailClient:
    """IMAP-based Outlook mail client."""
    
    def __init__(
        self,
        email: str,
        app_password: str,
        host: str = "outlook.office365.com",
        port: int = 993,
    ):
        """Initialize IMAP client.
        
        Args:
            email: Email address
            app_password: App password
            host: IMAP server host
            port: IMAP server port
        """
        self.email = email
        self.app_password = app_password
        self.host = host
        self.port = port
        self._connection: Optional[imaplib.IMAP4_SSL] = None
    
    def __enter__(self):
        """Connect to IMAP server."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection."""
        self.disconnect()
    
    def connect(self) -> None:
        """Connect to IMAP server."""
        try:
            self._connection = imaplib.IMAP4_SSL(host=self.host, port=self.port)
            self._connection.login(self.email, self.app_password)
            logger.info(f"Connected to {self.host}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from IMAP server."""
        if self._connection:
            try:
                self._connection.logout()
            except Exception:
                pass
            self._connection = None
    
    def _connection_check(self) -> None:
        """Check connection status."""
        if self._connection is None:
            self.connect()
    
    def fetch_recent(self, count: int = 20, folder: str = "INBOX") -> List[Email]:
        """Fetch recent emails.
        
        Args:
            count: Number of emails to fetch
            folder: Folder name
            
        Returns:
            List of Email objects
        """
        self._connection_check()
        
        try:
            status, _ = self._connection.select(folder)
            if status != "OK":
                logger.error(f"Failed to select folder: {folder}")
                return []
            
            # Fetch recent emails (from newest)
            typ, msg_ids = self._connection.search(None, "ALL")
            if typ != "OK":
                return []
            
            msg_id_list = msg_ids[0].split()
            msg_id_list = msg_id_list[-count:]  # Get last N emails
            
            emails = []
            for msg_id in msg_id_list:
                email_obj = self._fetch_email(msg_id.decode())
                if email_obj:
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
            List of unread Email objects
        """
        self._connection_check()
        
        try:
            status, _ = self._connection.select(folder)
            if status != "OK":
                return []
            
            # Search for unread emails
            typ, msg_ids = self._connection.search(None, "UNSEEN")
            if typ != "OK":
                return []
            
            msg_id_list = msg_ids[0].split()
            
            emails = []
            for msg_id in msg_id_list:
                email_obj = self._fetch_email(msg_id.decode())
                if email_obj:
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
        self._connection_check()
        
        try:
            status, _ = self._connection.select(folder)
            if status != "OK":
                return []
            
            # Search for emails since date
            since_str = since.strftime("%d-%b-%Y")
            typ, msg_ids = self._connection.search(None, f"SINCE {since_str}")
            if typ != "OK":
                return []
            
            msg_id_list = msg_ids[0].split()
            
            emails = []
            for msg_id in msg_id_list:
                email_obj = self._fetch_email(msg_id.decode())
                if email_obj:
                    emails.append(email_obj)
            
            # Sort by date (newest first)
            emails.sort(key=lambda e: e.date, reverse=True)
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails by date: {e}")
            return []
    
    def _fetch_email(self, msg_id: str) -> Optional[Email]:
        """Fetch a single email by ID.
        
        Args:
            msg_id: Message ID
            
        Returns:
            Email object or None
        """
        try:
            typ, msg_data = self._connection.fetch(msg_id, "(RFC822)")
            if typ != "OK":
                return None
            
            msg_content = msg_data[0][1]
            msg = email.message_from_bytes(msg_content)
            
            # Parse headers
            subject = msg.get("Subject", "")
            sender = msg.get("From", "")
            date_str = msg.get("Date", "")
            
            # Parse date
            try:
                email_date = email.utils.parsedate_to_datetime(date_str)
            except Exception:
                email_date = datetime.now()
            
            # Check if read
            typ, flags = self._connection.fetch(msg_id, "(FLAGS)")
            is_read = b"\\Seen" in flags[0] if flags else False
            
            # Get body
            body_text = ""
            body_html = ""
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body_text = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    elif content_type == "text/html":
                        body_html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_text = payload.decode("utf-8", errors="ignore")
            
            # Parse sender
            from_name, from_email = self._parse_sender(sender)
            
            return Email(
                uid=msg_id,
                subject=subject,
                sender=sender,
                sender_name=from_name,
                sender_email=from_email,
                to=[msg.get("To", "")],
                cc=[msg.get("Cc", "")],
                date=email_date,
                body_text=body_text,
                body_html=body_html,
                is_read=is_read,
            )
            
        except Exception as e:
            logger.error(f"Error parsing email {msg_id}: {e}")
            return None
    
    def _parse_sender(self, sender: str) -> tuple:
        """Parse sender address.
        
        Args:
            sender: Sender string
            
        Returns:
            Tuple of (name, email)
        """
        if "<" in sender and ">" in sender:
            name = sender.split("<")[0].strip()
            email = sender.split("<")[1].split(">")[0].strip()
            return name, email
        return None, sender.strip()
    
    def search(self, query: str, folder: str = "INBOX") -> List[Email]:
        """Search emails.
        
        Args:
            query: Search query
            folder: Folder name
            
        Returns:
            List of Email objects
        """
        self._connection_check()
        
        try:
            status, _ = self._connection.select(folder)
            if status != "OK":
                return []
            
            typ, msg_ids = self._connection.search(None, query)
            if typ != "OK":
                return []
            
            msg_id_list = msg_ids[0].split()
            
            emails = []
            for msg_id in msg_id_list:
                email_obj = self._fetch_email(msg_id.decode())
                if email_obj:
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
        self._connection_check()
        
        try:
            typ, folder_list = self._connection.list()
            if typ != "OK":
                return []
            
            folders = []
            for folder in folder_list:
                folder_name = folder.decode().split('"')[-2]
                folders.append(folder_name)
            
            return folders
            
        except Exception as e:
            logger.error(f"Error getting folders: {e}")
            return []
    
    def mark_as_read(self, uid: str, folder: str = "INBOX") -> bool:
        """Mark email as read.
        
        Args:
            uid: Email UID
            folder: Folder name
            
        Returns:
            True if successful
        """
        self._connection_check()
        
        try:
            status, _ = self._connection.select(folder)
            if status != "OK":
                return False
            
            self._connection.store(uid, "+FLAGS", "\\Seen")
            return True
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
