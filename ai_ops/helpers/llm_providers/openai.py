"""OpenAI LLM provider handler."""

import logging
import os

from ai_ops.helpers.llm_providers.base import BaseLLMProviderHandler

logger = logging.getLogger(__name__)


class OpenAIHandler(BaseLLMProviderHandler):
    """Handler for OpenAI LLM provider.

    Supports all OpenAI models including GPT-4, GPT-3.5-turbo, and other variants.

    Reference: https://docs.langchain.com/oss/python/integrations/chat/openai
    """

    def validate_config(self) -> None:
        """Validate OpenAI provider configuration.

        Checks for API key availability and validates any configured base_url.

        Raises:
            ValueError: If configuration is invalid
        """
        import os

        # API key can be provided at runtime, so we don't strictly require it during validation
        # But we can warn if it's not available
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning(
                "OpenAI API key not found in environment. "
                "Ensure OPENAI_API_KEY is set or provide api_key parameter when creating models."
            )

        # Validate base_url if provided
        base_url = self.config.get("base_url")
        if base_url and not base_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid OpenAI base_url: '{base_url}'. Must start with http:// or https://")

        logger.debug("OpenAI configuration validation passed")

    async def get_chat_model(
        self,
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ):
        """Get a ChatOpenAI model instance.

        Args:
            model_name: The OpenAI model name (e.g., 'gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo')
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY environment variable
            temperature: Temperature setting (0.0 to 2.0)
            **kwargs: Additional parameters passed to ChatOpenAI (organization, base_url, etc.)

        Returns:
            ChatOpenAI: Configured OpenAI chat model instance

        Raises:
            ImportError: If langchain-openai is not installed
            ValueError: If API key is not provided and not found in environment
        """
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise ImportError(
                "langchain-openai is required for OpenAI provider. Install it with: pip install langchain-openai"
            ) from e

        # Get API key from parameter or environment
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not provided. Set via parameter or OPENAI_API_KEY environment variable.")

        # Get base_url - prioritize kwargs (model_config), then provider config, then default
        # Support both 'base_url' and 'endpoint' as aliases
        base_url = (
            kwargs.pop("base_url", None) or kwargs.pop("endpoint", None) or self.config.get("base_url") or None
        )
        if base_url:
            kwargs["base_url"] = base_url

        logger.info(f"Initializing ChatOpenAI with model={model_name}, temperature={temperature}")

        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
            **kwargs,
        )
