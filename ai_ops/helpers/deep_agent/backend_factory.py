"""
Backend factory for deepagents CompositeBackend in ai-ops.

The backend system in deepagents provides file system routing for skills and memory:
- FilesystemBackend: For accessing skills and memory markdown files
- StoreBackend: For cross-conversation memory storage
- CompositeBackend: Routes requests between backends based on path

Adapted from network-agent to work with ai-ops.
"""

import logging

from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


def create_composite_backend(runtime: Runtime, root_dir: str = ".") -> CompositeBackend:
    """
    Create a CompositeBackend for deepagents with proper routing.

    The CompositeBackend routes file system operations:
    - Default: FilesystemBackend for skills and memory markdown files
    - /memories/: StoreBackend for cross-conversation memory (Redis/InMemory)

    Args:
        runtime: LangGraph Runtime instance containing the store
        root_dir: Root directory for FilesystemBackend (default: ".")

    Returns:
        Configured CompositeBackend instance

    Example:
        ```python
        from deepagents import create_deep_agent

        agent = create_deep_agent(
            ...
            backend=lambda rt: create_composite_backend(rt, root_dir=".")
        )
        ```
    """
    logger.debug(f"Creating CompositeBackend with root_dir={root_dir}")

    return CompositeBackend(
        default=FilesystemBackend(root_dir=root_dir, virtual_mode=True), routes={"/memories/": StoreBackend(runtime)}
    )
