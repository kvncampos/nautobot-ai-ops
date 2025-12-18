"""Base provider handler abstract class."""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseLLMProviderHandler(ABC):
    """Abstract base class for LLM provider handlers.

    Each llm provider (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, etc.)
    has a corresponding handler that knows how to initialize and configure
    that provider's chat model.

    Subclasses must implement get_chat_model() to return the provider's
    chat model instance configured with the given parameters.

    Example:
        class CustomHandler(BaseLLMProviderHandler):
            async def get_chat_model(self, model_name, **kwargs):
                from langchain_custom import ChatCustom
                return ChatCustom(model=model_name, **kwargs)
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the provider handler.

        Args:
            config: Provider-specific configuration dictionary from the Provider model's config_schema.
                   This allows admins to configure provider-specific settings (e.g., API versions,
                   custom endpoints) without code changes.
        """
        self.config = config or {}
        logger.debug(f"Initialized {self.__class__.__name__} with config: {self.config}")

    @abstractmethod
    async def get_chat_model(
        self,
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ):
        """Get a configured chat model instance for this provider.

        Subclasses must implement this method to return a LangChain chat model
        instance configured for their specific provider.

        Args:
            model_name: The model name/deployment name specific to the provider
                       (e.g., 'gpt-4' for OpenAI, 'llama2' for Ollama, 'claude-3' for Anthropic)
            api_key: Optional API key. If not provided, should be retrieved from environment or config
            temperature: Temperature setting for the model (0.0 to 2.0)
            **kwargs: Additional provider-specific parameters

        Returns:
            A LangChain chat model instance (e.g., ChatOpenAI, ChatOllama, ChatAnthropic)

        Raises:
            ValueError: If required configuration is missing
            ImportError: If provider library is not installed
        """
        pass

    @abstractmethod
    def validate_config(self) -> None:
        """Validate provider configuration.

        Subclasses can override this to validate that required config values are present.
        Called during handler initialization if validation is needed.

        Raises:
            ValueError: If configuration is invalid
        """
        pass
