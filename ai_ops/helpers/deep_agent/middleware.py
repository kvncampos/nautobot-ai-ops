"""
Middleware utilities for LangGraph deep agents in ai-ops.

This module provides reusable middleware classes for agent workflows,
including error handling and tool result caching.

Adapted from network-agent to work with Django configuration.
"""

import asyncio
import hashlib
import json
import logging
import os

import redis.asyncio as aioredis
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)


class ToolErrorHandlerMiddleware(AgentMiddleware):
    """
    Middleware to handle tool execution errors gracefully with automatic retry for transient errors.

    Usage:
        ```python
        from ai_ops.helpers.deep_agent.middleware import ToolErrorHandlerMiddleware

        # Default: 2 retries, 1 second delay
        middleware=[ToolErrorHandlerMiddleware()]

        # Custom: 3 retries, 2 second delay
        middleware=[ToolErrorHandlerMiddleware(max_retries=3, retry_delay=2.0)]
        ```
    """

    # Keywords that indicate a transient/retriable error
    RETRIABLE_KEYWORDS = [
        "eof while parsing",
        "invalid json",
        "validationerror",
        "connection",
        "timeout",
        "timed out",
        "broken pipe",
        "connection reset",
        "network",
        "eof occurred",
        "sse",
        "server-sent events",
        "streamable_http",
    ]

    def __init__(self, max_retries: int = 2, retry_delay: float = 1.0):
        """
        Initialize the middleware.

        Args:
            max_retries: Number of retry attempts (default: 2, total 3 attempts)
            retry_delay: Delay between retries in seconds (default: 1.0)
        """
        super().__init__()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def awrap_tool_call(self, request, handler):
        """
        Wrap async tool calls with error handling and retry logic for transient errors.

        Args:
            request: Tool call request with tool_call dict containing 'id' and 'name'
            handler: Async tool execution handler

        Returns:
            ToolMessage: Success result or error message with status="error"
        """
        tool_name = request.tool_call.get("name", "unknown")
        last_error = None

        # Attempt execution with retries
        for attempt in range(self.max_retries + 1):
            try:
                result = await handler(request)

                # Log successful retry
                if attempt > 0:
                    logger.info(f"[TOOL_CALL] ✓ Tool '{tool_name}' succeeded on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_error = e
                is_retriable = self._is_retriable(str(e))

                # Log attempt
                logger.warning(
                    f"[TOOL_CALL] ✗ Tool '{tool_name}' attempt {attempt + 1}/{self.max_retries + 1}: "
                    f"{type(e).__name__} (retriable={is_retriable})"
                )

                # Break if last attempt or not retriable
                if attempt >= self.max_retries or not is_retriable:
                    break

                await asyncio.sleep(self.retry_delay)

        # Build error message with repr(e)
        error_msg = (
            f"Tool error: {repr(last_error)}\n\nPlease try a different approach or ask for clarification if needed."
        )

        logger.error(f"[TOOL_CALL] ✗ Tool '{tool_name}' failed after {self.max_retries + 1} attempts")

        return ToolMessage(content=error_msg, tool_call_id=request.tool_call["id"], name=tool_name, status="error")

    def _is_retriable(self, error_str: str) -> bool:
        """Check if error is transient and retriable."""
        error_lower = error_str.lower()
        return any(keyword in error_lower for keyword in self.RETRIABLE_KEYWORDS)


class ToolResultCacheMiddleware(AgentMiddleware):
    """
    Redis-backed cache for tool call results with per-tool TTL configuration.

    Caches results keyed on tool name + arguments hash. Supports skipping
    cache for write operations (POST, PUT, DELETE, PATCH) on API tools.

    Usage:
        ```python
        from ai_ops.helpers.deep_agent.middleware import ToolResultCacheMiddleware

        # Default config caches both nautobot MCP tools
        middleware=[ToolResultCacheMiddleware()]

        # Custom per-tool config
        middleware=[ToolResultCacheMiddleware(tool_cache_config={
            "mcp_nautobot_openapi_api_request_schema": {"ttl": 600},
            "mcp_nautobot_dynamic_api_request": {"ttl": 60, "skip_methods": ["POST", "PUT", "DELETE", "PATCH"]},
        })]
        ```
    """

    DEFAULT_TOOL_CACHE_CONFIG = {
        "mcp_nautobot_openapi_api_request_schema": {"ttl": 600},
        "mcp_nautobot_dynamic_api_request": {"ttl": 60, "skip_methods": ["POST", "PUT", "DELETE", "PATCH"]},
    }

    def __init__(self, tool_cache_config: dict | None = None):
        """
        Initialize the cache middleware.

        Args:
            tool_cache_config: Per-tool cache configuration. Keys are tool names,
                values are dicts with "ttl" (seconds) and optional "skip_methods"
                (list of HTTP methods to never cache).
                Defaults to caching both nautobot MCP tools.
        """
        super().__init__()
        self.tool_cache_config = tool_cache_config or self.DEFAULT_TOOL_CACHE_CONFIG
        self._redis: aioredis.Redis | None = None
        self._redis_unavailable = False

    async def _get_redis(self) -> aioredis.Redis | None:
        """Lazily connect to Redis. Returns None if unavailable."""
        if self._redis_unavailable:
            return None

        if self._redis is not None:
            return self._redis

        redis_url = os.getenv("TOOL_CACHE_REDIS_URL") or os.getenv("REDIS_URL")
        if not redis_url:
            logger.warning("[TOOL_CACHE] No TOOL_CACHE_REDIS_URL or REDIS_URL configured, caching disabled")
            self._redis_unavailable = True
            return None

        try:
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("[TOOL_CACHE] Redis connection established")
            return self._redis
        except Exception as e:
            logger.warning(f"[TOOL_CACHE] Redis unavailable, caching disabled: {e}")
            self._redis_unavailable = True
            self._redis = None
            return None

    @staticmethod
    def _build_cache_key(tool_name: str, tool_args: dict) -> str:
        """Build a deterministic cache key from tool name and arguments."""
        args_json = json.dumps(tool_args, sort_keys=True, default=str)
        args_hash = hashlib.sha256(args_json.encode()).hexdigest()[:16]
        return f"tool_cache:{tool_name}:{args_hash}"

    def _should_skip(self, tool_name: str, tool_args: dict) -> bool:
        """Check if this tool call should skip caching (e.g. write operations)."""
        config = self.tool_cache_config.get(tool_name)
        if config is None:
            return True  # Tool not in config, don't cache

        skip_methods = config.get("skip_methods", [])
        if skip_methods:
            method = str(tool_args.get("method", "GET")).upper()
            if method in skip_methods:
                return True

        return False

    async def awrap_tool_call(self, request, handler):
        """
        Wrap tool calls with Redis result caching.

        Args:
            request: Tool call request with tool_call dict containing 'id', 'name', 'args'
            handler: Async tool execution handler

        Returns:
            ToolMessage: Cached or fresh result
        """
        tool_name = request.tool_call.get("name", "unknown")
        tool_args = request.tool_call.get("args", {})

        # Only cache configured tools
        if self._should_skip(tool_name, tool_args):
            return await handler(request)

        cache_key = self._build_cache_key(tool_name, tool_args)
        config = self.tool_cache_config[tool_name]
        ttl = config.get("ttl", 300)

        # Try to get from cache
        r = await self._get_redis()
        if r is not None:
            try:
                cached = await r.get(cache_key)
                if cached is not None:
                    logger.info(f"[TOOL_CACHE] HIT tool={tool_name} key={cache_key}")
                    cached_data = json.loads(cached)
                    return ToolMessage(
                        content=cached_data["content"],
                        tool_call_id=request.tool_call["id"],
                        name=tool_name,
                    )
            except Exception as e:
                logger.warning(f"[TOOL_CACHE] Redis read error, falling through: {e}")

        # Cache miss — execute tool
        logger.info(f"[TOOL_CACHE] MISS tool={tool_name} key={cache_key}")
        result = await handler(request)

        # Cache the result if Redis is available and tool succeeded
        result_content = getattr(result, "content", None)
        if r is not None and getattr(result, "status", None) != "error" and result_content is not None:
            try:
                cache_data = json.dumps({"content": result_content})
                await r.setex(cache_key, ttl, cache_data)
                logger.info(f"[TOOL_CACHE] SET tool={tool_name} key={cache_key} ttl={ttl}s")
            except Exception as e:
                logger.warning(f"[TOOL_CACHE] Redis write error: {e}")

        return result
