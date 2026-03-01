"""Email cache using SQLite with push deduplication."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from outlook_ai.models import Email, ActionItem


class EmailCache:
    """SQLite-based email cache with push deduplication."""
    
    def __init__(self, db_path: str = "~/.outlook-ai/cache.db"):
        """Initialize cache.
        
        Args:
            db_path: Path to SQLite database
        """
        db_path = str(Path(db_path).expanduser())
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Processed emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_emails (
                email_uid TEXT PRIMARY KEY,
                subject TEXT,
                sender TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ai_category TEXT,
                ai_priority TEXT,
                vip_category TEXT
            )
        """)
        
        # Push log table (for deduplication)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_uid TEXT,
                push_type TEXT,
                pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email_uid, push_type)
            )
        """)
        
        # Action items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_uid TEXT,
                title TEXT,
                description TEXT,
                deadline TEXT,
                priority TEXT,
                category TEXT,
                synced_calendar BOOLEAN DEFAULT FALSE,
                synced_notion BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # AI results cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_results (
                email_uid TEXT,
                task_type TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (email_uid, task_type)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # === Processed Email Methods ===
    
    def is_processed(self, email_uid: str) -> bool:
        """Check if email has been processed.
        
        Args:
            email_uid: Email UID
            
        Returns:
            True if already processed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM processed_emails WHERE email_uid = ?", 
            (email_uid,)
        )
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def mark_processed(
        self, 
        email: Email, 
        category: str = "", 
        priority: str = "", 
        vip_category: str = ""
    ) -> None:
        """Mark email as processed.
        
        Args:
            email: Email object
            category: AI category
            priority: AI priority
            vip_category: VIP category
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO processed_emails
               (email_uid, subject, sender, ai_category, ai_priority, vip_category)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (email.uid, email.subject, email.sender, category, priority, vip_category)
        )
        conn.commit()
        conn.close()
    
    # === Push Deduplication Methods ===
    
    def is_pushed(self, email_uid: str, push_type: str, dedup_hours: int = 24) -> bool:
        """Check if push already sent (deduplication).
        
        Args:
            email_uid: Email UID
            push_type: Type of push (vip, payment, daily)
            dedup_hours: Hours to deduplicate within
            
        Returns:
            True if already pushed within dedup window
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT 1 FROM push_log
               WHERE email_uid = ? AND push_type = ?
               AND pushed_at > datetime('now', ?)""",
            (email_uid, push_type, f"-{dedup_hours} hours")
        )
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def log_push(self, email_uid: str, push_type: str) -> None:
        """Log push notification.
        
        Args:
            email_uid: Email UID
            push_type: Type of push
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO push_log (email_uid, push_type) VALUES (?, ?)",
                (email_uid, push_type)
            )
            conn.commit()
        except Exception:
            pass  # Ignore duplicate errors
        finally:
            conn.close()
    
    # === Action Items Methods ===
    
    def save_action_item(self, item: ActionItem) -> None:
        """Save action item.
        
        Args:
            item: Action item to save
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO action_items (email_uid, title, description, deadline, priority, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            item.source_email_uid,
            item.title,
            item.description,
            item.deadline,
            item.priority,
            item.category,
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
            SELECT email_uid, title, description, deadline, priority, category
            FROM action_items
            ORDER BY created_at DESC
        """)
        
        items = []
        for row in cursor.fetchall():
            item = ActionItem(
                source_email_uid=row[0],
                title=row[1],
                description=row[2],
                deadline=row[3],
                priority=row[4],
                category=row[5],
            )
            items.append(item)
        
        conn.close()
        return items
    
    def get_pending_actions(self, category: str = None) -> List[ActionItem]:
        """Get pending action items.
        
        Args:
            category: Filter by category
            
        Returns:
            List of pending action items
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category:
            cursor.execute("""
                SELECT email_uid, title, description, deadline, priority, category
                FROM action_items
                WHERE synced_calendar = FALSE OR synced_notion = FALSE
                AND category = ?
                ORDER BY deadline ASC
            """, (category,))
        else:
            cursor.execute("""
                SELECT email_uid, title, description, deadline, priority, category
                FROM action_items
                WHERE synced_calendar = FALSE OR synced_notion = FALSE
                ORDER BY deadline ASC
            """)
        
        items = []
        for row in cursor.fetchall():
            item = ActionItem(
                source_email_uid=row[0],
                title=row[1],
                description=row[2],
                deadline=row[3],
                priority=row[4],
                category=row[5],
            )
            items.append(item)
        
        conn.close()
        return items
    
    # === Cache Management ===
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM processed_emails")
        cursor.execute("DELETE FROM push_log")
        cursor.execute("DELETE FROM action_items")
        cursor.execute("DELETE FROM ai_results")
        
        conn.commit()
        conn.close()
    
    def clear_push_log(self) -> None:
        """Clear push log only."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM push_log")
        conn.commit()
        conn.close()
