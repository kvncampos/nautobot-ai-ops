"""HuggingFace LLM provider handler."""

import logging
import os

from ai_ops.helpers.llm_providers.base import BaseLLMProviderHandler

logger = logging.getLogger(__name__)


class HuggingFaceHandler(BaseLLMProviderHandler):
    """Handler for HuggingFace LLM provider.

    Supports HuggingFace models through their endpoints and APIs.

    Reference: https://docs.langchain.com/oss/python/integrations/chat/huggingface
    """

    async def get_chat_model(
        self,
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ):
        """Get a ChatHuggingFace or HuggingFaceEndpoint model instance.

        Args:
            model_name: The HuggingFace model name or endpoint URL
            api_key: HuggingFace API token. If not provided, uses HF_API_TOKEN environment variable
            temperature: Temperature setting (0.0 to 2.0)
            **kwargs: Additional parameters passed to HuggingFaceEndpoint (repo_id, task, etc.)

        Returns:
            HuggingFaceEndpoint: Configured HuggingFace chat model instance

        Raises:
            ImportError: If langchain-huggingface is not installed
            ValueError: If API key is not provided and not found in environment
        """
        try:
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        except ImportError as e:
            raise ImportError(
                "langchain-huggingface is required for HuggingFace provider. "
                "Install it with: pip install langchain-huggingface"
            ) from e

        # Get API token from parameter or environment
        api_token = api_key or os.getenv("HF_API_TOKEN")
        if not api_token:
            raise ValueError(
                "HuggingFace API token not provided. Set via parameter or HF_API_TOKEN environment variable."
            )

        logger.info(f"Initializing HuggingFaceEndpoint with model={model_name}, temperature={temperature}")

        # Create HuggingFace endpoint
        llm_endpoint = HuggingFaceEndpoint(
            repo_id=model_name,
            huggingfacehub_api_token=api_token,
            temperature=temperature,
            **kwargs,
        )

        return ChatHuggingFace(llm=llm_endpoint)
