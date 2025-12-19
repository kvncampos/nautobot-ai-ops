"""Azure OpenAI model initialization utilities.

DEPRECATED: This module is kept for backward compatibility.
Use ai_ops.helpers.get_llm_model instead for multi-provider support.
"""

import os
import warnings

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

from ai_ops.helpers.common.enums import NautobotEnvironment
from ai_ops.helpers.common.helpers import get_environment

load_dotenv()


def get_azure_model(
    azure_deployment: str | None = None,
    azure_endpoint: str | None = None,
    api_key: str | None = None,
    api_version: str | None = None,
    temperature: float | None = None,
    model_name: str | None = None,
    **kwargs,
):
    """Initialize and return an Azure OpenAI model instance.

    This function supports two modes of operation:
    1. LAB environment: Uses environment variables from .env file
    2. Production environments (NONPROD/PROD): Uses configuration from LLMModel in database

    Args:
        azure_deployment (str | None): Azure deployment name. If not provided, uses model configuration.
        azure_endpoint (str | None): Azure OpenAI endpoint URL. If not provided, uses model configuration.
        api_key (str | None): API key for authentication. If not provided, retrieves from Secret.
        api_version (str | None): Azure OpenAI API version. If not provided, uses model configuration.
        temperature (float | None): Temperature setting for the model. Defaults to model configuration.
        model_name (str | None): Name of the LLM model to use from database. If not provided, uses default model.
        **kwargs: Additional keyword arguments to pass to AzureChatOpenAI.

    Returns:
        AzureChatOpenAI: Initialized Azure OpenAI model instance.

    Raises:
        ValueError: If required parameters are missing or invalid.
        LLMModel.DoesNotExist: If no models exist in the database (non-LAB environments).

    Examples:
        # LAB environment - uses .env variables automatically
        model = get_azure_model()

        # Production - uses default model from database
        model = get_azure_model()

        # Production - uses specific model from database
        model = get_azure_model(model_name="gpt-4o")

        # Override specific parameters
        model = get_azure_model(temperature=0.7)

        # Fully manual configuration (bypasses database)
        model = get_azure_model(
            azure_deployment="my-deployment",
            azure_endpoint="https://my-resource.openai.azure.com/",
            api_key="my-key",
            api_version="2024-02-15-preview"
        )
    """
    env = get_environment()

    # LAB environment: Use environment variables
    if env == NautobotEnvironment.LAB:
        final_azure_deployment = azure_deployment or os.getenv("AZURE_MODEL")
        final_azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        final_api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        final_api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION")
        final_temperature = temperature if temperature is not None else 0

        if not all([final_azure_deployment, final_azure_endpoint, final_api_key, final_api_version]):
            raise ValueError(
                "Missing required configuration. In LAB environment, ensure all environment variables are set: "
                "AZURE_MODEL, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION"
            )

    # Production environments: Use database configuration
    else:
        # Import here to avoid circular dependency issues
        from ai_ops.models import LLMModel

        # Get model from database
        if model_name:
            try:
                llm_model = LLMModel.objects.get(name=model_name)
            except LLMModel.DoesNotExist as err:
                # Query available model names for user guidance
                available_models = list(LLMModel.objects.values_list("name", flat=True))
                available_models_str = ", ".join(available_models) if available_models else "No models configured"
                raise ValueError(
                    f"LLM model '{model_name}' not found in database. "
                    f"Available models: {available_models_str}. "
                    "Please check the database or configure the desired model."
                ) from err
        else:
            llm_model = LLMModel.get_default_model()

        # Use provided parameters or fall back to model configuration
        final_azure_deployment = azure_deployment or llm_model.name
        final_azure_endpoint = azure_endpoint or llm_model.azure_endpoint
        final_api_version = api_version or llm_model.api_version
        final_temperature = temperature if temperature is not None else llm_model.temperature

        # Get API key from Secret if not provided
        if api_key:
            final_api_key = api_key
        else:
            final_api_key = llm_model.get_api_key()

        if not all([final_azure_deployment, final_azure_endpoint, final_api_key, final_api_version]):
            raise ValueError(
                f"Missing required configuration for model '{llm_model.name}'. "
                "Ensure all fields are properly configured in the database."
            )

    # Initialize and return the model
    model = AzureChatOpenAI(
        azure_endpoint=final_azure_endpoint,
        api_key=final_api_key,  # type: ignore
        api_version=final_api_version,
        azure_deployment=final_azure_deployment,
        temperature=final_temperature,
        **kwargs,
    )
    return model


async def get_azure_model_async(
    azure_deployment: str | None = None,
    azure_endpoint: str | None = None,
    api_key: str | None = None,
    api_version: str | None = None,
    temperature: float | None = None,
    model_name: str | None = None,
    **kwargs,
):
    """DEPRECATED: Use get_llm_model_async() instead.

    This function is deprecated and will be removed in a future release.
    Please migrate to get_llm_model_async() which provides provider-agnostic
    model initialization supporting Ollama, OpenAI, Azure AI, Anthropic, and HuggingFace.

    For backward compatibility, this function still works but internally delegates
    to the new provider-agnostic implementation.

    Args:
        azure_deployment (str | None): Azure deployment name. If not provided, uses model configuration.
        azure_endpoint (str | None): Azure OpenAI endpoint URL. If not provided, uses model configuration.
        api_key (str | None): API key for authentication. If not provided, retrieves from Secret.
        api_version (str | None): Azure OpenAI API version. If not provided, uses model configuration.
        temperature (float | None): Temperature setting for the model. Defaults to model configuration.
        model_name (str | None): Name of the LLM model to use from database. If not provided, uses default model.
        **kwargs: Additional keyword arguments to pass to the chat model.

    Returns:
        A LangChain chat model instance.

    Raises:
        ValueError: If required parameters are missing or invalid.
        LLMModel.DoesNotExist: If no models exist in the database (non-LAB environments).

    .. deprecated:: 1.1.0
        Use :func:`get_llm_model_async` instead. This function only supports Azure AI.
        The new function supports multiple providers and is more flexible.

    Examples:
        # DEPRECATED - use get_llm_model_async instead
        model = await get_azure_model_async()
    """
    warnings.warn(
        "get_azure_model_async() is deprecated and will be removed in a future release. "
        "Please use get_llm_model_async() instead for multi-provider support.",
        DeprecationWarning,
        stacklevel=2,
    )

    from ai_ops.helpers.get_llm_model import get_llm_model_async

    # Delegate to the new provider-agnostic function, forcing Azure provider
    return await get_llm_model_async(
        model_name=model_name,
        provider="azure_ai",
        temperature=temperature,
        # Azure-specific parameters
        api_version=api_version,
        **kwargs,
    )
