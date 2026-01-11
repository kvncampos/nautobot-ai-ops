"""LangGraph checkpointing configuration.

This module provides short-term memory (conversation history) using MemorySaver.
Conversation history is stored in memory and will be lost on application restart.

Note: Redis checkpointing requires Redis Stack with RediSearch module.
For persistent storage in production, use langgraph-checkpoint-postgres.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import redis

from ai_ops.helpers.common.asyncio_utils import get_or_create_event_loop_lock

logger = logging.getLogger(__name__)

# Global singleton MemorySaver instance for conversation persistence
_memory_saver_instance = None
# Use list to allow modification via get_or_create_event_loop_lock
_memory_saver_lock: list = [None]
# Global dict to track checkpoint creation timestamps for TTL enforcement
_checkpoint_timestamps = {}


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
    from langgraph.checkpoint.memory import MemorySaver

    global _memory_saver_instance

    lock = get_or_create_event_loop_lock(_memory_saver_lock, "memory_saver_lock")

    # Use singleton pattern to maintain conversation history across requests
    try:
        async with lock:
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
    global _memory_saver_instance, _checkpoint_timestamps

    if _memory_saver_instance is None:
        logger.warning("No MemorySaver instance exists to clear")
        return False

    try:
        # MemorySaver stores checkpoints in a dict keyed by tuples like (thread_id,)
        # We can access the storage directly to clear a specific thread
        config = {"configurable": {"thread_id": thread_id}}

        # Get current state to check if thread exists
        # Type ignore: LangGraph accepts dict config but types show RunnableConfig
        state = await _memory_saver_instance.aget(config)  # type: ignore[arg-type]

        if state is None:
            logger.debug(f"No conversation history found for thread {thread_id}")
            return False

        # Clear by removing from storage
        # MemorySaver stores data with tuple keys like (thread_id,)
        if hasattr(_memory_saver_instance, "storage"):
            logger.debug(f"Storage keys before clearing: {list(_memory_saver_instance.storage.keys())}")

            # Create the thread key tuple - MemorySaver uses tuples for storage keys
            thread_key = (thread_id,)
            
            # Clear all keys associated with this thread
            # MemorySaver may have multiple keys per thread for different checkpoint IDs
            cleared = False
            keys_to_delete = []
            for key in list(_memory_saver_instance.storage.keys()):
                # Keys are tuples like (thread_id,) or (thread_id, checkpoint_id, ...)
                if isinstance(key, tuple) and len(key) > 0 and key[0] == thread_id:
                    keys_to_delete.append(key)
            
            # Delete all matching keys
            for key in keys_to_delete:
                del _memory_saver_instance.storage[key]
                cleared = True
                logger.debug(f"Cleared storage key: {key}")
            
            # Also remove timestamp tracking
            if thread_key in _checkpoint_timestamps:
                del _checkpoint_timestamps[thread_key]

            if cleared:
                logger.info(f"Cleared checkpoint storage for thread {thread_id} ({len(keys_to_delete)} keys)")
                logger.debug(f"Storage keys after clearing: {list(_memory_saver_instance.storage.keys())}")
                return True
            else:
                logger.warning(
                    f"Thread {thread_id} not found in storage keys: {list(_memory_saver_instance.storage.keys())}"
                )
                return False

        logger.warning(f"Could not access storage to clear thread {thread_id}")
        return False

    except RuntimeError as e:
        if "cannot schedule new futures after interpreter shutdown" in str(e):
            logger.warning(f"Cannot clear thread {thread_id} during interpreter shutdown: {e}")
            # During shutdown, we can still try to clear from memory directly if available
            if hasattr(_memory_saver_instance, "storage"):
                cleared = False
                keys_to_delete = []
                for key in list(_memory_saver_instance.storage.keys()):
                    if isinstance(key, tuple) and len(key) > 0 and key[0] == thread_id:
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    del _memory_saver_instance.storage[key]
                    cleared = True
                
                thread_key = (thread_id,)
                if thread_key in _checkpoint_timestamps:
                    del _checkpoint_timestamps[thread_key]

                if cleared:
                    logger.info(f"Force-cleared checkpoint for thread {thread_id} during shutdown")
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
    from langgraph.checkpoint.memory import MemorySaver

    global _memory_saver_instance, _checkpoint_timestamps

    lock = get_or_create_event_loop_lock(_memory_saver_lock, "memory_saver_lock")

    async with lock:
        if _memory_saver_instance is None:
            logger.info("No MemorySaver instance to reset")
            return 0

        # Count threads before clearing
        thread_count = 0
        if hasattr(_memory_saver_instance, "storage"):
            thread_count = len(_memory_saver_instance.storage)

        # Create new instance
        _memory_saver_instance = MemorySaver()
        _checkpoint_timestamps.clear()
        logger.info(f"Reset MemorySaver checkpointer, cleared {thread_count} thread(s)")
        return thread_count


def track_checkpoint_creation(thread_id: str):
    """Track when a checkpoint is created for TTL enforcement.

    Args:
        thread_id: The thread identifier being tracked
    """
    global _checkpoint_timestamps
    thread_key = (thread_id,)
    _checkpoint_timestamps[thread_key] = datetime.now()
    logger.debug(f"Tracked checkpoint creation for thread {thread_id}")


def cleanup_expired_checkpoints(ttl_minutes: int = 5) -> dict:
    """Clean up checkpoints older than the specified TTL.

    This function scans all checkpoints and removes those older than the TTL
    plus a 30-second grace period to prevent race conditions with the frontend.
    
    When checkpoints are deleted, it also clears the middleware cache to ensure
    stateful middleware instances (e.g., summarization buffers) are also removed.

    Args:
        ttl_minutes: Time-to-live in minutes (default: 5)

    Returns:
        dict: Cleanup results with processed/deleted counts
    """
    global _memory_saver_instance, _checkpoint_timestamps

    if _memory_saver_instance is None:
        logger.warning("No MemorySaver instance exists for cleanup")
        return {
            "success": False,
            "processed_count": 0,
            "deleted_count": 0,
            "error": "No MemorySaver instance",
        }

    try:
        now = datetime.now()
        grace_period = timedelta(seconds=30)
        ttl_threshold = timedelta(minutes=ttl_minutes) + grace_period

        deleted_count = 0
        processed_count = 0

        if not hasattr(_memory_saver_instance, "storage"):
            logger.warning("MemorySaver instance has no storage attribute")
            return {
                "success": False,
                "processed_count": 0,
                "deleted_count": 0,
                "error": "No storage attribute",
            }

        # Get list of thread keys to process (copy to avoid modification during iteration)
        thread_keys = list(_memory_saver_instance.storage.keys())

        for thread_key in thread_keys:
            processed_count += 1

            # Check if we have timestamp for this thread
            if thread_key in _checkpoint_timestamps:
                checkpoint_age = now - _checkpoint_timestamps[thread_key]

                if checkpoint_age > ttl_threshold:
                    # Remove expired checkpoint
                    del _memory_saver_instance.storage[thread_key]
                    del _checkpoint_timestamps[thread_key]
                    deleted_count += 1
                    logger.info(f"Removed expired checkpoint {thread_key} (age: {checkpoint_age})")
            else:
                # No timestamp - assume it was created now to give it full TTL
                _checkpoint_timestamps[thread_key] = now
                logger.debug(f"Added timestamp for existing checkpoint {thread_key}")

        # Clear middleware cache if any checkpoints were deleted
        # This ensures stateful middleware instances are also removed
        if deleted_count > 0:
            try:
                # Import here to avoid circular dependencies
                # Use asyncio to run the async clear function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    from ai_ops.helpers.get_middleware import clear_middleware_cache
                    loop.run_until_complete(clear_middleware_cache())
                    logger.info(f"Cleared middleware cache after removing {deleted_count} expired checkpoints")
                finally:
                    loop.close()
            except Exception as e:
                logger.warning(f"Failed to clear middleware cache during checkpoint cleanup: {e}")
                # Don't fail the entire cleanup if middleware cache clear fails

        logger.info(
            f"Checkpoint cleanup completed: processed {processed_count} checkpoints, "
            f"deleted {deleted_count} expired checkpoints (TTL: {ttl_minutes} minutes)"
        )

        return {
            "success": True,
            "processed_count": processed_count,
            "deleted_count": deleted_count,
            "ttl_minutes": ttl_minutes,
        }

    except Exception as e:
        logger.error(f"Error during checkpoint cleanup: {e}", exc_info=True)
        return {
            "success": False,
            "processed_count": 0,
            "deleted_count": 0,
            "error": str(e),
        }


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
