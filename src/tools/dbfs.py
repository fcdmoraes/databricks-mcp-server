"""DBFS (Databricks File System) access tools."""

import json

from src.core.utils import make_api_request


def list_files(dbfs_path: str) -> str:
    """List files and directories at a DBFS path."""
    return json.dumps(make_api_request("GET", "/api/2.0/dbfs/list", params={"path": dbfs_path}))
