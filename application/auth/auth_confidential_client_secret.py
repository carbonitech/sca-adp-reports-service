"""
    Authentication of application with Microsoft Azure 
        for sending automated emails
"""
import os
import msal
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "authority": os.getenv('MS_AUTHORITY'),
    "client_id": os.getenv('MS_CLIENT_ID'),
    "scope": [ os.getenv('MS_SCOPE') ],
    "secret": os.getenv('MS_SECRET')
}

def get_auth_token_for_ms_graph() -> str:
    # Create a preferably long-lived app instance which maintains a token cache.
    app = msal.ConfidentialClientApplication(
        CONFIG["client_id"], authority=CONFIG["authority"],
        client_credential=CONFIG["secret"],
        # token_cache=...  # Default cache is in memory only.
                        # You can learn how to use SerializableTokenCache from
                        # https://msal-python.rtfd.io/en/latest/#msal.SerializableTokenCache
        )

    # Acquire token from Microsoft
    result = None

    # looks up a token from cache
    # account parameter is None because token for current app, NOT user
    result = app.acquire_token_silent(CONFIG["scope"], account=None)

    if not result:
        # acquire from Azure if token not in cache
        result = app.acquire_token_for_client(scopes=CONFIG["scope"])

    if "access_token" not in result:
        print(result.get("error"))
        print(result.get("error_description"))
        print(result.get("correlation_id"))  # need this when reporting a bug
        # Calling graph using the access token
    
    return result["access_token"]
        

