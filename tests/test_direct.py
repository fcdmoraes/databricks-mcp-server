"""
Direct tests for the Databricks MCP server.

This module contains tests that call the tool functions directly
(src/tools/clusters.py), without going through the MCP protocol.
"""

import json
import logging
from unittest.mock import patch

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from src.tools import clusters


def test_list_clusters_direct():
    """Test calling the list_clusters tool function directly."""
    mock_response = {
        "clusters": [
            {
                "cluster_id": "1234-567890-abcdef",
                "cluster_name": "Test Cluster",
                "state": "RUNNING",
            }
        ]
    }

    with patch("src.tools.clusters.make_api_request", return_value=mock_response) as mock_req:
        result = json.loads(clusters.list_clusters())

    mock_req.assert_called_once_with("GET", "/api/2.0/clusters/list")
    assert "clusters" in result
    assert len(result["clusters"]) == 1
    logger.info(f"Found {len(result['clusters'])} clusters")
