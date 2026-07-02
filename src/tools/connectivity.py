"""Connectivity and discovery tools for the Databricks server."""

import json

from src.core.config import get_genie_spaces
from src.core.utils import make_api_request


def ping_endpoint(path: str, method: str = "GET") -> str:
    """
    Test connectivity to a Databricks API endpoint.

    Use /api/2.0/genie/spaces to check Genie access before querying it.
    """
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
            "message": "Nenhum Genie Space configurado. "
                       "Adicione GENIE_SPACE_<N>_ID, GENIE_SPACE_<N>_NAME "
                       "e opcionalmente GENIE_SPACE_<N>_DESCRIPTION ao .env."
        })
    return json.dumps({"spaces": spaces})
