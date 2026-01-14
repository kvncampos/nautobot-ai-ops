"""Async shutdown utilities for graceful cleanup.

This module is used to ensure that global async resources (such as MCP client cache and checkpointer)
are cleaned up properly during interpreter or process shutdown. It is compatible with both WSGI and ASGI
runtimes, and is safe to use in a hybrid sync/async Nautobot plugin.
"""

import asyncio
import atexit
import logging
import signal

logger = logging.getLogger(__name__)

# Track if shutdown has been initiated to prevent duplicate cleanup
_shutdown_initiated = False

# Note: This module is imported and used in ai_ops/__init__.py to register atexit and signal handlers.
# It is safe to call register_shutdown_handlers() multiple times.


def async_shutdown() -> None:
    """Synchronous wrapper for async cleanup during interpreter shutdown.

    This function is called by atexit and signal handlers. It creates a new
    event loop if needed (since the main loop may already be closed) and
    runs the async cleanup.

    Safe to call multiple times - only performs cleanup once.
    """
    global _shutdown_initiated

    if _shutdown_initiated:
        logger.debug("Shutdown already initiated, skipping duplicate cleanup")
        return

    _shutdown_initiated = True
    logger.info("Initiating graceful async shutdown...")

    try:
        # Try to get the running loop, create new one if needed
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - create a new one for cleanup
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run cleanup with a timeout to prevent hanging
        if loop.is_running():
            # If loop is running (e.g., in async context), schedule cleanup
            asyncio.ensure_future(_async_cleanup())
        else:
            # Run cleanup synchronously
            loop.run_until_complete(asyncio.wait_for(_async_cleanup(), timeout=5.0))
            loop.close()

    except asyncio.TimeoutError:
        logger.warning("Async cleanup timed out after 5 seconds")
    except RuntimeError as e:
        # Handle "cannot schedule new futures after interpreter shutdown"
        if "cannot schedule new futures" in str(e):
            logger.debug("Event loop already closed, skipping async cleanup")
        else:
            logger.warning(f"RuntimeError during async shutdown: {e}")
    except Exception as e:
        logger.warning(f"Error during async shutdown cleanup: {e}")


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
            logger.info(f"Cleared MCP client cache ({cleared_count} servers)")
    except ImportError:
        logger.debug("MCP agent module not available for cleanup")
    except Exception as e:
        logger.warning(f"Error clearing MCP cache: {e}")

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
        logger.warning(f"Error clearing checkpointer: {e}")

    logger.debug("Async cleanup complete")


def _signal_handler(signum: int, frame) -> None:
    """Signal handler for SIGTERM and SIGINT.

    Performs graceful shutdown before the interpreter begins shutting down.
    This is called earlier in the shutdown sequence than atexit handlers.

    Args:
        signum: Signal number (e.g., signal.SIGTERM)
        frame: Current stack frame (unused)
    """
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, initiating graceful shutdown...")

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

    Safe to call multiple times - handlers are only registered once.
    """
    # Register atexit handler (runs during normal interpreter shutdown)
    atexit.register(async_shutdown)
    logger.debug("Registered atexit shutdown handler")

    # Register signal handlers for production shutdown
    # Only register if we're the main process (not a Gunicorn worker child)
    try:
        # SIGTERM - sent by Kubernetes/Docker for graceful shutdown
        signal.signal(signal.SIGTERM, _signal_handler)
        logger.debug("Registered SIGTERM shutdown handler")
    except (ValueError, OSError) as e:
        # ValueError: signal only works in main thread
        # OSError: can happen in certain contexts
        logger.debug(f"Could not register SIGTERM handler: {e}")

    try:
        # SIGINT - sent by Ctrl+C in development
        signal.signal(signal.SIGINT, _signal_handler)
        logger.debug("Registered SIGINT shutdown handler")
    except (ValueError, OSError) as e:
        logger.debug(f"Could not register SIGINT handler: {e}")

    logger.info("Async shutdown handlers registered")


def reset_shutdown_state() -> None:
    """Reset shutdown state for testing purposes.

    Only use this in test fixtures to reset the global state between tests.
    """
    global _shutdown_initiated
    _shutdown_initiated = False
