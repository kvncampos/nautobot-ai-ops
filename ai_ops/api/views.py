"""API views for ai_ops."""

import httpx
from nautobot.apps.api import NautobotModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from ai_ops import filters, models
from ai_ops.api import serializers


class LLMProviderViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """LLMProvider viewset."""

    queryset = models.LLMProvider.objects.all()
    serializer_class = serializers.LLMProviderSerializer
    filterset_class = filters.LLMProviderFilterSet


class LLMModelViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """LLMModel viewset."""

    queryset = models.LLMModel.objects.all()
    serializer_class = serializers.LLMModelSerializer
    filterset_class = filters.LLMModelFilterSet

    # Option for modifying the default HTTP methods:
    # http_method_names = ["get", "post", "put", "patch", "delete", "head", "options", "trace"]


class MiddlewareTypeViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """MiddlewareType viewset."""

    queryset = models.MiddlewareType.objects.all()
    serializer_class = serializers.MiddlewareTypeSerializer
    filterset_class = filters.MiddlewareTypeFilterSet


class LLMMiddlewareViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """LLMMiddleware viewset."""

    queryset = models.LLMMiddleware.objects.all()
    serializer_class = serializers.LLMMiddlewareSerializer
    filterset_class = filters.LLMMiddlewareFilterSet


class MCPServerViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """MCPServer viewset."""

    queryset = models.MCPServer.objects.all()
    serializer_class = serializers.MCPServerSerializer
    filterset_class = filters.MCPServerFilterSet

    # Option for modifying the default HTTP methods:
    # http_method_names = ["get", "post", "put", "patch", "delete", "head", "options", "trace"]

    @action(detail=True, methods=["post"], url_path="health-check")
    async def health_check(self, request, pk=None):
        """Perform health check on MCP server."""
        mcp_server = self.get_object()

        try:
            # Build health check URL using base URL + health_check path
            # Note: health check is NOT at the MCP endpoint, it's at the base URL
            health_path = getattr(mcp_server, "health_check", "/health")
            health_url = f"{mcp_server.url.rstrip('/')}{health_path}"

            # Only disable SSL verification for internal MCP servers
            verify_ssl = mcp_server.mcp_type != "internal"

            # Perform health check with async client
            async with httpx.AsyncClient(verify=verify_ssl, timeout=5.0) as client:
                response = await client.get(health_url)

                if response.status_code == 200:
                    return Response(
                        {
                            "success": True,
                            "message": f"MCP Server '{mcp_server.name}' is healthy",
                            "details": f"Successfully connected to {health_url}",
                            "url": health_url,
                        }
                    )
                else:
                    return Response(
                        {
                            "success": False,
                            "message": f"MCP Server '{mcp_server.name}' health check failed",
                            "details": f"HTTP {response.status_code} from {health_url}",
                            "url": health_url,
                        }
                    )
        except httpx.TimeoutException:
            health_path = getattr(mcp_server, "health_check", "/health")
            health_url = f"{mcp_server.url.rstrip('/')}{health_path}"
            return Response(
                {
                    "success": False,
                    "message": f"MCP Server '{mcp_server.name}' health check timed out",
                    "details": f"No response after 5 seconds from {health_url}",
                    "url": health_url,
                }
            )
        except Exception as e:
            health_path = getattr(mcp_server, "health_check", "/health")
            health_url = f"{mcp_server.url.rstrip('/')}{health_path}"
            return Response(
                {
                    "success": False,
                    "message": f"MCP Server '{mcp_server.name}' health check failed",
                    "details": f"{str(e)}",
                    "url": health_url,
                }
            )
