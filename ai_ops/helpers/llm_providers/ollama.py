"""Ollama LLM provider handler."""

import logging
import os

from ai_ops.helpers.llm_providers.base import BaseLLMProviderHandler

logger = logging.getLogger(__name__)


class OllamaHandler(BaseLLMProviderHandler):
    """Handler for Ollama LLM provider.

    Ollama is a local LLM runtime that allows running open-source models
    (llama2, mistral, etc.) on personal hardware.

    Reference: https://docs.langchain.com/oss/python/integrations/chat/ollama
    """

    def validate_config(self) -> None:
        """Validate Ollama provider configuration.

        Ollama typically runs locally, so we mainly check if the base_url
        is configured properly.

        Raises:
            ValueError: If configuration is invalid
        """
        import os

        # Check if base_url is provided via config or use default localhost
        base_url = self.config.get("base_url") or os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Basic URL validation
        if not base_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid Ollama base_url: '{base_url}'. Must start with http:// or https://")

        logger.debug(f"Ollama configuration validation passed for base_url: {base_url}")

    async def get_chat_model(
        self,
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ):
        """Get a ChatOllama model instance.

        Args:
            model_name: The Ollama model name (e.g., 'llama2', 'mistral', 'neural-chat')
            api_key: Unused for Ollama (local model), included for interface compatibility
            temperature: Temperature setting (0.0 to 2.0)
            **kwargs: Additional parameters passed to ChatOllama (base_url, num_gpu, etc.)

        Returns:
            ChatOllama: Configured Ollama chat model instance

        Raises:
            ImportError: If langchain-ollama is not installed
        """
        try:
            from langchain_ollama import ChatOllama
        except ImportError as e:
            raise ImportError(
                "langchain-ollama is required for Ollama provider. Install it with: pip install langchain-ollama"
            ) from e

        # Get base URL from config or environment
        base_url = self.config.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

        logger.info(f"Initializing ChatOllama with model={model_name}, base_url={base_url}, temperature={temperature}")

        return ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=temperature,
            **kwargs,
        )
