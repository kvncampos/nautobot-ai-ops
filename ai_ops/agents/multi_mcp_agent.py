"""Production Multi-MCP Agent implementation using langchain-mcp-adapters.

This is the production-ready agent that supports multiple MCP servers with
enterprise features including caching, health checks, and checkpointing.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Annotated, Callable

import httpx
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import add_messages
from typing_extensions import TypedDict

from ai_ops.helpers.common.asyncio_utils import get_or_create_event_loop_lock
from ai_ops.helpers.get_llm_model import get_llm_model_async
from ai_ops.helpers.logging_config import (
    generate_correlation_id,
    get_correlation_id,
    get_user,
    set_user,
)
from ai_ops.helpers.tool_callback import ToolLoggingCallback
from ai_ops.models import MCPServer

logger = logging.getLogger(__name__)

# Lazy lock initialization to avoid event loop binding issues
# Use list to allow modification via get_or_create_event_loop_lock
_cache_lock: list = [None]


# Application-level cache structure
_mcp_client_cache = {
    "client": None,
    "tools": None,
    "timestamp": None,
    "server_count": 0,
}

# Note: This module is used in both sync and async contexts.
# All ORM and Nautobot model access is wrapped with sync_to_async.
# Shutdown is handled via async_shutdown and atexit/signal handlers.


class MessagesState(TypedDict):
    """State for the agent graph.

    Uses add_messages reducer to properly handle message accumulation
    and persistence with checkpointers.
    """

    messages: Annotated[list[BaseMessage], add_messages]


async def get_or_create_mcp_client(force_refresh: bool = False) -> tuple[MultiServerMCPClient | None, list]:
    """Get or create MCP client with application-level caching.

    Args:
        force_refresh: Force cache refresh even if not expired

    Returns:
        Tuple of (client, tools) or (None, []) if no healthy servers
    """
    # Get lock bound to current event loop
    lock = get_or_create_event_loop_lock(_cache_lock, "mcp_cache_lock")

    try:
        async with lock:
            now = datetime.now()

            # Get cache TTL from default LLM model
            try:
                from asgiref.sync import sync_to_async

                from ai_ops.models import LLMModel

                default_model = await sync_to_async(LLMModel.get_default_model)()
                cache_ttl_seconds = default_model.cache_ttl
            except Exception as e:
                logger.warning(f"Failed to get cache TTL from default model, using 300s: {e}")
                cache_ttl_seconds = 300

            # Check cache validity
            if not force_refresh and _mcp_client_cache["client"] is not None:
                cache_age = (now - _mcp_client_cache["timestamp"]).total_seconds()
                if cache_age < cache_ttl_seconds:
                    logger.debug(f"Using cached MCP client (age: {cache_age:.1f}s, TTL: {cache_ttl_seconds}s)")
                    return _mcp_client_cache["client"], _mcp_client_cache["tools"]

            # Query for enabled, healthy MCP servers
            try:
                from asgiref.sync import sync_to_async
                from nautobot.extras.models import Status

                healthy_status = await sync_to_async(Status.objects.get)(name="Healthy")
                servers = await sync_to_async(list)(
                    MCPServer.objects.filter(
                        status__name="Healthy",
                        protocol="http",
                        status=healthy_status,
                    )
                )

                if not servers:
                    logger.warning("No enabled, healthy MCP servers found")
                    _mcp_client_cache.update(
                        {
                            "client": None,
                            "tools": [],
                            "timestamp": now,
                            "server_count": 0,
                        }
                    )
                    return None, []

                # Build connections dict for MultiServerMCPClient
                def httpx_client_factory(**kwargs):
                    """Factory for httpx client with SSL verification disabled.

                    Note: verify=False is intentional per requirements for connecting
                    to internal MCP servers with self-signed certificates.
                    Includes X-Correlation-ID and X-Nautobot-User headers for cross-service tracing.
                    """
                    # Get correlation ID and user from current context for cross-service tracing
                    correlation_id = get_correlation_id()
                    user = get_user()
                    headers = {}
                    if correlation_id:
                        headers["X-Correlation-ID"] = correlation_id
                    if user:
                        headers["X-Nautobot-User"] = user

                    return httpx.AsyncClient(
                        verify=False,  # noqa: S501 - intentional per requirements
                        headers=headers,
                        limits=httpx.Limits(
                            max_keepalive_connections=5,
                            max_connections=10,
                        ),
                    )

                connections = {}
                for server in servers:
                    # Build full MCP URL: base_url + mcp_endpoint
                    mcp_url = f"{server.url.rstrip('/')}{server.mcp_endpoint}"
                    connections[server.name] = {
                        "transport": "streamable_http",
                        "url": mcp_url,
                        "httpx_client_factory": httpx_client_factory,
                    }

                # Create MultiServerMCPClient
                client = MultiServerMCPClient(connections)
                tools = await client.get_tools()

                # Stage: mcp_connect - Log tool discovery
                logger.warning(f"[mcp_connect] discovered {len(tools)} tools from {len(servers)} server(s)")

                # Update cache
                _mcp_client_cache.update(
                    {
                        "client": client,
                        "tools": tools,
                        "timestamp": now,
                        "server_count": len(servers),
                    }
                )

                logger.info(f"[mcp_connect] cache updated: servers={len(servers)}, tools={len(tools)}")
                return client, tools

            except Exception as e:
                logger.error(f"Failed to create MCP client: {e}", exc_info=True)
                _mcp_client_cache.update(
                    {
                        "client": None,
                        "tools": [],
                        "timestamp": now,
                        "server_count": 0,
                    }
                )
                return None, []

    except RuntimeError as e:
        if "cannot schedule new futures after interpreter shutdown" in str(e):
            logger.warning(f"Cannot access MCP client during interpreter shutdown: {e}")
            return None, []
        else:
            raise
    except Exception as e:
        logger.error(f"Unexpected error in get_or_create_mcp_client: {e}", exc_info=True)
        return None, []


async def clear_mcp_cache() -> int:
    """Clear the MCP client cache.

    Returns:
        Number of servers that were cached (for audit logging)
    """
    # Get lock bound to current event loop
    lock = get_or_create_event_loop_lock(_cache_lock, "mcp_cache_lock")

    async with lock:
        cleared_count = _mcp_client_cache.get("server_count", 0)

        # Close existing client if present
        if _mcp_client_cache["client"] is not None:
            try:
                # MultiServerMCPClient cleanup if needed
                pass
            except Exception as e:
                logger.warning(f"Error closing MCP client: {e}")

        # Reset cache
        _mcp_client_cache.update(
            {
                "client": None,
                "tools": None,
                "timestamp": None,
                "server_count": 0,
            }
        )

        logger.info(f"Cleared MCP client cache (was tracking {cleared_count} server(s))")
        return cleared_count


async def warm_mcp_cache():
    """Warm the MCP client cache on application startup."""
    try:
        logger.info("Warming MCP client cache...")
        await get_or_create_mcp_client(force_refresh=True)
    except Exception as e:
        logger.warning(f"Failed to warm MCP cache on startup: {e}")
        # Don't raise - wait for scheduled health check


async def shutdown_mcp_client():
    """Gracefully shutdown MCP client and clear cache.

    This function should be called during application shutdown to ensure
    proper cleanup of async resources and prevent shutdown errors.
    """
    global _mcp_client_cache

    lock = get_or_create_event_loop_lock(_cache_lock, "mcp_cache_lock")

    try:
        async with lock:
            logger.info("Shutting down MCP client...")

            # Close existing client if present
            if _mcp_client_cache["client"] is not None:
                try:
                    # Attempt to close client connections gracefully
                    client = _mcp_client_cache["client"]
                    if hasattr(client, "close"):
                        await client.close()
                    elif hasattr(client, "aclose"):
                        await client.aclose()
                except Exception as e:
                    logger.warning(f"Error closing MCP client during shutdown: {e}")

            # Reset cache
            _mcp_client_cache.update(
                {
                    "client": None,
                    "tools": None,
                    "timestamp": None,
                    "server_count": 0,
                }
            )

            logger.info("MCP client shutdown completed")

    except RuntimeError as e:
        if "cannot schedule new futures after interpreter shutdown" in str(e):
            logger.warning(f"Cannot shutdown MCP client gracefully, interpreter already shutting down: {e}")
            # Force clear the cache without async operations
            _mcp_client_cache.update(
                {
                    "client": None,
                    "tools": None,
                    "timestamp": None,
                    "server_count": 0,
                }
            )
        else:
            logger.error(f"Runtime error during MCP client shutdown: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error during MCP client shutdown: {e}", exc_info=True)


async def build_agent(llm_model=None, checkpointer=None, provider: str | None = None):
    """Build agent using create_agent() API with middleware support.

    This is the new v2 approach that uses LangChain's create_agent() factory
    function with middleware support. Middleware are loaded from the database
    and applied in priority order.

    Args:
        llm_model: LLMModel instance. If None, uses the default model.
        checkpointer: Checkpointer instance for conversation persistence.
        provider: Optional provider name override. If specified, uses this provider for LLM initialization.

    Returns:
        Compiled graph ready for execution, or None if no default model available
    """
    logger.debug("Building agent with middleware and tools")

    from asgiref.sync import sync_to_async
    from langchain.agents import create_agent

    from ai_ops.helpers.get_middleware import get_middleware
    from ai_ops.helpers.get_prompt import get_active_prompt
    from ai_ops.models import LLMModel

    # Get LLM model
    if llm_model is None:
        llm_model = await sync_to_async(LLMModel.get_default_model)()

    # Get MCP client and tools
    client, tools = await get_or_create_mcp_client()

    # Log tool availability
    if tools:
        logger.debug(f"Loaded {len(tools)} MCP tools")
    else:
        logger.warning("No MCP tools available - agent will work for conversation only")

    # Get LLM model with optional provider override
    # If provider is specified, it will be used instead of the model's configured provider
    llm = await get_llm_model_async(model_name=llm_model.name, provider=provider)

    # Get middleware in priority order
    # Middleware are always instantiated fresh to prevent state leaks between conversations
    middleware = await get_middleware(llm_model)

    logger.info(f"Creating agent for {llm_model.name}: {len(tools)} tools, {len(middleware)} middleware")

    # Get system prompt from database or fallback to code-based prompt
    # Uses the SystemPrompt model with status='Approved' if available
    system_prompt = await sync_to_async(get_active_prompt)(llm_model)

    # Create agent with middleware
    # If no tools are available, the agent will still work for basic conversation
    tools_to_pass = tools if tools else []
    graph = create_agent(
        model=llm,
        tools=tools_to_pass,
        system_prompt=system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )

    return graph


async def process_message(
    user_input: str,
    thread_id: str,
    provider: str | None = None,
    username: str | None = None,
    cancellation_check: Callable[[], bool] | None = None,
) -> str:
    """Process a user message through the agent with checkpointed conversation history.

    This implementation follows Approach 1: compile graph per-request within checkpointer
    context manager. This ensures proper connection lifecycle management per LangGraph
    documentation best practices.

    Performance Note: Per-request compilation adds ~10-50ms latency compared to singleton
    pattern, but ensures proper context manager cleanup and connection management.
    If load testing shows unacceptable latency, consider Approach 2 (singleton with
    long-lived checkpointer + application shutdown hook).

    Connection Pooling Note: RedisSaver uses default connection settings. If experiencing
    high concurrent request volume, may need to tune max_connections or implement
    connection pooling. Monitor Redis connection count in production.

    Args:
        user_input: User's input message
        thread_id: Unique conversation thread identifier (e.g., session key)
        provider: Optional provider name override. If specified, uses this provider instead of default.
                 Only admin users should be allowed to specify this parameter.
        username: Optional username of the logged-in Nautobot user (for logging/debugging).
        cancellation_check: Optional callable that returns True if the request should be cancelled.
                           Used by ChatClearView to signal cancellation when user clears history.

    Returns:
        Assistant's response text
    """
    # Generate correlation ID for end-to-end request tracing
    correlation_id = generate_correlation_id()
    request_start_time = time.perf_counter()

    # Set user context for logging
    if username:
        set_user(username)

    logger.info(
        f"[request_start] thread={thread_id} correlation_id={correlation_id} "
        f"user={username or 'anonymous'} input_length={len(user_input)}"
    )

    # Check for cancellation before starting
    # TODO: Enhance with interrupt support within graph execution
    if cancellation_check and cancellation_check():
        logger.info(f"[request_cancelled] thread={thread_id} correlation_id={correlation_id} stage=pre_start")
        return "Request was cancelled. Starting fresh conversation."

    try:
        # Get timeout and recursion limit settings with sensible defaults
        from asgiref.sync import sync_to_async
        from nautobot.apps.config import get_app_settings_or_config

        request_timeout: int = (
            await sync_to_async(get_app_settings_or_config)("ai_ops", "agent_request_timeout_seconds") or 120
        )  # Default: 2 minutes
        recursion_limit: int = (
            await sync_to_async(get_app_settings_or_config)("ai_ops", "agent_recursion_limit") or 25
        )  # Default: 25 steps

        # Use context manager for proper checkpointer lifecycle
        from ai_ops.checkpointer import get_checkpointer, track_checkpoint_creation

        async with get_checkpointer() as checkpointer:
            # Handle case where checkpointer is None (during shutdown)
            if checkpointer is None:
                logger.warning("Checkpointer unavailable during shutdown, using stateless response")
                return "Server is currently shutting down. Please try again in a moment."

            # Track checkpoint creation for TTL enforcement
            track_checkpoint_creation(thread_id)

            # Check if this is a fresh conversation (no previous messages)
            # This happens after clearing conversation history or starting a new session
            config = {"configurable": {"thread_id": thread_id}}

            try:
                # DIAGNOSTIC: Log storage keys if available
                if hasattr(checkpointer, "storage"):
                    all_keys = list(checkpointer.storage.keys())
                    matching_keys = [k for k in all_keys if isinstance(k, tuple) and len(k) > 0 and k[0] == thread_id]
                    logger.info(
                        f"[STATE_CHECK] Storage has {len(all_keys)} total keys, {len(matching_keys)} match this thread"
                    )
                    logger.debug(f"[STATE_CHECK] Matching keys: {matching_keys}")

                # Type ignore: LangGraph accepts dict config but types show RunnableConfig
                state = await checkpointer.aget(config)  # type: ignore[arg-type]

                # DIAGNOSTIC: Log state check result
                state_exists = state is not None
                logger.info(f"[STATE_CHECK] State exists: {state_exists}")
                if state_exists:
                    logger.debug(f"[STATE_CHECK] State details: {state}")

            except Exception as e:
                logger.warning(f"[STATE_CHECK] Error checking conversation state: {e}")

            # Build agent v2 with checkpointer integration
            # If provider is specified, the LLM model selection will use it
            graph = await build_agent(checkpointer=checkpointer, provider=provider)

            # Configuration with thread_id for conversation isolation
            # Include recursion_limit from settings to prevent infinite loops
            config = {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}

            logger.debug(
                f"Processing message for thread: {thread_id} (timeout={request_timeout}s, recursion_limit={recursion_limit})"
            )

            # Check for cancellation before invoking the agent
            if cancellation_check and cancellation_check():
                logger.info(f"[request_cancelled] thread={thread_id} correlation_id={correlation_id} stage=pre_invoke")
                return "Request was cancelled. Starting fresh conversation."

            # Only pass the new user message
            # Graph automatically loads conversation history from checkpointer
            # Type ignore: LangGraph accepts dict config but types show RunnableConfig
            # Include ToolLoggingCallback for real-time tool call logging
            config["callbacks"] = [ToolLoggingCallback()]
            logger.info(f"[llm_invoke] thread={thread_id} correlation_id={correlation_id} timeout={request_timeout}s")

            # Wrap ainvoke with timeout to prevent long-running requests

            try:
                result = await asyncio.wait_for(
                    graph.ainvoke({"messages": [HumanMessage(content=user_input)]}, config=config),  # type: ignore[arg-type]
                    timeout=float(request_timeout),
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"[request_timeout] thread={thread_id} correlation_id={correlation_id} "
                    f"timeout_seconds={request_timeout}"
                )
                return (
                    f"Request timed out after {request_timeout} seconds. "
                    "Please try a simpler query or break your request into smaller parts."
                )

            # Check for cancellation immediately after agent invocation
            if cancellation_check and cancellation_check():
                logger.info(f"[request_cancelled] thread={thread_id} correlation_id={correlation_id} stage=post_invoke")
                return "Request was cancelled. Starting fresh conversation."

            # Log conversation state after processing
            logger.debug(f"Message processed for thread_id: {thread_id}, total messages: {len(result['messages'])}")

            # Stage: tool_call - Log summary of tool calls made
            tool_calls_made = []

            for message in result["messages"]:
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tc in message.tool_calls:
                        name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                        tool_calls_made.append(name)

            if tool_calls_made:
                logger.info(f"[tool_call] thread={thread_id} tools_used={tool_calls_made}")
            else:
                logger.debug(f"[tool_call] thread={thread_id} no_tools_used")

            # Stage: response - Extract and return final response
            # Find the last AI message that has actual content (not just tool calls)
            response_text = None
            for message in reversed(result["messages"]):
                # Check if it's an AI message with content (and not just tool calls)
                if hasattr(message, "content") and message.content:
                    # Skip messages that are only tool calls without text content
                    if hasattr(message, "tool_calls") and message.tool_calls and not message.content.strip():
                        continue
                    response_text = message.content
                    break

            # Fallback to last message if no suitable message found
            if response_text is None:
                response_text = result["messages"][-1].content if result["messages"] else "No response generated"

            # Log request completion with timing
            request_duration_ms = (time.perf_counter() - request_start_time) * 1000
            logger.info(
                f"[request_complete] thread={thread_id} correlation_id={correlation_id} "
                f"duration_ms={request_duration_ms:.1f} response_chars={len(response_text)} "
                f"tools_used={len(tool_calls_made)}"
            )
            return response_text

    except RuntimeError as e:
        if "cannot schedule new futures after interpreter shutdown" in str(e):
            logger.warning(f"Cannot process message during interpreter shutdown: {e}")
            return "Server is shutting down. Please try again in a moment."
        else:
            logger.error(f"Runtime error in process_message: {e}", exc_info=True)
            return f"Runtime error processing message: {str(e)}"
    except Exception as e:
        logger.error(f"Error in process_message: {e}", exc_info=True)
        return f"Error processing message: {str(e)}"


# TODO: Implement long-term memory (Store) integration
# When ready to implement cross-conversation memory:
# 1. Import get_store() from checkpointer.py
# 2. Use nested context managers:
#    async with get_store() as store, get_checkpointer() as checkpointer:
#        graph = workflow.compile(checkpointer=checkpointer, store=store)
# 3. Store user preferences, learned facts, etc. in the store
# 4. Query store in call_model() to retrieve relevant long-term memories
#
# Reference: https://docs.langchain.com/oss/python/langgraph/add-memory#example-using-redis-store
