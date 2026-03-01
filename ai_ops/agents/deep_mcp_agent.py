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
- ENABLE_LANGFUSE: Enable Langfuse LLM observability (default: false, must be explicitly enabled)
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, cast

from asgiref.sync import sync_to_async
from deepagents import CompiledSubAgent, SubAgent, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ai_ops.helpers.deep_agent import (
    ToolErrorHandlerMiddleware,
    get_checkpointer,
    get_mcp_tools,
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

__all__ = ["build_deep_agent", "process_message", "shutdown_deep_agent", "warmup_deep_agent_connections"]

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------

AGENT_NAME = "deep_agent"
AGENT_DIR = Path(__file__).parent.parent  # ai_ops/ directory

# Execution limits — override via env vars without code changes
REQUEST_TIMEOUT_SECS: int = int(os.getenv("AGENT_REQUEST_TIMEOUT", "120"))
RECURSION_LIMIT: int = int(os.getenv("AGENT_RECURSION_LIMIT", "100"))

# Langfuse observability — opt-in only; never enabled by default
ENABLE_LANGFUSE: bool = os.getenv("ENABLE_LANGFUSE", "false").lower() in ("true", "1", "yes", "on")


class _AgentLogger(logging.LoggerAdapter):
    """LoggerAdapter that automatically prepends ``[<agent_name>]`` to every message.

    Eliminates the manual ``f"[{AGENT_NAME}] ..."`` prefix on every log call and
    enables ``%``-style lazy formatting throughout the module (Ruff G004).
    """

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:  # type: ignore[override]
        name = (self.extra or {}).get("name", AGENT_NAME)
        return f"[{name}] {msg}", kwargs


_log = _AgentLogger(logging.getLogger(__name__), {"name": AGENT_NAME})


def _get_langfuse_handler():
    """Return a Langfuse ``CallbackHandler``, or ``None`` if disabled / unavailable.

    Initialised lazily rather than at module import time so that:
    - Tests that import this module never trigger network connectivity.
    - Missing env vars only raise an issue when the feature is actually used.

    Returns:
        A ``langfuse.callback.CallbackHandler`` instance, or ``None``.
    """
    if not ENABLE_LANGFUSE:
        return None
    try:
        from langfuse.callback import CallbackHandler

        return CallbackHandler(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )
    except Exception as exc:
        _log.warning("Failed to initialize Langfuse: %s", exc)
        return None


async def build_deep_agent(
    llm_model: "LLMModel | None" = None,
    provider: str | None = None,
    user_token: str | None = None,
) -> Any:
    """Build and return a compiled deep agent graph.

    Uses the deepagents framework which provides:
    - Native subagent delegation
    - Skills system from directory
    - Memory system with markdown files
    - Backend routing for file operations
    - Store integration for cross-conversation memory

    Args:
        llm_model: LLMModel instance. If ``None``, the default model is used.
        provider: Optional LLM provider name override.
        user_token: Bearer token for MCP authentication.

    Returns:
        A compiled LangGraph runnable ready for ``ainvoke``.

    Raises:
        Exception: Re-raised if any component (checkpointer, store, graph) fails to initialise.
    """
    _log.debug("Building deep agent (user_token=%s)", user_token is not None)
    _log.info(
        "[build_deep_agent] user_token_provided=%s token_length=%d",
        user_token is not None,
        len(user_token) if user_token else 0,
    )

    try:
        # Resolve LLM model
        if llm_model is None:
            llm_model = await sync_to_async(LLMModel.get_default_model)()

        llm = await get_llm_model_async(model_name=llm_model.name, provider=provider)
        _log.info("LLM model initialised: %s", type(llm).__name__)

        # Retrieve MCP tools — pass user_token only when present to preserve
        # backwards compatibility with implementations that don't accept the kwarg.
        _log.info("[get_mcp_tools] Retrieving MCP tools (authenticated=%s)", bool(user_token))
        mcp_tool_kwargs: dict = {"user_token": user_token} if user_token else {}
        mcp_tools = await get_mcp_tools(agent_name=AGENT_NAME, **mcp_tool_kwargs)
        _log.info("Retrieved %d MCP tools", len(mcp_tools))

        # Checkpointer — connection-pooled
        try:
            _log.info("[get_checkpointer] Initialising checkpointer...")
            checkpointer = await get_checkpointer(AGENT_NAME)
            _log.info("Checkpointer initialised: %s", type(checkpointer).__name__)
        except Exception as checkpointer_error:
            _log.error(
                "Checkpointer failed: %s: %s",
                type(checkpointer_error).__name__,
                checkpointer_error,
                exc_info=True,
            )
            raise

        # Store — cross-conversation memory
        try:
            _log.info("[get_store] Initialising store...")
            store = await get_store(AGENT_NAME)
            _log.info("Store initialised: %s", type(store).__name__)
        except Exception as store_error:
            _log.error(
                "Store failed: %s: %s",
                type(store_error).__name__,
                store_error,
                exc_info=True,
            )
            raise

        # Middleware — loaded fresh from DB to prevent state leaks across requests
        middleware = await get_middleware(llm_model)
        _log.info("Middleware loaded: %d component(s)", len(middleware))

        if not middleware:
            _log.warning("No DB middleware configured — falling back to env var defaults")
            max_retries = int(os.getenv("TOOL_MAX_RETRIES", "2"))
            middleware.append(ToolErrorHandlerMiddleware(max_retries=max_retries))
            _log.info("Tool error handler added (max_retries=%d)", max_retries)

        # System prompt
        system_prompt = await sync_to_async(get_active_prompt)(llm_model, tools=mcp_tools)
        if not mcp_tools:
            system_prompt += (
                "\n\nNote: You currently have no tools available. "
                "Respond directly to user queries without attempting to call any functions or tools."
            )

        # Wrap system prompt for Anthropic prompt-caching
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
            _log.info("System prompt wrapped as SystemMessage with cache_control (%d chars)", len(system_prompt))
        else:
            system_prompt_input = system_prompt
            _log.info("System prompt loaded (%d chars)", len(system_prompt))

        # Subagents
        subagents_path = AGENT_DIR / "agents" / "subagents.yaml"
        subagents = cast(
            list[SubAgent | CompiledSubAgent],
            await load_agents(str(subagents_path), tools={"mcp_tools": mcp_tools}),
        )
        _log.info("Subagents loaded: %d", len(subagents))

        # Skills — virtual path relative to FilesystemBackend root_dir (AGENT_DIR)
        skills_dir = AGENT_DIR / "skills"
        skills_path = "/skills" if skills_dir.exists() else None
        _log.info("Skills path: %s", skills_path or "<not found>")

        # Memory files — virtual paths relative to FilesystemBackend root_dir (AGENT_DIR)
        memory_dir = AGENT_DIR / "memory"
        memory_files = [f"/memory/{f.name}" for f in memory_dir.glob("*.md")] if memory_dir.exists() else []
        _log.info("Memory files: %d", len(memory_files))

        _log.info(
            "Creating deep agent — tools=%d middleware=%d subagents=%d skills=%s memory=%d",
            len(mcp_tools),
            len(middleware),
            len(subagents),
            skills_path is not None,
            len(memory_files),
        )

        graph = create_deep_agent(
            tools=mcp_tools or [],
            middleware=middleware,
            memory=memory_files or None,
            skills=[skills_path] if skills_path else None,
            checkpointer=checkpointer,
            store=store,
            backend=lambda rt: CompositeBackend(
                default=FilesystemBackend(root_dir=str(AGENT_DIR), virtual_mode=True),
                routes={"/memories/": StoreBackend(rt)},
            ),
            model=llm,
            subagents=subagents or None,
            system_prompt=system_prompt_input,
        )

        # Attach Langfuse callback and set recursion guard.
        # Callbacks at graph level propagate to all child runnables (including LLM).
        agent_config = RunnableConfig(recursion_limit=RECURSION_LIMIT)
        langfuse_handler = _get_langfuse_handler()
        if langfuse_handler:
            agent_config["callbacks"] = [langfuse_handler]
            _log.info("Langfuse callback attached to graph")

        graph = graph.with_config(agent_config)
        _log.info("Graph configured (recursion_limit=%d)", RECURSION_LIMIT)
        _log.info("Deep agent created successfully")
        return graph

    except Exception as exc:
        _log.error("Failed to build deep agent: %s", exc, exc_info=True)
        raise


async def process_message(
    user_input: str,
    thread_id: str,
    provider: str | None = None,
    username: str | None = None,
    user_token: str | None = None,
    cancellation_check: Callable[[], bool] | None = None,
) -> str:
    """Process a user message with the deep agent and return the response text.

    Args:
        user_input: The user's input message.
        thread_id: Conversation thread identifier (used for checkpointing).
        provider: Optional LLM provider override.
        username: Username associated with the request (used for logging/audit).
        user_token: Bearer token for MCP authentication.
        cancellation_check: Callable that returns ``True`` when the request
            should be aborted before execution begins.

    Returns:
        The agent's response as a plain string. Returns a user-friendly error
        message string on failure rather than raising, so callers can surface
        it directly to the user.
    """
    correlation_id = generate_correlation_id()
    request_start_time = time.perf_counter()

    if username:
        set_user(username)

    _log.info(
        "[RequestStart] correlation_id=%s thread=%s user=%s input_len=%d",
        correlation_id,
        thread_id,
        username or "anonymous",
        len(user_input),
    )

    if cancellation_check and cancellation_check():
        return "Request was cancelled. Starting fresh conversation."

    try:
        graph = await build_deep_agent(provider=provider, user_token=user_token)

        config = RunnableConfig(configurable={"thread_id": thread_id}, tags=["deep-agent", "mcp"])

        result = await asyncio.wait_for(
            graph.ainvoke({"messages": [HumanMessage(content=user_input)]}, config=config),
            timeout=REQUEST_TIMEOUT_SECS,
        )

        # Extract response text — handle both plain string and Anthropic structured
        # content (list of typed content blocks).
        last_message = result["messages"][-1]
        raw_content = getattr(last_message, "content", None)
        if isinstance(raw_content, list):
            # Flatten text blocks; skip tool_use and other non-text block types.
            response_text = (
                " ".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in raw_content
                    if not isinstance(block, dict) or block.get("type") == "text"
                )
                or "No response generated"
            )
        else:
            response_text = raw_content or "No response generated"

        duration_ms = (time.perf_counter() - request_start_time) * 1000

        # Log Anthropic prompt-cache performance metrics when available.
        # Guard with hasattr to handle varying UsageMetadata implementations.
        usage_metadata = getattr(last_message, "usage_metadata", None)
        if usage_metadata and hasattr(usage_metadata, "get"):
            _log.info(
                "[CacheMetrics] correlation_id=%s cache_creation=%s cache_read=%s input_tokens=%s",
                correlation_id,
                usage_metadata.get("cache_creation_input_tokens", 0),
                usage_metadata.get("cache_read_input_tokens", 0),
                usage_metadata.get("input_tokens", 0),
            )

        _log.info("[RequestCompleted] correlation_id=%s duration_ms=%.1f", correlation_id, duration_ms)
        return str(response_text)

    except asyncio.TimeoutError:
        _log.error("[timeout] correlation_id=%s", correlation_id)
        return f"Request timed out after {REQUEST_TIMEOUT_SECS} seconds. Please try a simpler query."

    except RuntimeError as exc:
        # Handle asyncio event-loop errors that occur when cached async resources
        # (checkpointers, stores) were bound to a now-closed event loop.
        if "event loop" in str(exc).lower() or "loop" in str(exc).lower():
            _log.error(
                "[event_loop_error] correlation_id=%s — cached resources may be bound to a closed event loop: %s",
                correlation_id,
                exc,
                exc_info=True,
            )
            from ai_ops.helpers.deep_agent.checkpoint_factory import _checkpointers
            from ai_ops.helpers.deep_agent.store_factory import _stores

            _checkpointers.clear()
            _stores.clear()
            _log.warning("[event_loop_error] Cleared cached checkpointers/stores — will recreate on next request")

            return (
                "An internal error occurred (event loop issue). "
                "The system has been reset. Please try your request again."
            )
        raise

    except Exception as exc:
        _log.error("[error] correlation_id=%s details=%s", correlation_id, exc, exc_info=True)
        return f"Error processing message: {exc}"


