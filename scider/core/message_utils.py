"""
Message validation and cleaning utilities for OpenAI API compatibility.
"""

from loguru import logger


def validate_and_clean_messages(messages: list[dict]) -> list[dict]:
    """
    Validate and clean message sequence for OpenAI API compatibility.

    OpenAI API requires that any assistant message with tool_calls must be
    followed by tool messages responding to each tool_call_id.

    This function:
    1. Validates that all tool_call_ids have corresponding tool responses
    2. Removes assistant messages with tool_calls that have no responses
    3. Ensures the message sequence is valid for OpenAI API

    Args:
        messages: List of message dicts with 'role', 'content', 'tool_calls', etc.

    Returns:
        Cleaned list of messages that satisfy OpenAI API requirements
    """
    if not messages:
        return messages

    cleaned_messages = []
    i = 0

    while i < len(messages):
        msg = messages[i]

        # Check if this is an assistant message with tool_calls
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            tool_calls = msg.get("tool_calls", [])
            tool_call_ids = {tc.get("id") if isinstance(tc, dict) else tc.id
                           for tc in tool_calls}

            # Collect all following tool responses until we hit a non-tool message
            tool_responses = []
            j = i + 1
            while j < len(messages) and messages[j].get("role") == "tool":
                tool_responses.append(messages[j])
                j += 1

            # Check if all tool_call_ids have responses
            response_ids = {resp.get("tool_call_id") for resp in tool_responses}
            missing_ids = tool_call_ids - response_ids

            if missing_ids:
                # Missing responses - skip this assistant message and its partial responses
                logger.warning(
                    f"Skipping assistant message with tool_calls at index {i}: "
                    f"missing responses for tool_call_ids {missing_ids}. "
                    f"This may indicate a bug in message history management."
                )
                # Skip the assistant message and any partial tool responses
                i = j
                continue
            else:
                # All tool_calls have responses - include them all
                cleaned_messages.append(msg)
                cleaned_messages.extend(tool_responses)
                i = j
                continue

        # Regular message - include it
        cleaned_messages.append(msg)
        i += 1

    return cleaned_messages
