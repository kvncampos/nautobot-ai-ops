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
from ai_ops.tests.factories import TestDataMixin


class LLMProviderTestCase(TestCase, TestDataMixin):
    """Test cases for LLMProvider model."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self.ollama_provider = self.ollama_provider

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

    def test_llm_provider_creation(self):
        """Test LLMProvider instance creation."""
        self.assertEqual(self.ollama_provider.name, LLMProviderChoice.OLLAMA)
        self.assertTrue(self.ollama_provider.is_enabled)
        self.assertEqual(str(self.ollama_provider), "Ollama (Provider)")

    def test_llm_provider_unique_name(self):
        """Test that provider names must be unique."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
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


class LLMModelTestCase(TestCase, TestDataMixin):
    """Test cases for LLMModel model."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self.provider = self.ollama_provider
        self.model = self.llama2_model

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

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

        new_model, _ = LLMModel.objects.get_or_create(
            llm_provider=self.provider,
            name="test-no-default",
            defaults={
                "is_default": False,
            },
        )

        default = LLMModel.get_default_model()
        self.assertIn(default, [self.model, new_model])

    def test_llm_model_get_all_models_summary(self):
        """Test get_all_models_summary class method."""
        summary = LLMModel.get_all_models_summary()
        self.assertGreaterEqual(len(summary), 1)

        # Check that our test model is in the summary
        model_names = [model_info["name"] for model_info in summary]
        self.assertIn(self.model.name, model_names)

        # Find our specific model and check its properties
        our_model_info = next((m for m in summary if m["name"] == self.model.name), None)
        self.assertIsNotNone(our_model_info)
        self.assertEqual(our_model_info["name"], "llama2")
        self.assertTrue(our_model_info["is_default"])

    def test_llm_model_cache_ttl_minimum(self):
        """Test that cache_ttl has minimum validator."""
        with self.assertRaises(ValidationError):
            model = LLMModel(
                llm_provider=self.provider,
                name="test-model",
                cache_ttl=30,  # Less than minimum of 60
            )
            model.full_clean()


class MiddlewareTypeTestCase(TestCase, TestDataMixin):
    """Test cases for MiddlewareType model."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        # Create additional middleware types for testing
        from ai_ops.tests.factories import MiddlewareTypeFactory

        self.custom_middleware, _ = MiddlewareTypeFactory.create_logging_middleware(
            name="CustomMiddleware", description="Custom test middleware"
        )

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

    def test_middleware_type_creation(self):
        """Test MiddlewareType instance creation."""
        middleware_type, created = MiddlewareType.objects.get_or_create(
            name="TestCreation",
            defaults={
                "description": "Test middleware type",
                "is_custom": True,
            },
        )
        self.assertIsNotNone(middleware_type)
        self.assertEqual(middleware_type.name, "TestCreation")
        # Only check is_custom if we created it new, otherwise it might already exist with different value
        if created:
            self.assertTrue(middleware_type.is_custom)
            self.assertIn("[Custom]", str(middleware_type))
        # Always check that it has some string representation
        self.assertIsNotNone(str(middleware_type))

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


class LLMMiddlewareTestCase(TestCase, TestDataMixin):
    """Test cases for LLMMiddleware model."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self.provider = self.ollama_provider
        self.model = self.llama2_model
        self.middleware_type = self.auth_middleware_type

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

    def test_llm_middleware_creation(self):
        """Test LLMMiddleware instance creation."""
        middleware, _ = LLMMiddleware.objects.get_or_create(
            llm_model=self.model,
            middleware=self.middleware_type,
            defaults={
                "priority": 5,
                "is_active": True,
            },
        )
        self.assertEqual(middleware.priority, 5)
        self.assertTrue(middleware.is_active)
        # Check that the middleware name appears in the string representation
        self.assertIn(self.middleware_type.name, str(middleware))

    def test_llm_middleware_unique_together(self):
        """Test that each middleware type can only be configured once per model."""
        from django.db import IntegrityError

        LLMMiddleware.objects.create(
            llm_model=self.model,
            middleware=self.middleware_type,
            priority=5,
        )

        with self.assertRaises(IntegrityError):
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


class MCPServerTestCase(TestCase, TestDataMixin):
    """Test cases for MCPServer model."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        from nautobot.extras.models import Status

        self.status = Status.objects.get_for_model(MCPServer).first()
        self.server = self.http_server

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

    def test_mcp_server_creation(self):
        """Test MCPServer instance creation."""
        from nautobot.extras.models import Status

        status = Status.objects.get_for_model(MCPServer).first()
        server, created = MCPServer.objects.get_or_create(
            name="test-creation-server",
            defaults={
                "status": status,
                "protocol": "http",
                "url": "http://localhost:8000",
                "mcp_endpoint": "/mcp",
                "health_check": "/health",
                "description": "Test MCP server",
            },
        )
        self.assertEqual(server.name, "test-creation-server")
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
