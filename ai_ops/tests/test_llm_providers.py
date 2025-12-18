"""Tests for LLM provider handlers."""

import unittest
from unittest.mock import MagicMock, patch

from ai_ops.helpers.llm_providers.base import BaseLLMProviderHandler
from ai_ops.helpers.llm_providers.ollama import OllamaHandler


class TestBaseLLMProviderHandler(unittest.TestCase):
    """Test cases for BaseLLMProviderHandler abstract class."""

    def test_handler_initialization(self):
        """Test handler initialization with config."""

        class ConcreteHandler(BaseLLMProviderHandler):
            """Concrete implementation for testing."""

            async def get_chat_model(self, model_name, api_key=None, temperature=0.0, **kwargs):
                """Dummy implementation."""
                return None

            def validate_config(self):
                """Dummy implementation."""
                pass

        config = {"key": "value"}
        handler = ConcreteHandler(config=config)
        self.assertEqual(handler.config, config)

    def test_handler_initialization_without_config(self):
        """Test handler initialization without config."""

        class ConcreteHandler(BaseLLMProviderHandler):
            """Concrete implementation for testing."""

            async def get_chat_model(self, model_name, api_key=None, temperature=0.0, **kwargs):
                """Dummy implementation."""
                return None

            def validate_config(self):
                """Dummy implementation."""
                pass

        handler = ConcreteHandler()
        self.assertEqual(handler.config, {})


class TestOllamaHandler(unittest.TestCase):
    """Test cases for OllamaHandler."""

    def setUp(self):
        """Set up test data."""
        self.handler = OllamaHandler()

    def test_validate_config_with_valid_url(self):
        """Test config validation with valid URL."""
        self.handler.config = {"base_url": "http://localhost:11434"}
        # Should not raise any exception
        self.handler.validate_config()

    def test_validate_config_with_invalid_url(self):
        """Test config validation with invalid URL."""
        self.handler.config = {"base_url": "invalid-url"}
        with self.assertRaises(ValueError) as context:
            self.handler.validate_config()
        self.assertIn("Invalid Ollama base_url", str(context.exception))

    def test_validate_config_with_https_url(self):
        """Test config validation with HTTPS URL."""
        self.handler.config = {"base_url": "https://example.com:11434"}
        # Should not raise any exception
        self.handler.validate_config()

    @patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://custom:11434"})
    def test_validate_config_with_env_var(self):
        """Test config validation with environment variable."""
        self.handler.config = {}
        # Should use env var and not raise exception
        self.handler.validate_config()

    @patch("ai_ops.helpers.llm_providers.ollama.ChatOllama")
    @patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://test:11434"})
    async def test_get_chat_model(self, mock_chat_ollama):
        """Test get_chat_model method."""
        mock_instance = MagicMock()
        mock_chat_ollama.return_value = mock_instance

        result = await self.handler.get_chat_model(
            model_name="llama2",
            temperature=0.5,
        )

        self.assertEqual(result, mock_instance)
        mock_chat_ollama.assert_called_once()
        call_kwargs = mock_chat_ollama.call_args[1]
        self.assertEqual(call_kwargs["model"], "llama2")
        self.assertEqual(call_kwargs["temperature"], 0.5)

    async def test_get_chat_model_import_error(self):
        """Test get_chat_model raises ImportError when package not installed."""
        with patch("ai_ops.helpers.llm_providers.ollama.ChatOllama", side_effect=ImportError):
            with self.assertRaises(ImportError) as context:
                await self.handler.get_chat_model(model_name="llama2")
            self.assertIn("langchain-ollama is required", str(context.exception))


class TestLLMProviderRegistry(unittest.TestCase):
    """Test cases for LLM provider registry."""

    def test_get_llm_provider_handler(self):
        """Test getting handler from registry."""
        from ai_ops.helpers.llm_providers import get_llm_provider_handler

        handler = get_llm_provider_handler("ollama")
        self.assertIsInstance(handler, OllamaHandler)

    def test_get_llm_provider_handler_with_config(self):
        """Test getting handler with config."""
        from ai_ops.helpers.llm_providers import get_llm_provider_handler

        config = {"base_url": "http://custom:11434"}
        handler = get_llm_provider_handler("ollama", config=config)
        self.assertEqual(handler.config, config)

    def test_get_llm_provider_handler_invalid_provider(self):
        """Test getting handler for invalid provider."""
        from ai_ops.helpers.llm_providers import get_llm_provider_handler

        with self.assertRaises(ValueError) as context:
            get_llm_provider_handler("invalid_provider")
        self.assertIn("Unknown LLM provider", str(context.exception))


if __name__ == "__main__":
    unittest.main()
