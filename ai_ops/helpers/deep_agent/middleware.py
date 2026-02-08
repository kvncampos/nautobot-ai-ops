"""
Middleware utilities for LangGraph deep agents in ai-ops.

This module provides reusable middleware classes for agent workflows,
including error handling for tool execution and semantic caching for LLM responses.

Adapted from network-agent to work with Django configuration.
"""

import asyncio
import logging
import os
from typing import Optional

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, ToolMessage
from redisvl.extensions.llmcache import SemanticCache
from redisvl.utils.vectorize import BaseVectorizer

from ai_ops.helpers.common.asyncio_utils import get_or_create_event_loop_lock

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


class SemanticCacheMiddleware(AgentMiddleware):
    """
    Middleware to cache FINAL LLM responses using Redis semantic cache.

    This middleware intelligently caches only the final responses from the agent,
    skipping intermediate steps like planning, reasoning, and tool calls. It checks
    for semantically similar prompts before calling the LLM and returns cached
    responses on hit, reducing costs and improving performance.

    **Caching Strategy:**
    - ✓ Caches: Final responses without tool calls (agent answering user)
    - ✗ Skips: Intermediate planning, reasoning, or tool-calling steps

    **How it works:**
    1. For each LLM call, check cache for semantically similar prompt
    2. If cache hit: return cached response (skip LLM call)
    3. If cache miss: call LLM and get response
    4. If response has NO tool calls (final answer): store in cache
    5. If response has tool calls (intermediate): skip caching

    Only activated if SEMANTIC_CACHE_REDIS_URL or REDIS_URL environment variable is set.

    Example:
        ```python
        from ai_ops.helpers.deep_agent.middleware import SemanticCacheMiddleware
        from ai_ops.helpers.deep_agent.embedding_factory import create_embedding_model

        embed_model = create_embedding_model("deep_agent")
        middleware=[
            SemanticCacheMiddleware(
                embed_model=embed_model,
                ttl=3600,              # 1 hour cache TTL
                distance_threshold=0.05  # Semantic similarity threshold (stricter)
            )
        ]
        ```
    """

    def __init__(
        self, embed_model, ttl: int = 3600, distance_threshold: float = 0.05, cache_name: str = "deep_agent_llm_cache"
    ):
        """
        Initialize the semantic cache middleware.

        Args:
            embed_model: Embedding model instance (from embedding_factory)
            ttl: Time-to-live for cached entries in seconds (default: 3600)
            distance_threshold: Semantic similarity threshold 0-1 (default: 0.05, stricter)
            cache_name: Redis cache index name (default: "deep_agent_llm_cache")
        """
        super().__init__()
        # Try SEMANTIC_CACHE_REDIS_URL first, then fall back to REDIS_URL
        self.redis_url = os.getenv("SEMANTIC_CACHE_REDIS_URL") or os.getenv("REDIS_URL")
        self.embed_model = embed_model
        self.ttl = ttl
        self.distance_threshold = distance_threshold
        self.cache_name = cache_name
        self.cache = None
        self._initialized = False
        # Use list container for event-loop-aware lock management
        # This allows get_or_create_event_loop_lock to modify the reference
        self._init_lock: list = [None]

    async def _ensure_cache_initialized(self) -> bool:
        """Lazy initialization of cache. Returns True if available, False otherwise."""
        if self._initialized:
            return self.cache is not None

        # Get lock bound to current event loop
        # This prevents "bound to a different event loop" errors in Django async views
        lock = get_or_create_event_loop_lock(self._init_lock, "semantic_cache_init")

        async with lock:
            # Double-check after acquiring lock
            if self._initialized:
                return self.cache is not None

            if not self.redis_url:
                self._initialized = True
                logger.info("[SEMANTIC_CACHE] No Redis URL configured - semantic caching disabled")
                return False

            try:
                # Get embedding dimensions
                test_embedding = await asyncio.to_thread(self.embed_model.get_text_embedding, "test")
                embedding_dims = len(test_embedding)

                # Create custom async vectorizer
                class AsyncEmbeddingVectorizer(BaseVectorizer):
                    """Async vectorizer wrapping the embedding model."""

                    def __init__(self, embed_model, dims):
                        super().__init__(model="custom", dims=dims)
                        object.__setattr__(self, "embed_model", embed_model)

                    async def aembed(self, text: str, **kwargs):
                        return await asyncio.to_thread(self.embed_model.get_text_embedding, text)

                # Create cache with vectorizer
                vectorizer = AsyncEmbeddingVectorizer(self.embed_model, embedding_dims)

                def create_cache():
                    return SemanticCache(
                        name=self.cache_name,
                        ttl=self.ttl,
                        redis_url=self.redis_url,
                        distance_threshold=self.distance_threshold,
                        vectorizer=vectorizer,
                        overwrite=False,
                    )

                try:
                    self.cache = await asyncio.to_thread(create_cache)
                except Exception as e:
                    if "schema does not match" in str(e) or "Existing index" in str(e):
                        # Recreate with schema update
                        def create_cache_overwrite():
                            return SemanticCache(
                                name=self.cache_name,
                                ttl=self.ttl,
                                redis_url=self.redis_url,
                                distance_threshold=self.distance_threshold,
                                vectorizer=vectorizer,
                                overwrite=True,
                            )

                        self.cache = await asyncio.to_thread(create_cache_overwrite)
                    else:
                        raise

                self._initialized = True
                logger.info(
                    f"[SEMANTIC_CACHE] ✓ Initialized successfully "
                    f"(ttl={self.ttl}s, threshold={self.distance_threshold})"
                )
                return True

            except Exception as e:
                self.cache = None
                self._initialized = True
                logger.warning(f"[SEMANTIC_CACHE] ⚠ Initialization failed: {str(e)[:100]}")
                return False

    async def awrap_model_call(self, request, handler):
        """
        Async wrapper around model calls with semantic caching.

        Only caches FINAL responses (without tool calls), not intermediate
        planning, reasoning, or tool-calling steps.

        1. Call LLM first to get the response
        2. If response has tool_calls → Skip caching (intermediate step)
        3. If response has NO tool_calls → Check cache and store (final answer)

        Args:
            request: Model request containing the prompt and state
            handler: The LLM execution handler

        Returns:
            ModelResponse from cache or LLM
        """
        # Initialize cache (lazy loading)
        if not await self._ensure_cache_initialized() or not self.cache:
            return await handler(request)

        # Extract prompt from request state
        prompt = self._extract_prompt_from_state(request.state)
        if not prompt:
            return await handler(request)

        # Check semantic cache ONLY for final responses
        # We check cache before calling LLM to save costs
        cached_results = await self.cache.acheck(
            prompt=prompt, distance_threshold=self.distance_threshold, num_results=1
        )

        if cached_results:
            # Check if result is within similarity threshold
            result = cached_results[0]
            similarity = result.get("vector_distance", 0.0)

            if similarity <= self.distance_threshold:
                logger.info(
                    f"[SEMANTIC_CACHE] ✓ Cache HIT - similarity {similarity:.4f} <= threshold {self.distance_threshold}"
                )

                response_text = result.get("response", "")
                from langchain.agents.middleware import ModelResponse

                return ModelResponse(result=[AIMessage(content=response_text)], structured_response=None)

            logger.debug(
                f"[SEMANTIC_CACHE] ✗ Cache MISS - similarity {similarity:.4f} > threshold {self.distance_threshold}"
            )

        # Cache miss - call LLM to get response
        response = await handler(request)

        # Only cache if this is a FINAL response (no tool calls)
        if response.result and len(response.result) > 0:
            last_message = response.result[-1]

            # Check if this is a final response (no tool calls)
            has_tool_calls = (
                hasattr(last_message, "tool_calls") and last_message.tool_calls and len(last_message.tool_calls) > 0
            )

            if not has_tool_calls:
                # This is a final response - cache it
                response_content = self._extract_response_from_state({"messages": response.result})
                if response_content:
                    await self.cache.astore(prompt=prompt, response=response_content)
                    logger.debug("[SEMANTIC_CACHE] ✓ Stored FINAL response in semantic cache")
            else:
                logger.debug("[SEMANTIC_CACHE] ⊘ Skipped caching - intermediate step with tool calls")

        return response

    def _extract_prompt_from_state(self, state) -> Optional[str]:
        """Extract the user prompt from the agent state."""
        messages = state.get("messages", [])
        if not messages:
            return None

        # Get the last user message
        for message in reversed(messages):
            if hasattr(message, "type") and message.type == "human":
                return self._extract_text_content(message.content)

        return None

    def _extract_response_from_state(self, state) -> Optional[str]:
        """Extract the AI response from the agent state."""
        messages = state.get("messages", [])
        if not messages:
            return None

        # Get the last AI message
        for message in reversed(messages):
            if hasattr(message, "type") and message.type == "ai":
                return self._extract_text_content(message.content)

        return None

    def _extract_text_content(self, content) -> Optional[str]:
        """Extract text from various content formats."""
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            return " ".join(text_parts) if text_parts else None

        return None
