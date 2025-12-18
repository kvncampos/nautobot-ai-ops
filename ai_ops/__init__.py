"""App declaration for ai_ops."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig, nautobot_database_ready

__version__ = metadata.version(__name__)


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
    docs_view_name = "plugins:ai_ops:docs"
    searchable_models = ["llmmodel", "mcpserver"]

    def ready(self):
        """Connect signal handlers when the app is ready."""
        import logging

        from .signals import (
            assign_mcp_server_statuses,
            create_default_llm_providers,
            create_default_middleware_types,
            setup_checkpoint_cleanup_schedule,
            setup_mcp_health_check_schedule,
            setup_middleware_cache_jobs,
        )

        logger = logging.getLogger(__name__)

        nautobot_database_ready.connect(assign_mcp_server_statuses, sender=self)
        nautobot_database_ready.connect(create_default_llm_providers, sender=self)
        nautobot_database_ready.connect(create_default_middleware_types, sender=self)
        nautobot_database_ready.connect(setup_checkpoint_cleanup_schedule, sender=self)
        nautobot_database_ready.connect(setup_middleware_cache_jobs, sender=self)
        nautobot_database_ready.connect(setup_mcp_health_check_schedule, sender=self)

        # Note: Periodic tasks are handled via Nautobot Jobs (ai_agents.jobs).
        # These jobs can be scheduled through the Nautobot UI for automatic execution.

        # Warm caches on startup (if event loop is available)
        # During unit tests, there may not be a running event loop
        try:
            import asyncio

            from ai_ops.agents.multi_mcp_agent import warm_mcp_cache
            from ai_ops.helpers.get_middleware import warm_middleware_cache

            # Try to get the running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we have a running loop, schedule the tasks
                loop.create_task(warm_mcp_cache())
                loop.create_task(warm_middleware_cache())
                logger.info("Scheduled MCP and middleware cache warming")
            except RuntimeError:
                # No running event loop (e.g., during tests or startup)
                # This is expected and not an error
                logger.debug("No running event loop available for cache warming")
        except Exception as e:
            logger.warning(f"Failed to warm caches on startup: {e}")

        super().ready()


config = AiOpsConfig  # pylint:disable=invalid-name
