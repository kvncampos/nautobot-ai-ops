"""Deep Agent utilities for integrating deepagents framework with ai-ops.

This package provides utilities adapted from network-agent to work with ai-ops's
Django-based configuration while maintaining the benefits of the deepagents
architecture including:
- Semantic caching with embeddings
- Tool error retry with backoff
- Connection pooling for checkpointers
- Cross-conversation memory (Store)
- RAG utilities with PGVector
- Subagent delegation
- Skills system
"""

from .agents_loader import load_agents
from .backend_factory import create_composite_backend
from .checkpoint_factory import get_checkpointer
from .embedding_factory import create_embedding_model
from .mcp_tools_auth import get_mcp_tools_with_auth
from .middleware import SemanticCacheMiddleware, ToolErrorHandlerMiddleware
from .store_factory import get_store

__all__ = [
    "get_checkpointer",
    "get_store",
    "create_embedding_model",
    "SemanticCacheMiddleware",
    "ToolErrorHandlerMiddleware",
    "get_mcp_tools_with_auth",
    "load_agents",
    "create_composite_backend",
]
