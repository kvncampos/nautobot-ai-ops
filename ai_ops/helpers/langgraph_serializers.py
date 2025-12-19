"""LangGraph message serialization utilities."""

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage, messages_from_dict, messages_to_dict


def serialize_messages(messages: list[BaseMessage]) -> list[dict]:
    """Convert LangChain messages to JSON-serializable format.

    Uses LangChain's built-in serialization to preserve all message metadata
    including tool_calls, tool_call_id, and other important fields.

    Args:
        messages: List of LangChain BaseMessage objects

    Returns:
        List of dicts compatible with LangChain's message format
    """
    return messages_to_dict(messages)


def validate_message_sequence(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Validate and clean message sequence to ensure tool messages follow tool calls.

    OpenAI API requires that ToolMessages must immediately follow an AIMessage with tool_calls.
    This function removes orphaned tool messages that would cause API errors.

    Args:
        messages: List of messages to validate

    Returns:
        Cleaned list of messages with valid tool message sequences
    """
    if not messages:
        return []

    cleaned = []
    last_had_tool_calls = False

    for msg in messages:
        # Check if this is a tool message
        if isinstance(msg, ToolMessage):
            # Only keep tool messages that follow an AI message with tool_calls
            if last_had_tool_calls:
                cleaned.append(msg)
            # else: skip orphaned tool message
        else:
            # Not a tool message, always keep it
            cleaned.append(msg)
            # Track if this AI message has tool calls
            last_had_tool_calls = isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls

    return cleaned


def deserialize_messages(data: list[dict]) -> list[BaseMessage]:
    """Convert serialized message data back to LangChain messages.

    Uses LangChain's built-in deserialization to restore all message metadata
    including tool_calls, tool_call_id, and other important fields.

    Handles legacy format for backward compatibility during migration.
    Validates message sequence to ensure tool messages are properly paired.

    Args:
        data: List of dicts in LangChain's message format

    Returns:
        List of LangChain BaseMessage objects with valid tool message sequences
    """
    if not data:
        return []

    # Check if this is the old custom format (missing 'data' key)
    # Old format: [{"type": "human", "content": "..."}, ...]
    # New format: [{"type": "human", "data": {"content": "...", ...}}, ...]
    if data and isinstance(data[0], dict) and "data" not in data[0]:
        # Legacy format detected - return empty to start fresh conversation
        # This avoids compatibility issues with old cached messages
        return []

    try:
        messages = messages_from_dict(data)
        # Validate and clean the message sequence
        return validate_message_sequence(messages)
    except Exception:
        # If deserialization fails, return empty to start fresh
        return []
