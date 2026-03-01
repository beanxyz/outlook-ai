"""Email cache using SQLite."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from outlook_ai.models import Email, ActionItem


class EmailCache:
    """SQLite-based email cache."""
    
    def __init__(self, db_path: str = "emails.db"):
        """Initialize cache.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                uid TEXT PRIMARY KEY,
                subject TEXT,
                sender TEXT,
                sender_name TEXT,
                sender_email TEXT,
                date TEXT,
                body_text TEXT,
                is_read INTEGER,
                cached_at TEXT
            )
        """)
        
        # Action items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT,
                deadline TEXT,
                from_email_subject TEXT,
                priority TEXT,
                email_uid TEXT,
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def cache_emails(self, emails: List[Email]) -> None:
        """Cache emails.
        
        Args:
            emails: List of emails to cache
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for email in emails:
            cursor.execute("""
                INSERT OR REPLACE INTO emails (uid, subject, sender, sender_name, sender_email, date, body_text, is_read, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email.uid,
                email.subject,
                email.sender,
                email.sender_name,
                email.sender_email,
                email.date.isoformat(),
                email.body_text[:5000],  # Limit body size
                1 if email.is_read else 0,
                datetime.now().isoformat(),
            ))
        
        conn.commit()
        conn.close()
    
    def get_cached_emails(self, limit: int = 50) -> List[Email]:
        """Get cached emails.
        
        Args:
            limit: Maximum number of emails
            
        Returns:
            List of cached emails
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT uid, subject, sender, sender_name, sender_email, date, body_text, is_read
            FROM emails
            ORDER BY date DESC
            LIMIT ?
        """, (limit,))
        
        emails = []
        for row in cursor.fetchall():
            email = Email(
                uid=row[0],
                subject=row[1],
                sender=row[2],
                sender_name=row[3],
                sender_email=row[4],
                date=datetime.fromisoformat(row[5]),
                body_text=row[6],
                is_read=bool(row[7]),
            )
            emails.append(email)
        
        conn.close()
        return emails
    
    def save_action_item(self, item: ActionItem) -> None:
        """Save action item.
        
        Args:
            item: Action item to save
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO action_items (task, deadline, from_email_subject, priority, email_uid, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            item.task,
            item.deadline,
            item.from_email_subject,
            item.priority.value,
            item.email_uid,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    def get_action_items(self) -> List[ActionItem]:
        """Get action items.
        
        Returns:
            List of action items
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task, deadline, from_email_subject, priority, email_uid
            FROM action_items
            ORDER BY created_at DESC
        """)
        
        items = []
        for row in cursor.fetchall():
            item = ActionItem(
                task=row[0],
                deadline=row[1],
                from_email_subject=row[2],
                priority=row[3],
                email_uid=row[4],
            )
            items.append(item)
        
        conn.close()
        return items
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM emails")
        cursor.execute("DELETE FROM action_items")
        
        conn.commit()
        conn.close()
