"""
Simple script to show clusters from Databricks
"""

import json

from src.tools import clusters


def show_all_clusters():
    """Show all clusters in the Databricks workspace."""
    print("Fetching clusters from Databricks...")
    try:
        result = json.loads(clusters.list_clusters())
        print("\nClusters found:")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"Error listing clusters: {e}")
        return None


if __name__ == "__main__":
    show_all_clusters()
