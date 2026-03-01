"""Debug script to test Graph API with cache."""
from outlook_ai.graph import OutlookGraphClient, MSAL_CACHE_FILE
from outlook_ai.config import get_config
import msal

config = get_config()
print(f"Client ID: {config.azure_client_id[:20]}...")
print(f"Cache file exists: {MSAL_CACHE_FILE.exists()}")

# Load cache from file
cache = msal.SerializableTokenCache()
if MSAL_CACHE_FILE.exists():
    cache.deserialize(open(MSAL_CACHE_FILE, "rb").read())
    print(f"Cache loaded, has_data: {bool(cache)}")
    # Check cache contents
    accounts = cache.get_accounts()
    print(f"Accounts in cache: {accounts}")
else:
    print("No cache file found")

# Now create app with cache
app = msal.PublicClientApplication(
    client_id=config.azure_client_id,
    authority="https://login.microsoftonline.com/consumers",
    token_cache=cache
)

# Check accounts
accounts = app.get_accounts()
print(f"Accounts from app: {accounts}")

# Try silent token
if accounts:
    result = app.acquire_token_silent(
        scopes=["Mail.Read", "Mail.ReadWrite", "User.Read"],
        account=accounts[0]
    )
    print(f"Silent result: {result}")
