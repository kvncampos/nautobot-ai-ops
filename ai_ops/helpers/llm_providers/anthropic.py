"""Anthropic LLM provider handler."""

import logging
import os

from pydantic import SecretStr

from ai_ops.helpers.llm_providers.base import BaseLLMProviderHandler

logger = logging.getLogger(__name__)


class AnthropicHandler(BaseLLMProviderHandler):
    """Handler for Anthropic LLM provider.

    Supports Anthropic models like Claude 3, Claude 3.5, and other variants.

    Reference: https://docs.langchain.com/oss/python/integrations/chat/anthropic
    """

    def validate_config(self) -> None:
        """Validate Anthropic provider configuration.

        Checks for API key availability and validates any configured settings.

        Raises:
            ValueError: If configuration is invalid
        """
        import os

        # API key can be provided at runtime, so we don't strictly require it during validation
        # But we can warn if it's not available
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning(
                "Anthropic API key not found in environment. "
                "Ensure ANTHROPIC_API_KEY is set or provide api_key parameter when creating models."
            )

        logger.debug("Anthropic configuration validation passed")

    async def get_chat_model(
        self,
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ):
        """Get a ChatAnthropic model instance.

        Args:
            model_name: The Anthropic model name (e.g., 'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku')
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY environment variable
            temperature: Temperature setting (0.0 to 2.0)
            **kwargs: Additional parameters passed to ChatAnthropic (max_tokens, etc.)

        Returns:
            ChatAnthropic: Configured Anthropic chat model instance

        Raises:
            ImportError: If langchain-anthropic is not installed
            ValueError: If API key is not provided and not found in environment
        """
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:
            raise ImportError(
                "langchain-anthropic is required for Anthropic provider. "
                "Install it with: pip install langchain-anthropic"
            ) from e

        # Get API key from parameter or environment
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Anthropic API key not provided. Set via parameter or ANTHROPIC_API_KEY environment variable."
            )

        logger.info(f"Initializing ChatAnthropic with model={model_name}, temperature={temperature}")

        return ChatAnthropic(
            model_name=model_name,
            api_key=SecretStr(api_key),
            temperature=temperature,
            **kwargs,
        )
