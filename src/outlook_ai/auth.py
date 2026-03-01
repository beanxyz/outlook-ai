"""Microsoft OAuth 2.0 authentication module."""

import os
import msal

from outlook_ai.config import get_config


class MicrosoftAuth:
    """Microsoft OAuth 2.0 authentication.
    
    Uses MSAL for token management with local cache.
    Supports silent token refresh and interactive login.
    """

    SCOPES = [
        "Mail.Read",
        "Calendars.ReadWrite", 
        "User.Read",
    ]
    
    TOKEN_CACHE_PATH = "~/.outlook-ai/token_cache.json"

    def __init__(self, client_id: str):
        """Initialize Microsoft auth.
        
        Args:
            client_id: Azure AD application client ID
        """
        self.client_id = client_id
        
        # Load cached token
        self.cache = msal.SerializableTokenCache()
        cache_path = os.path.expanduser(self.TOKEN_CACHE_PATH)
        if os.path.exists(cache_path):
            try:
                self.cache.deserialize(open(cache_path).read())
            except Exception:
                pass  # Start fresh if cache is corrupted

        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority="https://login.microsoftonline.com/consumers",  # Personal accounts
            token_cache=self.cache
        )

    def get_token(self) -> str:
        """
        Get access token.
        
        First tries silent refresh using cached refresh token.
        Falls back to interactive login if needed.
        
        Returns:
            Access token string
            
        Raises:
            Exception: If authentication fails
        """
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(self.SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self._save_cache()
                return result["access_token"]

        # First time or token expired: interactive login
        result = self.app.acquire_token_interactive(scopes=self.SCOPES)
        if "access_token" in result:
            self._save_cache()
            return result["access_token"]
        
        raise Exception(f"Authentication failed: {result.get('error_description')}")

    def _save_cache(self) -> None:
        """Save token cache to disk."""
        cache_path = os.path.expanduser(self.TOKEN_CACHE_PATH)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            f.write(self.cache.serialize())
        os.chmod(cache_path, 0o600)

    @property
    def scopes(self) -> list:
        """Get OAuth scopes with full URL."""
        return [f"https://graph.microsoft.com/{s}" for s in self.SCOPES]


def get_auth() -> MicrosoftAuth:
    """Get MicrosoftAuth instance from config.
    
    Returns:
        MicrosoftAuth instance
    """
    config = get_config()
    return MicrosoftAuth(client_id=config.azure_client_id)
