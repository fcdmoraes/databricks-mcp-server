"""
Configuration settings for the Databricks MCP server.
"""

import os
import re
from typing import Dict, List, Optional

# Import dotenv if available, but don't require it
try:
    from dotenv import load_dotenv
    # Load .env file if it exists
    load_dotenv()
    # print("Successfully loaded dotenv")
except ImportError:
    print("WARNING: python-dotenv not found, environment variables must be set manually")
    # We'll just rely on OS environment variables being set manually

from pydantic_settings import BaseSettings

# Version
VERSION = "1.0.0"


class Settings(BaseSettings):
    """Base settings for the application."""

    # Databricks API configuration
    DATABRICKS_HOST: str = os.environ.get("DATABRICKS_HOST", "https://example.databricks.net")
    DATABRICKS_TOKEN: str = os.environ.get("DATABRICKS_TOKEN", "dapi_token_placeholder")

    # OAuth M2M authentication (client credentials)
    # If both are defined, OAuth takes precedence over the PAT.
    DATABRICKS_CLIENT_ID: str = ""
    DATABRICKS_CLIENT_SECRET: str = ""

    # MCP transport: "stdio" for Claude Desktop or "streamable-http" for HTTP transport
    mcp_transport: str = "stdio"
    mcp_host: str = "localhost"
    mcp_port: int = 8000
    mcp_path: str = "/mcp/"

    # Connector description (used in the MCP server's instructions)
    specialist_description: str = (
        "Use this server to query and manage Databricks resources."
    )

    # Logging
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    
    # Version
    VERSION: str = VERSION

    @property
    def auth_type(self) -> str:
        """Return 'oauth' or 'pat' depending on which credentials are configured."""
        if self.DATABRICKS_CLIENT_ID and self.DATABRICKS_CLIENT_SECRET:
            return "oauth"
        return "pat"

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Create global settings instance
settings = Settings(
    specialist_description=os.environ.get(
        "SPECIALIST_DESCRIPTION",
        "Use this server to query and manage Databricks resources.",
    )
)

# ---------------------------------------------------------------------------
# OAuth token provider placeholder
# ---------------------------------------------------------------------------

_oauth_provider = None

def _get_oauth_provider():
    global _oauth_provider
    if _oauth_provider is None:
        from src.core.auth import OAuthTokenProvider
        _oauth_provider = OAuthTokenProvider(
            host=settings.DATABRICKS_HOST,
            client_id=settings.DATABRICKS_CLIENT_ID,
            client_secret=settings.DATABRICKS_CLIENT_SECRET,
        )
    return _oauth_provider

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def get_genie_spaces() -> List[Dict[str, str]]:
    """
    Load Genie Space registry from environment variables.

    Reads variables in the pattern:
        GENIE_SPACE_<N>_ID
        GENIE_SPACE_<N>_NAME
        GENIE_SPACE_<N>_DESCRIPTION  (optional)

    Returns a list of dicts ordered by N, e.g.:
        [{"id": "...", "name": "vendas", "description": "Vendas B2C..."}]
    """
    spaces: Dict[int, Dict[str, str]] = {}

    for key, value in os.environ.items():
        match = re.match(r"^GENIE_SPACE_(\d+)_(ID|NAME|DESCRIPTION)$", key)
        if match:
            n = int(match.group(1))
            field = match.group(2).lower()
            spaces.setdefault(n, {})[field] = value

    result = []
    for n in sorted(spaces):
        space = spaces[n]
        if "id" in space and "name" in space:
            result.append({
                "id": space["id"],
                "name": space["name"],
                "description": space.get("description", ""),
            })

    return result

def get_api_headers() -> Dict[str, str]:
    """
    Get headers for Databricks API requests.
    
    Uses OAuth token if configured, otherwise uses the PAT from settings.
    """
    if settings.auth_type == "oauth":
        token = _get_oauth_provider().get_token()
    else:
        token = settings.DATABRICKS_TOKEN
    return {"Authorization": f"Bearer {token}"}


def get_databricks_api_url(endpoint: str) -> str:
    """
    Construct the full Databricks API URL.
    
    Args:
        endpoint: The API endpoint path, e.g., "/api/2.0/clusters/list"
    
    Returns:
        Full URL to the Databricks API endpoint
    """
    # Ensure endpoint starts with a slash
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    return f"{settings.DATABRICKS_HOST.rstrip('/')}{endpoint}"