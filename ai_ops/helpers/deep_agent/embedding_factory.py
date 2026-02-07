"""
Centralized Embedding Factory for creating embedding models for RAG operations.
This module provides a unified interface for creating embedding models that work
with LlamaIndex, supporting both OpenAI/Azure and Ollama embedding providers.

Adapted from network-agent to work with Django configuration.
"""

import logging
import os
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding

logger = logging.getLogger(__name__)


def create_embedding_model(
    agent_name: str = "deep_agent",
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    deployment_name: Optional[str] = None,
    api_version: Optional[str] = None,
    **kwargs: Any,
) -> Union[object, None]:
    """
    Create and return the appropriate embedding model for LlamaIndex.

    Args:
        agent_name: Name of the agent calling this function (for debugging)
        model_name: Override embedding model name
        base_url: Override base URL for embedding service
        api_key: Override API key
        deployment_name: Override Azure OpenAI deployment name
        api_version: Override Azure OpenAI API version
        **kwargs: Additional embedding model parameters

    Environment variables (used as defaults when overrides not provided):
    - EMBEDDING_MODEL: Embedding model name (default: "mxbai-embed-large")
    - EMBEDDING_BASE_URL: Base URL for embedding service
    - EMBEDDING_API_KEY: API key for embedding service
    - EMBEDDING_DEPLOYMENT_NAME: Azure deployment name (default: "text-embedding-ada-002")
    - EMBEDDING_API_VERSION: Azure API version (default: "2023-05-15")

    Returns:
        Configured embedding model or None if LlamaIndex not available

    Raises:
        Exception: If embedding model creation fails
    """
    try:
        config = _get_embedding_config(agent_name, model_name, base_url, api_key, deployment_name, api_version)

        logger.debug(f"[{agent_name}] Configuring embedding model: {config['model_name']}")
        logger.debug(f"[{agent_name}] Embedding base URL: {config['base_url']}")

        # Auto-detect provider based on base URL
        is_openai_provider = _is_openai_url(config["base_url"])
        is_azure_provider = _is_azure_url(config["base_url"])

        provider_name = "Azure" if is_azure_provider else "OpenAI" if is_openai_provider else "Ollama"
        logger.debug(f"[{agent_name}] Auto-detected embedding provider: {provider_name}")

        if is_azure_provider:
            return _create_azure_embedding(config, agent_name, **kwargs)
        elif is_openai_provider:
            return _create_openai_embedding(config, agent_name, **kwargs)
        else:
            return _create_ollama_embedding(config, agent_name, **kwargs)

    except Exception as e:
        logger.error(f"[{agent_name}] Failed to create embedding model: {str(e)}", exc_info=True)
        raise


def get_embedding_config(agent_name: str) -> Dict[str, Any]:
    """
    Get the current embedding configuration for an agent without creating the model.

    Args:
        agent_name: Name of the agent

    Returns:
        Dictionary containing the resolved configuration
    """
    return _get_embedding_config(agent_name, None, None, None, None, None)


def _get_embedding_config(
    agent_name: str,
    model_name: Optional[str],
    base_url: Optional[str],
    api_key: Optional[str],
    deployment_name: Optional[str],
    api_version: Optional[str],
) -> Dict[str, Any]:
    """Get embedding configuration with priority: function params > agent-specific env vars > global env vars > defaults."""
    agent_prefix = agent_name.upper()

    # Model name selection
    final_model_name = (
        model_name
        or os.environ.get(f"{agent_prefix}_EMBEDDING_MODEL")
        or os.environ.get("EMBEDDING_MODEL", "mxbai-embed-large")
    )

    # Base URL selection - fallback to Ollama if not specified
    final_base_url = (
        base_url
        or os.environ.get(f"{agent_prefix}_EMBEDDING_BASE_URL")
        or os.environ.get("EMBEDDING_BASE_URL")
        or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    # API key selection
    final_api_key = (
        api_key
        or os.environ.get(f"{agent_prefix}_EMBEDDING_API_KEY")
        or os.environ.get("EMBEDDING_API_KEY")
        or os.environ.get("OPENAI_API_KEY", "")
    )

    # Azure-specific configurations
    final_deployment_name = (
        deployment_name
        or os.environ.get(f"{agent_prefix}_EMBEDDING_DEPLOYMENT_NAME")
        or os.environ.get("EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002")
    )

    final_api_version = (
        api_version
        or os.environ.get(f"{agent_prefix}_EMBEDDING_API_VERSION")
        or os.environ.get("EMBEDDING_API_VERSION", "2023-05-15")
    )

    return {
        "model_name": final_model_name,
        "base_url": final_base_url,
        "api_key": final_api_key,
        "deployment_name": final_deployment_name,
        "api_version": final_api_version,
    }


def _create_azure_embedding(config: Dict[str, Any], agent_name: str, **kwargs: Any):
    """Create Azure OpenAI embedding model instance."""
    logger.debug(f"[{agent_name}] Using Azure OpenAI embedding model")

    model_params = {
        "model": config["model_name"],
        "azure_endpoint": config["base_url"],
        "api_key": config["api_key"],
        "api_version": config["api_version"],
        "deployment_name": config["deployment_name"],
        **kwargs,
    }

    return AzureOpenAIEmbedding(**model_params)


def _create_openai_embedding(config: Dict[str, Any], agent_name: str, **kwargs: Any):
    """Create OpenAI embedding model instance."""
    logger.debug(f"[{agent_name}] Using OpenAI embedding model")

    model_params = {
        "model": config["model_name"],
        "api_key": config["api_key"],
        "api_base": config["base_url"],
        **kwargs,
    }

    return OpenAIEmbedding(**model_params)


def _create_ollama_embedding(config: Dict[str, Any], agent_name: str, **kwargs: Any):
    """Create Ollama embedding model instance."""
    logger.debug(f"[{agent_name}] Using Ollama embedding model")

    model_params = {
        "model_name": config["model_name"],
        "base_url": config["base_url"],
        "ollama_additional_kwargs": {"mirostat": 0},
        **kwargs,
    }

    return OllamaEmbedding(**model_params)


def _is_openai_url(url: str) -> bool:
    """Check if the URL appears to be an OpenAI endpoint (but not Azure)."""
    if not url:
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False

    # Match api.openai.com and other *.openai.com hosts, but avoid Azure-specific hosts.
    if hostname == "api.openai.com" or hostname.endswith(".openai.com"):
        # Exclude Azure-style openai.azure.com hosts from being treated as vanilla OpenAI.
        return not hostname.endswith(".openai.azure.com")

    return False


def _is_azure_url(url: str) -> bool:
    """Check if the URL appears to be an Azure OpenAI endpoint."""
    if not url:
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False

    # Typical Azure OpenAI endpoints are of the form:
    #   https://{resource-name}.openai.azure.com/
    return hostname == "openai.azure.com" or hostname.endswith(".openai.azure.com")


def _is_ollama_url(url: str) -> bool:
    """Check if the URL appears to be an Ollama endpoint."""
    if not url:
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False

    # Default local Ollama endpoints
    if hostname in ("localhost", "127.0.0.1"):
        return True

    # Public Ollama domains, e.g. https://api.ollama.com/
    if hostname == "ollama.com" or hostname.endswith(".ollama.com"):
        return True

    return False
