"""
OAuth U2M PKCE Flow for Interactive Authentication via Claude Cowork

Exposes two tools:
  - start_auth  — initiates the flow and returns the login URL for the user
  - check_auth  — completes the token exchange after the user authenticates in the browser

Complete flow:
  1. Claude calls start_auth(host)
  2. Claude displays the auth_url for the user to click
  3. User opens the link, authenticates (corporate SSO via Azure AD or similar)
  4. Browser redirects to http://localhost:8020 — local server captures the code
  5. User confirms to Claude that they have logged in
  6. Claude calls check_auth()
  7. Server exchanges the code for a token and saves it in ~/.databricks/token-cache.json
  8. Query flow proceeds normally
"""

import base64
import datetime
import hashlib
import http.server
import json
import logging
import secrets
import string
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Dict

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────

CLIENT_ID      = "databricks-cli"   # Native client ID used by Databricks CLI and SDK
REDIRECT_PORT  = 8020
REDIRECT_URI   = f"http://localhost:{REDIRECT_PORT}"
TIMEOUT_SECS   = 300                # 5 minutes to complete the flow before timeout
TOKEN_CACHE    = Path.home() / ".databricks" / "token-cache.json"

# ── Global state for the ongoing flow ───────────────────────────────────────

_state: Dict = {}
_lock  = threading.Lock()


# ── PKCE helpers ─────────────────────────────────────────────────────────────

def _pkce_pair():
    allowed  = string.ascii_letters + string.digits + "-._~"
    verifier = "".join(secrets.choice(allowed) for _ in range(64))
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    return verifier, challenge


# ── Token cache (compatible with databricks CLI / SDK) ─────────────────

def _save_token(host: str, data: dict) -> None:
    host_key = host.rstrip("/") + "/"
    TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)

    cache: dict = {}
    if TOKEN_CACHE.exists():
        try:
            cache = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    cache.setdefault("Hosts", {}).setdefault(host_key, {})[CLIENT_ID] = {
        "TokenType":    "Bearer",
        "AccessToken":  data["access_token"],
        "RefreshToken": data.get("refresh_token", ""),
        "Expiry": (
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(seconds=data.get("expires_in", 3600))
        ).strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
    }

    TOKEN_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    logger.debug("Token saved to %s for host %s", TOKEN_CACHE, host_key)


def _token_exists(host: str) -> bool:
    """Returns True if there is a non-expired token in the cache for the host."""
    host_key = host.rstrip("/") + "/"
    if not TOKEN_CACHE.exists():
        return False
    try:
        cache = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
        entry = cache.get("Hosts", {}).get(host_key, {}).get(CLIENT_ID, {})
        if not entry.get("AccessToken"):
            return False
        expiry_str = entry.get("Expiry", "")
        if expiry_str:
            expiry = datetime.datetime.strptime(
                expiry_str[:19], "%Y-%m-%dT%H:%M:%S"
            ).replace(tzinfo=datetime.timezone.utc)
            if expiry <= datetime.datetime.now(datetime.timezone.utc):
                # Token expired — but there may be a refresh_token; the SDK will renew it
                return bool(entry.get("RefreshToken"))
        return True
    except Exception:
        return False

# ── HTTP server to capture OAuth callback ───────────────────────────────────

class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        with _lock:
            _state["code"]              = params.get("code",  [None])[0]
            _state["state_received"]    = params.get("state", [None])[0]
            _state["callback_received"] = True

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            b"<h2>&#10003; Success!</h2>"
            b"<p>Return to Claude Cowork and confirm you have logged in.</p>"
            b"</body></html>"
        )

    def log_message(self, *args):  # Override to suppress default logging
        pass


def _serve_until_callback(httpd):
    httpd.timeout = 1
    deadline = time.time() + TIMEOUT_SECS
    while time.time() < deadline:
        with _lock:
            if _state.get("callback_received"):
                break
        httpd.handle_request()
    httpd.server_close()


# ── Public tools ────────────────────────────────────────────────────────────

def start_auth(host: str) -> str:
    """
    Starts the OAuth U2M PKCE flow for the given Databricks workspace.

    Returns a URL that the user should open in their browser to authenticate.
    After logging in, call check_auth() to complete the process.
    """
    host = host.rstrip("/")

    # If there's already a valid token, no need to authenticate
    if _token_exists(host):
        return json.dumps({
            "status": "already_authenticated",
            "message": "Valid token already exists for this host. No action needed.",
        })

    verifier, challenge = _pkce_pair()
    state_val = secrets.token_urlsafe(16)

    # Start a callback HTTP server to listen for the redirect from Databricks
    try:
        httpd = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    except OSError:
        return json.dumps({
            "status": "error",
            "message": f"Port {REDIRECT_PORT} is already in use. Please wait a few seconds and try again.",
        })

    with _lock:
        _state.clear()
        _state.update({
            "host":              host,
            "verifier":          verifier,
            "state":             state_val,
            "callback_received": False,
        })

    threading.Thread(target=_serve_until_callback, args=(httpd,), daemon=True).start()

    auth_url = (
        f"{host}/oidc/v1/authorize?"
        + urllib.parse.urlencode({
            "client_id":             CLIENT_ID,
            "redirect_uri":          REDIRECT_URI,
            "response_type":         "code",
            "state":                 state_val,
            "code_challenge":        challenge,
            "code_challenge_method": "S256",
            "scope":                 "all-apis offline_access",
        })
    )

    return json.dumps({
        "status":   "pending",
        "message":  "Open the link below in your browser to authenticate with Databricks. "
                    "After logging in, confirm here to proceed.",
        "auth_url": auth_url,
    })


def check_auth() -> str:
    """
    Verifies if the OAuth callback has been received and completes the token exchange.

    Call after the user confirms they have logged in the browser.
    """
    with _lock:
        if not _state.get("callback_received"):
            return json.dumps({
                "status":  "waiting",
                "message": "Login still not detected. Open the link sent previously, "
                           "log in and confirm here again.",
            })

        if _state.get("state_received") != _state.get("state"):
            _state.clear()
            return json.dumps({
                "status":  "error",
                "message": "Validation of state failed (possible CSRF). Call start_auth again.",
            })

        code     = _state.get("code")
        host     = _state.get("host")
        verifier = _state.get("verifier")

    if not code:
        return json.dumps({"status": "error", "message": "Authorization code not received."})

    # Swap the authorization_code for an access_token + refresh_token
    try:
        resp = requests.post(
            f"{host}/oidc/v1/token",
            data={
                "client_id":     CLIENT_ID,
                "grant_type":    "authorization_code",
                "scope":         "all-apis offline_access",
                "redirect_uri":  REDIRECT_URI,
                "code_verifier": verifier,
                "code":          code,
            },
            verify=False,
            timeout=30,
        )
        resp.raise_for_status()
        token_data = resp.json()
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"Error obtaining token: {exc}"})

    _save_token(host, token_data)

    with _lock:
        _state.clear()

    return json.dumps({
        "status":  "ok",
        "message": "Successfully authenticated! You can now proceed with your query.",
    })
