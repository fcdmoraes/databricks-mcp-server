#!/usr/bin/env python
"""
Databricks MCP Server - Direct Usage Example

This example demonstrates how to directly use the Databricks MCP server's
tool functions without going through the MCP protocol. Since the tools
were migrated to plain functions under src/tools/, they can be imported
and called directly.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools import clusters, jobs, notebooks

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def print_section_header(title: str) -> None:
    """Print a section header with the given title."""
    print(f"\n{title}")
    print("=" * len(title))

def print_clusters(clusters_list: List[Dict[str, Any]]) -> None:
    """Print information about Databricks clusters."""
    print_section_header("Databricks Clusters")

    for i, cluster in enumerate(clusters_list, 1):
        print(f"\nCluster {i}:")
        print(f"  ID: {cluster.get('cluster_id')}")
        print(f"  Name: {cluster.get('cluster_name')}")
        print(f"  State: {cluster.get('state')}")
        print(f"  Spark Version: {cluster.get('spark_version')}")
        print(f"  Node Type: {cluster.get('node_type_id')}")

def print_notebooks(notebooks_list: List[Dict[str, Any]], path: str) -> None:
    """Print information about Databricks notebooks."""
    print_section_header(f"Databricks Notebooks in {path}")

    for notebook in notebooks_list:
        if notebook.get('object_type') == 'NOTEBOOK':
            print(f"\nNotebook: {notebook.get('path')}")
        elif notebook.get('object_type') == 'DIRECTORY':
            print(f"Directory: {notebook.get('path')}")

def print_jobs(jobs_list: List[Dict[str, Any]]) -> None:
    """Print information about Databricks jobs."""
    print_section_header("Databricks Jobs")

    for i, job in enumerate(jobs_list, 1):
        print(f"\nJob {i}:")
        print(f"  ID: {job.get('job_id')}")
        print(f"  Name: {job.get('settings', {}).get('name')}")
        print(f"  Created: {job.get('created_time')}")

def main() -> None:
    """Main function for the direct usage example."""
    print("\nDatabricks MCP Server - Direct Usage Example")
    print("===========================================")

    # Check for Databricks credentials (PAT or OAuth client credentials)
    has_pat = os.environ.get("DATABRICKS_HOST") and os.environ.get("DATABRICKS_TOKEN")
    has_oauth = os.environ.get("DATABRICKS_CLIENT_ID") and os.environ.get("DATABRICKS_CLIENT_SECRET")
    if not has_pat and not has_oauth:
        logger.error(
            "Please set DATABRICKS_HOST plus either DATABRICKS_TOKEN (PAT) or "
            "DATABRICKS_CLIENT_ID/DATABRICKS_CLIENT_SECRET (OAuth) environment variables"
        )
        sys.exit(1)

    try:
        # List clusters
        logger.info("Listing Databricks clusters...")
        clusters_data = json.loads(clusters.list_clusters())
        if 'error' in clusters_data:
            logger.error(f"Error listing clusters: {clusters_data['error']}")
        else:
            print_clusters(clusters_data.get('clusters', []))

        # List notebooks in root path
        logger.info("Listing Databricks notebooks...")
        notebooks_data = json.loads(notebooks.list_notebooks(path="/"))
        if 'error' in notebooks_data:
            logger.error(f"Error listing notebooks: {notebooks_data['error']}")
        else:
            print_notebooks(notebooks_data.get('objects', []), "/")

        # List jobs
        logger.info("Listing Databricks jobs...")
        jobs_data = json.loads(jobs.list_jobs())
        if 'error' in jobs_data:
            logger.error(f"Error listing jobs: {jobs_data['error']}")
        else:
            print_jobs(jobs_data.get('jobs', []))

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
