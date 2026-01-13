"""Structured JSON logging configuration for AI Ops agent.

This module provides JSON logging scoped to ai_ops.* loggers only,
with correlation ID support for end-to-end request tracing.

Environment Variables:
    AI_OPS_JSON_LOGGING: Set to 'false' for text logging (default: 'true')
"""

import logging
import os
import uuid
from contextvars import ContextVar

# Context variable for async-safe correlation ID tracking
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Context variable for async-safe user tracking
user_var: ContextVar[str] = ContextVar("user", default="")

# Module-level flag to track if logging has been configured
_logging_configured = False


def get_correlation_id() -> str:
    """Get current correlation ID, or generate a new one if not set."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current async context."""
    correlation_id_var.set(cid)


def generate_correlation_id() -> str:
    """Generate a new correlation ID and set it in context."""
    cid = str(uuid.uuid4())
    correlation_id_var.set(cid)
    return cid


def get_user() -> str:
    """Get current user from context."""
    return user_var.get()


def set_user(username: str) -> None:
    """Set the user for the current async context."""
    user_var.set(username)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation_id and user to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id and user to the log record."""
        record.correlation_id = correlation_id_var.get() or ""
        record.user = user_var.get() or ""
        return True


def _is_json_logging_enabled() -> bool:
    """Check if JSON logging is enabled via environment variable."""
    return os.environ.get("AI_OPS_JSON_LOGGING", "true").lower() in ("true", "1", "yes")


def setup_ai_ops_logging() -> None:
    """Configure JSON logging for ai_ops.* loggers only.

    This sets up structured JSON logging with correlation ID support,
    scoped only to ai_ops module loggers (not Django/Nautobot core).

    JSON format is default; set AI_OPS_JSON_LOGGING=false for text format.
    """
    global _logging_configured

    # Avoid duplicate configuration
    if _logging_configured:
        return

    # Get the ai_ops logger (parent of all ai_ops.* loggers)
    ai_ops_logger = logging.getLogger("ai_ops")

    # Create handler
    handler = logging.StreamHandler()

    if _is_json_logging_enabled():
        try:
            from pythonjsonlogger.json import JsonFormatter

            # Configure JSON formatter with standard fields
            formatter = JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s %(correlation_id)s %(user)s",
                rename_fields={
                    "asctime": "timestamp",
                    "levelname": "level",
                    "funcName": "function",
                    "lineno": "line",
                },
                static_fields={
                    "service": "nautobot_ai_ops",
                },
                timestamp=True,
            )
            handler.setFormatter(formatter)
        except ImportError:
            # Fallback to text format if python-json-logger not installed
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s %(name)s [%(correlation_id)s] [%(user)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
    else:
        # Text format for development
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s [%(correlation_id)s] [%(user)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

    # Add correlation ID filter
    handler.addFilter(CorrelationIdFilter())

    # Add handler to ai_ops logger
    ai_ops_logger.addHandler(handler)

    # Don't propagate to root logger to avoid duplicate logs
    # But allow INFO and above to still show
    ai_ops_logger.setLevel(logging.DEBUG)

    # Mark as configured
    _logging_configured = True

    # Log setup confirmation
    mode = "JSON" if _is_json_logging_enabled() else "text"
    logging.getLogger(__name__).info(f"AI Ops logging configured: format={mode}")
