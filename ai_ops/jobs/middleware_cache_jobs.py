"""Jobs for middleware cache management."""

import asyncio

from nautobot.apps.jobs import JobHookReceiver, register_jobs
from nautobot.extras.choices import ObjectChangeActionChoices

name = "AI Agents"


class MiddlewareCacheInvalidationJob(JobHookReceiver):
    """Job hook to invalidate middleware cache when LLMMiddleware objects change."""

    class Meta:
        """Meta class for MiddlewareCacheInvalidationJob."""

        name = "Middleware Cache Invalidation"
        description = "Automatically invalidate middleware cache when LLMMiddleware objects are modified"
        has_sensitive_variables = False
        hidden = True

    def receive_job_hook(self, change: dict, action: str, changed_object: object) -> None:
        """Handle LLMMiddleware object changes.

        Args:
            change: The ObjectChange instance
            action: The action performed (create, update, delete)
            changed_object: The LLMMiddleware instance that changed
        """
        from ai_ops.helpers.get_middleware import clear_middleware_cache

        # Import here to avoid circular dependency
        from ai_ops.models import LLMMiddleware

        # Only process if the changed object is an LLMMiddleware
        if not isinstance(changed_object, LLMMiddleware):
            return

        self.logger.info(
            f"Middleware cache invalidation triggered: {action} on {changed_object.middleware.name} "
            f"for model {changed_object.llm_model.name}"
        )

        # Clear the cache
        try:
            stats = asyncio.run(clear_middleware_cache())
            self.logger.info(f"Middleware cache cleared. Previous state: {stats}")
        except Exception as e:
            self.logger.error(f"Failed to clear middleware cache: {e}", exc_info=True)
            raise


class DefaultModelCacheWarmingJob(JobHookReceiver):
    """Job hook to warm middleware cache when default model changes."""

    class Meta:
        """Meta class for DefaultModelCacheWarmingJob."""

        name = "Default Model Cache Warming"
        description = "Automatically warm middleware cache when a model is marked as default"
        has_sensitive_variables = False
        hidden = True

    def receive_job_hook(self, change: dict, action: str, changed_object: object) -> None:
        """Handle LLMModel default status changes.

        Args:
            change: The ObjectChange instance
            action: The action performed (create, update, delete)
            changed_object: The LLMModel instance that changed
        """
        from ai_ops.helpers.get_middleware import warm_middleware_cache

        # Import here to avoid circular dependency
        from ai_ops.models import LLMModel

        # Only process updates to LLMModel
        if not isinstance(changed_object, LLMModel):
            return

        if action != ObjectChangeActionChoices.ACTION_UPDATE:
            return

        # Only warm cache if the model is now the default
        if not changed_object.is_default:
            return

        self.logger.info(f"Default model cache warming triggered for model {changed_object.name}")

        # Warm the cache for the new default model
        try:
            stats = asyncio.run(warm_middleware_cache(changed_object))
            self.logger.info(f"Middleware cache warmed. Cache state: {stats}")
        except Exception as e:
            self.logger.error(f"Failed to warm middleware cache: {e}", exc_info=True)
            # Don't raise - warming is a performance optimization, not critical


jobs = [
    MiddlewareCacheInvalidationJob,
    DefaultModelCacheWarmingJob,
]

register_jobs(*jobs)
