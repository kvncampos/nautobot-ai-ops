"""
Checkpoint factory utilities for LangGraph deep agents in ai-ops.

Provides reusable checkpoint configuration with connection pooling.
Supports both Redis and PostgreSQL checkpointers.

Adapted from network-agent to work with Django configuration.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Union

from django.conf import settings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# Global connection pools per agent - initialized once and reused
_connection_pools: dict[str, AsyncConnectionPool[AsyncConnection[DictRow]]] = {}

# Track when pools were created (for Azure token refresh)
_pool_creation_times: dict[str, datetime] = {}

# Global Redis checkpointers per agent - initialized once and reused
_redis_checkpointers: dict[str, AsyncRedisSaver] = {}

# Track which event loop each checkpointer/pool was created in
# This prevents "Event loop is closed" errors when Django switches event loops
_checkpointer_event_loops: dict[str, int] = {}
_pool_event_loops: dict[str, int] = {}


async def _get_connection_string_from_django(agent_name: str) -> str:
    """
    Get PostgreSQL connection string from Django settings.

    Args:
        agent_name: Name of the agent for debugging

    Returns:
        PostgreSQL connection string

    Raises:
        ValueError: If DATABASE_URL or Django database config is missing
    """
    logger.debug(f"[{agent_name}] Getting connection string from Django settings")

    # Try to get from environment first (for docker-compose)
    import os

    db_url = os.getenv("DATABASE_URL")

    if db_url:
        logger.debug(f"[{agent_name}] Using DATABASE_URL from environment")
        return db_url

    # Otherwise, construct from Django settings
    db_config = settings.DATABASES.get("default", {})

    if not db_config:
        raise ValueError("No default database configured in Django settings")

    # Extract database configuration
    host = db_config.get("HOST", "localhost")
    port = db_config.get("PORT", 5432)
    name = db_config.get("NAME", "nautobot")
    user = db_config.get("USER", "nautobot")
    password = db_config.get("PASSWORD", "")

    # Build connection string
    # Note: For Azure AD auth, password would be the access token
    conninfo = f"postgresql://{user}:{password}@{host}:{port}/{name}?sslmode=require"

    logger.debug(f"[{agent_name}] Built connection string from Django: host={host}, port={port}, db={name}")

    return conninfo


async def get_checkpointer(agent_name: str = "deep_agent") -> Union[AsyncRedisSaver, AsyncPostgresSaver]:
    """
    Get or create a checkpointer with connection pooling for an agent.

    Returns AsyncRedisSaver if CHECKPOINT_REDIS_URL or REDIS_URL is set,
    otherwise AsyncPostgresSaver.
    Connection pools/checkpointers are cached globally to ensure persistence
    during streaming operations.

    Args:
        agent_name: Name of the agent requesting the checkpointer

    Returns:
        Union[AsyncRedisSaver, AsyncPostgresSaver]: Configured checkpointer

    Raises:
        Exception: If database/Redis connection or checkpointer setup fails
    """
    import os

    # Get TTL configuration from Django settings or environment
    default_ttl = int(os.getenv("CHECKPOINT_TTL", "3600"))  # 1 hour default

    # Check if we're in dev/local environment
    is_dev = os.getenv("NAUTOBOT_DEBUG", "false").lower() in ("true", "1", "yes")

    # Configure automatic expiration
    ttl_config = {
        "default_ttl": default_ttl // 60,  # Convert to minutes for Redis
        "refresh_on_read": True,  # Reset expiration time when reading checkpoints
    }

    # Try CHECKPOINT_REDIS_URL first, then fall back to REDIS_URL
    redis_url = os.getenv("CHECKPOINT_REDIS_URL") or os.getenv("REDIS_URL")

    # Use Redis if REDIS_URL is configured
    if redis_url:
        # Check if we need to recreate checkpointer due to event loop change
        try:
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
        except RuntimeError:
            current_loop_id = None

        # Get or create Redis checkpointer for this agent
        if agent_name not in _redis_checkpointers:
            logger.info(f"[{agent_name}] Creating new AsyncRedisSaver with TTL={default_ttl}s")

            # Create Redis checkpointer with connection string
            try:
                checkpointer = AsyncRedisSaver(redis_url, ttl=ttl_config)
                await checkpointer.asetup()

                _redis_checkpointers[agent_name] = checkpointer
                _checkpointer_event_loops[agent_name] = current_loop_id
                logger.info(f"[{agent_name}] ✓ Redis checkpointer created successfully")
                return _redis_checkpointers[agent_name]
            except Exception as redis_error:
                error_msg = str(redis_error)
                is_auth_error = "Authentication required" in error_msg or "WRONGPASS" in error_msg

                if is_dev and is_auth_error:
                    logger.info(
                        f"[{agent_name}] Redis auth failed in DEV environment ({type(redis_error).__name__}). "
                        f"Falling back to PostgreSQL checkpointer."
                    )
                    # Fall through to PostgreSQL below
                else:
                    logger.warning(
                        f"[{agent_name}] ✗ Redis checkpointer failed ({type(redis_error).__name__}): {error_msg[:200]}. "
                        f"Falling back to PostgreSQL checkpointer."
                    )
                    # Fall through to PostgreSQL below
        else:
            # Checkpointer exists - verify it's compatible with current event loop
            stored_loop_id = _checkpointer_event_loops.get(agent_name)
            if stored_loop_id is not None and current_loop_id is not None and stored_loop_id != current_loop_id:
                logger.warning(
                    f"[{agent_name}] Event loop changed (old={stored_loop_id}, new={current_loop_id}). "
                    f"Recreating Redis checkpointer to prevent 'Event loop is closed' errors."
                )
                # Close old checkpointer
                try:
                    if hasattr(_redis_checkpointers[agent_name], "_redis"):
                        await _redis_checkpointers[agent_name]._redis.aclose()
                except Exception as close_error:
                    logger.debug(f"[{agent_name}] Error closing old checkpointer: {close_error}")

                # Recreate checkpointer with new event loop
                try:
                    checkpointer = AsyncRedisSaver(redis_url, ttl=ttl_config)
                    await checkpointer.asetup()
                    _redis_checkpointers[agent_name] = checkpointer
                    _checkpointer_event_loops[agent_name] = current_loop_id
                    logger.info(f"[{agent_name}] ✓ Redis checkpointer recreated for new event loop")
                except Exception as redis_error:
                    logger.warning(f"[{agent_name}] Failed to recreate Redis checkpointer: {redis_error}")
                    # Fall through to PostgreSQL below
                    # Remove failed checkpointer from cache
                    del _redis_checkpointers[agent_name]
                    del _checkpointer_event_loops[agent_name]
                else:
                    return _redis_checkpointers[agent_name]
            else:
                # Event loop hasn't changed, return cached checkpointer
                return _redis_checkpointers[agent_name]

    # Fall back to PostgreSQL
    # Check if using Azure service principal authentication
    auth_method = os.environ.get("DB_AUTH_METHOD", "basic").lower()

    # Get current event loop for pool binding check
    try:
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)
    except RuntimeError:
        current_loop_id = None

    # Check if pool needs to be recreated due to event loop change
    if agent_name in _connection_pools:
        stored_loop_id = _pool_event_loops.get(agent_name)
        if stored_loop_id is not None and current_loop_id is not None and stored_loop_id != current_loop_id:
            logger.warning(
                f"[{agent_name}] Event loop changed for connection pool (old={stored_loop_id}, new={current_loop_id}). "
                f"Recreating pool to prevent 'Event loop is closed' errors."
            )
            # Close old pool
            try:
                await _connection_pools[agent_name].close()
            except Exception as close_error:
                logger.debug(f"[{agent_name}] Error closing old connection pool: {close_error}")
            del _connection_pools[agent_name]
            if agent_name in _pool_creation_times:
                del _pool_creation_times[agent_name]
            if agent_name in _pool_event_loops:
                del _pool_event_loops[agent_name]

    # For Azure auth, check if pool needs to be recreated due to token expiry
    if auth_method == "service_principal" and agent_name in _connection_pools:
        pool_age = datetime.now() - _pool_creation_times.get(agent_name, datetime.now())
        # Recreate pool after 45 minutes (before 1 hour token expiry)
        if pool_age > timedelta(minutes=45):
            logger.info(f"[{agent_name}] Pool is {pool_age} old, recreating with fresh Azure AD token")
            # Close old pool
            await _connection_pools[agent_name].close()
            del _connection_pools[agent_name]
            del _pool_creation_times[agent_name]
            if agent_name in _pool_event_loops:
                del _pool_event_loops[agent_name]

    # Get or create connection pool for this agent
    if agent_name not in _connection_pools:
        logger.info(f"[{agent_name}] Creating new AsyncPostgresConnectionPool")

        # Get database connection string from Django
        conninfo = await _get_connection_string_from_django(agent_name)

        # Get pool size from environment or use defaults
        pool_max_size = int(os.getenv("CHECKPOINT_POOL_SIZE", "10"))
        pool_min_size = int(os.getenv("CHECKPOINT_POOL_MIN_SIZE", "2"))

        # Create pool
        pool: AsyncConnectionPool[AsyncConnection[DictRow]] = AsyncConnectionPool(
            conninfo=conninfo,
            max_size=pool_max_size,
            min_size=pool_min_size,
            open=False,
            kwargs={"autocommit": True, "row_factory": dict_row},
        )

        if auth_method == "service_principal":
            # Track creation time for token refresh
            _pool_creation_times[agent_name] = datetime.now()
            logger.info(f"[{agent_name}] Using Azure service principal with automatic token refresh")

        await pool.open()
        _connection_pools[agent_name] = pool
        _pool_event_loops[agent_name] = current_loop_id  # Track event loop binding

        logger.info(
            f"[{agent_name}] AsyncPostgresConnection pool created: max_size={pool_max_size}, min_size={pool_min_size}"
        )

    # Create and setup checkpointer with the pool
    checkpointer = AsyncPostgresSaver(_connection_pools[agent_name])
    await checkpointer.setup()

    return checkpointer


async def close_all_pools():
    """
    Close all connection pools and Redis checkpointers gracefully.

    Should be called during application shutdown.
    """
    # Close Redis checkpointers
    for agent_name, checkpointer in _redis_checkpointers.items():
        logger.info(f"[{agent_name}] Closing Redis checkpointer")
        # Close the Redis connection
        if hasattr(checkpointer, "_redis"):
            await checkpointer._redis.aclose()

    _redis_checkpointers.clear()
    _checkpointer_event_loops.clear()

    # Close PostgreSQL connection pools
    for agent_name, pool in _connection_pools.items():
        logger.info(f"[{agent_name}] Closing AsyncPostgresConnection pool")
        await pool.close()

    _connection_pools.clear()
    _pool_creation_times.clear()
    _pool_event_loops.clear()
    logger.info("All checkpointer pools closed successfully")
