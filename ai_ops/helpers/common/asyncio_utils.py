"""Asyncio utility functions for event loop management.

This module provides utilities for managing asyncio primitives across
different event loops, which is necessary in Django async views where
each request may create a new event loop.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_or_create_event_loop_lock(lock_ref: list[Optional[asyncio.Lock]], lock_name: str = "lock") -> asyncio.Lock:
    """Get or create an asyncio.Lock bound to the current event loop.

    Django's async views can create new event loops for each request,
    causing locks created in one event loop to fail when accessed from another.
    This helper ensures we always have a lock bound to the current event loop.

    Args:
        lock_ref: List containing single lock reference (mutable container).
                  Use a list to allow modification of module-level reference.
                  Example: _lock = [None]
        lock_name: Name for logging purposes (default: "lock")

    Returns:
        asyncio.Lock: A lock bound to the current event loop

    Example:
        >>> _cache_lock = [None]
        >>> lock = get_or_create_event_loop_lock(_cache_lock, "cache_lock")
        >>> async with lock:
        ...     # Critical section
    """
    try:
        # Get current running loop
        loop = asyncio.get_running_loop()

        # Create new lock if none exists
        if not lock_ref or lock_ref[0] is None:
            lock_ref[0] = asyncio.Lock()
            logger.debug(f"Created new asyncio.Lock: {lock_name}")
            return lock_ref[0]

        # Check if existing lock is bound to current loop
        # _loop is a private attribute but necessary for event loop detection
        if hasattr(lock_ref[0], "_loop") and lock_ref[0]._loop is not loop:  # type: ignore[attr-defined]
            logger.debug(f"Recreating {lock_name} for new event loop")
            lock_ref[0] = asyncio.Lock()

        return lock_ref[0]

    except RuntimeError:
        # No running loop - just create/return lock
        if not lock_ref or lock_ref[0] is None:
            lock_ref[0] = asyncio.Lock()
            logger.debug(f"Created new asyncio.Lock without running loop: {lock_name}")
        return lock_ref[0]

    except Exception as e:
        logger.warning(f"Error managing {lock_name}, recreating: {e}")
        lock_ref[0] = asyncio.Lock()
        return lock_ref[0]
