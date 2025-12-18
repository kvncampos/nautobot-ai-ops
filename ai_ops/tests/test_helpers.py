"""Tests for helper functions."""

import unittest
from unittest.mock import MagicMock, patch

from django.test import TestCase

from ai_ops.helpers.get_info import get_default_status
from ai_ops.models import LLMModel, LLMProvider, LLMProviderChoice


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


class GetLLMModelAsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """Test cases for get_llm_model_async helper."""

    async def asyncSetUp(self):
        """Set up test data."""
        from asgiref.sync import sync_to_async

        # Create provider
        self.provider = await sync_to_async(LLMProvider.objects.create)(
            name=LLMProviderChoice.OLLAMA,
            description="Test provider",
        )

        # Create model
        self.model = await sync_to_async(LLMModel.objects.create)(
            llm_provider=self.provider,
            name="llama2",
            temperature=0.7,
            is_default=True,
        )

    async def asyncTearDown(self):
        """Clean up test data."""
        from asgiref.sync import sync_to_async

        await sync_to_async(LLMModel.objects.all().delete)()
        await sync_to_async(LLMProvider.objects.all().delete)()

    @patch("ai_ops.helpers.get_llm_model.logger")
    async def test_get_default_model(self, mock_logger):
        """Test getting default model without specifying name."""
        from ai_ops.helpers.get_llm_model import get_llm_model_async

        with patch.object(self.provider, "get_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_chat_model = MagicMock()
            mock_handler.get_chat_model.return_value = mock_chat_model
            mock_get_handler.return_value = mock_handler

            result = await get_llm_model_async()

            self.assertEqual(result, mock_chat_model)
            mock_handler.get_chat_model.assert_called_once()

    @patch("ai_ops.helpers.get_llm_model.logger")
    async def test_get_model_by_name(self, mock_logger):
        """Test getting model by name."""
        from ai_ops.helpers.get_llm_model import get_llm_model_async

        with patch.object(self.provider, "get_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_chat_model = MagicMock()
            mock_handler.get_chat_model.return_value = mock_chat_model
            mock_get_handler.return_value = mock_handler

            result = await get_llm_model_async(model_name="llama2")

            self.assertEqual(result, mock_chat_model)

    @patch("ai_ops.helpers.get_llm_model.logger")
    async def test_get_model_with_temperature_override(self, mock_logger):
        """Test getting model with temperature override."""
        from ai_ops.helpers.get_llm_model import get_llm_model_async

        with patch.object(self.provider, "get_handler") as mock_get_handler:
            mock_handler = MagicMock()
            mock_chat_model = MagicMock()
            mock_handler.get_chat_model.return_value = mock_chat_model
            mock_get_handler.return_value = mock_handler

            result = await get_llm_model_async(temperature=0.9)

            self.assertEqual(result, mock_chat_model)
            call_kwargs = mock_handler.get_chat_model.call_args[1]
            self.assertEqual(call_kwargs["temperature"], 0.9)


class CheckpointerTestCase(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()
