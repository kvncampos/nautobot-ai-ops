"""Tests for helper functions."""

from unittest.mock import MagicMock, patch

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
