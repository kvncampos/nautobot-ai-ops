"""Production Multi-MCP Agent implementation using langchain-mcp-adapters.

This is the production-ready agent that supports multiple MCP servers with
enterprise features including caching, health checks, and checkpointing.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Callable

import httpx
from asgiref.sync import sync_to_async
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient

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


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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

    from langchain.agents import create_agent

    from ai_ops.helpers.get_middleware import get_middleware
    from ai_ops.helpers.get_prompt import get_active_prompt
    from ai_ops.models import LLMModel

    # Get LLM model
    if llm_model is None:
        llm_model = await sync_to_async(LLMModel.get_default_model)()

    # Get MCP client and tools
    client, tools = await get_or_create_mcp_client()

    # Get LLM model with optional provider override
    # If provider is specified, it will be used instead of the model's configured provider
    llm = await get_llm_model_async(model_name=llm_model.name, provider=provider)

    # Get middleware in priority order
    # Middleware are always instantiated fresh to prevent state leaks between conversations
    middleware = await get_middleware(llm_model)

    logger.info(f"Creating agent for {llm_model.name}: {len(tools)} tools, {len(middleware)} middleware")

    # Get system prompt from database or fallback to code-based prompt
    # Uses the SystemPrompt model with status='Approved' if available
    # Inject tool info into the prompt for LLM grounding
    system_prompt = await sync_to_async(get_active_prompt)(llm_model, tools=tools)

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
    """
    Asynchronously processes a user message within a conversational thread using a specified provider and optional user context.

    Args:
        user_input (str): The user's input message to process.
        thread_id (str): Identifier for the conversation thread.
        provider (str | None, optional): The provider to use for processing the message. Defaults to None.
        username (str | None, optional): The username associated with the request. Defaults to None.
        cancellation_check (Callable[[], bool] | None, optional): A callable that returns True if the request should be cancelled. Defaults to None.

    Returns:
        str: The response generated by the agent, or an error/cancellation message.

    Raises:
        Exception: Logs and returns an error message if message processing fails.
    """
    correlation_id = generate_correlation_id()
    request_start_time = time.perf_counter()

    if username:
        set_user(username)

    logger.info(
        f"[RequestStart] correlation_id={correlation_id} thread={thread_id} user={username or 'anonymous'} input_len={len(user_input)}"
    )

    if cancellation_check and cancellation_check():
        return "Request was cancelled. Starting fresh conversation."

    try:
        from ai_ops.checkpointer import get_checkpointer

        async with get_checkpointer() as checkpointer:
            graph = await build_agent(checkpointer=checkpointer, provider=provider)

            config = RunnableConfig(
                configurable={"thread_id": thread_id}, callbacks=[ToolLoggingCallback()], tags=["mcp-agent"]
            )

            result = await asyncio.wait_for(
                graph.ainvoke({"messages": [HumanMessage(content=user_input)]}, config=config), timeout=120
            )

            last_message = result["messages"][-1]
            response_text = getattr(last_message, "content", None) or "No response generated"

            logger.info(
                f"[RequestCompleted] correlation_id={correlation_id} duration_ms={(time.perf_counter() - request_start_time) * 1000:.1f}"
            )
            return str(response_text)

    except Exception as e:
        logger.error(f"[error] correlation_id={correlation_id} details={e}", exc_info=True)
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
