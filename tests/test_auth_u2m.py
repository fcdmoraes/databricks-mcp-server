"""
Unit tests for the OAuth U2M functionality:

  - src/tools/auth_flow.py    — PKCE helpers, token cache, check_auth
  - src/core/auth.py          — U2MTokenProvider (cache read / expiry / refresh)
  - src/tools/connectivity.py — ping_endpoint needs_auth path (U2M, no token)

No calls hit Databricks: every network call (requests.post) is mocked, and the
token cache is redirected to a temporary file.
"""

import base64
import datetime
import hashlib
import json
import string
from unittest.mock import MagicMock, patch

import pytest

from src.core import auth as core_auth
from src.tools import auth_flow

HOST = "https://adb-1234567890123456.7.azuredatabricks.net"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _iso(dt: datetime.datetime) -> str:
    """Format a datetime the way _save_token stores the Expiry field."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


def _write_cache(path, *, access="tok", refresh="ref", expiry=None, client=None):
    """Write a token-cache.json entry directly, bypassing _save_token."""
    client = client or auth_flow.CLIENT_ID
    entry = {"TokenType": "Bearer", "AccessToken": access, "RefreshToken": refresh}
    if expiry is not None:
        entry["Expiry"] = expiry
    path.write_text(
        json.dumps({"Hosts": {HOST + "/": {client: entry}}}), encoding="utf-8"
    )


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    """
    Redirect the token cache to a temp file in BOTH modules.

    auth.py imports the constant by value (``from ... import TOKEN_CACHE as
    _TOKEN_CACHE``), so patching only auth_flow would leave auth.py writing to
    the real ~/.databricks path. Both names must be patched.
    """
    path = tmp_path / "token-cache.json"
    monkeypatch.setattr(auth_flow, "TOKEN_CACHE", path)
    monkeypatch.setattr(core_auth, "_TOKEN_CACHE", path)
    return path


@pytest.fixture(autouse=True)
def clear_flow_state():
    """The auth_flow module keeps flow state in a module global; reset it."""
    auth_flow._state.clear()
    yield
    auth_flow._state.clear()


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def test_pkce_verifier_length_and_charset():
    verifier, _ = auth_flow._pkce_pair()
    assert 43 <= len(verifier) <= 128
    allowed = set(string.ascii_letters + string.digits + "-._~")
    assert set(verifier) <= allowed


def test_pkce_challenge_is_sha256_of_verifier_without_padding():
    verifier, challenge = auth_flow._pkce_pair()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    assert challenge == expected
    assert "=" not in challenge


def test_pkce_pairs_are_random():
    v1, c1 = auth_flow._pkce_pair()
    v2, c2 = auth_flow._pkce_pair()
    assert v1 != v2 and c1 != c2


# ---------------------------------------------------------------------------
# Token cache: _save_token / _token_exists
# ---------------------------------------------------------------------------

def test_save_then_token_exists_roundtrip(cache_file):
    auth_flow._save_token(
        HOST, {"access_token": "abc", "refresh_token": "ref", "expires_in": 3600}
    )
    assert cache_file.exists()
    assert auth_flow._token_exists(HOST) is True


def test_token_exists_false_when_no_cache(cache_file):
    assert auth_flow._token_exists(HOST) is False


def test_token_exists_normalizes_trailing_slash(cache_file):
    auth_flow._save_token(HOST + "/", {"access_token": "abc", "expires_in": 3600})
    assert auth_flow._token_exists(HOST) is True


def test_token_exists_expired_without_refresh_is_false(cache_file):
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    _write_cache(cache_file, access="old", refresh="", expiry=_iso(past))
    assert auth_flow._token_exists(HOST) is False


def test_token_exists_expired_with_refresh_is_true(cache_file):
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    _write_cache(cache_file, access="old", refresh="ref", expiry=_iso(past))
    # Expired but a refresh_token is available -> still usable (will be refreshed).
    assert auth_flow._token_exists(HOST) is True


def test_save_token_stores_expiry_and_refresh(cache_file):
    auth_flow._save_token(
        HOST, {"access_token": "abc", "refresh_token": "r", "expires_in": 3600}
    )
    entry = json.loads(cache_file.read_text())["Hosts"][HOST + "/"][auth_flow.CLIENT_ID]
    assert entry["AccessToken"] == "abc"
    assert entry["RefreshToken"] == "r"
    assert entry["Expiry"].endswith("Z")


# ---------------------------------------------------------------------------
# U2MTokenProvider._is_expired
# ---------------------------------------------------------------------------

def test_is_expired_false_for_future():
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    assert core_auth.U2MTokenProvider(HOST)._is_expired({"Expiry": _iso(future)}) is False


def test_is_expired_true_for_past():
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    assert core_auth.U2MTokenProvider(HOST)._is_expired({"Expiry": _iso(past)}) is True


def test_is_expired_false_when_missing():
    assert core_auth.U2MTokenProvider(HOST)._is_expired({}) is False


def test_is_expired_true_when_malformed():
    assert core_auth.U2MTokenProvider(HOST)._is_expired({"Expiry": "not-a-date"}) is True


# ---------------------------------------------------------------------------
# U2MTokenProvider.get_headers
# ---------------------------------------------------------------------------

def test_get_headers_raises_when_no_token(cache_file):
    with pytest.raises(RuntimeError, match="not found"):
        core_auth.U2MTokenProvider(HOST).get_headers()


def test_get_headers_returns_bearer_for_valid_token(cache_file):
    auth_flow._save_token(
        HOST, {"access_token": "tok123", "refresh_token": "r", "expires_in": 3600}
    )
    assert core_auth.U2MTokenProvider(HOST).get_headers() == {
        "Authorization": "Bearer tok123"
    }


def test_get_headers_raises_when_expired_and_no_refresh(cache_file):
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    _write_cache(cache_file, access="old", refresh="", expiry=_iso(past),
                 client=core_auth._U2M_CLIENT_ID)
    with pytest.raises(RuntimeError, match="expired"):
        core_auth.U2MTokenProvider(HOST).get_headers()


def test_get_headers_refreshes_when_expired_with_refresh(cache_file):
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    _write_cache(cache_file, access="old", refresh="ref", expiry=_iso(past),
                 client=core_auth._U2M_CLIENT_ID)

    fake_resp = MagicMock()
    fake_resp.json.return_value = {
        "access_token": "new-tok", "refresh_token": "new-ref", "expires_in": 3600
    }
    fake_resp.raise_for_status.return_value = None

    with patch("src.core.auth.requests.post", return_value=fake_resp) as mock_post:
        headers = core_auth.U2MTokenProvider(HOST).get_headers()

    assert headers == {"Authorization": "Bearer new-tok"}
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["data"]["grant_type"] == "refresh_token"
    assert mock_post.call_args.kwargs["data"]["refresh_token"] == "ref"

    # The refreshed token must be persisted back to the cache.
    saved = json.loads(cache_file.read_text())["Hosts"][HOST + "/"][core_auth._U2M_CLIENT_ID]
    assert saved["AccessToken"] == "new-tok"
    assert saved["RefreshToken"] == "new-ref"


def test_get_headers_raises_when_refresh_call_fails(cache_file):
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    _write_cache(cache_file, access="old", refresh="ref", expiry=_iso(past),
                 client=core_auth._U2M_CLIENT_ID)

    with patch("src.core.auth.requests.post", side_effect=Exception("network down")):
        with pytest.raises(RuntimeError, match="Failed to refresh"):
            core_auth.U2MTokenProvider(HOST).get_headers()


# ---------------------------------------------------------------------------
# start_auth (early-return branch only — the HTTP callback server is not tested)
# ---------------------------------------------------------------------------

def test_start_auth_returns_already_authenticated_when_token_valid(cache_file):
    auth_flow._save_token(
        HOST, {"access_token": "tok", "refresh_token": "r", "expires_in": 3600}
    )
    result = json.loads(auth_flow.start_auth(HOST))
    assert result["status"] == "already_authenticated"


# ---------------------------------------------------------------------------
# check_auth
# ---------------------------------------------------------------------------

def test_check_auth_waiting_when_no_callback():
    result = json.loads(auth_flow.check_auth())
    assert result["status"] == "waiting"


def test_check_auth_error_on_state_mismatch():
    auth_flow._state.update(
        {"callback_received": True, "state": "expected", "state_received": "tampered"}
    )
    result = json.loads(auth_flow.check_auth())
    assert result["status"] == "error"
    assert "state" in result["message"].lower()


def test_check_auth_error_when_code_missing():
    auth_flow._state.update(
        {
            "callback_received": True,
            "state": "s",
            "state_received": "s",
            "code": None,
            "host": HOST,
            "verifier": "v",
        }
    )
    result = json.loads(auth_flow.check_auth())
    assert result["status"] == "error"


def test_check_auth_success_exchanges_code_and_saves_token(cache_file):
    auth_flow._state.update(
        {
            "callback_received": True,
            "state": "s",
            "state_received": "s",
            "code": "auth-code",
            "host": HOST,
            "verifier": "verifier-123",
        }
    )
    fake_resp = MagicMock()
    fake_resp.json.return_value = {
        "access_token": "final-tok", "refresh_token": "rf", "expires_in": 3600
    }
    fake_resp.raise_for_status.return_value = None

    with patch("src.tools.auth_flow.requests.post", return_value=fake_resp) as mock_post:
        result = json.loads(auth_flow.check_auth())

    assert result["status"] == "ok"
    assert mock_post.call_args.kwargs["data"]["grant_type"] == "authorization_code"
    assert mock_post.call_args.kwargs["data"]["code"] == "auth-code"
    assert auth_flow._token_exists(HOST) is True
    # State is cleared after a successful exchange.
    assert auth_flow._state == {}


# ---------------------------------------------------------------------------
# connectivity.ping_endpoint — U2M needs_auth path
#
# Imports connectivity lazily because it pulls in src.core.config (pydantic).
# ---------------------------------------------------------------------------

def test_ping_endpoint_returns_needs_auth_in_u2m_without_token(cache_file, monkeypatch):
    from src.tools import connectivity

    monkeypatch.setattr(type(connectivity.settings), "auth_type",
                        property(lambda self: "u2m"))
    monkeypatch.setattr(connectivity.settings, "DATABRICKS_HOST", HOST)

    result = json.loads(connectivity.ping_endpoint("/api/2.0/clusters/list"))
    assert result["status"] == "needs_auth"
    assert result["host"] == HOST.rstrip("/")
