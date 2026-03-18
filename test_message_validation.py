"""
Simple test runner for message validation utilities (no pytest required).
"""

import sys
sys.path.insert(0, '/Users/liuzf/opencode/SciDER')

from scider.core.message_utils import validate_and_clean_messages


def test_valid_message_sequence():
    """Test that valid message sequences pass through unchanged."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "How are you?"},
    ]
    result = validate_and_clean_messages(messages)
    assert result == messages, "Valid messages should pass through unchanged"
    print("✓ test_valid_message_sequence passed")


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
    assert len(result) == 4, f"Expected 4 messages, got {len(result)}"
    assert result == messages, "Complete tool call sequences should be kept"
    print("✓ test_assistant_with_tool_calls_and_responses passed")


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
    assert len(result) == 2, f"Expected 2 messages, got {len(result)}"
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "user"
    print("✓ test_assistant_with_missing_tool_responses passed")


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
    assert len(result) == 5, f"Expected 5 messages, got {len(result)}"
    assert result == messages, "All tool calls with responses should be kept"
    print("✓ test_multiple_tool_calls_all_responses passed")


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
    assert len(result) == 2, f"Expected 2 messages, got {len(result)}"
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
    assert result[1]["content"] == "Found results"
    print("✓ test_multiple_tool_calls_partial_responses passed")


def run_all_tests():
    """Run all tests."""
    print("Running message validation tests...\n")
    try:
        test_valid_message_sequence()
        test_assistant_with_tool_calls_and_responses()
        test_assistant_with_missing_tool_responses()
        test_multiple_tool_calls_all_responses()
        test_multiple_tool_calls_partial_responses()
        print("\n✅ All tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
