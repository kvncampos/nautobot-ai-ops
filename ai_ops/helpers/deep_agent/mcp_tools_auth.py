"""
MCP tools authentication utility for deep agents in ai-ops.

This module provides functionality to load MCP tools from Django's MCPServer
model with optional authentication token injection. Unlike the standard multi_mcp_agent,
this does NOT cache tools to ensure fresh auth tokens are always used.

Security Note:
    SSL verification is disabled (verify=False) for connecting to internal MCP
    servers with self-signed certificates. This is intentional per requirements.

Adapted from network-agent to work with Django's MCPServer model.

Example:
    >>> # With authentication
    >>> tools = await get_mcp_tools(user_token="Bearer abc123", agent_name="my_agent")
    >>> print(f"Loaded {len(tools)} tools")

    >>> # Without authentication
    >>> tools = await get_mcp_tools(agent_name="my_agent")
"""

import logging
from typing import Any

import httpx
from asgiref.sync import sync_to_async
from langchain_mcp_adapters.client import MultiServerMCPClient
from nautobot.extras.models import Status

from ai_ops.models import MCPServer

logger = logging.getLogger(__name__)

# Type alias for tool lists
ToolList = list[Any]


def _create_httpx_client_factory(user_token: str | None = None):
    """
    Create an httpx client factory with optional authentication.

    Args:
        user_token: Optional Bearer token for authentication

    Returns:
        Factory function that creates configured httpx clients

    Note:
        SSL verification is disabled per requirements for internal servers
        with self-signed certificates.
    """

    def factory(**_kwargs):
        """Factory for httpx client with configured settings."""
        headers = {}

        if user_token:
            # Ensure token has Bearer prefix
            auth_header = user_token if user_token.startswith("Bearer ") else f"Bearer {user_token}"
            headers["Authorization"] = auth_header

        return httpx.AsyncClient(
            verify=False,  # noqa: S501 - intentional per requirements
            headers=headers,
            timeout=httpx.Timeout(30.0),  # Prevent hanging
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
            ),
        )

    return factory


async def _get_healthy_mcp_servers(agent_name: str) -> list[MCPServer]:
    """
    Query database for enabled, healthy HTTP MCP servers.

    Args:
        agent_name: Name of agent for logging

    Returns:
        List of healthy MCPServer instances

    Raises:
        Status.DoesNotExist: If "Healthy" status not found in database
    """
    servers = await sync_to_async(list)(
        MCPServer.objects.filter(
            status__name="Healthy",  # Single query with lookup
            protocol="http",
        ).select_related("status")  # Optimize query
    )

    if not servers:
        logger.warning(f"[{agent_name}] No enabled, healthy MCP servers found")
    else:
        logger.info(f"[{agent_name}] Found {len(servers)} healthy MCP server(s)")

    return servers


def _build_mcp_connections(
    servers: list[MCPServer],
    httpx_factory,
) -> dict[str, Any]:
    """
    Build connections dictionary for MultiServerMCPClient.

    Args:
        servers: List of MCPServer instances
        httpx_factory: Factory function for creating httpx clients

    Returns:
        Dictionary mapping server names to connection configs
    """
    return {
        server.name: {
            "transport": "streamable_http",
            "url": f"{server.url.rstrip('/')}{server.mcp_endpoint}",
            "httpx_client_factory": httpx_factory,
        }
        for server in servers
    }


async def get_mcp_tools(
    user_token: str | None = None,
    agent_name: str = "deep_agent",
) -> ToolList:
    """
    Get MCP tools with optional authentication token injection.

    IMPORTANT: Tools are NOT cached. Each call creates a fresh client with
    current auth tokens to prevent 401 errors from stale/expired tokens.

    Args:
        user_token: Optional Bearer token for authenticating with MCP servers.
                   If None, no authentication is used.
        agent_name: Name of the agent (for logging)

    Returns:
        List of tools from all healthy MCP servers. Returns empty list if
        no servers found or on error to allow agent to work without tools.

    Example:
        >>> # With authentication
        >>> tools = await get_mcp_tools(user_token="Bearer abc123")
        >>>
        >>> # Without authentication
        >>> tools = await get_mcp_tools()
    """
    try:
        # Get healthy servers
        servers = await _get_healthy_mcp_servers(agent_name)
        if not servers:
            return []

        # Create httpx client factory with optional auth
        httpx_factory = _create_httpx_client_factory(user_token)

        # Build connections dictionary
        connections = _build_mcp_connections(servers, httpx_factory)

        # Create MultiServerMCPClient and get tools
        client = MultiServerMCPClient(connections)
        tools = await client.get_tools()

        auth_msg = "with auth" if user_token else "without auth"
        logger.info(f"[{agent_name}] Loaded {len(tools)} tools from {len(servers)} MCP server(s) {auth_msg}")

        return tools

    except Status.DoesNotExist:
        logger.error(
            f"[{agent_name}] 'Healthy' status not found in database. Please ensure Nautobot statuses are configured.",
            exc_info=True,
        )
        return []

    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error(
            f"[{agent_name}] HTTP error connecting to MCP servers: {e}",
            exc_info=True,
        )
        return []

    except ValueError as e:
        logger.error(
            f"[{agent_name}] Invalid configuration for MCP servers: {e}",
            exc_info=True,
        )
        return []

    except Exception as e:
        # Unexpected errors should be visible for debugging
        logger.critical(
            f"[{agent_name}] Unexpected error loading MCP tools: {e}",
            exc_info=True,
        )
        # Still return empty list to allow agent to work
        return []
