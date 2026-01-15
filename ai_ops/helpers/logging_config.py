"""Structured JSON logging configuration for AI Ops agent.

This module provides JSON logging scoped to ai_ops.* loggers only,
with correlation ID support for end-to-end request tracing.

Environment Variables:
    AI_OPS_JSON_LOGGING: Set to 'false' for text logging (default: 'true')
"""

import logging
from contextvars import ContextVar
from datetime import datetime

# Context variable for async-safe correlation ID tracking
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Context variable for async-safe user tracking
user_var: ContextVar[str] = ContextVar("user", default="")

# Module-level flag to track if logging has been configured
_logging_configured = False


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation_id and user to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id and user to the log record."""
        record.correlation_id = correlation_id_var.get() or ""
        record.user = user_var.get() or ""
        return True


class ConciseFormatter(logging.Formatter):
    """Logging formatter that outputs a concise, human-readable format and accepts extra fields."""

    def __init__(self, *args, **kwargs):
        """Initialize with optional extra fields to include in log output."""
        self.extra_fields = kwargs.pop("extra_fields", {})
        super().__init__(*args, **kwargs)

    def format(self, record):
        """Format the specified record as text, including extra fields.

        Args:
            record (logging.LogRecord): The log record to be formatted.

        Returns:
            str: The formatted log message string.
        """
        ts = datetime.fromtimestamp(record.created).strftime("%Y%m%d-%H:%M:%S")
        user = getattr(record, "user", None)
        thread = getattr(record, "thread", None)
        func = getattr(record, "funcName", "?")
        module = getattr(record, "module", "?")
        msg = record.getMessage()
        # Add extra fields if present
        extra_str = ""
        for k, v in self.extra_fields.items():
            val = getattr(record, k, v)
            extra_str += f" {k}={val}"
        if user is None:
            if "user=" in msg:
                user = msg.split("user=")[1].split()[0]
            else:
                user = "unknown"
        if thread is None:
            if "thread=" in msg:
                thread = msg.split("thread=")[1].split()[0]
            else:
                thread = ""
        return f"[{ts} {record.levelname}] {module}.{func} user={user} thread={thread}{extra_str} {msg}"


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

    # Set concise formatter for root logger
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        root_logger.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setFormatter(ConciseFormatter())
    handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Mark as configured
    _logging_configured = True

    # Log setup confirmation
    logging.getLogger(__name__).info("AI Ops logging configured: concise format")


def get_correlation_id() -> str:
    """Get the current correlation ID; if none is set, generate a new one and store it in the context."""
    cid = correlation_id_var.get()
    if not cid:
        import uuid

        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Get the current correlation ID; if none is set, generate a new one and store it in the context."""
    correlation_id_var.set(cid)


def generate_correlation_id() -> str:
    """Generate a new correlation ID and set it in context."""
    import uuid

    cid = str(uuid.uuid4())
    correlation_id_var.set(cid)
    return cid


def get_user() -> str:
    """Get current user from context.

    Returns:
        str: The username string from context, or an empty string if not set.
    """
    return user_var.get()


def set_user(username: str) -> None:
    """Set the user for the current async context."""
    user_var.set(username)
