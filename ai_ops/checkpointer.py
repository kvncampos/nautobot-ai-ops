"""LangGraph checkpointing configuration.

This module provides short-term memory (conversation history) using MemorySaver.
Conversation history is stored in memory and will be lost on application restart.

Note: Redis checkpointing requires Redis Stack with RediSearch module.
For persistent storage in production, use langgraph-checkpoint-postgres.
"""

import logging
import os
from contextlib import asynccontextmanager

import redis

logger = logging.getLogger(__name__)

# Global singleton MemorySaver instance for conversation persistence
_memory_saver_instance = None
_memory_saver_lock = None


def get_redis_uri() -> str:
    """Build Redis URI from environment variables.

    Uses the existing Redis infrastructure configured for Nautobot's cache/Celery,
    but with a separate database number to isolate LangGraph checkpoints.

    Returns:
        str: Redis connection URI in format redis://[:password@]host:port/database
    """
    host = os.getenv("NAUTOBOT_REDIS_HOST", "localhost")
    port = os.getenv("NAUTOBOT_REDIS_PORT", "6379")
    password = os.getenv("NAUTOBOT_REDIS_PASSWORD", "")
    # Use separate database for LangGraph checkpoints
    # DB 0: Django cache, DB 1: Celery, DB 2: LangGraph
    database = os.getenv("LANGGRAPH_REDIS_DB", "2")

    if password:
        return f"redis://:{password}@{host}:{port}/{database}"
    return f"redis://{host}:{port}/{database}"


def get_redis_connection() -> redis.Redis:
    """Get a synchronous Redis connection for maintenance tasks.

    This provides a direct Redis client for tasks like cleanup operations
    that need to scan and manage checkpoint keys directly.

    Returns:
        redis.Redis: Synchronous Redis client instance

    Note:
        This is separate from the async RedisSaver used by LangGraph.
        Use this for maintenance/cleanup tasks that run in Celery workers.
    """
    host = os.getenv("NAUTOBOT_REDIS_HOST", "localhost")
    port = os.getenv("NAUTOBOT_REDIS_PORT", "6379")
    password = os.getenv("NAUTOBOT_REDIS_PASSWORD", "")
    database = os.getenv("LANGGRAPH_REDIS_DB", "2")

    return redis.Redis(
        host=host,
        port=int(port),
        db=int(database),
        password=password if password else None,
        decode_responses=True,
    )


@asynccontextmanager
async def get_checkpointer():
    """Get MemorySaver checkpointer as an async context manager with singleton pattern.

    Uses a global singleton MemorySaver instance to maintain conversation history
    across requests during the application lifecycle. This is non-persistent,
    meaning conversation history will be lost when the application restarts.

    The singleton pattern ensures that all requests share the same MemorySaver,
    allowing conversation history to be maintained between requests using the
    same thread_id (session key).

    Example usage:
        async with get_checkpointer() as checkpointer:
            graph = workflow.compile(checkpointer=checkpointer)
            result = await graph.ainvoke(...)

    Yields:
        MemorySaver: Singleton in-memory checkpointer instance

    Note:
        To enable persistent storage with Redis, you need Redis Stack which includes
        the RediSearch module. Install via:
        - Docker: redis/redis-stack-server image
        - Package: redis-stack-server (includes Redis + modules)

        For production, consider using langgraph-checkpoint-postgres instead.
    """
    import asyncio

    from langgraph.checkpoint.memory import MemorySaver

    global _memory_saver_instance, _memory_saver_lock

    # Initialize lock on first access
    if _memory_saver_lock is None:
        _memory_saver_lock = asyncio.Lock()

    # Use singleton pattern to maintain conversation history across requests
    try:
        async with _memory_saver_lock:
            if _memory_saver_instance is None:
                logger.info("Initializing singleton LangGraph MemorySaver checkpointer")
                _memory_saver_instance = MemorySaver()
            else:
                logger.debug("Reusing existing MemorySaver checkpointer instance")

        try:
            yield _memory_saver_instance
        finally:
            logger.debug("MemorySaver checkpointer request complete")

    except RuntimeError as e:
        if "cannot schedule new futures after interpreter shutdown" in str(e):
            logger.warning(f"Cannot access checkpointer during interpreter shutdown: {e}")
            # Return a None checkpointer during shutdown to prevent further errors
            yield None
        else:
            raise


