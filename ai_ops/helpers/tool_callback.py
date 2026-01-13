"""LangChain callback handler for tool call logging.

This module provides a callback handler that logs tool invocations
in real-time with timing information and correlation IDs.
"""

import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from ai_ops.helpers.logging_config import get_correlation_id

logger = logging.getLogger(__name__)


class ToolLoggingCallback(BaseCallbackHandler):
    """Callback handler that logs tool calls with timing information.

    Logs tool start/end events at INFO level with:
    - Tool name
    - Correlation ID
    - Duration (on completion)

    Does NOT log tool arguments or full responses to keep logs concise.
    """

    def __init__(self) -> None:
        """Initialize the callback handler."""
        super().__init__()
        # Track start times by run_id for duration calculation
        self._start_times: dict[UUID, float] = {}

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log when a tool starts execution.

        Args:
            serialized: Serialized tool information containing name
            input_str: String representation of input (not logged)
            run_id: Unique identifier for this tool run
            parent_run_id: Parent run ID if nested
            tags: Optional tags
            metadata: Optional metadata
            inputs: Optional input dict (not logged)
            **kwargs: Additional arguments
        """
        tool_name = serialized.get("name", "unknown")
        correlation_id = get_correlation_id()

        # Store start time for duration calculation
        self._start_times[run_id] = time.perf_counter()

        logger.info(
            f"[tool_start] tool={tool_name} correlation_id={correlation_id}",
            extra={
                "tool_name": tool_name,
                "event_type": "tool_start",
            },
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log when a tool completes execution.

        Args:
            output: Tool output (not logged, only size)
            run_id: Unique identifier for this tool run
            parent_run_id: Parent run ID if nested
            tags: Optional tags
            **kwargs: Additional arguments (may contain name)
        """
        correlation_id = get_correlation_id()

        # Calculate duration
        start_time = self._start_times.pop(run_id, None)
        duration_ms = (time.perf_counter() - start_time) * 1000 if start_time else 0

        # Try to get tool name from kwargs or use unknown
        tool_name = kwargs.get("name", "unknown")

        # Get output size for logging (without logging actual content)
        output_size = len(str(output)) if output else 0

        logger.info(
            f"[tool_end] tool={tool_name} duration_ms={duration_ms:.1f} output_chars={output_size} correlation_id={correlation_id}",
            extra={
                "tool_name": tool_name,
                "event_type": "tool_end",
                "duration_ms": round(duration_ms, 1),
                "output_chars": output_size,
            },
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log when a tool encounters an error.

        Args:
            error: The exception that occurred
            run_id: Unique identifier for this tool run
            parent_run_id: Parent run ID if nested
            tags: Optional tags
            **kwargs: Additional arguments
        """
        correlation_id = get_correlation_id()

        # Calculate duration
        start_time = self._start_times.pop(run_id, None)
        duration_ms = (time.perf_counter() - start_time) * 1000 if start_time else 0

        # Try to get tool name from kwargs
        tool_name = kwargs.get("name", "unknown")

        logger.error(
            f"[tool_error] tool={tool_name} error={type(error).__name__} duration_ms={duration_ms:.1f} correlation_id={correlation_id}",
            extra={
                "tool_name": tool_name,
                "event_type": "tool_error",
                "error_type": type(error).__name__,
                "duration_ms": round(duration_ms, 1),
            },
        )
