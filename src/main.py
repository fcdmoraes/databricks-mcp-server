"""
Main entry point for the Databricks MCP server.
"""

import argparse
import logging
import sys
from typing import Optional

from src.core.config import settings
from src.server.databricks_mcp_server import main as run_server


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Set up logging configuration.

    Args:
        log_level: Optional log level to override the default
    """
    level = getattr(logging, (log_level or settings.LOG_LEVEL).upper(), logging.WARNING)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
        ],
    )


def main() -> None:
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Databricks MCP Server")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the log level",
    )
    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level)

    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Databricks MCP server v{settings.VERSION}")
    logger.info(f"Databricks host: {settings.DATABRICKS_HOST}")

    # Start the MCP server (blocking call)
    run_server()


if __name__ == "__main__":
    main()
