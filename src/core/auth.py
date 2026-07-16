"""
Authentication functionality for the Databricks MCP server.
"""

import datetime
import json
import logging
import threading
import time
from typing import Dict, Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OAuth M2M (client credentials) — service principal
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# OAuth U2M (user-to-machine)
# ---------------------------------------------------------------------------

# Shared with auth_flow.py to keep a single source of truth for the cache
# location and client ID (avoids the two modules drifting apart).
from src.tools.auth_flow import CLIENT_ID as _U2M_CLIENT_ID
from src.tools.auth_flow import TOKEN_CACHE as _TOKEN_CACHE


class U2MTokenProvider:
    """
    Get OAuth U2M tokens by reading the token cache directly:
        ~/.databricks/token-cache.json

    Cache format (same as saved by auth_flow._save_token):
        {"Hosts": {"https://host/": {"databricks-cli": {
            "TokenType": "Bearer",
            "AccessToken": "...",
            "RefreshToken": "...",
            "Expiry": "2025-01-01T12:00:00.000000000Z"
        }}}}

    If the AccessToken is expired and a RefreshToken is available, it will be refreshed
    automatically via HTTP without any interaction with the user.
    """

    def __init__(self, host: str) -> None:
        self._host = host.rstrip("/")
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Reading the cache
    # ------------------------------------------------------------------

    def _read_entry(self) -> dict:
        host_key = self._host + "/"
        try:
            cache = json.loads(_TOKEN_CACHE.read_text(encoding="utf-8"))
            return cache.get("Hosts", {}).get(host_key, {}).get(_U2M_CLIENT_ID, {})
        except Exception:
            return {}

    def _is_expired(self, entry: dict) -> bool:
        expiry_str = entry.get("Expiry", "")
        if not expiry_str:
            return False
        try:
            expiry = datetime.datetime.strptime(
                expiry_str[:19], "%Y-%m-%dT%H:%M:%S"
            ).replace(tzinfo=datetime.timezone.utc)
            return expiry <= datetime.datetime.now(datetime.timezone.utc)
        except Exception:
            # Malformed Expiry: treat as expired so the token gets refreshed.
            return True

    # ------------------------------------------------------------------
    # Refreshing via refresh_token
    # ------------------------------------------------------------------

    def _do_refresh(self, refresh_token: str) -> str:
        """Exchanges the refresh_token for a new access_token and saves it to the cache."""
        resp = requests.post(
            f"{self._host}/oidc/v1/token",
            data={
                "client_id":     _U2M_CLIENT_ID,
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token,
                "scope":         "all-apis offline_access",
            },
            verify=False,
            timeout=30,
        )
        resp.raise_for_status()
        new_data = resp.json()

        # Save the new access_token and refresh_token to the cache
        from src.tools.auth_flow import _save_token
        _save_token(self._host, new_data)

        logger.debug("Token U2M refreshed via refresh_token for %s", self._host)
        return new_data["access_token"]

    # ------------------------------------------------------------------
    # Public Interface
    # ------------------------------------------------------------------

    def get_headers(self) -> Dict[str, str]:
        """
        Returns {"Authorization": "Bearer <token>"}.

        Raises RuntimeError with instructions if no token is found in the cache.
        """
        with self._lock:
            entry = self._read_entry()

            if not entry or not entry.get("AccessToken"):
                raise RuntimeError(
                    f"Token U2M not found for {self._host}.\n"
                    "Execute the authentication flow (start_auth) first."
                )

            if self._is_expired(entry):
                refresh_token = entry.get("RefreshToken", "")
                if not refresh_token:
                    raise RuntimeError(
                        f"Token U2M expired and no refresh_token available for {self._host}.\n"
                        "Execute the authentication flow (start_auth) again."
                    )
                try:
                    access_token = self._do_refresh(refresh_token)
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to refresh U2M token for {self._host}: {exc}\n"
                        "Execute the authentication flow (start_auth) again."
                    ) from exc
            else:
                access_token = entry["AccessToken"]

            logger.debug("Token U2M obtained from cache for %s", self._host)
            return {"Authorization": f"Bearer {access_token}"}
