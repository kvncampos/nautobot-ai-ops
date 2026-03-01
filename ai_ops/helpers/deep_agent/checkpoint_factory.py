"""
Checkpoint factory utilities for LangGraph deep agents in ai-ops.

Provides reusable checkpoint configuration with connection pooling.
Supports both Redis and PostgreSQL checkpointers with automatic fallback.

Adapted from network-agent to work with Django configuration.

Example:
    >>> checkpointer = await get_checkpointer("my_agent")
    >>> # Checkpointer is cached and reused
    >>> await close_all_pools()  # On shutdown
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from ._utils import (
    get_current_event_loop,
    get_postgres_connection_string,
    get_redis_url,
    is_dev_environment,
    log_redis_fallback,
)

logger = logging.getLogger(__name__)

# Type aliases
CheckpointerType = AsyncRedisSaver | AsyncPostgresSaver
PostgresPool = AsyncConnectionPool[AsyncConnection[DictRow]]


@dataclass
class CheckpointerMetadata:
    """Metadata for tracking checkpointer state."""

    checkpointer: CheckpointerType
    event_loop: asyncio.AbstractEventLoop | None
    pool: PostgresPool | None = None  # For PostgreSQL only
    context_manager: Any | None = None  # For Redis: async CM returned by from_conn_string()


# Global checkpointer cache per agent
_checkpointers: dict[str, CheckpointerMetadata] = {}


def _get_ttl_config() -> dict:
    """Get TTL configuration for Redis checkpointer."""
    default_ttl = int(os.getenv("CHECKPOINT_TTL", "3600"))  # 1 hour default
    return {
        "default_ttl": default_ttl // 60,  # Convert to minutes for Redis
        "refresh_on_read": True,  # Reset expiration time when reading
    }


def _get_redis_url() -> str | None:
    """Get Redis URL, preferring CHECKPOINT_REDIS_URL over REDIS_URL."""
    return get_redis_url("CHECKPOINT_REDIS_URL")


async def _close_checkpointer_cm(cm: Any, agent_name: str) -> None:
    """Exit an async context manager returned by ``AsyncRedisSaver.from_conn_string()``.

    Args:
        cm: Context manager to exit.
        agent_name: Agent name for logging.
    """
    try:
        await cm.__aexit__(None, None, None)
    except Exception as exc:
        logger.debug(f"[{agent_name}] Error closing checkpointer context manager: {exc}")


async def _create_redis_checkpointer(redis_url: str, agent_name: str) -> tuple[AsyncRedisSaver, Any]:
    """
    Create and setup a Redis checkpointer.

    Args:
        redis_url: Redis connection URL
        agent_name: Agent name for logging

    Returns:
        Configured AsyncRedisSaver

    Raises:
        Exception: If Redis connection or setup fails
    """
    ttl_config = _get_ttl_config()
    default_ttl = ttl_config["default_ttl"] * 60  # Convert back to seconds for logging

    logger.info(f"[{agent_name}] Creating AsyncRedisSaver with TTL={default_ttl}s")

    # from_conn_string() returns an async context manager; enter it to get the
    # live checkpointer.  Return the CM so the caller can store it for __aexit__.
    #
    # NOTE: from_conn_string().__aenter__() calls asetup() internally — it
    # creates all RediSearch indexes and detects cluster mode.  There is no
    # need (and it would be harmful) to call asetup() again explicitly.
    cm = AsyncRedisSaver.from_conn_string(redis_url, ttl=ttl_config)
    checkpointer = await cm.__aenter__()

    logger.info(f"[{agent_name}] \u2713 Redis checkpointer created successfully")
    return checkpointer, cm


async def _create_postgres_pool(agent_name: str, conninfo: str) -> PostgresPool:
    """
    Create PostgreSQL connection pool.

    Args:
        agent_name: Agent name for logging
        conninfo: PostgreSQL connection string

    Returns:
        Configured AsyncConnectionPool

    Raises:
        Exception: If pool creation fails
    """
    pool_max_size = int(os.getenv("CHECKPOINT_POOL_SIZE", "10"))
    pool_min_size = int(os.getenv("CHECKPOINT_POOL_MIN_SIZE", "2"))

    logger.info(f"[{agent_name}] Creating PostgreSQL connection pool (max={pool_max_size}, min={pool_min_size})")

    pool: PostgresPool = AsyncConnectionPool(
        conninfo=conninfo,
        max_size=pool_max_size,
        min_size=pool_min_size,
        open=False,
        kwargs={"autocommit": True, "row_factory": dict_row},
    )

    await pool.open()
    logger.info(f"[{agent_name}] ✓ PostgreSQL pool created successfully")
    return pool


def _should_recreate_for_event_loop(
    metadata: CheckpointerMetadata,
    current_loop: asyncio.AbstractEventLoop | None,
    agent_name: str,
) -> bool:
    """Check if the checkpointer must be recreated because its event loop is closed.

    Async connections (Redis, psycopg) are bound to the event loop they were
    created in.  Re-using a connection after its loop has been closed raises
    ``RuntimeError: Event loop is closed``.

    Django creates a **new** event loop object for every async request and closes
    it when the response is sent.  Using loop *identity* comparison (``is not``)
    would therefore trigger a recreation on every single request — causing
    redundant connection setup on each call even when the Redis connection is
    perfectly healthy.

    The correct signal is the stored loop's ``is_closed()`` flag: once closed,
    any connections tied to it are dead and must be replaced.  Within a single
    request the loop stays open, so the cached connection is safely reused.

    Args:
        metadata: Cached checkpointer metadata.
        current_loop: Currently running event loop (unused — kept for signature
            compatibility with callers).
        agent_name: Agent name used in log messages.

    Returns:
        ``True`` if the stored loop is closed and the checkpointer must be
        recreated; ``False`` if the cached checkpointer can be reused.
    """
    stored = metadata.event_loop

    if stored is None:
        return False

    if stored.is_closed():
        logger.debug(f"[{agent_name}] Stored event loop is closed — recreating checkpointer")
        return True

    return False


async def _get_or_create_redis_checkpointer(redis_url: str, agent_name: str) -> CheckpointerType:
    """
    Get or create Redis checkpointer with event loop validation.

    Args:
        redis_url: Redis connection URL
        agent_name: Agent name for logging and caching

    Returns:
        AsyncRedisSaver checkpointer

    Raises:
        Exception: If Redis connection fails (caller should fall back to PostgreSQL)
    """
    current_loop = get_current_event_loop()

    # Check if checkpointer exists and is valid
    if agent_name in _checkpointers:
        metadata = _checkpointers[agent_name]

        # Verify event loop compatibility
        if _should_recreate_for_event_loop(metadata, current_loop, agent_name):
            # Close old checkpointer via its context manager
            if metadata.context_manager is not None:
                await _close_checkpointer_cm(metadata.context_manager, agent_name)
            del _checkpointers[agent_name]
        else:
            # Return cached checkpointer
            logger.debug(f"[{agent_name}] Reusing cached Redis checkpointer")
            return metadata.checkpointer

    # Create new checkpointer
    checkpointer, cm = await _create_redis_checkpointer(redis_url, agent_name)

    # Cache with metadata
    _checkpointers[agent_name] = CheckpointerMetadata(
        checkpointer=checkpointer,
        event_loop=current_loop,
        context_manager=cm,
    )

    return checkpointer


async def _get_or_create_postgres_checkpointer(agent_name: str) -> AsyncPostgresSaver:
    """
    Get or create PostgreSQL checkpointer with connection pool management.

    Handles event loop changes automatically.

    Args:
        agent_name: Agent name for logging and caching

    Returns:
        AsyncPostgresSaver checkpointer

    Raises:
        Exception: If database connection or pool creation fails
    """
    current_loop = get_current_event_loop()

    # Check if checkpointer/pool exists and needs recreation
    if agent_name in _checkpointers:
        metadata = _checkpointers[agent_name]

        # Check event loop compatibility
        if _should_recreate_for_event_loop(metadata, current_loop, agent_name):
            # Close old pool
            if metadata.pool:
                logger.info(f"[{agent_name}] Closing old PostgreSQL pool (event loop changed)")
                await metadata.pool.close()
            del _checkpointers[agent_name]
        else:
            # Create new checkpointer instance with existing pool
            # Note: AsyncPostgresSaver requires a fresh instance per call
            if not metadata.pool:
                logger.warning(f"[{agent_name}] Pool metadata missing, recreating")
                del _checkpointers[agent_name]
            else:
                logger.debug(f"[{agent_name}] Reusing cached PostgreSQL pool")
                checkpointer = AsyncPostgresSaver(metadata.pool)
                await checkpointer.setup()
                return checkpointer

    # Create new pool and checkpointer
    conninfo = get_postgres_connection_string("CHECKPOINT_DB_URL")
    pool = await _create_postgres_pool(agent_name, conninfo)

    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

    # Cache with metadata
    _checkpointers[agent_name] = CheckpointerMetadata(
        checkpointer=checkpointer,
        event_loop=current_loop,
        pool=pool,
    )

    logger.info(f"[{agent_name}] ✓ PostgreSQL checkpointer created successfully")
    return checkpointer


async def get_checkpointer(agent_name: str = "deep_agent") -> CheckpointerType:
    """
    Get or create a checkpointer with connection pooling for an agent.

    Tries Redis first (if configured), falls back to PostgreSQL.
    Checkpointers and pools are cached globally with automatic:
    - Event loop change detection and recreation
    - Redis connection failure fallback to PostgreSQL

    Args:
        agent_name: Name of the agent requesting the checkpointer (default: "deep_agent")

    Returns:
        AsyncRedisSaver if Redis is configured and healthy, otherwise AsyncPostgresSaver

    Raises:
        Exception: If both Redis and PostgreSQL fail to connect

    Example:
        >>> checkpointer = await get_checkpointer("my_agent")
        >>> # Use checkpointer with LangGraph StateGraph
        >>> graph = StateGraph(checkpointer=checkpointer)
    """
    # Try Redis first if configured
    redis_url = _get_redis_url()

    if redis_url:
        try:
            return await _get_or_create_redis_checkpointer(redis_url, agent_name)
        except Exception as redis_error:
            # Log Redis failure and fall back to PostgreSQL
            log_redis_fallback(agent_name, redis_error, "PostgreSQL", is_dev_environment())

    # Use PostgreSQL (either as fallback or primary)
    return await _get_or_create_postgres_checkpointer(agent_name)


async def close_all_pools() -> None:
    """
    Close all connection pools and Redis checkpointers gracefully.

    Should be called during application shutdown to release resources.

    Example:
        >>> # In Django app shutdown
        >>> await close_all_pools()
    """
    if not _checkpointers:
        logger.debug("No checkpointers to close")
        return

    logger.info(f"Closing {len(_checkpointers)} checkpointer(s)")

    for agent_name, metadata in list(_checkpointers.items()):
        try:
            # Close Redis checkpointer via its context manager
            if isinstance(metadata.checkpointer, AsyncRedisSaver):
                logger.info(f"[{agent_name}] Closing Redis checkpointer")
                if metadata.context_manager is not None:
                    await _close_checkpointer_cm(metadata.context_manager, agent_name)

            # Close PostgreSQL pool
            elif isinstance(metadata.checkpointer, AsyncPostgresSaver) and metadata.pool:
                logger.info(f"[{agent_name}] Closing PostgreSQL connection pool")
                await metadata.pool.close()

        except Exception as e:
            logger.warning(f"[{agent_name}] Error closing checkpointer: {e}")

    _checkpointers.clear()
    logger.info("✓ All checkpointers closed successfully")
