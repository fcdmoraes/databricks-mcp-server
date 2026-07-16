"""
Databricks MCP Server

This module implements a standalone MCP server that provides tools for interacting
with Databricks APIs. It follows the Model Context Protocol standard, communicating
via stdio and directly connecting to Databricks when tools are invoked.
"""


import logging
import sys

from fastmcp import FastMCP

from src.tools import auth_flow, clusters, connectivity, dbfs, genie, jobs, notebooks, sql
from src.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.WARNING),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)

mcp = FastMCP("databricks-mcp", instructions=settings.specialist_description)

# Interactive authentication flow (OAuth U2M PKCE)
mcp.tool()(auth_flow.start_auth)
mcp.tool()(auth_flow.check_auth)

# Connectivity
mcp.tool()(connectivity.ping_endpoint)
mcp.tool()(connectivity.list_genie_spaces)

# Genie
mcp.tool()(genie.genie_ask)
mcp.tool()(genie.genie_start_conversation)
mcp.tool()(genie.genie_send_message)
mcp.tool()(genie.genie_get_message)

# SQL
mcp.tool()(sql.execute_sql)

# Clusters
mcp.tool()(clusters.list_clusters)
mcp.tool()(clusters.get_cluster)
mcp.tool()(clusters.create_cluster)
mcp.tool()(clusters.start_cluster)
mcp.tool()(clusters.terminate_cluster)

# Jobs
mcp.tool()(jobs.list_jobs)
mcp.tool()(jobs.run_job)

# Notebooks
mcp.tool()(notebooks.list_notebooks)
mcp.tool()(notebooks.export_notebook)

# DBFS
mcp.tool()(dbfs.list_files)

def main():
   mcp.run(transport=settings.mcp_transport)

if __name__ == "__main__":
    main()