async def clear_checkpointer_for_thread(thread_id: str) -> bool:
    """Clear conversation history for a specific thread.

    Args:
        thread_id: The thread identifier to clear

    Returns:
        bool: True if thread was cleared, False if thread not found or error occurred
    """
    global _memory_saver_instance

    if _memory_saver_instance is None:
        logger.warning("No MemorySaver instance exists to clear")
        return False

    try:
        # MemorySaver stores checkpoints in a dict keyed by thread_id
        # We can access the storage directly to clear a specific thread
        config = {"configurable": {"thread_id": thread_id}}

        # Get current state to check if thread exists
        state = await _memory_saver_instance.aget(config)

        if state is None:
            logger.debug(f"No conversation history found for thread {thread_id}")
            return False

        # Clear by removing from storage
        # Note: MemorySaver doesn't have a delete method, so we need to access storage directly
        if hasattr(_memory_saver_instance, "storage"):
            thread_key = (thread_id,)  # MemorySaver uses tuple key
            if thread_key in _memory_saver_instance.storage:
                del _memory_saver_instance.storage[thread_key]
                logger.info(f"Cleared conversation history for thread {thread_id}")
                return True

        logger.warning(f"Could not access storage to clear thread {thread_id}")
        return False

    except RuntimeError as e:
        if "cannot schedule new futures after interpreter shutdown" in str(e):
            logger.warning(f"Cannot clear thread {thread_id} during interpreter shutdown: {e}")
            # During shutdown, we can still try to clear from memory directly if available
            if hasattr(_memory_saver_instance, "storage"):
                thread_key = (thread_id,)
                if thread_key in _memory_saver_instance.storage:
                    del _memory_saver_instance.storage[thread_key]
                    logger.info(f"Force-cleared conversation history for thread {thread_id} during shutdown")
                    return True
            return False
        else:
            logger.error(f"Runtime error clearing checkpointer for thread {thread_id}: {e}", exc_info=True)
            return False
    except Exception as e:
        logger.error(f"Error clearing checkpointer for thread {thread_id}: {e}", exc_info=True)
        return False


async def reset_checkpointer() -> int:
    """Reset the entire checkpointer, clearing all conversation histories.

    This is useful for testing or administrative cleanup. In production,
    prefer clearing individual threads rather than resetting everything.

    Returns:
        int: Number of threads that were cleared
    """
    import asyncio

    global _memory_saver_instance, _memory_saver_lock

    if _memory_saver_lock is None:
        _memory_saver_lock = asyncio.Lock()

    async with _memory_saver_lock:
        if _memory_saver_instance is None:
            logger.info("No MemorySaver instance to reset")
            return 0

        # Count threads before clearing
        thread_count = 0
        if hasattr(_memory_saver_instance, "storage"):
            thread_count = len(_memory_saver_instance.storage)

        # Create new instance
        from langgraph.checkpoint.memory import MemorySaver

        _memory_saver_instance = MemorySaver()
        logger.info(f"Reset MemorySaver checkpointer, cleared {thread_count} thread(s)")
        return thread_count


# TODO: Migrate to persistent checkpointing for production
# Currently using MemorySaver which loses conversation history on restart.
#
# Option 1: Redis Stack with RediSearch (recommended for caching layer)
# - Update docker-compose.yml to use: redis/redis-stack-server:latest
# - Or install redis-stack-server package on host
# - Then replace get_checkpointer() implementation with:
#
#   @asynccontextmanager
#   async def get_checkpointer():
#       from langgraph.checkpoint.redis import RedisSaver
#       uri = get_redis_uri()
#       with RedisSaver.from_conn_string(uri) as checkpointer:
#           checkpointer.setup()
#           try:
#               yield checkpointer
#           finally:
#               logger.debug("Redis checkpointer connection closed")
#
# Option 2: PostgreSQL (recommended for production)
# - Add dependency: langgraph-checkpoint-postgres
# - Use AsyncPostgresSaver with Nautobot's existing PostgreSQL database
# - Reference: https://langchain-ai.github.io/langgraph/how-tos/persistence_postgres/
#
# Implementation decision factors:
# - Redis Stack: Fast, good for high-volume chat, requires Redis Stack installation
# - PostgreSQL: Uses existing infrastructure, better for audit/compliance, slightly slower


# TODO: Implement long-term memory (Store) for cross-conversation memory
# This will be added in a future version when we store conversation logs in the database.
# Reference: https://docs.langchain.com/oss/python/langgraph/add-memory#example-using-redis-store
#
# Future implementation pattern:
# @asynccontextmanager
# async def get_store():
#     """Get Redis store for long-term memory across conversations."""
#     from langgraph.store.redis import RedisStore
#     uri = get_redis_uri()
#     store = RedisStore.from_conn_string(uri)
#     await store.setup()
#     try:
#         yield store
#     finally:
#         await store.aclose()
