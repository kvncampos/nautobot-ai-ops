"""
Agent configuration loading utility for deep agents in ai-ops.

This module provides functionality to load subagent configurations from YAML files
and wire them up with available tools. Unlike memory and skills, deepagents
doesn't natively load subagents from files - they're normally defined inline
in the create_deep_agent() call. This utility externalizes configuration to YAML
to keep configuration separate from code.

Adapted from network-agent to work with ai-ops.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml

logger = logging.getLogger(__name__)


async def load_agents(config_path: str | Path, tools: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    """
    Load subagent definitions from YAML and wire up tools.

    Args:
        config_path: Path to the YAML configuration file (string or Path object)
        tools: Dictionary mapping tool names to actual tool objects/functions
               Example: {"mcp_tools": [list_of_tools]}

    Returns:
        List of subagent configuration dictionaries

    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        IOError: If there's an error reading the file
        KeyError: If a tool referenced in config is not available
        yaml.YAMLError: If the YAML file is malformed
    """
    # Convert string to Path if needed
    config_path = Path(config_path) if isinstance(config_path, str) else config_path

    if not config_path.exists():
        logger.warning(f"Subagent configuration file not found: {config_path}")
        return []

    try:
        # Use asyncio.to_thread for non-blocking file reading
        def read_config_sync():
            with open(config_path, encoding="utf-8") as f:
                return yaml.safe_load(f)

        config = await asyncio.to_thread(read_config_sync)

        if not config:
            logger.info(f"Empty subagent configuration: {config_path}")
            return []

        tools = tools or {}
        agents = []

        for name, spec in config.items():
            agent = {
                "name": name,
                "description": spec.get("description", ""),
                "system_prompt": spec.get("system_prompt", ""),
            }

            # Add optional model configuration
            if "model" in spec:
                agent["model"] = spec["model"]

            # Wire up tools if specified
            if "tools" in spec and tools:
                agent_tools = []
                for tool_name in spec["tools"]:
                    if tool_name not in tools:
                        logger.warning(
                            f"Tool '{tool_name}' referenced in subagent '{name}' is not available - skipping"
                        )
                        continue

                    tool_value = tools[tool_name]
                    # If the tool value is a list, extend; otherwise append
                    if isinstance(tool_value, list):
                        agent_tools.extend(tool_value)
                    else:
                        agent_tools.append(tool_value)

                agent["tools"] = agent_tools

            agents.append(agent)

        logger.info(f"Loaded {len(agents)} subagent(s) from {config_path}")
        return agents

    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration {config_path}: {e}")
        return []
    except OSError as e:
        logger.error(f"Error reading configuration file {config_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error loading subagents from {config_path}: {e}")
        return []
