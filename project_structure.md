databricks-mcp-server/
├── src/                             # Source code
│   ├── __init__.py                  # Makes src a package
│   ├── __main__.py                  # Run the package directly (python -m src)
│   ├── main.py                      # CLI entry point: arg parsing, logging setup, starts the server
│   ├── tools/                       # MCP tool functions (plain Python functions, FastMCP 3.x style)
│   │   ├── __init__.py              # Makes tools a package
│   │   ├── auth_flow.py             # OAuth U2M PKCE interactive flow (start_auth / check_auth)
│   │   ├── clusters.py              # Cluster management tools
│   │   ├── connectivity.py          # ping_endpoint / list_genie_spaces
│   │   ├── dbfs.py                  # DBFS tools
│   │   ├── genie.py                 # Genie Space tools (ask / conversations / messages)
│   │   ├── jobs.py                  # Job management tools
│   │   ├── notebooks.py             # Notebook management tools
│   │   └── sql.py                   # SQL execution tools
│   ├── core/                        # Core functionality
│   │   ├── __init__.py              # Makes core a package
│   │   ├── auth.py                  # OAuth token providers: M2M (client credentials) + U2M (token-cache reader/refresh)
│   │   ├── config.py                # Settings (Pydantic), PAT/OAuth/U2M selection, Genie Space registry
│   │   └── utils.py                 # Shared HTTP request helper (make_api_request) and error type
│   ├── server/                      # Server implementation
│   │   ├── __init__.py              # Makes server a package
│   │   ├── __main__.py              # Run server module directly (python -m src.server)
│   │   └── databricks_mcp_server.py # FastMCP instance, tool registration, main() entry point
│   └── cli/                         # Command-line interface
│       ├── __init__.py              # Makes cli a package 
│       └── commands.py              # CLI commands: start / list-tools / version
├── tests/                           # Test directory
│   ├── __init__.py                  # Makes tests a package
│   ├── test_auth_u2m.py             # OAuth U2M tests (PKCE, token cache, provider, check_auth)
│   ├── test_clusters.py             # Cluster tool tests
│   ├── test_config.py               # Genie Space registry + auth_type selection tests
│   ├── test_direct.py               # Direct tool-function tests (no MCP protocol)
│   ├── test_genie.py                # Genie tool tests
│   ├── test_mcp_client.py           # MCP client tests (legacy, skipped)
│   ├── test_mcp_server.py           # MCP server tests (legacy, skipped)
│   └── test_tools.py                # Integration tests for individual tools
├── scripts/                         # Scripts directory
│   ├── start_mcp_server.ps1         # Server startup script (Windows)
│   ├── start_mcp_server.sh          # Server startup script (Linux/Mac)
│   ├── run_tests.ps1                # Test runner script
│   ├── run_direct_test.ps1          # Direct test script
│   ├── run_direct_test.sh           # Direct test script (Linux/Mac)
│   ├── show_clusters.py             # Script to show clusters
│   └── show_notebooks.py            # Script to show notebooks
├── examples/                        # Example usage
│   ├── direct_usage.py              # Direct tool-function usage (no MCP protocol)
│   ├── mcp_client_usage.py          # Client example
│   └── README.md                    # Examples documentation
├── docs/                            # Documentation
│   └── phase1.md                    # Project notes
├── .venv/                           # Virtual environment
├── .env                             # Environment variables (not committed)
├── .env.example                     # Example environment file
├── .gitignore                       # Git ignore file
├── start_mcp_server.ps1             # Wrapper for server startup script
├── start_mcp_server.sh              # Wrapper for server startup script (Linux/Mac)
├── README.md                        # Main README
├── LICENSE                          # License file
├── pyproject.toml                   # Modern Python packaging (FastMCP 3.x, Pydantic, requests)
└── uv.lock                          # UV package manager lock file
``` 