"""
API for interacting with Databricks Genie Spaces.
"""

import logging
import time
from typing import Any, Dict, Optional

from src.core.utils import DatabricksAPIError, make_api_request

logger = logging.getLogger(__name__)


def start_conversation(space_id: str, content: str) -> Dict[str, Any]:
    """
    Start a new conversation in a Genie Space.

    Args:
        space_id: The Genie Space ID
        content: The initial question/message

    Returns:
        Response containing conversation_id and message_id
    """
    logger.info(f"Starting conversation in Genie Space: {space_id}")
    return make_api_request(
        "POST",
        f"/api/2.0/genie/spaces/{space_id}/start-conversation",
        data={"content": content},
    )


def create_message(space_id: str, conversation_id: str, content: str) -> Dict[str, Any]:
    """
    Send a follow-up message in an existing Genie conversation.

    Args:
        space_id: The Genie Space ID
        conversation_id: The conversation ID
        content: The message content

    Returns:
        Response containing message_id
    """
    logger.info(f"Sending message to conversation {conversation_id} in space {space_id}")
    return make_api_request(
        "POST",
        f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages",
        data={"content": content},
    )


def get_message(space_id: str, conversation_id: str, message_id: str) -> Dict[str, Any]:
    """
    Get the status and result of a Genie message.

    Args:
        space_id: The Genie Space ID
        conversation_id: The conversation ID
        message_id: The message ID

    Returns:
        Message object with status and content
    """
    logger.info(f"Getting message {message_id} from conversation {conversation_id}")
    return make_api_request(
        "GET",
        f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}",
    )


def get_query_result(space_id: str, conversation_id: str, message_id: str) -> Dict[str, Any]:
    """
    Get the SQL query result associated with a Genie message.

    Args:
        space_id: The Genie Space ID
        conversation_id: The conversation ID
        message_id: The message ID

    Returns:
        Query result data
    """
    logger.info(f"Getting query result for message {message_id}")
    return make_api_request(
        "GET",
        f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}/query-result",
    )


def ask_genie(space_id: str, question: str, poll_timeout: int = 60) -> Dict[str, Any]:
    """
    Ask a question to a Genie Space and wait for the response.

    Starts a conversation, then polls until the message status is COMPLETED or FAILED.

    Args:
        space_id: The Genie Space ID
        question: The natural language question
        poll_timeout: Max seconds to wait for a response (default 60)

    Returns:
        Final message object including query results if available
    """
    logger.info(f"Asking Genie Space {space_id}: {question}")

    # Start conversation
    response = start_conversation(space_id, question)
    conversation_id = response.get("conversation_id") or response.get("conversation", {}).get("id")
    message_id = response.get("message_id") or response.get("message", {}).get("id")

    if not conversation_id or not message_id:
        return {"error": "Could not extract conversation_id or message_id from response", "raw": response}

    # Poll for completion
    start = time.time()
    while time.time() - start < poll_timeout:
        message = get_message(space_id, conversation_id, message_id)
        status = message.get("status")

        if status == "COMPLETED":
            # Try to fetch query result if available
            try:
                query_result = get_query_result(space_id, conversation_id, message_id)
                message["query_result"] = query_result
            except DatabricksAPIError:
                pass  # Not all messages have query results
            return message

        if status in ("FAILED", "CANCELLED"):
            return message

        time.sleep(2)

    return {"error": f"Timed out waiting for Genie response after {poll_timeout}s", "conversation_id": conversation_id, "message_id": message_id}
