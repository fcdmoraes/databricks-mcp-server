"""Databricks cluster management tools."""

import json
import logging
from typing import Any, Dict

from src.core.utils import make_api_request

logger = logging.getLogger(__name__)


def list_clusters() -> str:
    """List all Databricks clusters."""
    return json.dumps(make_api_request("GET", "/api/2.0/clusters/list"))


def get_cluster(cluster_id: str) -> str:
    """Return information about a specific cluster."""
    return json.dumps(make_api_request("GET", "/api/2.0/clusters/get", params={"cluster_id": cluster_id}))


def create_cluster(
    cluster_name: str,
    spark_version: str,
    node_type_id: str,
    num_workers: int = 1,
    autotermination_minutes: int = 30,
) -> str:
    """Create a new Databricks cluster."""
    return json.dumps(make_api_request(
        "POST",
        "/api/2.0/clusters/create",
        data={
            "cluster_name": cluster_name,
            "spark_version": spark_version,
            "node_type_id": node_type_id,
            "num_workers": num_workers,
            "autotermination_minutes": autotermination_minutes,
        },
    ))


def start_cluster(cluster_id: str) -> str:
    """Start a terminated Databricks cluster."""
    return json.dumps(make_api_request("POST", "/api/2.0/clusters/start", data={"cluster_id": cluster_id}))


def terminate_cluster(cluster_id: str) -> str:
    """Terminate a Databricks cluster."""
    return json.dumps(make_api_request("POST", "/api/2.0/clusters/delete", data={"cluster_id": cluster_id}))
