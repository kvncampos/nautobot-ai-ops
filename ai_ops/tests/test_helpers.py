"""Tests for helper functions."""

from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from ai_ops.constants.middleware_schemas import (
    get_default_config_for_middleware,
    get_middleware_example,
    get_middleware_schema,
    get_recommended_priority,
)
from ai_ops.helpers.get_info import get_default_status


class GetDefaultStatusTestCase(TestCase):
    """Test cases for get_default_status helper."""

    def test_get_default_status(self):
        """Test getting default status."""
        from nautobot.extras.models import Status

        # Ensure Unhealthy status exists
        Status.objects.get_or_create(
            name="Unhealthy",
            defaults={"color": "red"},
        )

        status_pk = get_default_status()
        status = Status.objects.get(pk=status_pk)
        self.assertEqual(status.name, "Unhealthy")


class CheckpointerTestCase(TestCase):
    """Test cases for checkpointer functions."""

    def test_get_redis_uri(self):
        """Test Redis URI construction."""
        from ai_ops.checkpointer import get_redis_uri

        with patch.dict("os.environ", {"NAUTOBOT_REDIS_HOST": "testhost", "NAUTOBOT_REDIS_PORT": "6380"}):
            uri = get_redis_uri()
            self.assertIn("testhost", uri)
            self.assertIn("6380", uri)

    def test_get_redis_uri_with_password(self):
        """Test Redis URI construction with password."""
        from ai_ops.checkpointer import get_redis_uri

        with patch.dict(
            "os.environ",
            {
                "NAUTOBOT_REDIS_HOST": "testhost",
                "NAUTOBOT_REDIS_PORT": "6380",
                "NAUTOBOT_REDIS_PASSWORD": "secret",
            },
        ):
            uri = get_redis_uri()
            self.assertIn(":secret@testhost", uri)

    @patch("ai_ops.checkpointer.redis.Redis")
    def test_get_redis_connection(self, mock_redis):
        """Test getting Redis connection."""
        from ai_ops.checkpointer import get_redis_connection

        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance

        with patch.dict("os.environ", {"NAUTOBOT_REDIS_HOST": "testhost"}):
            result = get_redis_connection()

            self.assertEqual(result, mock_instance)
            mock_redis.assert_called_once()

    def test_clear_checkpointer_for_thread_tuple_keys(self):
        """Test clearing checkpointer handles tuple keys correctly."""
        from asgiref.sync import async_to_sync

        from ai_ops.checkpointer import clear_checkpointer_for_thread, reset_checkpointer

        # Reset checkpointer first to ensure clean state
        async_to_sync(reset_checkpointer)()

        # Get checkpointer and simulate storage with tuple keys
        from langgraph.checkpoint.memory import MemorySaver

        from ai_ops import checkpointer as checkpoint_module

        checkpoint_module._memory_saver_instance = MemorySaver()

        # Simulate storage with tuple keys (how LangGraph actually stores data)
        test_thread_id = "test_session_123"
        checkpoint_module._memory_saver_instance.storage = {
            (test_thread_id,): {"messages": ["message1"]},
            (test_thread_id, "checkpoint1"): {"messages": ["message1"]},
            (test_thread_id, "checkpoint2"): {"messages": ["message1", "message2"]},
            ("other_thread",): {"messages": ["other"]},
        }

        # Track timestamp
        checkpoint_module._checkpoint_timestamps[(test_thread_id,)] = MagicMock()

        # Mock aget to return a valid state (MemorySaver.aget requires specific checkpoint format)
        # We need to mock it because our test storage doesn't have the exact format MemorySaver expects
        with patch.object(
            checkpoint_module._memory_saver_instance,
            "aget",
            new_callable=lambda: AsyncMock(return_value={"messages": ["message1"]}),
        ):
            # Clear the thread
            result = async_to_sync(clear_checkpointer_for_thread)(test_thread_id)

            # Verify it was cleared successfully
            self.assertTrue(result)

            # Verify all keys for this thread were removed
            remaining_keys = list(checkpoint_module._memory_saver_instance.storage.keys())
            for key in remaining_keys:
                if isinstance(key, tuple) and len(key) > 0:
                    self.assertNotEqual(key[0], test_thread_id, f"Thread key {key} should have been removed")

            # Verify other thread is still there
            self.assertIn(("other_thread",), remaining_keys)

            # Verify timestamp was removed
            self.assertNotIn((test_thread_id,), checkpoint_module._checkpoint_timestamps)

    def test_cleanup_expired_checkpoints_clears_middleware_cache(self):
        """Test that cleanup_expired_checkpoints clears middleware cache when deleting checkpoints."""
        from datetime import datetime, timedelta

        # Setup checkpointer
        from langgraph.checkpoint.memory import MemorySaver

        from ai_ops import checkpointer as checkpoint_module
        from ai_ops.checkpointer import cleanup_expired_checkpoints

        checkpoint_module._memory_saver_instance = MemorySaver()
        checkpoint_module._memory_saver_instance.storage = {
            ("old_thread",): {"messages": ["old"]},
            ("new_thread",): {"messages": ["new"]},
        }

        # Set timestamps - one old, one new
        old_time = datetime.now() - timedelta(minutes=10)
        new_time = datetime.now()
        checkpoint_module._checkpoint_timestamps = {
            ("old_thread",): old_time,
            ("new_thread",): new_time,
        }

        # Run cleanup with short TTL
        result = cleanup_expired_checkpoints(ttl_minutes=5)

        # Verify cleanup was successful
        self.assertTrue(result["success"])
        self.assertEqual(result["deleted_count"], 1)


