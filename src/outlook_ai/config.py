"""Configuration management."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from dotenv import load_dotenv


class Config(BaseModel):
    """Application configuration."""
    # Email settings
    email: str = ""
    app_password: str = ""
    imap_host: str = "outlook.office365.com"
    imap_port: int = 993
    
    # Azure/Graph API settings
    azure_client_id: str = ""
    azure_client_secret: str = ""
    
    # Ollama settings
    ollama_model: str = "qwen2.5:14b"
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 120
    
    # Notion settings (V2)
    notion_token: str = ""
    notion_database_id: str = ""
    
    # WeChat Push settings (V2)
    pushplus_token: str = ""
    
    # Scan settings (V2)
    scan_days: int = 3
    
    # Cache settings
    cache_dir: str = "~/.outlook-ai"
    
    @property
    def use_graph_api(self) -> bool:
        """Check if Graph API should be used."""
        return bool(self.azure_client_id)
    
    @property
    def use_notion(self) -> bool:
        """Check if Notion integration is enabled."""
        return bool(self.notion_token and self.notion_database_id)
    
    @property
    def use_wechat_push(self) -> bool:
        """Check if WeChat push is enabled."""
        return bool(self.pushplus_token)
    
    def get_cache_db_path(self) -> Path:
        """Get cache database path."""
        return Path(self.cache_dir).expanduser() / "cache.db"
    
    def save_to_env_file(self, path: Optional[Path] = None) -> None:
        """Save configuration to .env file."""
        if path is None:
            path = Path.home() / ".outlook-ai" / ".env"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        env_content = f"""# Outlook AI Configuration
OUTLOOK_EMAIL={self.email}
APP_PASSWORD={self.app_password}
AZURE_CLIENT_ID={self.azure_client_id}
AZURE_CLIENT_SECRET={self.azure_client_secret}
OLLAMA_MODEL={self.ollama_model}
OLLAMA_BASE_URL={self.ollama_base_url}
OLLAMA_TIMEOUT={self.ollama_timeout}

# Notion Integration (V2)
NOTION_TOKEN={self.notion_token}
NOTION_DATABASE_ID={self.notion_database_id}

# WeChat Push (V2)
PUSHPLUS_TOKEN={self.pushplus_token}

# Scan Settings (V2)
SCAN_DAYS={self.scan_days}
"""
        path.write_text(env_content)


_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create configuration."""
    global _config
    
    if _config is None:
        # Load from environment
        load_dotenv()
        
        # Try to load from .env file
        env_file = Path.home() / ".outlook-ai" / ".env"
        if env_file.exists():
            load_dotenv(env_file)
        
        _config = Config(
            email=os.getenv("OUTLOOK_EMAIL", ""),
            app_password=os.getenv("APP_PASSWORD", ""),
            azure_client_id=os.getenv("AZURE_CLIENT_ID", ""),
            azure_client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:14b"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
            notion_token=os.getenv("NOTION_TOKEN", ""),
            notion_database_id=os.getenv("NOTION_DATABASE_ID", ""),
            pushplus_token=os.getenv("PUSHPLUS_TOKEN", ""),
            scan_days=int(os.getenv("SCAN_DAYS", "3")),
            cache_dir=os.getenv("CACHE_DIR", "~/.outlook-ai"),
        )
    
    return _config


def reload_config() -> Config:
    """Reload configuration."""
    global _config
    _config = None
    return get_config()
