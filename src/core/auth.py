"""
Authentication functionality for the Databricks MCP server.
"""

import logging
import threading
import time
from typing import Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logger = logging.getLogger(__name__)

class OAuthTokenProvider:
    """
    Get and refresh OAuth tokens for Databricks API access.

    This class handles the retrieval and caching of OAuth tokens using the
    client credentials flow. 
    It automatically refreshes the token 60 s before expiration.
    """

    def __init__(self, host: str, client_id: str, client_secret: str) -> None:
        self._host = host.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: Optional[str] = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        """Return a valid access token, refreshing it if necessary."""
        with self._lock:
            if self._token and time.time() < self._expires_at - 60:
                return self._token
            return self._refresh()

    def _refresh(self) -> str:
        url = f"{self._host}/oidc/v1/token"
        logger.debug("Refreshing OAuth M2M token")
        response = requests.post(
            url,
            data={"grant_type": "client_credentials", "scope": "all-apis"},
            auth=(self._client_id, self._client_secret),
            verify=False,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        self._token = payload["access_token"]
        self._expires_at = time.time() + payload.get("expires_in", 3600)
        logger.debug("OAuth token refreshed; expires in %ds", payload.get("expires_in", 3600))
        return self._token