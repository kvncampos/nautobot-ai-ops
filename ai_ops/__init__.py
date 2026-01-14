"""App declaration for ai_ops."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
import sys
from importlib import metadata
from pathlib import Path

from nautobot.apps import ConstanceConfigItem, NautobotAppConfig, nautobot_database_ready

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
            __version__ = "1.0.2"  # Ultimate fallback
    except (ImportError, KeyError, FileNotFoundError):
        __version__ = "1.0.2"  # Ultimate fallback


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
            default=5,
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
        from .signals import (
            assign_mcp_server_statuses,
            assign_system_prompt_statuses,
            create_default_llm_providers,
            create_default_middleware_types,
            setup_chat_session_cleanup_schedule,
            setup_checkpoint_cleanup_schedule,
            setup_mcp_health_check_schedule,
        )

        logger = logging.getLogger(__name__)

        # Setup structured JSON logging for ai_ops.* loggers
        setup_ai_ops_logging()

        # Register graceful shutdown handlers for async resources (MCP clients, checkpointers)
        # Handles both development (auto-reloader) and production (SIGTERM/SIGINT) scenarios
        register_shutdown_handlers()

        nautobot_database_ready.connect(assign_mcp_server_statuses, sender=self)
        nautobot_database_ready.connect(assign_system_prompt_statuses, sender=self)
        nautobot_database_ready.connect(create_default_llm_providers, sender=self)
        nautobot_database_ready.connect(create_default_middleware_types, sender=self)
        nautobot_database_ready.connect(setup_checkpoint_cleanup_schedule, sender=self)
        nautobot_database_ready.connect(setup_mcp_health_check_schedule, sender=self)
        nautobot_database_ready.connect(setup_chat_session_cleanup_schedule, sender=self)

        # Note: Periodic tasks are handled via Nautobot Jobs (ai_agents.jobs).
        # These jobs can be scheduled through the Nautobot UI for automatic execution.

        # Warm caches on startup (if event loop is available)
        # During unit tests, there may not be a running event loop
        try:
            import asyncio

            from ai_ops.agents.multi_mcp_agent import warm_mcp_cache

            # Try to get the running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we have a running loop, schedule the tasks
                loop.create_task(warm_mcp_cache())
                logger.info("Scheduled MCP cache warming")
            except RuntimeError:
                # No running event loop (e.g., during tests or startup)
                # This is expected and not an error
                logger.debug("No running event loop available for cache warming")
        except Exception as e:
            logger.warning(f"Failed to warm caches on startup: {e}")

        super().ready()


config = AiOpsConfig  # pylint:disable=invalid-name
