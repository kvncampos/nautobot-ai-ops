"""
Middleware utilities for LangGraph deep agents in ai-ops.

This module provides reusable middleware classes for agent workflows,
including error handling for tool execution.

Adapted from network-agent to work with Django configuration.
"""

import asyncio
import logging

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)


class ToolErrorHandlerMiddleware(AgentMiddleware):
    """
    Middleware to handle tool execution errors gracefully with automatic retry for transient errors.

    Usage:
        ```python
        from ai_ops.helpers.deep_agent.middleware import ToolErrorHandlerMiddleware

        # Default: 2 retries, 1 second delay
        middleware=[ToolErrorHandlerMiddleware()]

        # Custom: 3 retries, 2 second delay
        middleware=[ToolErrorHandlerMiddleware(max_retries=3, retry_delay=2.0)]
        ```
    """

    # Keywords that indicate a transient/retriable error
    RETRIABLE_KEYWORDS = [
        "eof while parsing",
        "invalid json",
        "validationerror",
        "connection",
        "timeout",
        "timed out",
        "broken pipe",
        "connection reset",
        "network",
        "eof occurred",
        "sse",
        "server-sent events",
        "streamable_http",
    ]

    def __init__(self, max_retries: int = 2, retry_delay: float = 1.0):
        """
        Initialize the middleware.

        Args:
            max_retries: Number of retry attempts (default: 2, total 3 attempts)
            retry_delay: Delay between retries in seconds (default: 1.0)
        """
        super().__init__()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def awrap_tool_call(self, request, handler):
        """
        Wrap async tool calls with error handling and retry logic for transient errors.

        Args:
            request: Tool call request with tool_call dict containing 'id' and 'name'
            handler: Async tool execution handler

        Returns:
            ToolMessage: Success result or error message with status="error"
        """
        tool_name = request.tool_call.get("name", "unknown")
        last_error = None

        # Attempt execution with retries
        for attempt in range(self.max_retries + 1):
            try:
                result = await handler(request)

                # Log successful retry
                if attempt > 0:
                    logger.info(f"[TOOL_CALL] ✓ Tool '{tool_name}' succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_error = e
                is_retriable = self._is_retriable(str(e))

                # Log attempt
                logger.warning(
                    f"[TOOL_CALL] ✗ Tool '{tool_name}' attempt {attempt + 1}/{self.max_retries + 1}: "
                    f"{type(e).__name__} (retriable={is_retriable})"
                )

                # Break if last attempt or not retriable
                if attempt >= self.max_retries or not is_retriable:
                    break

                await asyncio.sleep(self.retry_delay)

        # Build error message with repr(e)
        error_msg = (
            f"Tool error: {repr(last_error)}\n\nPlease try a different approach or ask for clarification if needed."
        )

        logger.error(f"[TOOL_CALL] ✗ Tool '{tool_name}' failed after {self.max_retries + 1} attempts")

        return ToolMessage(content=error_msg, tool_call_id=request.tool_call["id"], name=tool_name, status="error")

    def _is_retriable(self, error_str: str) -> bool:
        """Check if error is transient and retriable."""
        error_lower = error_str.lower()
        return any(keyword in error_lower for keyword in self.RETRIABLE_KEYWORDS)
