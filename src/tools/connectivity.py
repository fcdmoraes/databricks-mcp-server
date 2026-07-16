"""Connectivity and discovery tools for the Databricks server."""

import json

from src.core.config import get_genie_spaces, settings
from src.core.utils import make_api_request


def ping_endpoint(path: str, method: str = "GET") -> str:
    """
    Test connectivity to a Databricks API endpoint.

    Use /api/2.0/genie/spaces to check Genie access before querying it.
    """
    # U2M flow: if no token exists, return a needs_auth message prompting the user
    # to start the interactive authentication flow instead of a generic error.
    if settings.auth_type == "u2m":
        from src.tools.auth_flow import _token_exists
        if not _token_exists(settings.DATABRICKS_HOST):
            return json.dumps({
                "status": "needs_auth",
                "message": (
                    "Authentication required. Call the start_auth tool with the host "
                    f"'{settings.DATABRICKS_HOST.rstrip('/')}' to initiate the login process."
                ),
                "host": settings.DATABRICKS_HOST.rstrip("/"),
            })

    try:
        result = make_api_request(method=method, endpoint=path)
        return json.dumps({"status": "ok", "response": result})
    except Exception as e:
        return json.dumps({"status": "error", "detail": str(e)})


def list_genie_spaces() -> str:
    """List the Genie Spaces configured on this server (via GENIE_SPACE_<N>_* variables)."""
    spaces = get_genie_spaces()
    if not spaces:
        return json.dumps({
            "message": "No Genie Spaces configured. "
                       "Add GENIE_SPACE_<N>_ID, GENIE_SPACE_<N>_NAME "
                       "and optionally GENIE_SPACE_<N>_DESCRIPTION to the .env file."
        })
    return json.dumps({"spaces": spaces})
