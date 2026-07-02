"""Genie Space tools — natural language querying against Databricks."""

import json
import logging
import time
from typing import Any, Dict

from src.core.utils import DatabricksAPIError, make_api_request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal functions — HTTP helpers
# ---------------------------------------------------------------------------

def _start_conversation(space_id: str, content: str) -> Dict[str, Any]:
    return make_api_request(
        "POST",
        f"/api/2.0/genie/spaces/{space_id}/start-conversation",
        data={"content": content},
    )


def _create_message(space_id: str, conversation_id: str, content: str) -> Dict[str, Any]:
    return make_api_request(
        "POST",
        f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages",
        data={"content": content},
    )


def _get_message(space_id: str, conversation_id: str, message_id: str) -> Dict[str, Any]:
    return make_api_request(
        "GET",
        f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}",
    )


def _get_query_result(space_id: str, conversation_id: str, message_id: str) -> Dict[str, Any]:
    return make_api_request(
        "GET",
        f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}/query-result",
    )


def _ask_genie(space_id: str, question: str, poll_timeout: int = 60) -> Dict[str, Any]:
    """Start a conversation and poll until COMPLETED/FAILED or timeout."""
    response = _start_conversation(space_id, question)
    conversation_id = response.get("conversation_id") or response.get("conversation", {}).get("id")
    message_id = response.get("message_id") or response.get("message", {}).get("id")

    if not conversation_id or not message_id:
        return {"error": "Could not extract conversation_id or message_id", "raw": response}

    start = time.time()
    while time.time() - start < poll_timeout:
        message = _get_message(space_id, conversation_id, message_id)
        status = message.get("status")

        if status == "COMPLETED":
            try:
                message["query_result"] = _get_query_result(space_id, conversation_id, message_id)
            except DatabricksAPIError:
                pass  # Not every message has a query_result
            return message

        if status in ("FAILED", "CANCELLED"):
            return message

        time.sleep(2)

    return {
        "error": f"Timeout waiting for Genie's response after {poll_timeout}s",
        "conversation_id": conversation_id,
        "message_id": message_id,
    }


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

def genie_ask(space_id: str, question: str, poll_timeout: int = 60) -> str:
    """
    Ask a natural language question to a Genie Space and wait for the response.

    Polls until the response is ready (COMPLETED) or the timeout expires.
    """
    return json.dumps(_ask_genie(space_id=space_id, question=question, poll_timeout=poll_timeout))


def genie_start_conversation(space_id: str, question: str) -> str:
    """
    Start a new conversation in a Genie Space.

    Returns conversation_id and message_id for use in genie_send_message / genie_get_message.
    """
    return json.dumps(_start_conversation(space_id=space_id, content=question))


def genie_send_message(space_id: str, conversation_id: str, message: str) -> str:
    """Send a follow-up message in an existing Genie conversation."""
    return json.dumps(_create_message(space_id=space_id, conversation_id=conversation_id, content=message))


def genie_get_message(space_id: str, conversation_id: str, message_id: str) -> str:
    """Get the status and result of a Genie message."""
    return json.dumps(_get_message(space_id=space_id, conversation_id=conversation_id, message_id=message_id))
