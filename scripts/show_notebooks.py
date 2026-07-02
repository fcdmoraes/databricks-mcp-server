"""
Simple script to show notebooks from Databricks
"""

import json

from src.tools import notebooks


def show_all_notebooks():
    """Show all notebooks in the Databricks workspace."""
    print("Fetching notebooks from Databricks...")
    try:
        result = json.loads(notebooks.list_notebooks(path="/"))
        print("\nNotebooks found:")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"Error listing notebooks: {e}")
        return None


if __name__ == "__main__":
    show_all_notebooks()
