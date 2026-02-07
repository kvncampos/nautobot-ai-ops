"""
MCP tools authentication utility for deep agents in ai-ops.

This module provides functionality to load MCP tools from Django's MCPServer
model with proper authentication token injection. Unlike the standard multi_mcp_agent,
this does NOT cache tools to ensure fresh auth tokens are always used.

Adapted from network-agent to work with Django's MCPServer model.
"""

import logging
from typing import List

import httpx
from asgiref.sync import sync_to_async
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)


async def get_mcp_tools_with_auth(user_token: str, agent_name: str = "deep_agent") -> List:
    """
    Get MCP tools with authentication token injection.

    IMPORTANT: Tools are NOT cached. Each call creates a fresh client with
    current auth tokens to prevent 401 errors from stale/expired tokens.

    Args:
        user_token: Bearer token for authenticating with MCP servers
        agent_name: Name of the agent (for logging)

    Returns:
        List of tools from all healthy MCP servers

    Raises:
        Exception: If MCP servers cannot be queried or tools cannot be loaded
    """
    try:
        from nautobot.extras.models import Status

        from ai_ops.models import MCPServer

        # Query for enabled, healthy MCP servers
        healthy_status = await sync_to_async(Status.objects.get)(name="Healthy")
        servers = await sync_to_async(list)(
            MCPServer.objects.filter(
                status=healthy_status,
                protocol="http",
            )
        )

        if not servers:
            logger.warning(f"[{agent_name}] No enabled, healthy MCP servers found")
            return []

        # Build connections dict for MultiServerMCPClient
        def httpx_client_factory(**kwargs):
            """Factory for httpx client with SSL verification disabled and auth headers.

            Note: verify=False is intentional per requirements for connecting
            to internal MCP servers with self-signed certificates.
            Includes Authorization header for authentication.
            """
            headers = {}
            if user_token:
                # Ensure token has Bearer prefix
                if not user_token.startswith("Bearer "):
                    headers["Authorization"] = f"Bearer {user_token}"
                else:
                    headers["Authorization"] = user_token

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

        # Create MultiServerMCPClient with auth
        client = MultiServerMCPClient(connections)
        tools = await client.get_tools()

        logger.info(f"[{agent_name}] Loaded {len(tools)} tools from {len(servers)} MCP server(s) with fresh auth token")

        return tools

    except Exception as e:
        logger.error(f"[{agent_name}] Failed to get MCP tools with auth: {e}", exc_info=True)
        # Return empty list instead of raising to allow agent to work without tools
        return []


async def get_mcp_tools_no_cache(agent_name: str = "deep_agent") -> List:
    """
    Get MCP tools without authentication (for agents that don't require auth).

    IMPORTANT: Tools are NOT cached. Each call creates a fresh client.

    Args:
        agent_name: Name of the agent (for logging)

    Returns:
        List of tools from all healthy MCP servers
    """
    try:
        from nautobot.extras.models import Status

        from ai_ops.models import MCPServer

        # Query for enabled, healthy MCP servers
        healthy_status = await sync_to_async(Status.objects.get)(name="Healthy")
        servers = await sync_to_async(list)(
            MCPServer.objects.filter(
                status=healthy_status,
                protocol="http",
            )
        )

        if not servers:
            logger.warning(f"[{agent_name}] No enabled, healthy MCP servers found")
            return []

        # Build connections dict for MultiServerMCPClient
        def httpx_client_factory(**kwargs):
            """Factory for httpx client with SSL verification disabled.

            Note: verify=False is intentional per requirements.
            """
            return httpx.AsyncClient(
                verify=False,  # noqa: S501 - intentional
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

        logger.info(f"[{agent_name}] Loaded {len(tools)} tools from {len(servers)} MCP server(s)")

        return tools

    except Exception as e:
        logger.error(f"[{agent_name}] Failed to get MCP tools: {e}", exc_info=True)
        # Return empty list instead of raising to allow agent to work without tools
        return []
