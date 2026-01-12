"""Production Multi-MCP Agent implementation using langchain-mcp-adapters.

This is the production-ready agent that supports multiple MCP servers with
enterprise features including caching, health checks, and checkpointing.
"""

import logging
from datetime import datetime
from typing import Annotated

import httpx
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from ai_ops.helpers.common.asyncio_utils import get_or_create_event_loop_lock
from ai_ops.helpers.get_llm_model import get_llm_model_async
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
                    """
                    return httpx.AsyncClient(
                        verify=False,  # noqa: S501 - intentional per requirements
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

                # DIAGNOSTIC: Log MCP tool discovery details
                logger.warning(
                    f"[TOOL DEBUG] MCP client.get_tools() returned {len(tools)} tools from {len(servers)} server(s)"
                )
                if tools:
                    logger.warning(f"[TOOL DEBUG] Raw tool names from MCP: {[tool.name for tool in tools]}")
                    for idx, tool in enumerate(tools[:3], 1):  # Log first 3 tools in detail
                        logger.warning(f"[TOOL DEBUG]   MCP Tool #{idx}: {tool.name}")
                        if hasattr(tool, "description"):
                            desc = tool.description[:80] + "..." if len(tool.description) > 80 else tool.description
                            logger.warning(f"[TOOL DEBUG]     Description: {desc}")
                else:
                    logger.warning("[TOOL DEBUG] !!!!! MCP client.get_tools() RETURNED EMPTY LIST !!!!!")

                # Update cache
                _mcp_client_cache.update(
                    {
                        "client": client,
                        "tools": tools,
                        "timestamp": now,
                        "server_count": len(servers),
                    }
                )

                logger.info(f"Created MCP client with {len(servers)} server(s), {len(tools)} tool(s)")
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


async def build_agent(
    llm_model=None, checkpointer=None, provider: str | None = None, force_middleware_refresh: bool = False
):
    """Build agent using create_agent() API with middleware support.

    This is the new v2 approach that uses LangChain's create_agent() factory
    function with middleware support. Middleware are loaded from the database
    and applied in priority order.

    Args:
        llm_model: LLMModel instance. If None, uses the default model.
        checkpointer: Checkpointer instance for conversation persistence.
        provider: Optional provider name override. If specified, uses this provider for LLM initialization.
        force_middleware_refresh: If True, bypass cache and reload middleware from database.
                                 Useful when clearing conversation history to reset stateful middleware.

    Returns:
        Compiled graph ready for execution, or None if no default model available
    """
    # DIAGNOSTIC: Log function entry with all parameters
    logger.warning("[TOOL DEBUG] ========== build_agent() CALLED ==========")
    logger.warning(
        f"[TOOL DEBUG] Parameters: llm_model={llm_model}, provider={provider}, force_middleware_refresh={force_middleware_refresh}, has_checkpointer={checkpointer is not None}"
    )

    from asgiref.sync import sync_to_async
    from langchain.agents import create_agent

    from ai_ops.helpers.get_middleware import get_middleware
    from ai_ops.models import LLMModel
    from ai_ops.prompts.multi_mcp_system_prompt import get_multi_mcp_system_prompt

    # Get LLM model
    if llm_model is None:
        llm_model = await sync_to_async(LLMModel.get_default_model)()
        logger.warning(f"[TOOL DEBUG] Using default LLM model: {llm_model.name}")

    # Get MCP client and tools (may be empty if no MCP servers configured)
    logger.warning("[TOOL DEBUG] About to call get_or_create_mcp_client()...")
    client, tools = await get_or_create_mcp_client()
    logger.warning("[TOOL DEBUG] get_or_create_mcp_client() COMPLETED")

    # DIAGNOSTIC: Log tool loading details
    logger.warning(
        f"[TOOL DEBUG] get_or_create_mcp_client() returned: client={client is not None}, tools_count={len(tools) if tools else 0}"
    )
    if tools:
        logger.warning(f"[TOOL DEBUG] Tool types: {[type(tool).__name__ for tool in tools]}")
        logger.warning(f"[TOOL DEBUG] Tool names: {[tool.name for tool in tools]}")

        # Log detailed info for each tool
        logger.warning("[TOOL DEBUG] Detailed tool information:")
        for idx, tool in enumerate(tools, 1):
            logger.warning(f"[TOOL DEBUG]   Tool #{idx}:")
            logger.warning(f"[TOOL DEBUG]     - Name: {tool.name}")
            logger.warning(f"[TOOL DEBUG]     - Type: {type(tool).__name__}")
            if hasattr(tool, "description"):
                desc_preview = tool.description[:100] + "..." if len(tool.description) > 100 else tool.description
                logger.warning(f"[TOOL DEBUG]     - Description: {desc_preview}")
            if hasattr(tool, "args_schema"):
                logger.warning(f"[TOOL DEBUG]     - Has args_schema: {tool.args_schema is not None}")
                if tool.args_schema:
                    # Try to get schema fields
                    try:
                        if hasattr(tool.args_schema, "schema"):
                            schema = tool.args_schema.schema()
                            if "properties" in schema:
                                logger.warning(f"[TOOL DEBUG]     - Schema fields: {list(schema['properties'].keys())}")
                    except Exception as e:
                        logger.warning(f"[TOOL DEBUG]     - Could not extract schema fields: {e}")
    else:
        logger.warning("[TOOL DEBUG] !!!!! NO TOOLS RETURNED FROM get_or_create_mcp_client() !!!!!")

    # Get LLM model with optional provider override
    # If provider is specified, it will be used instead of the model's configured provider
    llm = await get_llm_model_async(model_name=llm_model.name, provider=provider)

    # DIAGNOSTIC: Log LLM temperature to verify it's set correctly
    if hasattr(llm, "temperature"):
        logger.info(f"LLM temperature: {llm.temperature}")
    elif hasattr(llm, "model_kwargs") and "temperature" in llm.model_kwargs:
        logger.info(f"LLM temperature: {llm.model_kwargs['temperature']}")

    # DIAGNOSTIC: Check if LLM supports tool calling
    logger.info(f"[TOOL DEBUG] LLM type: {type(llm).__name__}, has bind_tools: {hasattr(llm, 'bind_tools')}")

    # Get middleware in priority order
    # Force refresh if requested (e.g., after clearing conversation history)
    # This ensures stateful middleware like SummarizationMiddleware starts fresh
    middleware = await get_middleware(llm_model, force_refresh=force_middleware_refresh)

    log_msg = f"Building agent v2 for model {llm_model.name} with {len(middleware)} middleware and {len(tools)} tools"
    if provider:
        log_msg += f" (provider override: {provider})"
    if force_middleware_refresh:
        log_msg += " (middleware refreshed)"
    logger.info(log_msg)

    # DIAGNOSTIC: Log tool details to verify they're available
    if tools:
        tool_names = [tool.name for tool in tools]
        logger.info(f"Available tools: {tool_names}")
    else:
        logger.warning("No MCP tools available - agent will not be able to access Nautobot data")

    # Generate dynamic system prompt with actual tool information and model name
    system_prompt = get_multi_mcp_system_prompt(model_name=llm_model.name)

    # DIAGNOSTIC: Log a snippet of the system prompt to verify tool descriptions are included
    prompt_preview = system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt
    logger.debug(f"System prompt preview: {prompt_preview}")

    # DIAGNOSTIC: Log what we're passing to create_agent
    tools_to_pass = tools if tools else []
    logger.info(f"[TOOL DEBUG] Passing {len(tools_to_pass)} tools to create_agent()")
    logger.info(
        f"[TOOL DEBUG] create_agent parameters: model={type(llm).__name__}, tools_count={len(tools_to_pass)}, has_system_prompt={bool(system_prompt)}, middleware_count={len(middleware)}, has_checkpointer={checkpointer is not None}"
    )

    # Create agent with middleware
    # If no tools are available, the agent will still work for basic conversation
    graph = create_agent(
        model=llm,
        tools=tools_to_pass,
        system_prompt=system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )

    logger.info(f"[TOOL DEBUG] create_agent() returned: {type(graph).__name__}")

    return graph


async def build_workflow() -> StateGraph | None:
    """Build the LangGraph workflow without compiling.

    DEPRECATED: This function is no longer used. Use build_agent() instead.

    This older approach manually constructs the workflow and doesn't properly
    integrate the checkpointer, leading to loss of conversation context.

    Kept temporarily for reference - safe to delete after migration verification.

    This creates the workflow structure that will be compiled per-request
    with the checkpointer context manager. Removed singleton pattern to
    allow proper context manager lifecycle per LangGraph documentation.

    Returns:
        StateGraph: Uncompiled workflow, or None if no MCP tools available
    """
    # Get MCP client and tools
    client, tools = await get_or_create_mcp_client()

    if not client or not tools:
        logger.warning("Cannot build workflow without MCP tools")
        return None

    # Initialize LLM
    llm = await get_llm_model_async()
    llm_with_tools = llm.bind_tools(tools)

    # Define agent logic
    def call_model(state: MessagesState):
        from langchain_core.messages import SystemMessage

        from ai_ops.prompts.multi_mcp_system_prompt import get_multi_mcp_system_prompt

        messages = state["messages"]

        # Add system prompt if not already present
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            system_message = SystemMessage(content=get_multi_mcp_system_prompt())
            messages = [system_message] + messages

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # Build graph
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        lambda state: "tools" if state["messages"][-1].tool_calls else "__end__",
    )
    workflow.add_edge("tools", "agent")

    logger.debug("Built LangGraph workflow structure")
    return workflow


async def process_message(user_input: str, thread_id: str, provider: str | None = None) -> str:
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

    Returns:
        Assistant's response text
    """
    try:
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

            # DIAGNOSTIC: Log thread_id details before state check
            logger.info(f"[STATE_CHECK] Checking state for thread_id: '{thread_id}' (type: {type(thread_id).__name__})")

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

                # Force middleware refresh if no previous state exists
                # This ensures stateful middleware (e.g., SummarizationMiddleware) starts clean
                force_middleware_refresh = state is None
                if force_middleware_refresh:
                    logger.info(
                        f"[STATE_CHECK] Fresh conversation detected for thread {thread_id}, forcing middleware refresh"
                    )
            except Exception as e:
                logger.warning(f"[STATE_CHECK] Error checking conversation state: {e}")
                force_middleware_refresh = False

            # Build agent v2 with checkpointer integration
            # If provider is specified, the LLM model selection will use it
            graph = await build_agent(
                checkpointer=checkpointer, provider=provider, force_middleware_refresh=force_middleware_refresh
            )

            # Configuration with thread_id for conversation isolation
            config = {"configurable": {"thread_id": thread_id}}

            # Log conversation state before processing
            log_msg = f"Processing message for thread_id: {thread_id}"
            if provider:
                log_msg += f", provider override: {provider}"
            logger.debug(log_msg)

            # Only pass the new user message
            # Graph automatically loads conversation history from checkpointer
            # Type ignore: LangGraph accepts dict config but types show RunnableConfig
            logger.info(f"Invoking graph for thread_id: {thread_id} with user input: {user_input[:100]}...")
            result = await graph.ainvoke({"messages": [HumanMessage(content=user_input)]}, config=config)  # type: ignore[arg-type]

            # Log conversation state after processing
            logger.debug(f"Message processed for thread_id: {thread_id}, total messages: {len(result['messages'])}")

            # DIAGNOSTIC: Check if any tool calls were made and log args for traceability
            tool_calls_made = []
            for message in result["messages"]:
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tc in message.tool_calls:
                        name = tc.get("name", "unknown")
                        args = tc.get("args")
                        tool_calls_made.append(name)
                        logger.info("[TOOL CALL] thread=%s tool=%s args=%s", thread_id, name, args)
            if tool_calls_made:
                logger.info("Tools used in this request (thread=%s): %s", thread_id, tool_calls_made)
            else:
                logger.warning("No tools were used for user query (thread=%s): %s", thread_id, user_input[:100])

            # Extract response from last message
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
