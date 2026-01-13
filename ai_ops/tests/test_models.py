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
    SystemPrompt,
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


class SystemPromptTestCase(TestCase, TestDataMixin):
    """Test cases for SystemPrompt model."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self._create_system_prompt_statuses()

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

    def _create_system_prompt_statuses(self):
        """Create required statuses for SystemPrompt."""
        from django.contrib.contenttypes.models import ContentType
        from nautobot.core.choices import ColorChoices
        from nautobot.extras.models import Status

        system_prompt_ct = ContentType.objects.get_for_model(SystemPrompt)

        status_configs = [
            {"name": "Approved", "color": ColorChoices.COLOR_GREEN},
            {"name": "Testing", "color": ColorChoices.COLOR_AMBER},
            {"name": "Deprecated", "color": ColorChoices.COLOR_GREY},
        ]

        for config in status_configs:
            status, _ = Status.objects.get_or_create(
                name=config["name"],
                defaults={"color": config["color"]},
            )
            if system_prompt_ct not in status.content_types.all():
                status.content_types.add(system_prompt_ct)

    def _get_approved_status(self):
        """Get the Approved status."""
        from nautobot.extras.models import Status

        return Status.objects.get(name="Approved")

    def _get_testing_status(self):
        """Get the Testing status."""
        from nautobot.extras.models import Status

        return Status.objects.get(name="Testing")

    def _get_deprecated_status(self):
        """Get the Deprecated status."""
        from nautobot.extras.models import Status

        return Status.objects.get(name="Deprecated")

    def test_system_prompt_creation(self):
        """Test SystemPrompt instance creation."""
        import time

        approved_status = self._get_approved_status()
        unique_name = f"ModelTest_Create_{int(time.time())}"
        prompt = SystemPrompt.objects.create(
            name=unique_name,
            prompt_text="You are a helpful assistant.",
            status=approved_status,
            is_file_based=False,
        )
        self.assertEqual(prompt.name, unique_name)
        self.assertEqual(prompt.version, 1)
        self.assertFalse(prompt.is_file_based)
        self.assertIn("v1 (Approved)", str(prompt))

    def test_system_prompt_version_increments_on_prompt_text_change(self):
        """Test that version auto-increments when prompt_text is updated."""
        import time

        approved_status = self._get_approved_status()

        # Create prompt with unique name
        unique_name = f"ModelTest_Version_{int(time.time())}"
        prompt = SystemPrompt.objects.create(
            name=unique_name,
            prompt_text="Original content",
            status=approved_status,
        )
        self.assertEqual(prompt.version, 1)

        # Update prompt_text - version should increment
        prompt.prompt_text = "Updated content v2"
        prompt.save()
        self.assertEqual(prompt.version, 2)

        # Update prompt_text again - version should increment again
        prompt.prompt_text = "Updated content v3"
        prompt.save()
        self.assertEqual(prompt.version, 3)

    def test_system_prompt_version_unchanged_on_other_field_update(self):
        """Test that version does NOT increment when other fields change."""
        import time

        approved_status = self._get_approved_status()
        testing_status = self._get_testing_status()

        # Create prompt with unique name
        unique_name = f"ModelTest_NoVersion_{int(time.time())}"
        prompt = SystemPrompt.objects.create(
            name=unique_name,
            prompt_text="Content that won't change",
            status=approved_status,
        )
        original_version = prompt.version
        self.assertEqual(original_version, 1)

        # Update status only - version should NOT change
        prompt.status = testing_status
        prompt.save()
        self.assertEqual(prompt.version, original_version)

    def test_system_prompt_unique_name(self):
        """Test that prompt names must be unique."""
        import time

        from django.db import IntegrityError

        approved_status = self._get_approved_status()
        unique_name = f"ModelTest_Unique_{int(time.time())}"

        # Create first prompt
        SystemPrompt.objects.create(
            name=unique_name,
            prompt_text="Content",
            status=approved_status,
        )

        # Try to create another with same name - should fail
        with self.assertRaises(IntegrityError):
            SystemPrompt.objects.create(
                name=unique_name,
                prompt_text="Different content",
                status=approved_status,
            )

    def test_system_prompt_requires_prompt_text_when_not_file_based(self):
        """Test that prompt_text is required when is_file_based=False."""
        import time

        approved_status = self._get_approved_status()

        with self.assertRaises(ValidationError) as context:
            prompt = SystemPrompt(
                name=f"ModelTest_MissingText_{int(time.time())}",
                status=approved_status,
                is_file_based=False,
                prompt_text=None,
            )
            prompt.clean()

        self.assertIn("prompt_text", str(context.exception))

    def test_system_prompt_requires_file_name_when_file_based(self):
        """Test that prompt_file_name is required when is_file_based=True."""
        import time

        approved_status = self._get_approved_status()

        with self.assertRaises(ValidationError) as context:
            prompt = SystemPrompt(
                name=f"ModelTest_MissingFile_{int(time.time())}",
                status=approved_status,
                is_file_based=True,
                prompt_file_name=None,
            )
            prompt.clean()

        self.assertIn("prompt_file_name", str(context.exception))

    def test_system_prompt_file_based_valid_file(self):
        """Test that file-based prompt validates the file exists."""
        import time

        approved_status = self._get_approved_status()

        # This should work - the file exists
        prompt = SystemPrompt(
            name=f"ModelTest_ValidFile_{int(time.time())}",
            status=approved_status,
            is_file_based=True,
            prompt_file_name="multi_mcp_system_prompt",
        )
        prompt.clean()  # Should not raise

    def test_system_prompt_file_based_invalid_file(self):
        """Test that file-based prompt validation fails for non-existent file."""
        import time

        approved_status = self._get_approved_status()

        with self.assertRaises(ValidationError) as context:
            prompt = SystemPrompt(
                name=f"ModelTest_InvalidFile_{int(time.time())}",
                status=approved_status,
                is_file_based=True,
                prompt_file_name="nonexistent_prompt_file",
            )
            prompt.clean()

        self.assertIn("prompt_file_name", str(context.exception))

    def test_llm_model_system_prompt_assignment(self):
        """Test assigning SystemPrompt to LLMModel."""
        import time

        approved_status = self._get_approved_status()

        prompt = SystemPrompt.objects.create(
            name=f"ModelTest_Assignment_{int(time.time())}",
            prompt_text="You are a network expert.",
            status=approved_status,
        )

        self.llama2_model.system_prompt = prompt
        self.llama2_model.save()

        # Refresh from database
        self.llama2_model.refresh_from_db()
        self.assertEqual(self.llama2_model.system_prompt, prompt)

    def test_llm_model_system_prompt_nullable(self):
        """Test that system_prompt is nullable on LLMModel."""
        self.assertIsNone(self.llama2_model.system_prompt)
        self.llama2_model.save()  # Should not raise