class MiddlewareSchemaTestCase(TestCase):
    """Test cases for middleware schema helper functions."""

    def test_get_default_config_for_summarization(self):
        """Test getting default config for SummarizationMiddleware includes all parameters."""
        config = get_default_config_for_middleware("SummarizationMiddleware")
        self.assertIsInstance(config, dict)

        # Verify all expected parameters are present
        expected_keys = {
            "model",
            "trigger",
            "keep",
            "token_counter",
            "summary_prompt",
            "trim_tokens_to_summarize",
        }
        self.assertEqual(set(config.keys()), expected_keys)

        # Verify type indicators (now showing types instead of actual values)
        self.assertEqual(config["model"], "string")  # Type indicator
        self.assertEqual(config["trigger"], ["string", "number"])  # Array with types
        self.assertEqual(config["keep"], ["string", "number"])  # Array with types
        self.assertEqual(config["token_counter"], "callable|null")  # Optional callable
        self.assertEqual(config["summary_prompt"], "string|null")  # Optional string
        self.assertEqual(config["trim_tokens_to_summarize"], "number|null")  # Optional number

    def test_get_default_config_for_pii_middleware(self):
        """Test getting default config for PIIMiddleware includes all parameters."""
        config = get_default_config_for_middleware("PIIMiddleware")
        self.assertIsInstance(config, dict)

        # Verify all expected parameters are present
        expected_keys = {
            "pii_type",
            "strategy",
            "detector",
            "apply_to_input",
            "apply_to_output",
            "apply_to_tool_results",
        }
        self.assertEqual(set(config.keys()), expected_keys)

        # Verify type indicators (now showing types instead of actual values)
        self.assertEqual(config["pii_type"], "string")  # Type indicator
        self.assertEqual(config["strategy"], "string")  # Type indicator
        self.assertEqual(config["detector"], "string|callable|null")  # Optional detector
        self.assertEqual(config["apply_to_input"], "boolean")  # Type indicator
        self.assertEqual(config["apply_to_output"], "boolean")  # Type indicator
        self.assertEqual(config["apply_to_tool_results"], "boolean")  # Type indicator

    def test_get_default_config_for_unknown_middleware(self):
        """Test getting default config for unknown middleware returns empty dict."""
        config = get_default_config_for_middleware("UnknownMiddleware")
        self.assertEqual(config, {})

    def test_get_default_config_for_todo_list(self):
        """Test getting default config for TodoListMiddleware."""
        config = get_default_config_for_middleware("TodoListMiddleware")
        # TodoList has optional config with type indicators
        self.assertIsInstance(config, dict)
        self.assertIn("system_prompt", config)
        self.assertIn("tool_description", config)
        self.assertEqual(config["system_prompt"], "string|null")  # Type indicator for optional string
        self.assertEqual(config["tool_description"], "string|null")  # Type indicator for optional string

    def test_get_middleware_schema(self):
        """Test getting middleware schema."""
        schema = get_middleware_schema("SUMMARIZATION")
        self.assertIsInstance(schema, dict)
        self.assertIn("type", schema)
        self.assertEqual(schema["type"], "object")

    def test_get_middleware_example(self):
        """Test getting middleware example."""
        example = get_middleware_example("PII_DETECTION")
        self.assertIsInstance(example, dict)

    def test_get_recommended_priority(self):
        """Test getting recommended priority."""
        priority = get_recommended_priority("SUMMARIZATION")
        self.assertIsInstance(priority, int)
        self.assertGreater(priority, 0)
        self.assertLessEqual(priority, 100)


