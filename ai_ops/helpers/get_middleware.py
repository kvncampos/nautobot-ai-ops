"""Middleware cache management and retrieval.

This module provides caching and instantiation for LLM middleware configurations.
Middleware are cached per LLM model with automatic invalidation on configuration changes.
"""

import asyncio
import hashlib
import importlib
import json
import logging
from datetime import datetime, timedelta

from ai_ops.helpers.common.enums import NautobotEnvironment
from ai_ops.helpers.common.helpers import get_environment

logger = logging.getLogger(__name__)

# Cache structure: {
#     "llm_model_id": <model_id>,
#     "middlewares": [<middleware_instances>],
#     "timestamp": <datetime>,
#     "config_hash": <hash_of_configs>
# }
_middleware_cache: dict = {
    "llm_model_id": None,
    "middlewares": [],
    "timestamp": None,
    "config_hash": None,
}
_cache_lock = asyncio.Lock()
CACHE_TTL_SECONDS = 300  # 5 minutes


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


def _calculate_config_hash(middlewares_qs) -> str:
    """Calculate a hash of all middleware configurations for cache invalidation.

    Args:
        middlewares_qs: QuerySet of LLMMiddleware objects

    Returns:
        str: SHA256 hash of all configurations
    """
    config_data = []
    for mw in middlewares_qs:
        config_data.append(
            {
                "name": mw.middleware.name,
                "config": mw.config,
                "priority": mw.priority,
                "is_active": mw.is_active,
                "is_critical": mw.is_critical,
            }
        )
    config_json = json.dumps(config_data, sort_keys=True)
    return hashlib.sha256(config_json.encode()).hexdigest()


def _is_cache_valid(llm_model_id: int, config_hash: str) -> bool:
    """Check if the cache is still valid.

    Args:
        llm_model_id: ID of the LLM model
        config_hash: Hash of the current middleware configurations

    Returns:
        bool: True if cache is valid, False otherwise
    """
    if _middleware_cache["llm_model_id"] != llm_model_id:
        return False

    if _middleware_cache["config_hash"] != config_hash:
        return False

    if _middleware_cache["timestamp"] is None:
        return False

    age = datetime.now() - _middleware_cache["timestamp"]
    return age < timedelta(seconds=CACHE_TTL_SECONDS)


async def get_middleware(llm_model, force_refresh: bool = False) -> list:
    """Get middleware instances for an LLM model.

    Middleware are returned in priority order (lowest to highest).
    Cache is automatically invalidated after TTL or when configurations change.

    Args:
        llm_model: LLMModel instance
        force_refresh: If True, bypass cache and reload from database

    Returns:
        list: List of instantiated middleware objects in priority order

    Raises:
        Exception: If a critical middleware fails to instantiate
    """
    # Import here to avoid circular dependency
    from asgiref.sync import sync_to_async

    from ai_ops.models import LLMMiddleware

    async with _cache_lock:
        # Get current middlewares from database
        middlewares_qs = await sync_to_async(list)(
            LLMMiddleware.objects.filter(llm_model=llm_model, is_active=True)
            .select_related("llm_model", "middleware")
            .order_by("priority", "middleware__name")
        )

        # Calculate config hash
        config_hash = _calculate_config_hash(middlewares_qs)

        # Check if cache is valid
        if not force_refresh and _is_cache_valid(llm_model.id, config_hash):
            logger.debug(f"Using cached middleware for model {llm_model.name}")
            return _middleware_cache["middlewares"]

        # Build new middleware list
        middlewares = []
        env = get_environment()
        is_prod = env == NautobotEnvironment.PROD

        for mw in middlewares_qs:
            try:
                # Dynamically import the middleware class
                middleware_class = _import_middleware_class(mw.middleware.name)

                # Instantiate middleware with config
                instance = middleware_class(**mw.config)
                middlewares.append(instance)
                logger.info(
                    f"Loaded middleware {mw.middleware.name} (priority={mw.priority}) for model {llm_model.name}"
                )

            except Exception as e:
                if is_prod:
                    error_msg = (
                        f"Failed to load middleware {mw.middleware.name} "
                        f"for model {llm_model.name}. Contact administrator."
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

        # Update cache
        _middleware_cache.update(
            {
                "llm_model_id": llm_model.id,
                "middlewares": middlewares,
                "timestamp": datetime.now(),
                "config_hash": config_hash,
            }
        )

        logger.info(
            f"Cached {len(middlewares)} middleware instances for model {llm_model.name} "
            f"(expires in {CACHE_TTL_SECONDS}s)"
        )

        return middlewares


async def clear_middleware_cache() -> dict:
    """Clear the middleware cache.

    Returns:
        dict: Cache statistics before clearing
    """
    async with _cache_lock:
        stats = await get_middleware_cache_stats()
        _middleware_cache.update(
            {
                "llm_model_id": None,
                "middlewares": [],
                "timestamp": None,
                "config_hash": None,
            }
        )
        logger.info("Middleware cache cleared")
        return stats


async def warm_middleware_cache(llm_model=None) -> dict:
    """Pre-load middleware cache for a model.

    Args:
        llm_model: LLMModel instance. If None, uses the default model.

    Returns:
        dict: Cache statistics after warming
    """
    # Import here to avoid circular dependency
    from ai_ops.models import LLMModel

    try:
        if llm_model is None:
            llm_model = LLMModel.get_default_model()

        await get_middleware(llm_model, force_refresh=True)
        stats = await get_middleware_cache_stats()
        logger.info(f"Middleware cache warmed for model {llm_model.name}")
        return stats

    except Exception as e:
        logger.error(f"Failed to warm middleware cache: {e}", exc_info=True)
        return {"error": str(e)}


async def get_middleware_cache_stats() -> dict:
    """Get current cache statistics.

    Returns:
        dict: Cache statistics including model ID, count, age, and hash
    """
    async with _cache_lock:
        stats = {
            "llm_model_id": _middleware_cache["llm_model_id"],
            "middleware_count": len(_middleware_cache["middlewares"]),
            "config_hash": _middleware_cache["config_hash"],
            "cached_at": _middleware_cache["timestamp"].isoformat() if _middleware_cache["timestamp"] else None,
        }

        if _middleware_cache["timestamp"]:
            age = datetime.now() - _middleware_cache["timestamp"]
            stats["age_seconds"] = age.total_seconds()
            stats["expires_in_seconds"] = max(0, CACHE_TTL_SECONDS - age.total_seconds())
            stats["is_expired"] = age >= timedelta(seconds=CACHE_TTL_SECONDS)
        else:
            stats["age_seconds"] = None
            stats["expires_in_seconds"] = None
            stats["is_expired"] = True

        return stats
