"""Production Deep MCP Agent implementation using deepagents framework.

This agent provides advanced features from network-agent including:
- Langfuse LLM observability
- Tool error retry with backoff
- Subagent delegation
- Skills system
- Cross-conversation memory (Store)
- Connection pooling for checkpointers

Adapted to work with ai-ops's Django configuration and MCPServer model.

Observability Configuration:
- ENABLE_LANGFUSE: Enable Langfuse LLM observability (default: true)
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Callable

from asgiref.sync import sync_to_async
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ai_ops.helpers.deep_agent import (
    ToolErrorHandlerMiddleware,
    get_checkpointer,
    get_mcp_tools_with_auth,
    get_store,
    load_agents,
)
from ai_ops.helpers.get_llm_model import get_llm_model_async
from ai_ops.helpers.get_middleware import get_middleware
from ai_ops.helpers.get_prompt import get_active_prompt
from ai_ops.helpers.logging_config import (
    generate_correlation_id,
    set_user,
)
from ai_ops.models import LLMModel

logger = logging.getLogger(__name__)

# Agent configuration
AGENT_NAME = "deep_agent"
AGENT_DIR = Path(__file__).parent.parent  # ai_ops directory

# Initialize Langfuse observability
ENABLE_LANGFUSE = os.getenv("ENABLE_LANGFUSE", "true").lower() in ("true", "1", "yes")

langfuse_handler = None
if ENABLE_LANGFUSE:
    try:
        from langfuse.callback import CallbackHandler

        langfuse_handler = CallbackHandler(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )
        logger.info(f"[{AGENT_NAME}] ✓ Langfuse observability enabled")
    except Exception as e:
        logger.warning(f"[{AGENT_NAME}] ⚠ Failed to initialize Langfuse: {e}")
        langfuse_handler = None
else:
    logger.info(f"[{AGENT_NAME}] ℹ Langfuse observability disabled")


async def build_deep_agent(
    llm_model=None,
    provider: str | None = None,
    user_token: str | None = None,
):
    """
    Build deep agent using create_deep_agent() API with full feature set.

    This uses the deepagents framework which provides:
    - Native subagent delegation
    - Skills system from directory
    - Memory system with markdown files
    - Backend routing for file operations
    - Store integration for cross-conversation memory

    Args:
        llm_model: LLMModel instance. If None, uses the default model.
        provider: Optional provider name override.
        user_token: Bearer token for MCP authentication

    Returns:
        Compiled graph ready for execution

    Raises:
        Exception: If agent creation fails
    """
    logger.debug(f"[{AGENT_NAME}] Building deep agent with middleware and tools")
    logger.info(
        f"[{AGENT_NAME}] [build_deep_agent] user_token_provided={user_token is not None} token_length={len(user_token) if user_token else 0}"
    )

    try:
        # Get LLM model
        if llm_model is None:
            llm_model = await sync_to_async(LLMModel.get_default_model)()

        # Get LLM instance
        llm = await get_llm_model_async(model_name=llm_model.name, provider=provider)
        logger.info(f"[{AGENT_NAME}] ✓ LLM model initialized successfully: {type(llm).__name__}")

        # Get MCP tools with authentication
        if user_token:
            logger.info(f"[{AGENT_NAME}] [get_mcp_tools_with_auth] Attempting to retrieve MCP tools with user token")
            mcp_tools = await get_mcp_tools_with_auth(user_token, AGENT_NAME)
            logger.info(f"[{AGENT_NAME}] ✓ Retrieved {len(mcp_tools)} MCP tools")
        else:
            logger.warning(f"[{AGENT_NAME}] No user token provided - tools may fail authentication")
            mcp_tools = []
            logger.info(f"[{AGENT_NAME}] ✓ Using empty tools list (no token)")

        # Get checkpointer with connection pooling
        try:
            logger.info(f"[{AGENT_NAME}] [get_checkpointer] Attempting to create checkpointer...")
            checkpointer = await get_checkpointer(AGENT_NAME)
            logger.info(f"[{AGENT_NAME}] ✓ Checkpointer initialized: {type(checkpointer).__name__}")
        except Exception as checkpointer_error:
            logger.error(
                f"[{AGENT_NAME}] ✗ Checkpointer failed: {type(checkpointer_error).__name__}: {str(checkpointer_error)}",
                exc_info=True,
            )
            raise

        # Get store for cross-conversation memory
        try:
            logger.info(f"[{AGENT_NAME}] [get_store] Attempting to create store...")
            store = await get_store(AGENT_NAME)
            logger.info(f"[{AGENT_NAME}] ✓ Store initialized: {type(store).__name__}")
        except Exception as store_error:
            logger.error(
                f"[{AGENT_NAME}] ✗ Store failed: {type(store_error).__name__}: {str(store_error)}",
                exc_info=True,
            )
            raise

        # Get middleware from database (fresh instances to prevent state leaks)
        middleware = await get_middleware(llm_model)
        logger.info(f"[{AGENT_NAME}] ✓ Middleware loaded from database: {len(middleware)} middleware components")

        # Fallback to env vars if no DB middleware configured
        if len(middleware) == 0:
            logger.warning(f"[{AGENT_NAME}] No database middleware configured, using env var fallback")

            # Add tool error handler
            max_retries = int(os.getenv("TOOL_MAX_RETRIES", "2"))
            middleware.append(ToolErrorHandlerMiddleware(max_retries=max_retries))
            logger.info(f"[{AGENT_NAME}] Tool error handler enabled from env vars (max_retries={max_retries})")

        # Get system prompt with tool info injected
        system_prompt = await sync_to_async(get_active_prompt)(llm_model, tools=mcp_tools)

        # If no tools are available, add a note to the system prompt
        if not mcp_tools:
            system_prompt += "\n\nNote: You currently have no tools available. Respond directly to user queries without attempting to call any functions or tools."

        # For Anthropic models, structure system prompt as SystemMessage with explicit
        # cache_control breakpoints so the large system prompt is cached at the API level
        if isinstance(llm, ChatAnthropic):
            system_prompt_input = SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    },
                ]
            )
            logger.info(
                f"[{AGENT_NAME}] ✓ System prompt structured as SystemMessage with cache_control: {len(system_prompt)} chars"
            )
        else:
            system_prompt_input = system_prompt
            logger.info(f"[{AGENT_NAME}] ✓ System prompt loaded: {len(system_prompt)} chars")

        # Load subagents if configuration exists
        subagents_path = AGENT_DIR / "agents" / "subagents.yaml"
        subagents = await load_agents(str(subagents_path), tools={"mcp_tools": mcp_tools})
        logger.info(f"[{AGENT_NAME}] ✓ Subagents loaded: {len(subagents)} agents")

        # Get skills directory
        skills_dir = AGENT_DIR / "skills"
        skills_path = str(skills_dir) if skills_dir.exists() else None
        logger.info(f"[{AGENT_NAME}] ✓ Skills {'found' if skills_path else 'not found'}: {skills_path}")

        # Get memory directory for agent context
        memory_dir = AGENT_DIR / "memory"
        memory_files = []
        if memory_dir.exists():
            for memory_file in memory_dir.glob("*.md"):
                memory_files.append(str(memory_file))
        logger.info(f"[{AGENT_NAME}] ✓ Memory files loaded: {len(memory_files)} files")

        logger.info(
            f"[{AGENT_NAME}] Creating deep agent: "
            f"tools={len(mcp_tools)}, middleware={len(middleware)}, "
            f"subagents={len(subagents)}, skills={skills_path is not None}, "
            f"memory_files={len(memory_files)}"
        )
        logger.info(
            f"[{AGENT_NAME}] [create_deep_agent] Calling create_deep_agent with user_token={user_token is not None}"
        )

        # Create deep agent
        logger.info(f"[{AGENT_NAME}] [create_deep_agent] STARTING...")
        graph = create_deep_agent(
            tools=mcp_tools if mcp_tools else [],
            middleware=middleware,
            memory=memory_files if memory_files else None,
            skills=[skills_path] if skills_path else None,
            checkpointer=checkpointer,
            store=store,
            backend=lambda rt: CompositeBackend(
                default=FilesystemBackend(root_dir=str(AGENT_DIR), virtual_mode=True),
                routes={"/memories/": StoreBackend(rt)},
            ),
            model=llm,
            subagents=subagents if subagents else None,
            system_prompt=system_prompt_input,
        )
        logger.info(f"[{AGENT_NAME}] ✓ create_deep_agent completed successfully")

        # Configure recursion limit and add Langfuse callback if enabled
        # Callbacks at graph level propagate to all child runnables (including LLM model)
        agent_config = {"recursion_limit": 100}
        if langfuse_handler:
            agent_config["callbacks"] = [langfuse_handler]
            logger.info(f"[{AGENT_NAME}] ✓ Langfuse callback handler attached to graph")

        graph = graph.with_config(agent_config)
        logger.info(f"[{AGENT_NAME}] ✓ Graph configured with recursion_limit=100")

        logger.info(f"[{AGENT_NAME}] ✓✓✓ Deep agent created successfully ✓✓✓")
        return graph

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] Failed to build deep agent: {str(e)}", exc_info=True)
        raise


async def process_message(
    user_input: str,
    thread_id: str,
    provider: str | None = None,
    username: str | None = None,
    user_token: str | None = None,
    cancellation_check: Callable[[], bool] | None = None,
) -> str:
    """
    Asynchronously processes a user message using the deep agent.

    Args:
        user_input: The user's input message to process.
        thread_id: Identifier for the conversation thread.
        provider: Optional provider to use for processing.
        username: The username associated with the request.
        user_token: Bearer token for MCP authentication.
        cancellation_check: A callable that returns True if the request should be cancelled.

    Returns:
        str: The response generated by the deep agent.

    Raises:
        Exception: Logs and returns an error message if processing fails.
    """
    correlation_id = generate_correlation_id()
    request_start_time = time.perf_counter()

    if username:
        set_user(username)

    logger.info(
        f"[{AGENT_NAME}] [RequestStart] correlation_id={correlation_id} "
        f"thread={thread_id} user={username or 'anonymous'} input_len={len(user_input)}"
    )

    if cancellation_check and cancellation_check():
        return "Request was cancelled. Starting fresh conversation."

    try:
        # Build agent with current user token
        graph = await build_deep_agent(provider=provider, user_token=user_token)

        # Configure runtime
        config = RunnableConfig(configurable={"thread_id": thread_id}, tags=["deep-agent", "mcp"])

        # Execute with timeout
        result = await asyncio.wait_for(
            graph.ainvoke({"messages": [HumanMessage(content=user_input)]}, config=config), timeout=120
        )

        # Extract response
        last_message = result["messages"][-1]
        response_text = getattr(last_message, "content", None) or "No response generated"

        duration_ms = (time.perf_counter() - request_start_time) * 1000

        # Log prompt cache performance metrics if available (Anthropic)
        usage_metadata = getattr(last_message, "usage_metadata", None)
        if usage_metadata:
            cache_creation = usage_metadata.get("cache_creation_input_tokens", 0)
            cache_read = usage_metadata.get("cache_read_input_tokens", 0)
            input_tokens = usage_metadata.get("input_tokens", 0)
            logger.info(
                f"[{AGENT_NAME}] [CacheMetrics] correlation_id={correlation_id} "
                f"cache_creation={cache_creation} cache_read={cache_read} "
                f"input_tokens={input_tokens}"
            )

        logger.info(f"[{AGENT_NAME}] [RequestCompleted] correlation_id={correlation_id} duration_ms={duration_ms:.1f}")

        return str(response_text)

    except asyncio.TimeoutError:
        logger.error(f"[{AGENT_NAME}] [timeout] correlation_id={correlation_id}")
        return "Request timed out after 120 seconds. Please try a simpler query."

    except RuntimeError as e:
        # Handle event loop errors (closed loop, wrong loop, etc.)
        if "event loop" in str(e).lower() or "loop" in str(e).lower():
            logger.error(
                f"[{AGENT_NAME}] [event_loop_error] correlation_id={correlation_id} "
                f"details={e}. This may indicate cached resources bound to a closed event loop.",
                exc_info=True,
            )
            # Clear cached resources to force recreation on next request
            from ai_ops.helpers.deep_agent.checkpoint_factory import _connection_pools, _redis_checkpointers
            from ai_ops.helpers.deep_agent.store_factory import _redis_stores

            # Clear caches to force fresh connections next time
            _redis_checkpointers.clear()
            _connection_pools.clear()
            _redis_stores.clear()
            logger.warning(f"[{AGENT_NAME}] Cleared cached checkpointers and stores due to event loop error")

            return (
                "An internal error occurred (event loop issue). "
                "The system has been reset. Please try your request again."
            )
        else:
            # Re-raise if not an event loop error
            raise

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] [error] correlation_id={correlation_id} details={e}", exc_info=True)
        return f"Error processing message: {str(e)}"


async def shutdown_deep_agent():
    """
    Gracefully shutdown deep agent resources.

    This should be called during application shutdown to ensure
    proper cleanup of:
    - Connection pools
    - Redis connections
    - Store instances
    """
    logger.info(f"[{AGENT_NAME}] Shutting down deep agent resources...")

    try:
        from ai_ops.helpers.deep_agent.checkpoint_factory import close_all_pools
        from ai_ops.helpers.deep_agent.store_factory import close_all_stores

        await close_all_pools()
        await close_all_stores()

        logger.info(f"[{AGENT_NAME}] Shutdown completed successfully")

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] Error during shutdown: {e}", exc_info=True)
