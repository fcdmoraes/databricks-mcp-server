"""
Integration tests for the Databricks MCP server tools.

Tests that run without credentials (always run):
  - test_ping_endpoint
  - test_list_genie_spaces_no_config

Integration tests (skipped if DATABRICKS_HOST is a placeholder or empty):
  - test_list_clusters, test_list_jobs, test_list_notebooks, test_list_files
  - test_list_genie_spaces_with_config, test_genie_ask
"""

import json
import logging
import os

import pytest

# The tools are plain Python functions in the fastmcp pattern — imported directly
# from the modules under src/tools/, the same place the server registers them from.
from src.tools.clusters import list_clusters
from src.tools.connectivity import list_genie_spaces, ping_endpoint
from src.tools.dbfs import list_files
from src.tools.genie import genie_ask
from src.tools.jobs import list_jobs
from src.tools.notebooks import list_notebooks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_host = os.environ.get("DATABRICKS_HOST", "")
needs_databricks = pytest.mark.skipif(
    not _host or "example" in _host,
    reason="Requires a real DATABRICKS_HOST in .env (current value is a placeholder or empty)",
)


# ---------------------------------------------------------------------------
# No credentials required — always run
# ---------------------------------------------------------------------------

def test_ping_endpoint_returns_status():
    """ping_endpoint returns a dict with a 'status' field even without valid credentials."""
    result = json.loads(ping_endpoint(path="/api/2.0/genie/spaces"))
    assert "status" in result, f"Expected 'status', got: {result}"
    logger.info(f"ping_endpoint status: {result['status']}")


def test_list_genie_spaces_no_config():
    """list_genie_spaces returns a valid response when no GENIE_SPACE_* is configured."""
    result = json.loads(list_genie_spaces())
    assert "spaces" in result or "message" in result, f"Unexpected response: {result}"
    logger.info(f"list_genie_spaces: {result}")


# ---------------------------------------------------------------------------
# Integration — require a real Databricks workspace
# ---------------------------------------------------------------------------

@needs_databricks
def test_list_clusters():
    result = json.loads(list_clusters())
    assert "clusters" in result, f"Expected 'clusters', got: {result}"
    logger.info(f"Found {len(result['clusters'])} clusters")


@needs_databricks
def test_list_jobs():
    result = json.loads(list_jobs())
    assert "jobs" in result, f"Expected 'jobs', got: {result}"
    logger.info(f"Found {len(result['jobs'])} jobs")


@needs_databricks
def test_list_notebooks():
    result = json.loads(list_notebooks(path="/"))
    assert "objects" in result, f"Expected 'objects', got: {result}"
    logger.info(f"Found {len(result['objects'])} objects")


@needs_databricks
def test_list_files():
    result = json.loads(list_files(dbfs_path="/"))
    assert "files" in result, f"Expected 'files', got: {result}"
    logger.info(f"Found {len(result['files'])} files")


@needs_databricks
def test_list_genie_spaces_with_config():
    space_id = os.environ.get("GENIE_SPACE_1_ID")
    if not space_id:
        pytest.skip("GENIE_SPACE_1_ID not configured")
    result = json.loads(list_genie_spaces())
    assert "spaces" in result, f"Expected 'spaces', got: {result}"
    logger.info(f"Found {len(result['spaces'])} spaces")


@needs_databricks
def test_genie_ask():
    space_id = os.environ.get("GENIE_SPACE_1_ID")
    if not space_id:
        pytest.skip("GENIE_SPACE_1_ID not configured")
    result = json.loads(genie_ask(space_id=space_id, question="What tables are available?"))
    assert isinstance(result, dict), f"Expected dict, got: {type(result)}"
    logger.info(f"genie_ask result keys: {list(result.keys())}")
