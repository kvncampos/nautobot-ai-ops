"""App declaration for ai_ops."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
import os
import sys
import threading
from importlib import metadata
from pathlib import Path

from nautobot.apps import ConstanceConfigItem, NautobotAppConfig

# Process-level guard: ensures only one warmup thread is ever started, even when
# Django calls ready() multiple times (e.g. auto-reloader spawning a child process
# that imports all apps again, or multiple AppConfig instances in tests).
_WARMUP_STARTED = threading.Event()

# Management commands that perform DB migrations, testing, or other non-serving
# work where warming the MCP cache is wasteful or actively harmful.
_SKIP_WARMUP_COMMANDS = frozenset(
    [
        "migrate",
        "makemigrations",
        "test",
        "shell",
        "shell_plus",
        "collectstatic",
        "check",
        "inspectdb",
        "showmigrations",
        "sqlmigrate",
        "dbshell",
        "createsuperuser",
        "changepassword",
    ]
)

try:
    __version__ = metadata.version("nautobot-ai-ops")
except metadata.PackageNotFoundError:
    # Fall back to reading from pyproject.toml for development environments
    try:
        # Python 3.11+ has tomllib in stdlib, earlier versions need tomli
        if sys.version_info >= (3, 11):
            import tomllib as tomli_lib

            open_mode = "rb"
        else:
            import tomli as tomli_lib

            open_mode = "rb"

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, open_mode) as f:
                pyproject_data = tomli_lib.load(f)
            __version__ = pyproject_data["tool"]["poetry"]["version"]
        else:
            __version__ = "1.0.6"  # Ultimate fallback
    except (ImportError, KeyError, FileNotFoundError):
        __version__ = "1.0.6"  # Ultimate fallback


class AiOpsConfig(NautobotAppConfig):
    """App configuration for the ai_ops app."""

    name = "ai_ops"
    verbose_name = "AI Ops"
    version = __version__
    author = "Kevin Campos"
    description = "AI Ops integration for Nautobot."
    base_url = "ai-ops"
    required_settings = []
    default_settings = {}
    constance_config = {
        "chat_session_ttl_minutes": ConstanceConfigItem(
            default=10,
            help_text="Time-to-live (TTL) for chat sessions in minutes. Chat sessions automatically expire after this period of inactivity or message age. Applies to both frontend (localStorage) and backend (MemorySaver) cleanup. Valid range: 1-1440 minutes (1 minute to 24 hours).",
            field_type=int,
        ),
        "checkpoint_retention_days": ConstanceConfigItem(
            default=7,
            help_text="Retention period in days for conversation checkpoints. Used by cleanup jobs when migrated to Redis Stack or PostgreSQL persistent storage. Not enforced for current MemorySaver implementation which uses chat_session_ttl_minutes instead. Valid range: 1-365 days.",
            field_type=int,
        ),
        "agent_request_timeout_seconds": ConstanceConfigItem(
            default=120,
            help_text="Maximum time in seconds for agent request processing. If the agent takes longer than this to respond, the request will be cancelled and a timeout error returned. Valid range: 10-600 seconds (10 seconds to 10 minutes).",
            field_type=int,
        ),
        "agent_recursion_limit": ConstanceConfigItem(
            default=25,
            help_text="Maximum recursion depth for agent graph traversal. Limits the number of steps the agent can take in a single request to prevent infinite loops. Valid range: 5-100.",
            field_type=int,
        ),
    }
    docs_view_name = "plugins:ai_ops:docs"
    searchable_models = ["llmmodel", "mcpserver"]

    def ready(self):
        """Connect signal handlers when the app is ready."""
        import logging

        from .helpers.async_shutdown import register_shutdown_handlers
        from .helpers.logging_config import setup_ai_ops_logging

        logger = logging.getLogger(__name__)

        # Setup structured JSON logging for ai_ops.* loggers
        setup_ai_ops_logging()

        # Register graceful shutdown handlers for async resources (MCP clients, checkpointers)
        # Handles both development (auto-reloader) and production (SIGTERM/SIGINT) scenarios
        register_shutdown_handlers()

        # NOTE: All default data and scheduled job creation is handled by data migrations
        # (0006_populate_default_data, 0008_default_scheduled_jobs) so no signals are needed.

        # Note: Periodic tasks are handled via Nautobot Jobs (ai_agents.jobs).
        # These jobs can be scheduled through the Nautobot UI for automatic execution.

        # Warm the MCP client cache on startup using a background thread with
        # its own event loop.  AppConfig.ready() is called synchronously by
        # Django — there is never a *running* loop here, so loop.create_task()
        # always falls into the RuntimeError branch and the warmup silently
        # never runs.  A daemon thread runs the coroutine to completion without
        # blocking the main thread or the Django startup sequence.
        #
        # NOTE: Redis/Postgres async connections (checkpointer, store) are NOT
        # warmed up here.  Those connections are bound to the event loop they
        # were created in.  A background thread's loop is always closed before
        # any Django request loop starts, so the stored connections would be
        # immediately detected as stale and recreated on the first request
        # anyway — making the warmup work pointless.  Those connections are
        # initialised lazily on the first request instead.
        #
        # Guards applied before starting the thread:
        #   1. NAUTOBOT_AI_OPS_SKIP_WARMUP=1  — explicit opt-out (useful in CI/test)
        #   2. sys.argv[1] in _SKIP_WARMUP_COMMANDS — management commands that
        #      should not trigger network/DB calls (migrate, test, shell, …)
        #   3. _WARMUP_STARTED event — process-level dedup so multiple ready()
        #      calls (auto-reloader child, duplicate AppConfig) only fire once.
        _management_cmd = len(sys.argv) > 1 and sys.argv[1] in _SKIP_WARMUP_COMMANDS
        _env_skip = os.environ.get("NAUTOBOT_AI_OPS_SKIP_WARMUP", "").lower() in {"1", "true", "yes"}

        if _env_skip:
            logger.debug("Skipping MCP warmup: NAUTOBOT_AI_OPS_SKIP_WARMUP is set")
        elif _management_cmd:
            logger.debug("Skipping MCP warmup: running under management command '%s'", sys.argv[1])
        elif _WARMUP_STARTED.is_set():
            logger.debug("Skipping MCP warmup: already started in this process")
        else:
            # Atomically claim the warmup slot before spawning the thread.
            _WARMUP_STARTED.set()
            try:
                import asyncio

                from ai_ops.agents.multi_mcp_agent import warm_mcp_cache

                def _run_startup_warmup() -> None:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(warm_mcp_cache())
                    finally:
                        loop.close()

                warmup_thread = threading.Thread(
                    target=_run_startup_warmup,
                    name="ai-ops-startup-warmup",
                    daemon=True,  # won't block interpreter shutdown
                )
                warmup_thread.start()
                logger.info("Started startup warmup thread (MCP cache)")
            except Exception as e:
                # Release the guard so a later process restart can retry.
                _WARMUP_STARTED.clear()
                logger.warning(f"Failed to start startup warmup: {e}")

        super().ready()


config = AiOpsConfig  # pylint:disable=invalid-name
