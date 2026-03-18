"""
Unit tests for message validation and cleaning utilities.
"""

import pytest
from scider.core.message_utils import validate_and_clean_messages


def test_valid_message_sequence():
    """Test that valid message sequences pass through unchanged."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "How are you?"},
    ]
    result = validate_and_clean_messages(messages)
    assert result == messages


def test_assistant_with_tool_calls_and_responses():
    """Test that assistant messages with complete tool responses are kept."""
    messages = [
        {"role": "user", "content": "Search for papers"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "search", "arguments": "{}"}}
            ]
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "Found 5 papers"},
        {"role": "assistant", "content": "I found 5 papers"},
    ]
    result = validate_and_clean_messages(messages)
    assert len(result) == 4
    assert result == messages


def test_assistant_with_missing_tool_responses():
    """Test that assistant messages with missing tool responses are removed."""
    messages = [
        {"role": "user", "content": "Search for papers"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "search", "arguments": "{}"}}
            ]
        },
        # Missing tool response
        {"role": "user", "content": "What did you find?"},
    ]
    result = validate_and_clean_messages(messages)
    # Should skip the assistant message with tool_calls
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "user"


def test_multiple_tool_calls_all_responses():
    """Test assistant message with multiple tool_calls and all responses."""
    messages = [
        {"role": "user", "content": "Search papers and datasets"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "search_papers", "arguments": "{}"}},
                {"id": "call_2", "type": "function", "function": {"name": "search_datasets", "arguments": "{}"}}
            ]
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "Found 5 papers"},
        {"role": "tool", "tool_call_id": "call_2", "content": "Found 3 datasets"},
        {"role": "assistant", "content": "Found results"},
    ]
    result = validate_and_clean_messages(messages)
    assert len(result) == 5
    assert result == messages


def test_multiple_tool_calls_partial_responses():
    """Test assistant message with multiple tool_calls but only partial responses."""
    messages = [
        {"role": "user", "content": "Search papers and datasets"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "search_papers", "arguments": "{}"}},
                {"id": "call_2", "type": "function", "function": {"name": "search_datasets", "arguments": "{}"}}
            ]
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "Found 5 papers"},
        # Missing response for call_2
        {"role": "assistant", "content": "Found results"},
    ]
    result = validate_and_clean_messages(messages)
    # Should skip the assistant message with tool_calls and its partial response
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
    assert result[1]["content"] == "Found results"


def test_empty_messages():
    """Test that empty message list is handled correctly."""
    messages = []
    result = validate_and_clean_messages(messages)
    assert result == []


def test_consecutive_tool_calls():
    """Test multiple assistant messages with tool_calls in sequence."""
    messages = [
        {"role": "user", "content": "First request"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "tool1", "arguments": "{}"}}]
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "Result 1"},
        {"role": "assistant", "content": "Got result 1"},
        {"role": "user", "content": "Second request"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_2", "type": "function", "function": {"name": "tool2", "arguments": "{}"}}]
        },
        # Missing response for call_2
        {"role": "user", "content": "Third request"},
    ]
    result = validate_and_clean_messages(messages)
    # First tool call sequence should be kept, second should be removed
    assert len(result) == 5
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
    assert result[1].get("tool_calls")
    assert result[2]["role"] == "tool"
    assert result[3]["role"] == "assistant"
    assert result[4]["role"] == "user"
    assert result[4]["content"] == "Third request"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
