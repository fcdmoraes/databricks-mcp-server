"""
Databricks MCP Server

This module implements a standalone MCP server that provides tools for interacting
with Databricks APIs. It follows the Model Context Protocol standard, communicating
via stdio and directly connecting to Databricks when tools are invoked.
"""

import asyncio
import json
import logging
import sys
import os
from typing import Any, Dict, List, Optional, Union, cast

from mcp.server import FastMCP
from mcp.types import TextContent
from mcp.server.stdio import stdio_server

from src.api import clusters, dbfs, jobs, notebooks, sql
from src.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)


class DatabricksMCPServer(FastMCP):
    """An MCP server for Databricks APIs."""

    def __init__(self):
        """Initialize the Databricks MCP server."""
        super().__init__(name="databricks-mcp", 
                         version="1.0.0", 
                         instructions="Use this server to manage Databricks resources")
        logger.info("Initializing Databricks MCP server")
        logger.info(f"Databricks host: {settings.DATABRICKS_HOST}")
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all Databricks MCP tools."""
        
        # Cluster management tools
        @self.tool(
            name="list_clusters",
            description="List all Databricks clusters",
        )
        async def list_clusters(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Listing clusters with params: {params}")
            try:
                result = await clusters.list_clusters()
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error listing clusters: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        @self.tool(
            name="create_cluster",
            description="Create a new Databricks cluster with parameters: cluster_name (required), spark_version (required), node_type_id (required), num_workers, autotermination_minutes",
        )
        async def create_cluster(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Creating cluster with params: {params}")
            try:
                result = await clusters.create_cluster(params)
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error creating cluster: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        @self.tool(
            name="terminate_cluster",
            description="Terminate a Databricks cluster with parameter: cluster_id (required)",
        )
        async def terminate_cluster(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Terminating cluster with params: {params}")
            try:
                result = await clusters.terminate_cluster(params.get("cluster_id"))
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error terminating cluster: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        @self.tool(
            name="get_cluster",
            description="Get information about a specific Databricks cluster with parameter: cluster_id (required)",
        )
        async def get_cluster(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Getting cluster info with params: {params}")
            try:
                result = await clusters.get_cluster(params.get("cluster_id"))
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error getting cluster info: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        @self.tool(
            name="start_cluster",
            description="Start a terminated Databricks cluster with parameter: cluster_id (required)",
        )
        async def start_cluster(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Starting cluster with params: {params}")
            try:
                result = await clusters.start_cluster(params.get("cluster_id"))
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error starting cluster: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        # Job management tools
        @self.tool(
            name="list_jobs",
            description="List all Databricks jobs",
        )
        async def list_jobs(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Listing jobs with params: {params}")
            try:
                result = await jobs.list_jobs()
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error listing jobs: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        @self.tool(
            name="run_job",
            description="Run a Databricks job with parameters: job_id (required), notebook_params (optional)",
        )
        async def run_job(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Running job with params: {params}")
            try:
                notebook_params = params.get("notebook_params", {})
                result = await jobs.run_job(params.get("job_id"), notebook_params)
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error running job: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        # Notebook management tools
        @self.tool(
            name="list_notebooks",
            description="List notebooks in a workspace directory with parameter: path (required)",
        )
        async def list_notebooks(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Listing notebooks with params: {params}")
            try:
                result = await notebooks.list_notebooks(params.get("path"))
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error listing notebooks: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        @self.tool(
            name="export_notebook",
            description="Export a notebook from the workspace with parameters: path (required), format (optional, one of: SOURCE, HTML, JUPYTER, DBC)",
        )
        async def export_notebook(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Exporting notebook with params: {params}")
            try:
                format_type = params.get("format", "SOURCE")
                result = await notebooks.export_notebook(params.get("path"), format_type)
                
                # For notebooks, we might want to trim the response for readability
                content = result.get("content", "")
                if len(content) > 1000:
                    summary = f"{content[:1000]}... [content truncated, total length: {len(content)} characters]"
                    result["content"] = summary
                
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error exporting notebook: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        # DBFS tools
        @self.tool(
            name="list_files",
            description="List files and directories in a DBFS path with parameter: dbfs_path (required)",
        )
        async def list_files(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Listing files with params: {params}")
            try:
                result = await dbfs.list_files(params.get("dbfs_path"))
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error listing files: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
        
        # SQL tools
        @self.tool(
            name="execute_sql",
            description="Execute a SQL statement with parameters: statement (required), warehouse_id (required), catalog (optional), schema (optional)",
        )
        async def execute_sql(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Executing SQL with params: {params}")
            try:
                statement = params.get("statement")
                warehouse_id = params.get("warehouse_id")
                catalog = params.get("catalog")
                schema = params.get("schema")
                
                result = await sql.execute_sql(statement, warehouse_id, catalog, schema)
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error executing SQL: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]
            
        # Utility tools
        @self.tool(
            name="ping_endpoint",
            description="Test connectivity to a Databricks API endpoint. Parameters: path (required, e.g. '/api/2.0/mcp/sql'), method (optional, default 'GET').",
        )
        async def ping_endpoint(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Pinging endpoint: {params}")
            try:
                result = make_api_request(
                    method=params.get("method", "GET"),
                    endpoint=params.get("path"),
                )
                return [{"text": json.dumps({"status": "ok", "response": result})}]
            except Exception as e:
                return [{"text": json.dumps({"status": "error", "detail": str(e)})}]

        # Genie Space tools
        @self.tool(
            name="genie_ask",
            description="Ask a natural language question to a Databricks Genie Space and wait for the response. Parameters: space_id (required), question (required), poll_timeout (optional, seconds, default 60)",
        )
        async def genie_ask(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Genie ask with params: {params}")
            try:
                result = genie.ask_genie(
                    space_id=params.get("space_id"),
                    question=params.get("question"),
                    poll_timeout=params.get("poll_timeout", 60),
                )
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error calling Genie: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]

        @self.tool(
            name="genie_start_conversation",
            description="Start a new conversation in a Databricks Genie Space. Parameters: space_id (required), question (required). Returns conversation_id and message_id for follow-up calls.",
        )
        async def genie_start_conversation(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Genie start conversation with params: {params}")
            try:
                result = genie.start_conversation(
                    space_id=params.get("space_id"),
                    content=params.get("question"),
                )
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error starting Genie conversation: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]

        @self.tool(
            name="genie_send_message",
            description="Send a follow-up message in an existing Genie conversation. Parameters: space_id (required), conversation_id (required), message (required).",
        )
        async def genie_send_message(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Genie send message with params: {params}")
            try:
                result = genie.create_message(
                    space_id=params.get("space_id"),
                    conversation_id=params.get("conversation_id"),
                    content=params.get("message"),
                )
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error sending Genie message: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]

        @self.tool(
            name="genie_get_message",
            description="Get the status and result of a Genie message. Parameters: space_id (required), conversation_id (required), message_id (required).",
        )
        async def genie_get_message(params: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Genie get message with params: {params}")
            try:
                result = genie.get_message(
                    space_id=params.get("space_id"),
                    conversation_id=params.get("conversation_id"),
                    message_id=params.get("message_id"),
                )
                return [{"text": json.dumps(result)}]
            except Exception as e:
                logger.error(f"Error getting Genie message: {str(e)}")
                return [{"text": json.dumps({"error": str(e)})}]

async def main():
    """Main entry point for the MCP server."""
    try:
        logger.info("Starting Databricks MCP server")
        server = DatabricksMCPServer()
        
        # Use the built-in method for stdio servers
        # This is the recommended approach for MCP servers
        await server.run_stdio_async()
            
    except Exception as e:
        logger.error(f"Error in Databricks MCP server: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    # Turn off buffering in stdout
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
    
    asyncio.run(main()) 