"""Tests for AI Ops models."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from ai_ops.models import (
    LLMMiddleware,
    LLMModel,
    LLMProvider,
    LLMProviderChoice,
    MCPServer,
    MiddlewareType,
)


class LLMProviderTestCase(TestCase):
    """Test cases for LLMProvider model."""

    def setUp(self):
        """Set up test data."""
        self.ollama_provider = LLMProvider.objects.create(
            name=LLMProviderChoice.OLLAMA,
            description="Test Ollama provider",
            is_enabled=True,
        )

    def test_llm_provider_creation(self):
        """Test LLMProvider instance creation."""
        self.assertEqual(self.ollama_provider.name, LLMProviderChoice.OLLAMA)
        self.assertTrue(self.ollama_provider.is_enabled)
        self.assertEqual(str(self.ollama_provider), "Ollama (Provider)")

    def test_llm_provider_unique_name(self):
        """Test that provider names must be unique."""
        with self.assertRaises(Exception):
            LLMProvider.objects.create(
                name=LLMProviderChoice.OLLAMA,
                description="Duplicate provider",
            )

    def test_llm_provider_get_handler(self):
        """Test get_handler method returns appropriate handler."""
        handler = self.ollama_provider.get_handler()
        self.assertIsNotNone(handler)
        from ai_ops.helpers.llm_providers.base import BaseLLMProviderHandler

        self.assertIsInstance(handler, BaseLLMProviderHandler)


class LLMModelTestCase(TestCase):
    """Test cases for LLMModel model."""

    def setUp(self):
        """Set up test data."""
        self.provider = LLMProvider.objects.create(
            name=LLMProviderChoice.OLLAMA,
            description="Test provider",
        )
        self.model = LLMModel.objects.create(
            llm_provider=self.provider,
            name="llama2",
            description="Test model",
            temperature=0.7,
            is_default=True,
        )

    def test_llm_model_creation(self):
        """Test LLMModel instance creation."""
        self.assertEqual(self.model.name, "llama2")
        self.assertEqual(self.model.temperature, 0.7)
        self.assertTrue(self.model.is_default)
        self.assertEqual(str(self.model), "llama2 (default)")

    def test_llm_model_get_default_model(self):
        """Test get_default_model class method."""
        default_model = LLMModel.get_default_model()
        self.assertEqual(default_model, self.model)
        self.assertTrue(default_model.is_default)

    def test_llm_model_only_one_default(self):
        """Test that only one model can be marked as default."""
        with self.assertRaises(ValidationError):
            second_model = LLMModel(
                llm_provider=self.provider,
                name="mistral",
                is_default=True,
            )
            second_model.clean()

    def test_llm_model_without_default(self):
        """Test get_default_model when no model is marked as default."""
        self.model.is_default = False
        self.model.save()

        new_model = LLMModel.objects.create(
            llm_provider=self.provider,
            name="mistral",
            is_default=False,
        )

        default = LLMModel.get_default_model()
        self.assertIn(default, [self.model, new_model])

    def test_llm_model_get_all_models_summary(self):
        """Test get_all_models_summary class method."""
        summary = LLMModel.get_all_models_summary()
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["name"], "llama2")
        self.assertTrue(summary[0]["is_default"])

    def test_llm_model_cache_ttl_minimum(self):
        """Test that cache_ttl has minimum validator."""
        with self.assertRaises(ValidationError):
            model = LLMModel(
                llm_provider=self.provider,
                name="test-model",
                cache_ttl=30,  # Less than minimum of 60
            )
            model.full_clean()


class MiddlewareTypeTestCase(TestCase):
    """Test cases for MiddlewareType model."""

    def test_middleware_type_creation(self):
        """Test MiddlewareType instance creation."""
        middleware_type = MiddlewareType.objects.create(
            name="CustomMiddleware",
            description="Test middleware",
            is_custom=True,
        )
        self.assertEqual(middleware_type.name, "CustomMiddleware")
        self.assertTrue(middleware_type.is_custom)
        self.assertIn("[Custom]", str(middleware_type))

    def test_middleware_type_name_auto_suffix(self):
        """Test that Middleware suffix is automatically added."""
        middleware_type = MiddlewareType(name="Custom", is_custom=True)
        middleware_type.clean()
        self.assertEqual(middleware_type.name, "CustomMiddleware")

    def test_middleware_type_name_capitalization(self):
        """Test that first letter is auto-capitalized."""
        middleware_type = MiddlewareType(name="custom", is_custom=True)
        middleware_type.clean()
        self.assertEqual(middleware_type.name, "CustomMiddleware")


class LLMMiddlewareTestCase(TestCase):
    """Test cases for LLMMiddleware model."""

    def setUp(self):
        """Set up test data."""
        self.provider = LLMProvider.objects.create(
            name=LLMProviderChoice.OLLAMA,
            description="Test provider",
        )
        self.model = LLMModel.objects.create(
            llm_provider=self.provider,
            name="llama2",
        )
        self.middleware_type = MiddlewareType.objects.create(
            name="TestMiddleware",
            is_custom=False,
        )

    def test_llm_middleware_creation(self):
        """Test LLMMiddleware instance creation."""
        middleware = LLMMiddleware.objects.create(
            llm_model=self.model,
            middleware=self.middleware_type,
            priority=5,
            is_active=True,
        )
        self.assertEqual(middleware.priority, 5)
        self.assertTrue(middleware.is_active)
        self.assertIn("TestMiddleware", str(middleware))

    def test_llm_middleware_unique_together(self):
        """Test that each middleware type can only be configured once per model."""
        LLMMiddleware.objects.create(
            llm_model=self.model,
            middleware=self.middleware_type,
            priority=5,
        )

        with self.assertRaises(Exception):
            LLMMiddleware.objects.create(
                llm_model=self.model,
                middleware=self.middleware_type,
                priority=10,
            )

    def test_llm_middleware_priority_validation(self):
        """Test priority field validators."""
        with self.assertRaises(ValidationError):
            middleware = LLMMiddleware(
                llm_model=self.model,
                middleware=self.middleware_type,
                priority=0,  # Less than minimum of 1
            )
            middleware.full_clean()

        with self.assertRaises(ValidationError):
            middleware = LLMMiddleware(
                llm_model=self.model,
                middleware=self.middleware_type,
                priority=101,  # Greater than maximum of 100
            )
            middleware.full_clean()

    def test_llm_middleware_ttl_minimum(self):
        """Test that ttl has minimum validator."""
        with self.assertRaises(ValidationError):
            middleware = LLMMiddleware(
                llm_model=self.model,
                middleware=self.middleware_type,
                ttl=30,  # Less than minimum of 60
            )
            middleware.full_clean()


class MCPServerTestCase(TestCase):
    """Test cases for MCPServer model."""

    def test_mcp_server_creation(self):
        """Test MCPServer instance creation."""
        from nautobot.extras.models import Status

        status = Status.objects.get_for_model(MCPServer).first()
        server = MCPServer.objects.create(
            name="test-server",
            status=status,
            protocol="http",
            url="http://localhost:8000",
            mcp_endpoint="/mcp",
            health_check="/health",
            description="Test MCP server",
        )
        self.assertEqual(server.name, "test-server")
        self.assertEqual(server.protocol, "http")
        self.assertEqual(server.url, "http://localhost:8000")

    def test_mcp_server_endpoint_normalization(self):
        """Test that endpoints are normalized with leading slash."""
        from nautobot.extras.models import Status

        status = Status.objects.get_for_model(MCPServer).first()
        server = MCPServer(
            name="test-server",
            status=status,
            url="http://localhost:8000",
            mcp_endpoint="mcp",  # No leading slash
            health_check="health",  # No leading slash
        )
        server.clean()
        self.assertEqual(server.mcp_endpoint, "/mcp")
        self.assertEqual(server.health_check, "/health")

    def test_mcp_server_url_required(self):
        """Test that URL is required."""
        from nautobot.extras.models import Status

        status = Status.objects.get_for_model(MCPServer).first()
        with self.assertRaises(ValidationError):
            server = MCPServer(
                name="test-server",
                status=status,
                url="",  # Empty URL
            )
            server.clean()
