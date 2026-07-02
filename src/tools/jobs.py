"""Databricks job management tools."""

import json

from src.core.utils import make_api_request


def list_jobs() -> str:
    """List all Databricks jobs."""
    return json.dumps(make_api_request("GET", "/api/2.0/jobs/list"))


def run_job(job_id: int, notebook_params: str = "{}") -> str:
    """
    Run a Databricks job.

    Args:
        job_id: The job ID.
        notebook_params: Parameters as JSON (e.g. '{"key": "value"}').
    """
    params = json.loads(notebook_params) if notebook_params else {}
    data: dict = {"job_id": job_id}
    if params:
        data["notebook_params"] = params
    return json.dumps(make_api_request("POST", "/api/2.0/jobs/run-now", data=data))
