"""Async shutdown utilities for graceful cleanup.

This module is used to ensure that global async resources (such as MCP client cache and checkpointer)
are cleaned up properly during interpreter or process shutdown. It is compatible with both WSGI and ASGI
runtimes, and is safe to use in a hybrid sync/async Nautobot plugin.
"""

import asyncio
import atexit
import logging
import signal
import threading
import types

__all__ = ["async_shutdown", "register_shutdown_handlers", "reset_shutdown_state"]

logger = logging.getLogger(__name__)

# Module-level lock protecting both _shutdown_initiated and _handlers_registered
_module_lock = threading.Lock()

# Tracks whether async_shutdown() has already run to prevent duplicate cleanup
_shutdown_initiated = False

# Tracks whether register_shutdown_handlers() has already registered handlers
_handlers_registered = False

# Note: This module is imported and used in ai_ops/__init__.py to register atexit and signal handlers.
# Call register_shutdown_handlers() once during AppConfig.ready() — it is idempotent.


def async_shutdown() -> None:
    """Synchronous wrapper for async cleanup during interpreter shutdown.

    This function is called by atexit and signal handlers. It creates a new
    event loop if needed (since the main loop may already be closed) and
    runs the async cleanup.

    Thread-safe and idempotent — only performs cleanup on the first call.
    """
    global _shutdown_initiated

    with _module_lock:
        if _shutdown_initiated:
            logger.debug("Shutdown already initiated, skipping duplicate cleanup")
            return
        _shutdown_initiated = True

    logger.info("Initiating graceful async shutdown...")

    try:
        try:
            # Succeeds only when called from within the running event loop's thread.
            loop = asyncio.get_running_loop()
            # Cannot block the loop's own thread — schedule cleanup as a best-effort
            # task. For ASGI apps, prefer handling cleanup in the lifespan shutdown
            # event to guarantee completion.
            logger.warning(
                "Event loop is running in the current thread; "
                "cleanup scheduled as a best-effort task (may not complete before shutdown)"
            )
            loop.create_task(_async_cleanup())
        except RuntimeError:
            # No running loop in this thread — create a fresh isolated one for cleanup.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(asyncio.wait_for(_async_cleanup(), timeout=5.0))
            finally:
                loop.close()

    except asyncio.TimeoutError:
        logger.warning("Async cleanup timed out after 5 seconds")
    except RuntimeError as e:
        # Handle "cannot schedule new futures after interpreter shutdown"
        if "cannot schedule new futures" in str(e):
            logger.debug("Event loop already closed, skipping async cleanup")
        else:
            logger.warning("RuntimeError during async shutdown: %s", e)
    except Exception as e:
        logger.warning("Error during async shutdown cleanup: %s", e)


async def _async_cleanup() -> None:
    """Perform async cleanup of global resources.

    Cleans up:
    - MCP client cache
    - MemorySaver checkpointer instance
    """
    logger.debug("Running async cleanup tasks...")

    # Clear MCP client cache
    try:
        from ai_ops.agents.multi_mcp_agent import clear_mcp_cache

        cleared_count = await clear_mcp_cache()
        if cleared_count > 0:
            logger.info("Cleared MCP client cache (%d servers)", cleared_count)
    except ImportError:
        logger.debug("MCP agent module not available for cleanup")
    except Exception as e:
        logger.warning("Error clearing MCP cache: %s", e)

    # Reset MemorySaver checkpointer
    try:
        from ai_ops import checkpointer as checkpointer_module

        if checkpointer_module._memory_saver_instance is not None:
            # MemorySaver doesn't have a close method, just clear the reference
            checkpointer_module._memory_saver_instance = None
            logger.info("Cleared MemorySaver checkpointer instance")
    except ImportError:
        logger.debug("Checkpointer module not available for cleanup")
    except Exception as e:
        logger.warning("Error clearing checkpointer: %s", e)

    logger.debug("Async cleanup complete")


def _signal_handler(signum: int, frame: types.FrameType | None) -> None:
    """Signal handler for SIGTERM and SIGINT.

    Performs graceful shutdown before the interpreter begins shutting down.
    This is called earlier in the shutdown sequence than atexit handlers.

    Args:
        signum: Signal number (e.g., signal.SIGTERM).
        frame: Current stack frame (unused).
    """
    sig_name = signal.Signals(signum).name
    logger.info("Received %s, initiating graceful shutdown...", sig_name)

    # Perform async cleanup
    async_shutdown()

    # Re-raise the signal to allow normal shutdown to proceed
    # This ensures that other signal handlers (e.g., Gunicorn's) can run
    signal.signal(signum, signal.SIG_DFL)
    signal.raise_signal(signum)


def register_shutdown_handlers() -> None:
    """Register shutdown handlers for graceful cleanup.

    Call this during app initialization (e.g., in AppConfig.ready()).
    Registers:
    - atexit handler for normal interpreter shutdown
    - SIGTERM handler for production graceful shutdown (e.g., Kubernetes)
    - SIGINT handler for development Ctrl+C

    Idempotent — handlers are registered exactly once regardless of how many
    times this function is called.
    """
    global _handlers_registered

    with _module_lock:
        if _handlers_registered:
            logger.debug("Shutdown handlers already registered, skipping")
            return
        _handlers_registered = True

    # Register atexit handler (runs during normal interpreter shutdown)
    atexit.register(async_shutdown)
    logger.debug("Registered atexit shutdown handler")

    # Register signal handlers for production shutdown.
    # Signals can only be registered from the main thread; failures are non-fatal.
    try:
        # SIGTERM — sent by Kubernetes/Docker for graceful shutdown
        signal.signal(signal.SIGTERM, _signal_handler)
        logger.debug("Registered SIGTERM shutdown handler")
    except (ValueError, OSError) as e:
        # ValueError: signal only works in main thread
        # OSError: can happen in certain contexts
        logger.debug("Could not register SIGTERM handler: %s", e)

    try:
        # SIGINT — sent by Ctrl+C in development
        signal.signal(signal.SIGINT, _signal_handler)
        logger.debug("Registered SIGINT shutdown handler")
    except (ValueError, OSError) as e:
        logger.debug("Could not register SIGINT handler: %s", e)

    logger.info("Async shutdown handlers registered")


def reset_shutdown_state() -> None:
    """Reset shutdown state for testing purposes.

    Only use this in test fixtures to reset the global state between tests.
    Resets both the shutdown-initiated and handler-registration flags.
    """
    global _shutdown_initiated, _handlers_registered

    with _module_lock:
        _shutdown_initiated = False
        _handlers_registered = False
