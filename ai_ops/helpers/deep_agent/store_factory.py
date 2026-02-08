"""
Memory store factory utilities for LangGraph deep agents in ai-ops.
Provides reusable memory store configuration for cross-conversation memory.
Supports both Redis and InMemory stores.

Adapted from network-agent to work with Django configuration.
"""

import asyncio
import logging
import os
from typing import Union

from langgraph.store.memory import InMemoryStore
from langgraph.store.redis.aio import AsyncRedisStore

logger = logging.getLogger(__name__)

# Global Redis stores per agent - initialized once and reused
_redis_stores: dict[str, AsyncRedisStore] = {}

# Global in-memory stores per agent - initialized once and reused
_memory_stores: dict[str, InMemoryStore] = {}

# Track which event loop each store was created in
# This prevents "Event loop is closed" errors when Django switches event loops
_store_event_loops: dict[str, int] = {}


async def get_store(agent_name: str = "deep_agent") -> Union[AsyncRedisStore, InMemoryStore]:
    """
    Get or create a memory store for an agent.

    Returns AsyncRedisStore if STORE_REDIS_URL or REDIS_URL is set, otherwise InMemoryStore.
    Stores are cached globally to ensure persistence during agent execution.

    In dev/local environments, automatically falls back to InMemoryStore if Redis auth fails.

    Args:
        agent_name: Name of the agent requesting the store

    Returns:
        Union[AsyncRedisStore, InMemoryStore]: Configured memory store

    Raises:
        Exception: If Redis connection or store setup fails
    """
    # Check if we're in dev/local environment
    is_dev = os.getenv("NAUTOBOT_DEBUG", "false").lower() in ("true", "1", "yes")

    # Try STORE_REDIS_URL first (dedicated for Store), then fall back to REDIS_URL
    redis_url = os.getenv("STORE_REDIS_URL") or os.getenv("REDIS_URL")

    # Get current event loop for store binding check
    try:
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)
    except RuntimeError:
        current_loop_id = None

    # Use Redis if REDIS_URL is configured
    if redis_url:
        # Get or create Redis store for this agent
        if agent_name not in _redis_stores:
            logger.info(f"[{agent_name}] Creating new AsyncRedisStore for cross-conversation memory")

            # Create Redis store with connection string
            try:
                store = AsyncRedisStore(redis_url)
                await store.setup()

                _redis_stores[agent_name] = store
                _store_event_loops[agent_name] = current_loop_id
                logger.info(f"[{agent_name}] ✓ Redis store created successfully")
                return _redis_stores[agent_name]
            except Exception as redis_error:
                error_msg = str(redis_error)
                is_auth_error = "Authentication required" in error_msg or "WRONGPASS" in error_msg

                if is_dev and is_auth_error:
                    logger.info(
                        f"[{agent_name}] Redis auth failed in DEV environment ({type(redis_error).__name__}). "
                        f"Using InMemoryStore instead."
                    )
                    # Fall through to InMemoryStore
                else:
                    logger.warning(
                        f"[{agent_name}] ✗ Redis store failed ({type(redis_error).__name__}): {error_msg[:200]}. "
                        f"Falling back to InMemoryStore."
                    )
                    # Fall through to InMemoryStore
        else:
            # Store exists - verify it's compatible with current event loop
            stored_loop_id = _store_event_loops.get(agent_name)
            if stored_loop_id is not None and current_loop_id is not None and stored_loop_id != current_loop_id:
                logger.warning(
                    f"[{agent_name}] Event loop changed for store (old={stored_loop_id}, new={current_loop_id}). "
                    f"Recreating Redis store to prevent 'Event loop is closed' errors."
                )
                # Close old store
                try:
                    if hasattr(_redis_stores[agent_name], "_redis"):
                        await _redis_stores[agent_name]._redis.aclose()
                except Exception as close_error:
                    logger.debug(f"[{agent_name}] Error closing old store: {close_error}")

                # Recreate store with new event loop
                try:
                    store = AsyncRedisStore(redis_url)
                    await store.setup()
                    _redis_stores[agent_name] = store
                    _store_event_loops[agent_name] = current_loop_id
                    logger.info(f"[{agent_name}] ✓ Redis store recreated for new event loop")
                except Exception as redis_error:
                    logger.warning(f"[{agent_name}] Failed to recreate Redis store: {redis_error}")
                    # Fall through to InMemoryStore below
                    # Remove failed store from cache
                    del _redis_stores[agent_name]
                    del _store_event_loops[agent_name]
                else:
                    return _redis_stores[agent_name]
            else:
                # Event loop hasn't changed, return cached store
                return _redis_stores[agent_name]

    # Fall back to InMemoryStore (not persistent across restarts)
    if agent_name not in _memory_stores:
        logger.warning(
            f"[{agent_name}] No Redis URL configured - using InMemoryStore (memory will not persist across restarts)"
        )

        store = InMemoryStore()
        _memory_stores[agent_name] = store

        logger.info(f"[{agent_name}] InMemoryStore created successfully")

    return _memory_stores[agent_name]


async def close_all_stores():
    """
    Close all Redis stores gracefully.
    Should be called during application shutdown.
    """
    # Close Redis stores
    for agent_name, store in _redis_stores.items():
        logger.info(f"[{agent_name}] Closing Redis store")
        # Close the Redis connection
        if hasattr(store, "_redis"):
            await store._redis.aclose()

    _redis_stores.clear()
    _store_event_loops.clear()

    # Clear in-memory stores
    _memory_stores.clear()

    logger.info("All memory stores closed successfully")
