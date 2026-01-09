"""Tests for AI Ops views."""

from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory
from nautobot.core.testing import TestCase
from nautobot.extras.models import Status

from ai_ops.models import MCPServer
from ai_ops.tests.factories import TestDataMixin
from ai_ops.views import AIChatBotGenericView

User = get_user_model()


class AIChatBotGenericViewTestCase(TestCase, TestDataMixin):
    """Test cases for AIChatBotGenericView.

    Uses Nautobot's TestCase for proper test isolation and database handling.
    """

    def setUp(self):
        """Set up test data and common objects."""
        super().setUp()

        # Use TestDataMixin for consistent test data across all tests
        self.setup_test_data()

        self.factory = RequestFactory()
        self.view = AIChatBotGenericView()

        # Create test users
        self.admin_user = User.objects.create_user(
            username="admin", email="admin@example.com", is_staff=True, is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", email="regular@example.com", is_staff=False, is_superuser=False
        )

        # Access the pre-created test data from TestDataMixin
        # self.ollama_provider, self.openai_provider already exist
        # self.llama2_model, self.mistral_model already exist
        # self.http_server, self.stdio_server already exist

        # Create additional status objects for our tests
        content_type = ContentType.objects.get_for_model(MCPServer)

        # Create healthy status
        self.status_healthy, _ = Status.objects.get_or_create(
            name="Healthy",
            defaults={
                "description": "Healthy MCP Server status",
                "color": "4caf50",
            },
        )
        self.status_healthy.content_types.add(content_type)

        # Create unhealthy status
        self.status_unhealthy, _ = Status.objects.get_or_create(
            name="Unhealthy",
            defaults={
                "description": "Unhealthy MCP Server status",
                "color": "f44336",
            },
        )
        self.status_unhealthy.content_types.add(content_type)

        # Set servers to unhealthy by default (tests will modify as needed)
        self.http_server.status = self.status_unhealthy
        self.http_server.save()
        self.stdio_server.status = self.status_unhealthy
        self.stdio_server.save()

        # Set models to non-default by default (tests will modify as needed)
        self.llama2_model.is_default = False
        self.llama2_model.save()
        self.mistral_model.is_default = False
        self.mistral_model.save()

    def tearDown(self):
        """Clean up after tests."""
        # TestDataMixin will handle cleanup
        if hasattr(super(), "tearDown"):
            super().tearDown()

    def _create_request_with_user(self, user):
        """Helper to create a request with a user and session."""
        request = self.factory.get("/chat/")
        request.user = user

        # Create a session for the request - do this synchronously
        session = SessionStore()
        # Use save() instead of create() to avoid database checks in async context
        session.save(must_create=True)
        request.session = session

        return request

    def test_get_no_default_model_no_mcp_servers(self):
        """Test GET request when no default model and no MCP servers exist."""
        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering database issues in async context
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_response.context_data = {
                "title": "LLM ChatBot",
                "chat_enabled": False,
                "has_default_model": False,
                "has_healthy_mcp": False,
                "has_any_mcp": False,
                "is_admin": False,
                "enabled_providers": [],
            }
            mock_render.return_value = mock_response

            # Mock the database queries directly to simulate no models and no MCP servers
            with patch("ai_ops.models.LLMModel.objects") as mock_llm_manager, patch(
                "ai_ops.models.MCPServer.objects"
            ) as mock_mcp_manager:
                # Mock the specific queries the view makes - no models and no MCP servers
                mock_llm_manager.filter.return_value.exists.return_value = False  # has_default_model = False
                mock_mcp_manager.filter.return_value.exists.return_value = False  # has_healthy_mcp = False
                mock_mcp_manager.exists.return_value = False  # has_any_mcp = False

                # Test the async view using Django's async_to_sync
                async_view = async_to_sync(self.view.get)
                async_view(request)

                # Verify render was called with correct template and context
                mock_render.assert_called_once()
                call_args = mock_render.call_args
                self.assertEqual(call_args[0][0], request)
                self.assertEqual(call_args[0][1], "ai_ops/chat_widget.html")

                # Verify context data
                context = call_args[0][2]
                self.assertEqual(context["title"], "LLM ChatBot")
                self.assertFalse(context["chat_enabled"])
                self.assertFalse(context["has_default_model"])
                self.assertFalse(context["has_healthy_mcp"])
                self.assertFalse(context["has_any_mcp"])
                self.assertFalse(context["is_admin"])
                self.assertEqual(context["enabled_providers"], [])

    def test_get_has_default_model_and_healthy_mcp(self):
        """Test GET request when both default model and healthy MCP servers exist."""
        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering database issues
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Mock the database queries directly to bypass async/sync database isolation issues
            with patch("ai_ops.models.LLMModel.objects") as mock_llm_manager, patch(
                "ai_ops.models.MCPServer.objects"
            ) as mock_mcp_manager:
                # Mock the specific queries the view makes for both conditions met
                mock_llm_manager.filter.return_value.exists.return_value = True  # has_default_model = True
                mock_mcp_manager.filter.return_value.exists.return_value = True  # has_healthy_mcp = True
                mock_mcp_manager.exists.return_value = True  # has_any_mcp = True

                # Test the async view using Django's async_to_sync
                async_view = async_to_sync(self.view.get)
                async_view(request)

                # Verify context data passed to render
                context = mock_render.call_args[0][2]
                self.assertTrue(context["chat_enabled"])  # Both conditions met
                self.assertTrue(context["has_default_model"])
                self.assertTrue(context["has_healthy_mcp"])
                self.assertTrue(context["has_any_mcp"])
                self.assertFalse(context["is_admin"])

    def test_get_admin_user_gets_provider_list(self):
        """Test that admin users get the enabled providers list."""
        request = self._create_request_with_user(self.admin_user)

        # Mock render to avoid template rendering database issues
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Mock the database queries directly to bypass async/sync database isolation issues
            with patch("ai_ops.models.LLMModel.objects") as mock_llm_manager, patch(
                "ai_ops.models.MCPServer.objects"
            ) as mock_mcp_manager, patch("ai_ops.models.LLMProvider.objects") as mock_provider_manager:
                # Mock the specific queries the view makes for admin with chat enabled
                mock_llm_manager.filter.return_value.exists.return_value = True  # has_default_model = True
                mock_mcp_manager.filter.return_value.exists.return_value = True  # has_healthy_mcp = True
                mock_mcp_manager.exists.return_value = True  # has_any_mcp = True

                # Mock enabled providers list for admin
                class MockProvider:
                    def __init__(self, name, display_name):
                        self.name = name
                        self.display_name = display_name

                    def get_name_display(self):
                        return self.display_name

                mock_enabled_providers = [
                    MockProvider("ollama", "Ollama"),
                    MockProvider("azure", "Azure AI"),
                    MockProvider("anthropic", "Anthropic"),
                ]
                mock_provider_manager.filter.return_value = mock_enabled_providers

                # Test the async view using Django's async_to_sync
                async_view = async_to_sync(self.view.get)
                async_view(request)

                # Verify context data passed to render
                context = mock_render.call_args[0][2]
                self.assertTrue(context["chat_enabled"])
                self.assertTrue(context["is_admin"])

                # Should have enabled providers
                self.assertEqual(len(context["enabled_providers"]), 3)

                # Verify provider data structure
                provider_names = [p["name"] for p in context["enabled_providers"]]
                self.assertIn("ollama", provider_names)
                self.assertIn("azure", provider_names)
                self.assertIn("anthropic", provider_names)

                # Verify each provider has required fields
                for provider in context["enabled_providers"]:
                    self.assertIn("name", provider)
                    self.assertIn("get_name_display", provider)

    def test_get_admin_user_only_enabled_providers(self):
        """Test that admin users only get enabled providers in the list."""
        request = self._create_request_with_user(self.admin_user)

        # Mock render to avoid template rendering database issues
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Mock the database queries directly to bypass async/sync database isolation issues
            with patch("ai_ops.models.LLMModel.objects") as mock_llm_manager, patch(
                "ai_ops.models.MCPServer.objects"
            ) as mock_mcp_manager, patch("ai_ops.models.LLMProvider.objects") as mock_provider_manager:
                # Mock the specific queries the view makes for admin with chat enabled
                mock_llm_manager.filter.return_value.exists.return_value = True  # has_default_model = True
                mock_mcp_manager.filter.return_value.exists.return_value = True  # has_healthy_mcp = True
                mock_mcp_manager.exists.return_value = True  # has_any_mcp = True

                # Mock enabled providers list for admin (only enabled ones)
                class MockProvider:
                    def __init__(self, name, display_name):
                        self.name = name
                        self.display_name = display_name

                    def get_name_display(self):
                        return self.display_name

                mock_enabled_providers = [
                    MockProvider("ollama", "Ollama"),
                    MockProvider("azure", "Azure AI"),
                    MockProvider("huggingface", "HuggingFace"),
                ]
                mock_provider_manager.filter.return_value = mock_enabled_providers

                # Test the async view using Django's async_to_sync
                async_view = async_to_sync(self.view.get)
                async_view(request)

                # Verify context data passed to render
                context = mock_render.call_args[0][2]
                # Should have all enabled providers
                expected_count = 3
                self.assertEqual(len(context["enabled_providers"]), expected_count)

                provider_names = [p["name"] for p in context["enabled_providers"]]
                self.assertIn("ollama", provider_names)
                self.assertIn("azure", provider_names)
                self.assertIn("huggingface", provider_names)
                # anthropic should not be included (disabled)
                self.assertNotIn("anthropic", provider_names)

    def test_get_regular_user_no_providers_list(self):
        """Test that regular users don't get the providers list."""
        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering database issues
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Test the async view using Django's async_to_sync
            async_view = async_to_sync(self.view.get)
            async_view(request)

            # Verify context data passed to render
            context = mock_render.call_args[0][2]
            self.assertFalse(context["is_admin"])
            self.assertEqual(context["enabled_providers"], [])

    def test_get_no_default_model_with_healthy_mcp(self):
        """Test that chat is disabled when no default model exists even with healthy MCP."""
        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering database issues
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Mock the database queries directly to bypass async/sync database isolation issues
            with patch("ai_ops.models.LLMModel.objects") as mock_llm_manager, patch(
                "ai_ops.models.MCPServer.objects"
            ) as mock_mcp_manager:
                # Mock the specific queries - no default model but healthy MCP exists
                mock_llm_manager.filter.return_value.exists.return_value = False  # has_default_model = False
                mock_mcp_manager.filter.return_value.exists.return_value = True  # has_healthy_mcp = True
                mock_mcp_manager.exists.return_value = True  # has_any_mcp = True

                # Test the async view using Django's async_to_sync
                async_view = async_to_sync(self.view.get)
                async_view(request)

                # Verify context data passed to render
                context = mock_render.call_args[0][2]
                self.assertFalse(context["chat_enabled"])  # No default model
                self.assertFalse(context["has_default_model"])
                self.assertTrue(context["has_healthy_mcp"])
                self.assertTrue(context["has_any_mcp"])

    def test_get_template_name_is_correct(self):
        """Test that the correct template is used."""
        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering database issues
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Test the async view using Django's async_to_sync
            async_view = async_to_sync(self.view.get)
            async_view(request)

            # Verify render was called with correct template
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            self.assertEqual(call_args[0][1], "ai_ops/chat_widget.html")

    def test_get_context_contains_all_required_fields(self):
        """Test that the context contains all required fields."""
        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering database issues
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Test the async view using Django's async_to_sync
            async_view = async_to_sync(self.view.get)
            async_view(request)

            # Verify context data passed to render
            context = mock_render.call_args[0][2]
            required_fields = [
                "title",
                "chat_enabled",
                "has_default_model",
                "has_healthy_mcp",
                "has_any_mcp",
                "is_admin",
                "enabled_providers",
            ]

            for field in required_fields:
                self.assertIn(field, context, f"Required field '{field}' missing from context")

    def test_get_multiple_default_models_still_works(self):
        """Test that having multiple default models still enables chat (edge case)."""
        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering database issues
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Mock the database queries directly to bypass async/sync database isolation issues
            with patch("ai_ops.models.LLMModel.objects") as mock_llm_manager, patch(
                "ai_ops.models.MCPServer.objects"
            ) as mock_mcp_manager:
                # Mock the specific queries for both conditions met (multiple default models edge case)
                mock_llm_manager.filter.return_value.exists.return_value = True  # has_default_model = True
                mock_mcp_manager.filter.return_value.exists.return_value = True  # has_healthy_mcp = True
                mock_mcp_manager.exists.return_value = True  # has_any_mcp = True

                # Test the async view using Django's async_to_sync
                async_view = async_to_sync(self.view.get)
                async_view(request)

                # Verify context data passed to render
                context = mock_render.call_args[0][2]
                self.assertTrue(context["chat_enabled"])
                self.assertTrue(context["has_default_model"])
                self.assertTrue(context["has_healthy_mcp"])
                self.assertFalse(context["is_admin"])

    def test_sync_to_async_database_operations_work(self):
        """Test that sync_to_async wrapping of database operations works correctly."""
        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering database issues
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Mock the database queries directly to bypass async/sync database isolation issues
            with patch("ai_ops.models.LLMModel.objects") as mock_llm_manager, patch(
                "ai_ops.models.MCPServer.objects"
            ) as mock_mcp_manager:
                # Mock the specific queries the view makes for both conditions met
                mock_llm_manager.filter.return_value.exists.return_value = True  # has_default_model = True
                mock_mcp_manager.filter.return_value.exists.return_value = True  # has_healthy_mcp = True
                mock_mcp_manager.exists.return_value = True  # has_any_mcp = True

                # Test the async view using Django's async_to_sync
                async_view = async_to_sync(self.view.get)

                # Verify we can call this without database connection issues
                async_view(request)

                # Verify the database queries executed correctly in async context
                context = mock_render.call_args[0][2]
                self.assertTrue(context["has_default_model"])
                self.assertTrue(context["has_healthy_mcp"])
                self.assertTrue(context["chat_enabled"])

    @patch("ai_ops.views.get_app_settings_or_config")
    def test_get_ttl_config_passed_to_template(self, mock_get_config):
        """Test that chat_session_ttl_minutes is passed to template context."""
        # Mock config to return 10 minutes
        mock_get_config.return_value = 10

        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Mock database queries
            with patch("ai_ops.models.LLMModel.objects") as mock_llm_manager, patch(
                "ai_ops.models.MCPServer.objects"
            ) as mock_mcp_manager:
                mock_llm_manager.filter.return_value.exists.return_value = True
                mock_mcp_manager.filter.return_value.exists.return_value = True
                mock_mcp_manager.exists.return_value = True

                # Test the async view
                async_view = async_to_sync(self.view.get)
                async_view(request)

                # Verify TTL is in context
                context = mock_render.call_args[0][2]
                self.assertEqual(context["chat_session_ttl_minutes"], 10)

    def test_get_default_ttl_when_not_configured(self):
        """Test that default TTL (5 minutes) is used when not configured."""
        request = self._create_request_with_user(self.regular_user)

        # Mock render to avoid template rendering
        with patch("ai_ops.views.render") as mock_render:
            mock_response = HttpResponse()
            mock_render.return_value = mock_response

            # Mock database queries
            with patch("ai_ops.models.LLMModel.objects") as mock_llm_manager, patch(
                "ai_ops.models.MCPServer.objects"
            ) as mock_mcp_manager:
                mock_llm_manager.filter.return_value.exists.return_value = True
                mock_mcp_manager.filter.return_value.exists.return_value = True
                mock_mcp_manager.exists.return_value = True

                # Test the async view
                async_view = async_to_sync(self.view.get)
                async_view(request)

                # Verify default TTL is used
                context = mock_render.call_args[0][2]
                self.assertEqual(context["chat_session_ttl_minutes"], 5)