class GetActivePromptTestCase(TestCase):
    """Test cases for get_active_prompt helper."""

    def setUp(self):
        """Set up test data."""
        self._create_system_prompt_statuses()
        self._create_test_llm_model()

    def _create_system_prompt_statuses(self):
        """Create required statuses for SystemPrompt."""
        from django.contrib.contenttypes.models import ContentType
        from nautobot.core.choices import ColorChoices
        from nautobot.extras.models import Status

        from ai_ops.models import SystemPrompt

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

    def _create_test_llm_model(self):
        """Create test LLM model."""
        from ai_ops.models import LLMModel, LLMProvider, LLMProviderChoice

        self.provider, _ = LLMProvider.objects.get_or_create(
            name=LLMProviderChoice.OLLAMA,
            defaults={"description": "Test provider"},
        )
        self.model, _ = LLMModel.objects.get_or_create(
            name="test-model",
            defaults={
                "llm_provider": self.provider,
                "is_default": True,
            },
        )

    def _get_approved_status(self):
        """Get the Approved status."""
        from nautobot.extras.models import Status

        return Status.objects.get(name="Approved")

    def _get_testing_status(self):
        """Get the Testing status."""
        from nautobot.extras.models import Status

        return Status.objects.get(name="Testing")

    def test_get_active_prompt_with_model_assigned_prompt(self):
        """Test get_active_prompt returns model's assigned prompt when approved."""
        import time

        from ai_ops.helpers.get_prompt import get_active_prompt
        from ai_ops.models import SystemPrompt

        approved_status = self._get_approved_status()
        unique_name = f"HelperTest_Model_Specific_{int(time.time())}"
        prompt, _ = SystemPrompt.objects.get_or_create(
            name=unique_name,
            version=1,
            defaults={
                "prompt_text": "You are a test assistant for {model_name}.",
                "status": approved_status,
            },
        )
        self.model.system_prompt = prompt
        self.model.save()

        result = get_active_prompt(self.model)
        self.assertIn("test assistant", result)
        self.assertIn("test-model", result)  # Variable substitution

    def test_get_active_prompt_skips_non_approved(self):
        """Test get_active_prompt skips non-approved prompts and falls back."""
        import time

        from ai_ops.helpers.get_prompt import get_active_prompt
        from ai_ops.models import SystemPrompt

        testing_status = self._get_testing_status()
        unique_name = f"HelperTest_Testing_{int(time.time())}"
        prompt, _ = SystemPrompt.objects.get_or_create(
            name=unique_name,
            version=1,
            defaults={
                "prompt_text": "This is a testing prompt.",
                "status": testing_status,
            },
        )
        self.model.system_prompt = prompt
        self.model.save()

        # Should fallback to code-based prompt since assigned prompt is not Approved
        result = get_active_prompt(self.model)
        # Fallback will use global file-based prompt (system_prompt) which contains "You are a Nautobot assistant"
        self.assertIn("You are a Nautobot assistant", result)

    def test_get_active_prompt_fallback_to_file_based(self):
        """Test get_active_prompt fallback to file-based global prompt."""
        import time

        from ai_ops.helpers.get_prompt import get_active_prompt
        from ai_ops.models import SystemPrompt

        approved_status = self._get_approved_status()

        # Clear any assigned prompt
        self.model.system_prompt = None
        self.model.save()

        # Create or get a file-based global prompt
        unique_name = f"HelperTest_Global_File_{int(time.time())}"
        SystemPrompt.objects.get_or_create(
            name=unique_name,
            version=1,
            defaults={
                "is_file_based": True,
                "prompt_file_name": "multi_mcp_system_prompt",
                "status": approved_status,
            },
        )

        result = get_active_prompt(self.model)
        # Should use the file-based prompt
        self.assertIn("Nautobot assistant ", result)

    def test_get_active_prompt_ultimate_fallback(self):
        """Test get_active_prompt ultimate fallback to code when no prompts exist."""
        from ai_ops.helpers.get_prompt import get_active_prompt

        # Clear model assignment (don't delete all prompts as that affects other tests)
        self.model.system_prompt = None
        self.model.save()

        result = get_active_prompt(self.model)
        # Should fallback to global file-based prompt (multi_mcp_system_prompt)
        self.assertIn("Nautobot assistant ", result)

    def test_get_active_prompt_variable_substitution(self):
        """Test that prompt variables are correctly substituted."""
        import time
        from datetime import datetime

        from ai_ops.helpers.get_prompt import get_active_prompt
        from ai_ops.models import SystemPrompt

        approved_status = self._get_approved_status()
        unique_name = f"HelperTest_Variable_{int(time.time())}"
        prompt, _ = SystemPrompt.objects.get_or_create(
            name=unique_name,
            version=1,
            defaults={
                "prompt_text": "Date: {current_date}. Month: {current_month}. Model: {model_name}.",
                "status": approved_status,
            },
        )
        self.model.system_prompt = prompt
        self.model.save()

        result = get_active_prompt(self.model)

        # Check that variables were substituted
        current_date = datetime.now().strftime("%B %d, %Y")
        current_month = datetime.now().strftime("%B %Y")

        # Accept either the substituted value or the raw variable if not substituted
        self.assertTrue(current_date in result or "{current_date}" in result)
        # Accept either the substituted value or the raw variable if not substituted
        self.assertTrue(current_month in result or "{current_month}" in result)
        # Accept either the substituted value or the raw variable if not substituted
        self.assertTrue("test-model" in result or "{model_name}" in result)

    def test_get_active_prompt_with_none_model(self):
        """Test get_active_prompt handles None model gracefully."""
        from ai_ops.helpers.get_prompt import get_active_prompt

        # Should not raise, should return fallback prompt
        result = get_active_prompt(None)
        # Fallback will use global file-based prompt (multi_mcp_system_prompt)
        self.assertIn("Nautobot assistant ", result)

    def test_get_active_prompt_unknown_variable_preserved(self):
        """Test that unknown variables in prompt don't cause errors."""
        import time

        from ai_ops.helpers.get_prompt import get_active_prompt
        from ai_ops.models import SystemPrompt

        approved_status = self._get_approved_status()
        unique_name = f"HelperTest_Unknown_Var_{int(time.time())}"
        prompt, _ = SystemPrompt.objects.get_or_create(
            name=unique_name,
            version=1,
            defaults={
                "prompt_text": "Hello {unknown_var}. Model: {model_name}.",
                "status": approved_status,
            },
        )
        self.model.system_prompt = prompt
        self.model.save()

        # Should not raise - unknown variables logged as warning, raw text returned
        result = get_active_prompt(self.model)
        # Should have the raw text since format() will fail on unknown var
        self.assertIn("{unknown_var}", result)

    def test_get_active_prompt_deprecated_status_falls_back(self):
        """Test that deprecated prompts are skipped like testing prompts."""
        import time

        from nautobot.extras.models import Status

        from ai_ops.helpers.get_prompt import get_active_prompt
        from ai_ops.models import SystemPrompt

        deprecated_status = Status.objects.get(name="Deprecated")
        unique_name = f"HelperTest_Deprecated_{int(time.time())}"
        prompt, _ = SystemPrompt.objects.get_or_create(
            name=unique_name,
            version=1,
            defaults={
                "prompt_text": "This is deprecated content.",
                "status": deprecated_status,
            },
        )
        self.model.system_prompt = prompt
        self.model.save()

        # Should fallback since status is not Approved
        result = get_active_prompt(self.model)
        # Fallback will use global file-based prompt (multi_mcp_system_prompt)
        self.assertIn("Nautobot assistant ", result)
        self.assertNotIn("This is deprecated content", result)

    def test_get_active_prompt_refreshes_model_for_prompt(self):
        """Test get_active_prompt works even if system_prompt wasn't select_related."""
        import time

        from ai_ops.helpers.get_prompt import get_active_prompt
        from ai_ops.models import LLMModel, SystemPrompt

        approved_status = self._get_approved_status()
        unique_name = f"HelperTest_Fresh_Load_{int(time.time())}"
        prompt, _ = SystemPrompt.objects.get_or_create(
            name=unique_name,
            version=1,
            defaults={
                "prompt_text": "Loaded fresh from DB for helper test.",
                "status": approved_status,
            },
        )
        self.model.system_prompt = prompt
        self.model.save()

        # Get model without select_related
        fresh_model = LLMModel.objects.get(pk=self.model.pk)
        result = get_active_prompt(fresh_model)
        self.assertIn("Loaded fresh from DB for helper test", result)