async def warmup_deep_agent_connections() -> None:
    """Pre-warm the Redis checkpointer and store connections.

    **When this is useful**: ASGI lifespan startup handlers, where a single
    persistent event loop is shared across all requests.  In that scenario,
    connections initialised here remain valid for the lifetime of the process
    and ``from_conn_string().__aenter__()`` (which creates RediSearch indexes)
    runs once at boot rather than on the first user request.

    **When this is NOT useful**: Django WSGI/synchronous startup (e.g. inside
    ``AppConfig.ready()``).  Django async views create a new event loop per
    request and close it when the response is sent.  Any connections created
    here would be bound to a temporary event loop that is closed before the
    first request arrives.  The ``is_closed()`` check in the factories then
    detects the stale connections and recreates them on the first request
    anyway, making the warmup work wasteful.

    Errors are caught and logged — a failed warmup is never fatal.
    """
    _log.info("[warmup] Pre-warming checkpointer and store connections...")
    try:
        checkpointer = await get_checkpointer(AGENT_NAME)
        _log.info("[warmup] Checkpointer ready: %s", type(checkpointer).__name__)
    except Exception as exc:
        _log.warning("[warmup] Checkpointer warmup failed (will retry on first request): %s", exc)

    try:
        store = await get_store(AGENT_NAME)
        _log.info("[warmup] Store ready: %s", type(store).__name__)
    except Exception as exc:
        _log.warning("[warmup] Store warmup failed (will retry on first request): %s", exc)


async def shutdown_deep_agent() -> None:
    """Gracefully shut down deep agent resources.

    Should be called during application shutdown to ensure proper cleanup of:
    - Checkpointer connection pools
    - Redis / store connections
    """
    _log.info("Shutting down deep agent resources...")
    try:
        from ai_ops.helpers.deep_agent.checkpoint_factory import close_all_pools
        from ai_ops.helpers.deep_agent.store_factory import close_all_stores

        await close_all_pools()
        await close_all_stores()
        _log.info("Shutdown completed successfully")

    except Exception as exc:
        _log.error("Error during shutdown: %s", exc, exc_info=True)
