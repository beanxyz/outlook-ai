"""Utility functions."""

from typing import Optional


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate a string to max length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def parse_email_address(email: str) -> tuple[Optional[str], Optional[str]]:
    """Parse email address to name and email.
    
    Args:
        email: Email string like "Name <email@example.com>"
        
    Returns:
        Tuple of (name, email)
    """
    if not email:
        return None, None
    
    if "<" in email and ">" in email:
        name = email.split("<")[0].strip()
        email_addr = email.split("<")[1].split(">")[0].strip()
        return name or None, email_addr
    
    return None, email.strip()


def format_email_list(emails: list) -> str:
    """Format email list for display.
    
    Args:
        emails: List of email strings
        
    Returns:
        Formatted string
    """
    if not emails:
        return ""
    if len(emails) == 1:
        return emails[0]
    return f"{', '.join(emails[:-1])} and {emails[-1]}"
