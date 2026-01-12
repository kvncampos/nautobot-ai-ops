"""Middleware instantiation and retrieval.

This module provides fresh instantiation of LLM middleware for each request.
Middleware instances are NOT cached to prevent state leaks between conversations.

Note: Middleware instances used to be cached globally, which caused stateful middleware
(e.g., SummarizationMiddleware) to leak state between different users' conversations.
The "always fresh" approach eliminates this issue with negligible performance impact.
"""

import importlib
import json
import logging

from asgiref.sync import sync_to_async

from ai_ops.helpers.common.enums import NautobotEnvironment
from ai_ops.helpers.common.helpers import get_environment

logger = logging.getLogger(__name__)


def _import_middleware_class(middleware_name: str):
    """Dynamically import a middleware class.

    Attempts to import from:
    1. langchain.agents.middleware (built-in middleware)
    2. ai_ops.middleware (custom middleware)

    Args:
        middleware_name: Name of the middleware class (e.g., 'SummarizationMiddleware')

    Returns:
        The middleware class

    Raises:
        ImportError: If the middleware class cannot be found
    """
    # Try langchain.agents.middleware first (built-in)
    try:
        module = importlib.import_module("langchain.agents.middleware")
        middleware_class = getattr(module, middleware_name)
        logger.debug(f"Loaded built-in middleware: {middleware_name}")
        return middleware_class
    except (ImportError, AttributeError):
        pass

    # Try custom middleware in ai_ops.middleware
    try:
        module = importlib.import_module("ai_ops.middleware")
        middleware_class = getattr(module, middleware_name)
        logger.debug(f"Loaded custom middleware: {middleware_name}")
        return middleware_class
    except (ImportError, AttributeError):
        pass

    raise ImportError(
        f"Middleware class '{middleware_name}' not found in langchain.agents.middleware or ai_ops.middleware"
    )


async def get_middleware(llm_model, force_refresh: bool = False) -> list:
    """Get fresh middleware instances for an LLM model.

    IMPORTANT: Always instantiates fresh middleware instances to prevent state leaks
    between conversations. Stateful middleware (e.g., SummarizationMiddleware) maintain
    internal buffers that should NOT be shared across different users.

    Middleware are returned in priority order (lowest to highest).

    Args:
        llm_model: LLMModel instance
        force_refresh: Deprecated parameter, kept for API compatibility (always fresh now)

    Returns:
        list: List of instantiated middleware objects in priority order

    Raises:
        Exception: If a critical middleware fails to instantiate
    """
    # Import here to avoid circular dependency
    from ai_ops.models import LLMMiddleware

    # Get current middlewares from database
    middlewares_qs = await sync_to_async(list)(
        LLMMiddleware.objects.filter(llm_model=llm_model, is_active=True)
        .select_related("llm_model", "middleware")
        .order_by("priority", "middleware__name")
    )

    # Build fresh middleware list
    middlewares = []
    env = get_environment()
    is_prod = env == NautobotEnvironment.PROD

    for mw in middlewares_qs:
        try:
            # Dynamically import the middleware class
            middleware_class = _import_middleware_class(mw.middleware.name)

            # Instantiate middleware with config (FRESH instance)
            instance = middleware_class(**mw.config)
            middlewares.append(instance)
            logger.debug(
                f"Instantiated middleware {mw.middleware.name} (priority={mw.priority}) for model {llm_model.name}"
            )

        except Exception as e:
            if is_prod:
                error_msg = (
                    f"Failed to load middleware {mw.middleware.name} for model {llm_model.name}. Contact administrator."
                )
            else:
                error_msg = (
                    f"Failed to load middleware {mw.middleware.name} "
                    f"for model {llm_model.name}: {str(e)} | "
                    f"Config: {json.dumps(mw.config, indent=2)} | "
                    f"Config Version: {mw.config_version}"
                )

            logger.error(error_msg, exc_info=not is_prod)

            if mw.is_critical:
                raise Exception(error_msg) from e

    logger.info(f"Loaded {len(middlewares)} fresh middleware instances for model {llm_model.name}")
    return middlewares


async def clear_middleware_cache() -> dict:
    """Clear the middleware cache (deprecated - no-op since caching was removed).

    Kept for API compatibility with existing code that calls this function.

    Returns:
        dict: Empty statistics
    """
    logger.info("Middleware cache clear requested (no-op: caching disabled for correctness)")
    return {
        "llm_model_id": None,
        "middleware_count": 0,
        "config_hash": None,
        "cached_at": None,
        "note": "Middleware caching disabled - instances are always fresh",
    }


async def warm_middleware_cache(llm_model=None) -> dict:
    """Warm the middleware cache (deprecated - no-op since caching was removed).

    Kept for API compatibility with existing code that calls this function.

    Args:
        llm_model: LLMModel instance. If None, uses the default model.

    Returns:
        dict: Empty statistics
    """
    logger.info("Middleware cache warm requested (no-op: caching disabled for correctness)")
    return {
        "note": "Middleware caching disabled - instances are always fresh",
        "llm_model_id": llm_model.id if llm_model else None,
    }


async def get_middleware_cache_stats() -> dict:
    """Get current cache statistics (deprecated - returns empty since caching was removed).

    Kept for API compatibility with existing code that calls this function.

    Returns:
        dict: Empty cache statistics
    """
    return {
        "llm_model_id": None,
        "middleware_count": 0,
        "config_hash": None,
        "cached_at": None,
        "age_seconds": None,
        "expires_in_seconds": None,
        "is_expired": True,
        "note": "Middleware caching disabled - instances are always fresh",
    }
