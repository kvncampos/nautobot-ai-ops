"""Tests for exception handling in views."""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework.test import APIRequestFactory

from ai_ops.api.views import MCPServerViewSet
from ai_ops.helpers.common.enums import NautobotEnvironment
from ai_ops.tests.factories import TestDataMixin
from ai_ops.views import ChatClearView, ChatMessageView, ClearMCPCacheView

User = get_user_model()


class ExceptionHandlingTestCase(TestCase, TestDataMixin):
    """Test cases for exception handling based on environment."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self.factory = RequestFactory()
        self.api_factory = APIRequestFactory()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.superuser = User.objects.create_superuser(username="admin", password="adminpass")

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

    @patch("ai_ops.views.get_environment")
    @patch("ai_ops.views.process_message")
    async def test_chat_message_view_exception_in_local(self, mock_process_message, mock_get_environment):
        """Test ChatMessageView exception handling in LOCAL environment."""
        # Set environment to LOCAL
        mock_get_environment.return_value = NautobotEnvironment.LOCAL

        # Make process_message raise an exception
        mock_process_message.side_effect = Exception("Test error message")

        # Create request
        request = self.factory.post("/chat/message", {"message": "test message"})
        request.user = self.user
        request.session = MagicMock()
        request.session.session_key = "test-session-key"

        # Call view
        view = ChatMessageView.as_view()
        response = await view(request)

        # In LOCAL environment, exception details should be exposed
        response_data = response.content.decode("utf-8")
        self.assertIn("Test error message", response_data)
        self.assertEqual(response.status_code, 500)

    @patch("ai_ops.views.get_environment")
    @patch("ai_ops.views.process_message")
    async def test_chat_message_view_exception_in_prod(self, mock_process_message, mock_get_environment):
        """Test ChatMessageView exception handling in PROD environment."""
        # Set environment to PROD
        mock_get_environment.return_value = NautobotEnvironment.PROD

        # Make process_message raise an exception
        mock_process_message.side_effect = Exception("Test error message")

        # Create request
        request = self.factory.post("/chat/message", {"message": "test message"})
        request.user = self.user
        request.session = MagicMock()
        request.session.session_key = "test-session-key"

        # Call view
        view = ChatMessageView.as_view()
        response = await view(request)

        # In PROD environment, exception details should NOT be exposed
        response_data = response.content.decode("utf-8")
        self.assertNotIn("Test error message", response_data)
        self.assertIn("Unable to process your message at this time", response_data)
        self.assertEqual(response.status_code, 500)

    @patch("ai_ops.views.get_environment")
    @patch("ai_ops.checkpointer.clear_checkpointer_for_thread")
    async def test_chat_clear_view_runtime_exception_in_local(self, mock_clear, mock_get_environment):
        """Test ChatClearView RuntimeError handling in LOCAL environment."""
        # Set environment to LOCAL
        mock_get_environment.return_value = NautobotEnvironment.LOCAL

        # Make clear raise a RuntimeError
        mock_clear.side_effect = RuntimeError("Some runtime error")

        # Create request
        request = self.factory.post("/chat/clear")
        request.user = self.user
        request.session = MagicMock()
        request.session.session_key = "test-session-key"

        # Call view
        view = ChatClearView.as_view()
        response = await view(request)

        # In LOCAL environment, exception details should be exposed
        response_data = response.content.decode("utf-8")
        self.assertIn("Some runtime error", response_data)
        self.assertEqual(response.status_code, 500)

    @patch("ai_ops.views.get_environment")
    @patch("ai_ops.checkpointer.clear_checkpointer_for_thread")
    async def test_chat_clear_view_runtime_exception_in_nonprod(self, mock_clear, mock_get_environment):
        """Test ChatClearView RuntimeError handling in NONPROD environment."""
        # Set environment to NONPROD
        mock_get_environment.return_value = NautobotEnvironment.NONPROD

        # Make clear raise a RuntimeError
        mock_clear.side_effect = RuntimeError("Some runtime error")

        # Create request
        request = self.factory.post("/chat/clear")
        request.user = self.user
        request.session = MagicMock()
        request.session.session_key = "test-session-key"

        # Call view
        view = ChatClearView.as_view()
        response = await view(request)

        # In NONPROD environment, exception details should NOT be exposed
        response_data = response.content.decode("utf-8")
        self.assertNotIn("Some runtime error", response_data)
        self.assertIn("Failed to clear conversation history", response_data)
        self.assertEqual(response.status_code, 500)

    @patch("ai_ops.views.get_environment")
    @patch("ai_ops.checkpointer.clear_checkpointer_for_thread")
    async def test_chat_clear_view_generic_exception_in_local(self, mock_clear, mock_get_environment):
        """Test ChatClearView generic Exception handling in LOCAL environment."""
        # Set environment to LOCAL
        mock_get_environment.return_value = NautobotEnvironment.LOCAL

        # Make clear raise a generic Exception
        mock_clear.side_effect = Exception("Generic error")

        # Create request
        request = self.factory.post("/chat/clear")
        request.user = self.user
        request.session = MagicMock()
        request.session.session_key = "test-session-key"

        # Call view
        view = ChatClearView.as_view()
        response = await view(request)

        # In LOCAL environment, exception details should be exposed
        response_data = response.content.decode("utf-8")
        self.assertIn("Generic error", response_data)
        self.assertEqual(response.status_code, 500)

    @patch("ai_ops.views.get_environment")
    @patch("ai_ops.agents.multi_mcp_agent.clear_mcp_cache")
    async def test_clear_mcp_cache_view_exception_in_local(self, mock_clear_cache, mock_get_environment):
        """Test ClearMCPCacheView exception handling in LOCAL environment."""
        # Set environment to LOCAL
        mock_get_environment.return_value = NautobotEnvironment.LOCAL

        # Make clear_mcp_cache raise an exception
        mock_clear_cache.side_effect = Exception("Cache error")

        # Create request
        request = self.factory.post("/mcp/clear-cache")
        request.user = self.superuser

        # Call view
        view = ClearMCPCacheView.as_view()
        response = await view(request)

        # In LOCAL environment, exception details should be exposed
        response_data = response.content.decode("utf-8")
        self.assertIn("Cache error", response_data)
        self.assertEqual(response.status_code, 500)

    @patch("ai_ops.views.get_environment")
    @patch("ai_ops.agents.multi_mcp_agent.clear_mcp_cache")
    async def test_clear_mcp_cache_view_exception_in_lab(self, mock_clear_cache, mock_get_environment):
        """Test ClearMCPCacheView exception handling in LAB environment."""
        # Set environment to LAB
        mock_get_environment.return_value = NautobotEnvironment.LAB

        # Make clear_mcp_cache raise an exception
        mock_clear_cache.side_effect = Exception("Cache error")

        # Create request
        request = self.factory.post("/mcp/clear-cache")
        request.user = self.superuser

        # Call view
        view = ClearMCPCacheView.as_view()
        response = await view(request)

        # In LAB environment, exception details should NOT be exposed
        response_data = response.content.decode("utf-8")
        self.assertNotIn("Cache error", response_data)
        self.assertIn("Failed to clear MCP cache", response_data)
        self.assertEqual(response.status_code, 500)

    @patch("ai_ops.api.views.get_environment")
    @patch("httpx.Client")
    def test_mcp_server_health_check_exception_in_local(self, mock_client, mock_get_environment):
        """Test MCPServerViewSet health_check exception handling in LOCAL environment."""
        # Set environment to LOCAL
        mock_get_environment.return_value = NautobotEnvironment.LOCAL

        # Mock httpx.Client to raise an exception
        mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection failed")

        # Create request
        request = self.api_factory.post(f"/api/plugins/ai-ops/mcp-servers/{self.http_server.pk}/health-check/")
        request.user = self.superuser

        # Call the health_check method directly
        viewset_instance = MCPServerViewSet()
        viewset_instance.format_kwarg = None
        viewset_instance.request = request
        # Mock get_object to return our test server directly
        viewset_instance.get_object = lambda: self.http_server

        # health_check is a sync method
        response = viewset_instance.health_check(request, pk=self.http_server.pk)

        # In LOCAL environment, exception details should be exposed
        self.assertIn("Connection failed", response.data["details"])
        self.assertFalse(response.data["success"])
        self.assertIn("health check failed", response.data["message"])

    @patch("ai_ops.api.views.get_environment")
    @patch("httpx.Client")
    def test_mcp_server_health_check_exception_in_prod(self, mock_client, mock_get_environment):
        """Test MCPServerViewSet health_check exception handling in PROD environment."""
        # Set environment to PROD
        mock_get_environment.return_value = NautobotEnvironment.PROD

        # Mock httpx.Client to raise an exception
        mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection failed")

        # Create request
        request = self.api_factory.post(f"/api/plugins/ai-ops/mcp-servers/{self.http_server.pk}/health-check/")
        request.user = self.superuser

        # Call the health_check method directly
        viewset_instance = MCPServerViewSet()
        viewset_instance.format_kwarg = None
        viewset_instance.request = request
        # Mock get_object to return our test server directly
        viewset_instance.get_object = lambda: self.http_server

        # health_check is a sync method
        response = viewset_instance.health_check(request, pk=self.http_server.pk)

        # In PROD environment, exception details should NOT be exposed
        self.assertNotIn("Connection failed", response.data["details"])
        self.assertIn("Connection error", response.data["details"])
        self.assertFalse(response.data["success"])
        self.assertIn("health check failed", response.data["message"])
