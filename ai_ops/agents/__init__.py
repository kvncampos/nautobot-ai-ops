"""AI Agent implementations for Nautobot."""

from ai_ops.agents.multi_mcp_agent import (
    clear_mcp_cache,
    get_or_create_mcp_client,
    process_message,
    warm_mcp_cache,
)

# from ai_ops.agents.single_mcp_agent import (
#     initialize_agent,
#     shutdown_agent,
# )

__all__ = [
    # Multi-MCP Agent (Production)
    "clear_mcp_cache",
    "get_or_create_mcp_client",
    "process_message",
    "warm_mcp_cache",
    # Single-MCP Agent (Legacy/Development)
    # "initialize_agent",
    # "shutdown_agent",
]
