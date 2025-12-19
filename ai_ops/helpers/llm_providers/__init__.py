"""LLM Provider handler registry and factory."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Global provider handlers registry
# Maps provider names to handler classes
LLM_PROVIDER_HANDLERS: dict[str, Any] = {}


def register_llm_provider(name: str, handler_class: type) -> None:
    """Register a LLM provider handler.

    This function allows custom providers to be registered at runtime,
    enabling extensibility without modifying core code.

    Args:
        name: The provider name (e.g., 'ollama', 'openai', 'custom_provider')
        handler_class: The handler class (must inherit from BaseLLMProviderHandler)

    Example:
        from ai_ops.helpers.llm_providers import register_llm_provider
        from my_custom_provider import MyCustomHandler

        register_llm_provider('my_custom', MyCustomHandler)
    """
    LLM_PROVIDER_HANDLERS[name] = handler_class
    logger.debug(f"Registered LLM provider handler for '{name}': {handler_class.__name__}")


def get_llm_provider_handler(provider_type: str, config: dict | None = None):
    """Get a LLM provider handler instance by type.

    Args:
        provider_type: The LLM provider type (e.g., 'ollama', 'openai', 'azure_ai')
        config: Optional LLM provider-specific configuration dictionary

    Returns:
        BaseLLMProviderHandler: An instance of the appropriate LLM provider handler
    Raises:
        ValueError: If the provider type is not registered
    """
    if provider_type not in LLM_PROVIDER_HANDLERS:
        available_providers = ", ".join(LLM_PROVIDER_HANDLERS.keys())
        raise ValueError(
            f"Unknown provider type: {provider_type}. "
            f"Available providers: {available_providers}. "
            f"See documentation for how to register custom providers."
        )

    handler_class = LLM_PROVIDER_HANDLERS[provider_type]
    return handler_class(config or {})


# Import and register built-in providers
from ai_ops.helpers.llm_providers.anthropic import AnthropicHandler  # noqa: E402
from ai_ops.helpers.llm_providers.azure_ai import AzureAIHandler  # noqa: E402
from ai_ops.helpers.llm_providers.huggingface import HuggingFaceHandler  # noqa: E402
from ai_ops.helpers.llm_providers.ollama import OllamaHandler  # noqa: E402
from ai_ops.helpers.llm_providers.openai import OpenAIHandler  # noqa: E402

# Register all built-in providers
register_llm_provider("ollama", OllamaHandler)
register_llm_provider("openai", OpenAIHandler)
register_llm_provider("azure_ai", AzureAIHandler)
register_llm_provider("anthropic", AnthropicHandler)
register_llm_provider("huggingface", HuggingFaceHandler)

__all__ = [
    "get_llm_provider_handler",
    "register_llm_provider",
    "LLM_PROVIDER_HANDLERS",
    "OllamaHandler",
    "OpenAIHandler",
    "AzureAIHandler",
    "AnthropicHandler",
    "HuggingFaceHandler",
]
