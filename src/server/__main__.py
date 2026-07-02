"""
Main entry point for running the server module directly.
This allows the module to be run with 'python -m src.server' or 'uv run src.server'.
"""

from src.server.databricks_mcp_server import main

if __name__ == "__main__":
    main() 