"""
Unit tests for the Genie Space tools (src/tools/genie.py).
"""

import json
from unittest.mock import patch

from src.core.utils import DatabricksAPIError
from src.tools import genie


def test_genie_start_conversation_calls_correct_endpoint():
    with patch("src.tools.genie.make_api_request") as mock_req:
        mock_req.return_value = {"conversation_id": "conv-1", "message_id": "msg-1"}
        result = json.loads(genie.genie_start_conversation(space_id="space-1", question="What tables exist?"))

        mock_req.assert_called_once_with(
            "POST",
            "/api/2.0/genie/spaces/space-1/start-conversation",
            data={"content": "What tables exist?"},
        )
        assert result["conversation_id"] == "conv-1"


def test_genie_send_message_calls_correct_endpoint():
    with patch("src.tools.genie.make_api_request") as mock_req:
        mock_req.return_value = {"message_id": "msg-2"}
        genie.genie_send_message(space_id="space-1", conversation_id="conv-1", message="What about the sales table?")

        mock_req.assert_called_once_with(
            "POST",
            "/api/2.0/genie/spaces/space-1/conversations/conv-1/messages",
            data={"content": "What about the sales table?"},
        )


def test_genie_get_message_calls_correct_endpoint():
    with patch("src.tools.genie.make_api_request") as mock_req:
        mock_req.return_value = {"status": "COMPLETED"}
        result = json.loads(genie.genie_get_message(space_id="space-1", conversation_id="conv-1", message_id="msg-1"))

        mock_req.assert_called_once_with(
            "GET",
            "/api/2.0/genie/spaces/space-1/conversations/conv-1/messages/msg-1",
        )
        assert result["status"] == "COMPLETED"


def test_genie_ask_returns_completed_message_with_query_result():
    start_response = {"conversation_id": "conv-1", "message_id": "msg-1"}
    message_response = {"status": "COMPLETED"}
    query_result_response = {"result": {"data_array": [["sales_table"]]}}

    with patch("src.tools.genie.make_api_request") as mock_req:
        mock_req.side_effect = [start_response, message_response, query_result_response]

        result = json.loads(genie.genie_ask(space_id="space-1", question="What tables exist?", poll_timeout=5))

    assert result["status"] == "COMPLETED"
    assert result["query_result"] == query_result_response
    assert mock_req.call_count == 3


def test_genie_ask_handles_missing_query_result():
    """If the message completed but there is no query_result, the error should be ignored."""
    start_response = {"conversation_id": "conv-1", "message_id": "msg-1"}
    message_response = {"status": "COMPLETED"}

    with patch("src.tools.genie.make_api_request") as mock_req:
        mock_req.side_effect = [
            start_response,
            message_response,
            DatabricksAPIError("no query result", status_code=404),
        ]

        result = json.loads(genie.genie_ask(space_id="space-1", question="Hi", poll_timeout=5))

    assert result["status"] == "COMPLETED"
    assert "query_result" not in result


def test_genie_ask_returns_error_when_ids_missing():
    with patch("src.tools.genie.make_api_request") as mock_req:
        mock_req.return_value = {}
        result = json.loads(genie.genie_ask(space_id="space-1", question="Hi", poll_timeout=5))

    assert "error" in result
