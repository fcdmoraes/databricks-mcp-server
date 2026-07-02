"""
Unit tests for the cluster tools (src/tools/clusters.py).
"""

import json
from unittest.mock import patch

import pytest

from src.tools import clusters


@pytest.fixture
def mock_cluster():
    return {
        "cluster_id": "1234-567890-abcdef",
        "cluster_name": "Test Cluster",
        "spark_version": "10.4.x-scala2.12",
        "node_type_id": "Standard_D3_v2",
        "num_workers": 2,
        "state": "RUNNING",
    }


def test_list_clusters_calls_correct_endpoint():
    with patch("src.tools.clusters.make_api_request") as mock_req:
        mock_req.return_value = {"clusters": []}
        clusters.list_clusters()
        mock_req.assert_called_once_with("GET", "/api/2.0/clusters/list")


def test_list_clusters_returns_json(mock_cluster):
    with patch("src.tools.clusters.make_api_request") as mock_req:
        mock_req.return_value = {"clusters": [mock_cluster]}
        result = json.loads(clusters.list_clusters())
        assert len(result["clusters"]) == 1
        assert result["clusters"][0]["cluster_id"] == "1234-567890-abcdef"


def test_get_cluster_calls_correct_endpoint():
    with patch("src.tools.clusters.make_api_request") as mock_req:
        mock_req.return_value = {}
        clusters.get_cluster("1234-567890-abcdef")
        mock_req.assert_called_once_with(
            "GET", "/api/2.0/clusters/get", params={"cluster_id": "1234-567890-abcdef"}
        )


def test_get_cluster_returns_json(mock_cluster):
    with patch("src.tools.clusters.make_api_request") as mock_req:
        mock_req.return_value = mock_cluster
        result = json.loads(clusters.get_cluster("1234-567890-abcdef"))
        assert result["state"] == "RUNNING"


def test_create_cluster_sends_correct_data():
    with patch("src.tools.clusters.make_api_request") as mock_req:
        mock_req.return_value = {"cluster_id": "new-id"}
        clusters.create_cluster(
            cluster_name="My Cluster",
            spark_version="13.3.x-scala2.12",
            node_type_id="Standard_D3_v2",
            num_workers=4,
        )
        _, endpoint = mock_req.call_args[0]
        assert endpoint == "/api/2.0/clusters/create"
        data = mock_req.call_args[1]["data"]
        assert data["cluster_name"] == "My Cluster"
        assert data["num_workers"] == 4


def test_start_cluster_calls_correct_endpoint():
    with patch("src.tools.clusters.make_api_request") as mock_req:
        mock_req.return_value = {}
        clusters.start_cluster("1234-567890-abcdef")
        mock_req.assert_called_once_with(
            "POST", "/api/2.0/clusters/start", data={"cluster_id": "1234-567890-abcdef"}
        )


def test_terminate_cluster_calls_correct_endpoint():
    with patch("src.tools.clusters.make_api_request") as mock_req:
        mock_req.return_value = {}
        clusters.terminate_cluster("1234-567890-abcdef")
        mock_req.assert_called_once_with(
            "POST", "/api/2.0/clusters/delete", data={"cluster_id": "1234-567890-abcdef"}
        )
