"""Databricks SQL execution tools."""

import json

from src.core.utils import make_api_request


def execute_sql(
    statement: str,
    warehouse_id: str,
    catalog: str = "",
    schema: str = "",
) -> str:
    """
    Execute a SQL statement on a Databricks SQL Warehouse.

    Args:
        statement: SQL statement to execute.
        warehouse_id: SQL Warehouse ID.
        catalog: Unity Catalog (optional).
        schema: Schema (optional).
    """
    data: dict = {
        "statement": statement,
        "warehouse_id": warehouse_id,
        "wait_timeout": "30s",
        "row_limit": 10000,
        "byte_limit": 26214400,
    }
    if catalog:
        data["catalog"] = catalog
    if schema:
        data["schema"] = schema

    return json.dumps(make_api_request("POST", "/api/2.0/sql/statements", data=data))
