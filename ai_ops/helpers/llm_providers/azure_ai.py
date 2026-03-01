"""Azure AI LLM provider handler."""

import logging
import os

from ai_ops.helpers.llm_providers.base import BaseLLMProviderHandler

logger = logging.getLogger(__name__)


class AzureAIHandler(BaseLLMProviderHandler):
    """Handler for Azure OpenAI (Azure AI) LLM provider.

    Supports Azure OpenAI deployments for models like GPT-4, GPT-4-turbo, etc.

    Reference: https://docs.langchain.com/oss/python/integrations/providers/azure_ai
    """

    def validate_config(self) -> None:
        """Validate Azure AI provider configuration.

        Checks that required configuration values are present either in config
        or as environment variables.

        Raises:
            ValueError: If required configuration is missing
        """
        # Check if azure_endpoint is provided via config or environment
        azure_endpoint = self.config.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
        if not azure_endpoint:
            raise ValueError(
                "Azure endpoint is required. Set via config 'azure_endpoint' field or "
                "AZURE_OPENAI_ENDPOINT environment variable."
            )

        # API key can be provided at runtime, so we don't strictly require it during validation
        # But we can warn if it's not available
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            logger.warning(
                "Azure OpenAI API key not found in environment. "
                "Ensure AZURE_OPENAI_API_KEY is set or provide api_key parameter when creating models."
            )

        logger.debug(f"Azure AI configuration validation passed for endpoint: {azure_endpoint}")

    async def get_chat_model(
        self,
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ):
        """Get an AzureChatOpenAI model instance.

        Args:
            model_name: The Azure deployment name (e.g., 'gpt-4o', 'gpt-4-turbo')
            api_key: Azure OpenAI API key. If not provided, uses AZURE_OPENAI_API_KEY environment variable
            temperature: Temperature setting (0.0 to 2.0)
            **kwargs: Additional parameters passed to AzureChatOpenAI (api_version, etc.)

        Returns:
            AzureChatOpenAI: Configured Azure OpenAI chat model instance

        Raises:
            ImportError: If langchain-openai is not installed
            ValueError: If required configuration (endpoint, API key, api_version) is missing
        """
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError as e:
            raise ImportError(
                "langchain-openai is required for Azure AI provider. Install it with: pip install langchain-openai"
            ) from e

        # Get endpoint - prioritize kwargs (model_config), then provider config, then environment
        azure_endpoint = (
            kwargs.pop("azure_endpoint", None)
            or kwargs.pop("endpoint", None)  # Support both azure_endpoint and endpoint
            or self.config.get("azure_endpoint")
            or os.getenv("AZURE_OPENAI_ENDPOINT")
        )

        if not azure_endpoint:
            raise ValueError(
                "Azure endpoint not provided. Set via model_config, provider config, or AZURE_OPENAI_ENDPOINT environment variable."
            )

        # Remove deprecated parameters that conflict with Azure OpenAI >= 1.0.0
        # These must not be passed to AzureChatOpenAI
        kwargs.pop("base_url", None)
        kwargs.pop("openai_api_base", None)

        # Get API key from parameter or environment
        api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Azure OpenAI API key not provided. Set via parameter or AZURE_OPENAI_API_KEY environment variable."
            )

        # Get API version - prioritize kwargs (model_config), then provider config, then environment
        api_version = (
            kwargs.pop("api_version", None)
            or self.config.get("api_version")
            or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        )

        logger.info(
            f"Initializing AzureChatOpenAI with deployment={model_name}, "
            f"endpoint={azure_endpoint}, api_version={api_version}, temperature={temperature}"
        )

        return AzureChatOpenAI(
            azure_deployment=model_name,
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
            temperature=temperature,
            **kwargs,
        )
