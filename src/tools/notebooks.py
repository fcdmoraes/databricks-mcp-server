"""Databricks notebook management tools."""

import base64
import json
import logging

from src.core.utils import make_api_request

logger = logging.getLogger(__name__)


def list_notebooks(path: str) -> str:
    """List notebooks in a Databricks workspace directory."""
    return json.dumps(make_api_request("GET", "/api/2.0/workspace/list", params={"path": path}))


def export_notebook(path: str, format: str = "SOURCE") -> str:
    """
    Export a notebook from the workspace.

    Args:
        path: Path to the notebook.
        format: Export format (SOURCE, HTML, JUPYTER, DBC).
    """
    result = make_api_request("GET", "/api/2.0/workspace/export", params={"path": path, "format": format})

    # Decode base64 content for readable formats
    if "content" in result and format in ("SOURCE", "JUPYTER"):
        try:
            result["decoded_content"] = base64.b64decode(result["content"]).decode("utf-8")
        except Exception as e:
            logger.warning("Failed to decode notebook content: %s", e)

    # Truncate raw content if too long
    content = result.get("content", "")
    if len(content) > 1000:
        result["content"] = f"{content[:1000]}... [truncated, total: {len(content)} chars]"

    return json.dumps(result)
