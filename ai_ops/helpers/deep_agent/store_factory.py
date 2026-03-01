"""Memory store factory for LangGraph deep agents in ai-ops.

Hierarchy (controlled by ``STORE_BACKEND`` env var):

1. ``postgres`` — AsyncPostgresStore (default auto-mode primary; persistent, no Redis modules needed)
2. ``redis``    — AsyncRedisStore    (auto-mode fallback, or when STORE_BACKEND=redis)
3. ``memory``   — InMemoryStore      (last-resort fallback; data lost on restart)

The store deliberately favours PostgreSQL over Redis in auto-mode because:
- PostgreSQL needs no special modules (unlike Redis Stack's RediSearch requirement).
- The checkpointer already owns Redis for short-term thread state; keeping the
  long-term memory store on Postgres avoids competing on the same Redis instance.
- Redis is still available via ``STORE_BACKEND=redis`` for explicit opt-in.

When ``STORE_BACKEND`` is unset the factory auto-selects in order:
  • Postgres → if a Postgres connection string resolves and setup succeeds
  • Redis    → automatic fallback if Postgres is unavailable
  • memory   → automatic last-resort if both above fail

Setting ``STORE_BACKEND=memory`` disables Redis/Postgres entirely and jumps
directly to InMemoryStore (useful in local dev with no database).

Example:
    >>> store = await get_store("my_agent")
    >>> await close_all_stores()  # On shutdown

    >>> # Or use context manager:
    >>> async with managed_store("my_agent") as store:
    ...     pass

Note:
    - Stores are cached globally per agent_name.
    - Not thread-safe: use from async contexts only.
    - Automatically handles Django event-loop switching.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from langgraph.store.memory import InMemoryStore
from langgraph.store.postgres.aio import AsyncPostgresStore
from langgraph.store.redis.aio import AsyncRedisStore

from ._utils import (
    get_current_event_loop,
    get_postgres_connection_string,
    get_redis_url,
    is_dev_environment,
    log_redis_fallback,
)

logger = logging.getLogger(__name__)

# All supported backend types
StoreType = AsyncRedisStore | AsyncPostgresStore | InMemoryStore

# Valid STORE_BACKEND values
_BACKEND_REDIS = "redis"
_BACKEND_POSTGRES = "postgres"
_BACKEND_MEMORY = "memory"


@dataclass
class StoreMetadata:
    """Tracks a store instance alongside its owning event loop.

    Attributes:
        store: The active store instance.
        event_loop: Event loop that created the store, used to detect loop
            replacement and trigger recreation.
        context_manager: The async context manager returned by ``from_conn_string()``.
            Must be exited via ``__aexit__`` on cleanup; ``None`` for InMemoryStore.
    """

    store: StoreType
    event_loop: asyncio.AbstractEventLoop | None
    context_manager: Any | None = None


# Global store cache per agent_name
_stores: dict[str, StoreMetadata] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_store_backend() -> str | None:
    """Return the explicit STORE_BACKEND override, normalised to lowercase.

    Valid values: ``redis``, ``postgres``, ``memory``.

    Returns:
        The backend name string, or ``None`` when the variable is unset
        (triggers auto-select mode).
    """
    val = os.getenv("STORE_BACKEND", "").strip().lower()
    return val if val else None


def _get_redis_url() -> str | None:
    """Get Redis URL, preferring ``STORE_REDIS_URL`` over ``REDIS_URL``.

    Returns:
        Redis connection URL string, or ``None`` if not configured.
    """
    return get_redis_url("STORE_REDIS_URL")


# ---------------------------------------------------------------------------
# Redis store
# ---------------------------------------------------------------------------


async def _create_redis_store(redis_url: str, agent_name: str) -> tuple[AsyncRedisStore, Any]:
    """Create and set up a Redis store via the documented ``from_conn_string`` API.

    ``from_conn_string()`` returns an async context manager.  We enter it with
    ``__aenter__()`` to obtain the live store object, and return the context
    manager so the caller can exit it (``__aexit__``) on cleanup.

    Args:
        redis_url: Full Redis connection URL (e.g. ``redis://host:6379/0``).
        agent_name: Agent identifier used in log messages.

    Returns:
        Tuple of (configured AsyncRedisStore, context manager for cleanup).

    Raises:
        Exception: On connection failure or index-creation error.
    """
    logger.info(f"[{agent_name}] Creating AsyncRedisStore via from_conn_string")

    # AsyncRedisStore.from_conn_string() already calls store.setup() internally
    # before yielding (see langgraph-redis source: aio.py from_conn_string).
    # Calling setup() again here triggers a second FT.CREATE which Redis Stack
    # rejects with "Cannot create index on db != 0" — even on db=0.
    cm = AsyncRedisStore.from_conn_string(redis_url)
    store = await cm.__aenter__()

    logger.info(f"[{agent_name}] ✓ Redis store created successfully")
    return store, cm


async def _close_store_cm(cm: Any, agent_name: str) -> None:
    """Exit an async context manager returned by ``from_conn_string()``.

    Args:
        cm: Context manager to exit.
        agent_name: Agent identifier used in log messages.
    """
    try:
        await cm.__aexit__(None, None, None)
    except Exception as exc:
        logger.debug(f"[{agent_name}] Error closing store context manager: {exc}")


# ---------------------------------------------------------------------------
# PostgreSQL store
# ---------------------------------------------------------------------------


async def _create_postgres_store(agent_name: str) -> tuple[AsyncPostgresStore, Any]:
    """Create and set up a PostgreSQL store.

    ``from_conn_string()`` returns an async context manager.  We enter it with
    ``__aenter__()`` to obtain the live store object, and return the context
    manager so the caller can exit it (``__aexit__``) on cleanup.

    Connection info is resolved from ``STORE_DB_URL`` (preferred) or falls
    back to Django's ``DATABASES["default"]`` settings — the same convention
    used by the checkpointer factory.

    Args:
        agent_name: Agent identifier used in log messages.

    Returns:
        Tuple of (configured AsyncPostgresStore, context manager for cleanup).

    Raises:
        Exception: On connection or schema-setup failure.
    """
    conninfo = get_postgres_connection_string("STORE_DB_URL")
    logger.info(f"[{agent_name}] Creating AsyncPostgresStore")

    cm = AsyncPostgresStore.from_conn_string(conninfo)
    store = await cm.__aenter__()
    await store.setup()

    logger.info(f"[{agent_name}] ✓ PostgreSQL store created successfully")
    return store, cm


# ---------------------------------------------------------------------------
# InMemory store
# ---------------------------------------------------------------------------


def _create_inmemory_store(agent_name: str, reason: str = "No persistent backend configured") -> InMemoryStore:
    """Return an in-memory store with a prominent persistence warning.

    Used when ``STORE_BACKEND=memory`` is explicitly set, or as the automatic
    last-resort fallback when both Redis and PostgreSQL are unavailable.
    All data is lost on every process restart.

    Args:
        agent_name: Agent identifier used in log messages.
        reason: Human-readable reason included in the warning.

    Returns:
        A fresh ``InMemoryStore`` instance.
    """
    logger.warning(
        f"[{agent_name}] {reason} — using InMemoryStore. "
        "Long-term memory will NOT persist across restarts. "
        "Set STORE_BACKEND=postgres for persistence without Redis."
    )
    return InMemoryStore()


# ---------------------------------------------------------------------------
# Core factory logic
# ---------------------------------------------------------------------------


async def _build_store(agent_name: str, is_dev: bool) -> tuple[StoreType, Any]:
    """Select and create the appropriate store backend.

    Decision tree:

    1. ``STORE_BACKEND=memory``   → InMemoryStore directly (no Redis/Postgres attempted)
    2. ``STORE_BACKEND=redis``    → AsyncRedisStore (raise if unavailable)
    3. ``STORE_BACKEND=postgres`` → AsyncPostgresStore (skip Redis entirely)
    4. Unset (auto)               → try Postgres → try Redis → InMemoryStore (last resort)

    PostgreSQL is preferred in auto-mode: it requires no special Redis modules and
    keeps long-term memory separate from the Redis checkpointer.

    Args:
        agent_name: Agent identifier used in log messages.
        is_dev: ``True`` when running in the development environment.

    Returns:
        Tuple of (store instance, context manager for cleanup).
        Context manager is ``None`` for InMemoryStore.

    Raises:
        RuntimeError: When an explicit backend is unavailable.
    """
    backend = _get_store_backend()

    # ── Explicit memory override (dev/testing only) ──────────────────────────
    if backend == _BACKEND_MEMORY:
        logger.warning(f"[{agent_name}] STORE_BACKEND=memory explicitly set")
        return _create_inmemory_store(agent_name, reason="STORE_BACKEND=memory explicitly set"), None

    # ── Explicit redis override ───────────────────────────────────────────────
    if backend == _BACKEND_REDIS:
        redis_url = _get_redis_url()
        if not redis_url:
            raise RuntimeError("STORE_BACKEND=redis but no Redis URL found. Set STORE_REDIS_URL or REDIS_URL.")
        return await _create_redis_store(redis_url, agent_name)

    # ── Explicit postgres override ────────────────────────────────────────────
    if backend == _BACKEND_POSTGRES:
        logger.info(f"[{agent_name}] STORE_BACKEND=postgres")
        return await _create_postgres_store(agent_name)

    # ── Auto mode: Postgres first, Redis fallback, InMemory last resort ───────
    logger.info(f"[{agent_name}] Auto mode — trying AsyncPostgresStore first")
    try:
        return await _create_postgres_store(agent_name)
    except Exception as pg_err:
        logger.warning(
            f"[{agent_name}] PostgreSQL store unavailable ({type(pg_err).__name__}: {pg_err}) — trying Redis"
        )

    redis_url = _get_redis_url()
    if redis_url:
        try:
            return await _create_redis_store(redis_url, agent_name)
        except Exception as redis_err:
            log_redis_fallback(agent_name, redis_err, "InMemoryStore", is_dev)

    return _create_inmemory_store(agent_name, reason="Both PostgreSQL and Redis unavailable"), None


async def _get_or_create_store(agent_name: str, is_dev: bool) -> StoreType:
    """Return a cached store, recreating it if the event loop has changed.

    Args:
        agent_name: Agent identifier.
        is_dev: Development environment flag.

    Returns:
        A valid, ready-to-use store instance.
    """
    current_loop = get_current_event_loop()

    if agent_name in _stores:
        metadata = _stores[agent_name]
        stored_loop = metadata.event_loop
        # Recreate only when the stored loop has been closed (i.e. it belonged to
        # a previous Django request that has already finished).  Comparing loop
        # *identity* would force a recreation on every request because Django
        # allocates a new loop object per async view — causing setup() to run
        # and "Index already exists" to be logged on every call.
        if stored_loop is not None and stored_loop.is_closed():
            logger.debug(f"[{agent_name}] Stored event loop is closed — recreating store")
            if metadata.context_manager is not None:
                await _close_store_cm(metadata.context_manager, agent_name)
            del _stores[agent_name]
        else:
            return metadata.store

    store, cm = await _build_store(agent_name, is_dev)
    _stores[agent_name] = StoreMetadata(store=store, event_loop=current_loop, context_manager=cm)
    return store


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_store(agent_name: str = "deep_agent") -> StoreType:
    """Get or create a memory store for an agent.

    Backend priority (controlled by ``STORE_BACKEND`` env var):

    1. Redis          (if ``STORE_REDIS_URL`` / ``REDIS_URL`` set and healthy)
    2. PostgreSQL     (automatic fallback, or ``STORE_BACKEND=postgres``)
    3. InMemoryStore  (automatic last resort if both above fail, or ``STORE_BACKEND=memory``)

    Stores are cached globally per ``agent_name`` and reused across calls.

    Args:
        agent_name: Name of the requesting agent (used for caching/logging).
            Defaults to ``"deep_agent"``.

    Returns:
        A configured store instance ready for agent use.

    Example:
        >>> store = await get_store("my_agent")
        >>> same_store = await get_store("my_agent")  # returns cached instance
        >>> assert store is same_store
    """
    return await _get_or_create_store(agent_name, is_dev=is_dev_environment())


async def close_all_stores() -> None:
    """Close all cached stores and clear the global store cache.

    Should be called during application shutdown to release database/Redis
    connections. Safe to call multiple times.

    Example:
        >>> await close_all_stores()
    """
    for agent_name, metadata in list(_stores.items()):
        if metadata.context_manager is not None:
            backend = type(metadata.store).__name__
            logger.info(f"[{agent_name}] Closing {backend} store")
            await _close_store_cm(metadata.context_manager, agent_name)
        # InMemoryStore (context_manager is None) has no cleanup needed

    _stores.clear()
    logger.info("All memory stores closed successfully")


@asynccontextmanager
async def managed_store(agent_name: str = "deep_agent"):
    """Context manager for automatic store lifecycle management.

    Acquires a store on entry and ensures it is closed on exit — useful for
    short-lived tasks that need their own isolated store.

    Args:
        agent_name: Name of the requesting agent. Defaults to ``"deep_agent"``.

    Yields:
        A configured store instance.

    Example:
        >>> async with managed_store("my_agent") as store:
        ...     await store.put(("namespace",), "key", {"value": 42})
    """
    store = await get_store(agent_name)
    try:
        yield store
    finally:
        if agent_name in _stores:
            metadata = _stores[agent_name]
            if metadata.context_manager is not None:
                backend = type(metadata.store).__name__
                logger.info(f"[{agent_name}] Closing managed {backend} store")
                await _close_store_cm(metadata.context_manager, agent_name)
            del _stores[agent_name]
