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
    
    # Cache settings
    cache_dir: str = ".cache"
    
    @property
    def use_graph_api(self) -> bool:
        """Check if Graph API should be used."""
        return bool(self.azure_client_id)
    
    def get_cache_db_path(self) -> Path:
        """Get cache database path."""
        return Path(self.cache_dir) / "emails.db"
    
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
"""
        path.write_text(env_content)


_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create configuration."""
    global _config
    
    if _config is None:
        # Load from environment
        load_dotenv()
        
        _config = Config(
            email=os.getenv("OUTLOOK_EMAIL", ""),
            app_password=os.getenv("APP_PASSWORD", ""),
            azure_client_id=os.getenv("AZURE_CLIENT_ID", ""),
            azure_client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:14b"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
        )
        
        # Try to load from .env file
        env_file = Path.home() / ".outlook-ai" / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            _config = Config(
                email=os.getenv("OUTLOOK_EMAIL", _config.email),
                app_password=os.getenv("APP_PASSWORD", _config.app_password),
                azure_client_id=os.getenv("AZURE_CLIENT_ID", _config.azure_client_id),
                azure_client_secret=os.getenv("AZURE_CLIENT_SECRET", _config.azure_client_secret),
                ollama_model=os.getenv("OLLAMA_MODEL", _config.ollama_model),
                ollama_base_url=os.getenv("OLLAMA_BASE_URL", _config.ollama_base_url),
                ollama_timeout=int(os.getenv("OLLAMA_TIMEOUT", str(_config.ollama_timeout))),
            )
    
    return _config
