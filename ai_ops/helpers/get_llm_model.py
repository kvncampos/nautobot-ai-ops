"""Provider-agnostic LLM model retrieval helper.

This module provides the primary interface for getting chat models from any configured provider.
It handles provider selection, model lookup, API key retrieval, and model instantiation.
"""

import logging

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


async def get_llm_model_async(
    model_name: str | None = None,
    provider: str | None = None,
    temperature: float | None = None,
    **kwargs,
):
    """Get a configured LLM chat model instance.

    This is the primary interface for getting LangChain chat models. It supports
    multiple providers (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace) and
    automatically handles:
    - Model lookup from database
    - Provider handler selection
    - API key retrieval
    - Model instantiation with proper configuration

    Args:
        model_name: Name of the LLMModel to use. If None, uses the default model.
        provider: Provider name to override (e.g., 'ollama', 'openai', 'azure_ai').
                 If None, uses the provider from the LLMModel.
        temperature: Temperature override. If None, uses model's configured temperature.
        **kwargs: Additional provider-specific parameters passed to the handler.

    Returns:
        A LangChain chat model instance (ChatOpenAI, ChatOllama, ChatAnthropic, etc.)

    Raises:
        LLMModel.DoesNotExist: If the specified model doesn't exist
        ValueError: If provider is not registered or required config is missing
        ImportError: If provider library is not installed
    """
    from ai_ops.models import LLMModel

    try:
        # Get the LLM model from database
        if model_name:
            llm_model = await sync_to_async(LLMModel.objects.select_related("llm_provider").get)(name=model_name)
        else:
            llm_model = await sync_to_async(LLMModel.get_default_model)()

        logger.debug(f"Retrieved LLMModel: {llm_model.name}, provider: {llm_model.llm_provider.name}")

        # Use provided provider or model's configured provider
        provider_instance = llm_model.llm_provider
        if provider:
            # Override provider if specified
            provider_instance = await sync_to_async(
                lambda: __import__("ai_ops.models", fromlist=["LLMProvider"]).LLMProvider.objects.get(name=provider)
            )()
            logger.debug(f"Using overridden provider: {provider}")

        # Get provider handler
        handler = provider_instance.get_handler()

        # Get API key if configured
        api_key = None
        if llm_model.model_secret_key:
            try:
                api_key = await sync_to_async(llm_model.get_api_key)()
                logger.debug(f"Retrieved API key for model: {llm_model.name}")
            except Exception as e:
                logger.warning(f"Failed to retrieve API key for model {llm_model.name}: {e}")
                # Continue without API key - some providers may not need it (e.g., local Ollama)

        # Use provided temperature or model's configured temperature
        temperature = temperature if temperature is not None else llm_model.temperature

        logger.info(
            f"Getting chat model: name={llm_model.name}, provider={provider_instance.name}, temperature={temperature}"
        )

        # Merge model_config from database with runtime kwargs
        # Runtime kwargs take precedence over model_config
        merged_kwargs = {**llm_model.model_config, **kwargs}

        # Get the chat model from the provider handler
        chat_model = await handler.get_chat_model(
            model_name=llm_model.name,
            api_key=api_key,
            temperature=temperature,
            **merged_kwargs,  # Passes both DB config and runtime overrides
        )

        logger.debug(f"Model config merged: db={llm_model.model_config}, runtime={kwargs}")
        logger.info(f"Successfully initialized chat model: {llm_model.name} ({provider_instance.name})")
        return chat_model

    except Exception as e:
        logger.error(f"Error getting LLM model: {e}", exc_info=True)
        raise
