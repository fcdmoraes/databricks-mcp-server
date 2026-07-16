# Databricks MCP Server

A Model Context Protocol (MCP) server for Databricks, built on [FastMCP 3.x](https://gofastmcp.com/), that provides access to Databricks functionality via the MCP protocol. This allows LLM-powered tools (such as Claude Cowork) to interact with Databricks clusters, jobs, notebooks, SQL warehouses, and Genie Spaces.

## Features

- **MCP Protocol Support**: Built on FastMCP 3.x to expose Databricks functionality to LLMs
- **Databricks API Integration**: Provides access to Databricks REST API functionality via plain `requests` calls
- **Tool Registration**: Exposes Databricks functionality as MCP tools, organized under `src/tools/`
- **Flexible Authentication**: Supports Personal Access Tokens (PAT), OAuth 2.0 client credentials (machine-to-machine), and OAuth U2M (user-to-machine) interactive login

## Available Tools

The Databricks MCP Server exposes the following tools:

- **start_auth**: Start the OAuth U2M interactive login flow and return the URL to authenticate in the browser
- **check_auth**: Complete the U2M flow after the user logs in, exchanging the authorization code for a cached token
- **list_clusters**: List all Databricks clusters
- **create_cluster**: Create a new Databricks cluster
- **terminate_cluster**: Terminate a Databricks cluster
- **get_cluster**: Get information about a specific Databricks cluster
- **start_cluster**: Start a terminated Databricks cluster
- **list_jobs**: List all Databricks jobs
- **run_job**: Run a Databricks job
- **list_notebooks**: List notebooks in a workspace directory
- **export_notebook**: Export a notebook from the workspace
- **list_files**: List files and directories in a DBFS path
- **execute_sql**: Execute a SQL statement
- **ping_endpoint**: Verify if an endpoint is responding
- **list_genie_spaces**: List all available Genie Spaces configured in the .env
- **genie_ask**: Ask Genie a natural language question
- **genie_start_conversation**: Starts a new conversation in a Databricks Genie Space
- **genie_send_message**: Send a follow-up message in an existing Genie conversation
- **genie_get_message**: Get the status and result of a Genie message

## Installation

### Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended for MCP servers)

### Setup

1. Install `uv` if you don't have it already:

   ```bash
   # MacOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows (in PowerShell)
   irm https://astral.sh/uv/install.ps1 | iex
   ```

   Restart your terminal after installation.

2. Clone the repository:
   ```bash
   git clone https://github.com/fcdmoraes/databricks-mcp-server.git
   cd databricks-mcp-server
   ```

3. Set up the project with `uv`:
   ```bash
   # Create and activate virtual environment
   uv venv
   
   # On Windows
   .\.venv\Scripts\activate
   
   # On Linux/Mac
   source .venv/bin/activate
   
   # Install dependencies in development mode
   uv pip install -e .
   
   # Install development dependencies
   uv pip install -e ".[dev]"
   ```
   
4. Create an `.env` file based on the `.env.example` template

## Claude Cowork Configuration 

### Register the MCP server into Claude Cowork

In Claude Cowork access User > Settings > Developer

Open the config file `claude_desktop_config.json`

Add the databricks-mcp-server into mcpServers. Three authentication options are supported — pick one and fill the corresponding `env` block.

**Option 1: Personal Access Token (PAT)**

```json
  "mcpServers": {
    "databricks": {
      "command": "[PATH TO YOUR FOLDER]/databricks-mcp-server/.venv/bin/python",
      "args": ["-m", "src.server.databricks_mcp_server"],
      "env": {
        "DATABRICKS_HOST": [HOST_ADDRESS],
        "DATABRICKS_TOKEN": [DATABRICKS_TOKEN]
      }
    }
  },
```

**Option 2: OAuth 2.0 Client Credentials (M2M)**

```json
  "mcpServers": {
    "databricks": {
      "command": "[PATH TO YOUR FOLDER]/databricks-mcp-server/.venv/bin/python",
      "args": ["-m", "src.server.databricks_mcp_server"],
      "env": {
        "DATABRICKS_HOST": [HOST_ADDRESS],
        "DATABRICKS_CLIENT_ID": [CLIENT_ID],
        "DATABRICKS_CLIENT_SECRET": [CLIENT_SECRET]
      }
    }
  },
```

**Option 3: OAuth U2M (interactive user login)**

Use this when you want to authenticate as yourself (for example, via corporate SSO / Azure AD) instead of a static token or service principal. Provide only the host and leave the credential variables out:

```json
  "mcpServers": {
    "databricks": {
      "command": "[PATH TO YOUR FOLDER]/databricks-mcp-server/.venv/bin/python",
      "args": ["-m", "src.server.databricks_mcp_server"],
      "env": {
        "DATABRICKS_HOST": [HOST_ADDRESS]
      }
    }
  },
```

With U2M, the first query triggers a `needs_auth` response. Ask Claude to authenticate: it calls `start_auth`, returns a login URL for you to open in the browser, and after you sign in and confirm, `check_auth` completes the exchange. The resulting OAuth token (and refresh token) is cached in `~/.databricks/token-cache.json` — the same format used by the Databricks CLI/SDK — and refreshed automatically when it expires. See [Authorize user access to Databricks with OAuth (U2M)](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/oauth-u2m) for background.

**Authentication precedence:** the server selects the type automatically — OAuth M2M (if `DATABRICKS_CLIENT_ID`/`DATABRICKS_CLIENT_SECRET` are set) takes priority, then PAT (if `DATABRICKS_TOKEN` is set), and finally U2M (if none of the above are set).

> Note: today the `env` block requires the credentials to be passed inline (as shown above). Pointing to an external `.env` file path from this config is not yet supported by the server — if you need that, the server would need to be extended to read a path such as `DATABRICKS_ENV_FILE` and load it explicitly.

Restart Claude Cowork

**important: Ensure your token/credentials give you access to the Genie Space and the Unity Catalog**

### Testing

Ask Claude to verify if the MCP server is running



## Project Structure

```
databricks-mcp-server/
├── src/                             # Source code
│   ├── __init__.py                  # Makes src a package
│   ├── __main__.py                  # Main entry point for the package
│   ├── main.py                      # CLI entry point (arg parsing + startup logging)
│   ├── tools/                       # MCP tool functions, registered on the FastMCP server
│   │   ├── auth_flow.py             # OAuth U2M PKCE interactive flow (start_auth / check_auth)
│   │   ├── clusters.py              # Cluster management tools
│   │   ├── connectivity.py          # ping_endpoint / list_genie_spaces
│   │   ├── dbfs.py                  # DBFS tools
│   │   ├── genie.py                 # Genie Space tools
│   │   ├── jobs.py                  # Job management tools
│   │   ├── notebooks.py             # Notebook management tools
│   │   └── sql.py                   # SQL execution tools
│   ├── core/                        # Core functionality
│   │   ├── auth.py                  # OAuth token providers: M2M (client credentials) + U2M (cache reader/refresh)
│   │   ├── config.py                # Settings (Pydantic), PAT/OAuth/U2M selection, Genie registry
│   │   └── utils.py                 # Shared HTTP request helper (make_api_request)
│   ├── server/                      # Server implementation
│   │   └── databricks_mcp_server.py # FastMCP instance + tool registration + entry point
│   └── cli/                         # Command-line interface (start / list-tools / version)
├── tests/                           # Test directory
├── scripts/                         # Helper scripts
│   ├── start_mcp_server.ps1         # Server startup script (Windows)
│   ├── run_tests.ps1                # Test runner script
│   ├── show_clusters.py             # Script to show clusters
│   └── show_notebooks.py            # Script to show notebooks
├── examples/                        # Example usage
├── docs/                            # Documentation
└── pyproject.toml                   # Project configuration
```

See `project_structure.md` for a more detailed view of the project structure.

## Development

### Code Standards

- Python code follows PEP 8 style guide with a maximum line length of 100 characters
- Use 4 spaces for indentation (no tabs)
- Use double quotes for strings
- All classes, methods, and functions should have Google-style docstrings
- Type hints are required for all code except tests

### Linting

The project uses the following linting tools:

```bash
# Run all linters
uv run pylint src/ tests/
uv run flake8 src/ tests/
uv run mypy src/
```

## Testing

The project uses pytest for testing. To run the tests:

```bash
# Run all tests with our convenient script
.\scripts\run_tests.ps1

# Run with coverage report
.\scripts\run_tests.ps1 -Coverage

# Run specific tests with verbose output
.\scripts\run_tests.ps1 -Verbose -Coverage tests/test_clusters.py
```

You can also run the tests directly with pytest:

```bash
# Run all tests
uv run pytest tests/

# Run with coverage report
uv run pytest --cov=src tests/ --cov-report=term-missing
```

A minimum code coverage of 80% is the goal for the project.

## Documentation

- Project notes are kept in the `docs/` directory
- All code includes Google-style docstrings
- See the `examples/` directory for usage examples

## Examples

Check the `examples/` directory for usage examples. To run examples:

```bash
# Run example scripts with uv
uv run examples/direct_usage.py
uv run examples/mcp_client_usage.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Ensure your code follows the project's coding standards
2. Add tests for any new functionality
3. Update documentation as necessary
4. Verify all tests pass before submitting

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
