"""
Shared utilities for deep agent factory modules.

Provides common helpers used by both store_factory and checkpoint_factory
to avoid duplication: environment detection, event loop access, Redis
connection lifecycle, error classification, and PostgreSQL connection
string resolution.

Not part of the public package API — imported only by sibling factory modules.
"""

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Redis exceptions — gracefully handle missing redis package
try:
    from redis.exceptions import AuthenticationError
    from redis.exceptions import ConnectionError as RedisConnectionError
except ImportError:
    AuthenticationError = Exception  # type: ignore
    RedisConnectionError = Exception  # type: ignore


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def is_dev_environment() -> bool:
    """Return True when NAUTOBOT_DEBUG is set to a truthy value.

    Recognised values: ``true``, ``1``, ``yes``, ``on`` (case-insensitive).
    """
    return os.getenv("NAUTOBOT_DEBUG", "false").lower() in ("true", "1", "yes", "on")


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------


def get_current_event_loop() -> asyncio.AbstractEventLoop | None:
    """Return the running event loop, or ``None`` when no loop is active."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


# ---------------------------------------------------------------------------
# Redis URL resolution
# ---------------------------------------------------------------------------


def get_redis_url(*preferred_env_vars: str) -> str | None:
    """Return the first non-empty Redis URL found, warning if falling back to REDIS_URL.

    Checks ``preferred_env_vars`` in order before trying the shared ``REDIS_URL``
    fallback.  Feature-specific vars (CHECKPOINT_REDIS_URL, STORE_REDIS_URL) are
    preferred so each can be configured independently — but ALL must point to db=0
    (e.g. ``redis://host:6379/0``) because Redis Stack's RediSearch module only
    supports index creation on db=0.  Using any other database causes:
        ``RedisSearchError: Cannot create index on db != 0``

    Args:
        *preferred_env_vars: Ordered env var names to check before REDIS_URL.
            e.g. ``"CHECKPOINT_REDIS_URL"``, ``"STORE_REDIS_URL"``.

    Returns:
        Redis URL string, or ``None`` if none of the variables are set.

    Example:
        >>> url = get_redis_url("CHECKPOINT_REDIS_URL")
        >>> # Reads CHECKPOINT_REDIS_URL first, then falls back to REDIS_URL
    """
    for var in preferred_env_vars:
        value = os.getenv(var)
        if value:
            return value

    # Fall back to the shared REDIS_URL — same db=0 requirement applies.
    # This works for simple single-Redis deployments but shares keyspace with
    # Nautobot/Langfuse.  Prefer setting the feature-specific vars.
    fallback = os.getenv("REDIS_URL")
    if fallback and preferred_env_vars:
        missing = ", ".join(preferred_env_vars)
        logger.warning(
            f"Neither {missing} is set — falling back to REDIS_URL. "
            f"Set {preferred_env_vars[0]} to an explicit /0 URL for clarity, "
            f"e.g. redis://:password@host:6379/0 (RediSearch requires db=0)."
        )
    return fallback


# ---------------------------------------------------------------------------
# Redis connection lifecycle
# ---------------------------------------------------------------------------


async def close_redis_connection(obj: Any, agent_name: str) -> None:
    """Close an underlying ``_redis`` async connection on a store or checkpointer.

    Both ``AsyncRedisStore`` and ``AsyncRedisSaver`` expose their connection
    through a ``_redis`` attribute.  This helper closes it gracefully and
    swallows non-critical errors so teardown never raises.

    Args:
        obj: Object holding a ``_redis`` attribute (store or checkpointer).
        agent_name: Agent name used in log messages.
    """
    try:
        if hasattr(obj, "_redis") and obj._redis is not None:
            await obj._redis.aclose()
    except Exception as exc:
        logger.debug(f"[{agent_name}] Error closing Redis connection: {exc}")


# ---------------------------------------------------------------------------
# Redis error helpers
# ---------------------------------------------------------------------------


def is_redis_auth_error(error: Exception) -> bool:
    """Return True when *error* is a Redis authentication failure.

    Detects both the library exception type and the error message patterns
    emitted by Redis server (``Authentication required``, ``WRONGPASS``).

    Args:
        error: Exception to inspect.

    Returns:
        True if the error is a Redis auth failure.
    """
    if isinstance(error, AuthenticationError):
        return True
    msg = str(error)
    return "Authentication required" in msg or "WRONGPASS" in msg


def log_redis_fallback(
    agent_name: str,
    error: Exception,
    fallback_description: str,
    is_dev: bool,
) -> None:
    """Log a Redis failure at the appropriate level before falling back.

    In dev environments, auth errors are expected (no Redis password configured)
    and are logged at INFO.  All other failures, or non-dev auth errors, are
    logged at WARNING so they surface in production alerting.

    Args:
        agent_name: Agent name used in log messages.
        error: The Redis exception that triggered the fallback.
        fallback_description: Short description of what we fall back to
            (e.g. ``"InMemoryStore"``, ``"PostgreSQL"``).
        is_dev: Whether the application is running in dev/debug mode.
    """
    error_type = type(error).__name__
    error_msg = str(error)[:200]
    auth_error = is_redis_auth_error(error)

    if is_dev and auth_error:
        logger.info(f"[{agent_name}] Redis auth failed in DEV ({error_type}). Falling back to {fallback_description}.")
    else:
        logger.warning(
            f"[{agent_name}] Redis error ({error_type}): {error_msg}. Falling back to {fallback_description}."
        )


# ---------------------------------------------------------------------------
# PostgreSQL connection string
# ---------------------------------------------------------------------------


def get_postgres_connection_string(env_var: str = "CHECKPOINT_DB_URL") -> str:
    """Build a PostgreSQL connection string from an env var or Django settings.

    Checks ``env_var`` first (e.g. ``CHECKPOINT_DB_URL`` or ``STORE_DB_URL``),
    then falls back to constructing a URL from Django's ``DATABASES["default"]``.

    Both the checkpointer and store factories call this to avoid duplicating
    the Django settings introspection logic.

    Args:
        env_var: Name of the feature-specific env var to check first.
            Avoids collisions with ``DATABASE_URL`` (reserved for Langfuse).

    Returns:
        PostgreSQL connection string in the form
        ``postgresql://user:pass@host:port/dbname``.

    Raises:
        ImproperlyConfigured: If the configured database engine is not
            PostgreSQL/PostGIS, or if the database NAME is missing.
    """
    # Django imports are deferred so this module remains importable before
    # Django's app registry is ready (e.g. during test collection).
    from django.conf import settings  # noqa: PLC0415
    from django.core.exceptions import ImproperlyConfigured  # noqa: PLC0415

    db_url = os.getenv(env_var)
    if db_url:
        return db_url

    db_settings = settings.DATABASES.get("default", {})
    engine = db_settings.get("ENGINE", "")

    if "postgresql" not in engine and "postgis" not in engine:
        raise ImproperlyConfigured(
            f"Only PostgreSQL databases are supported (got engine={engine!r}). Set {env_var} to override."
        )

    user = db_settings.get("USER", "")
    password = db_settings.get("PASSWORD", "")
    host = db_settings.get("HOST", "localhost")
    port = db_settings.get("PORT", "5432")
    name = db_settings.get("NAME", "")

    if not name:
        raise ImproperlyConfigured("Database NAME is required in settings.DATABASES")

    if user and password:
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"
    if user:
        return f"postgresql://{user}@{host}:{port}/{name}"
    return f"postgresql://{host}:{port}/{name}"
