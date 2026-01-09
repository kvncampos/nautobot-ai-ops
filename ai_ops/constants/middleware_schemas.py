"""Middleware configuration schemas and examples.

This module contains JSON schemas, example configurations, and recommended priorities
for each LangChain middleware type supported by the AI Ops application.
"""

MIDDLEWARE_SCHEMAS = {
    "SUMMARIZATION": {
        "schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name for summarization (e.g., 'gpt-4o-mini')"},
                "trigger": {
                    "type": "array",
                    "items": [
                        {"type": "string", "enum": ["fraction", "tokens"]},
                        {"type": "number"},
                    ],
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Trigger condition: ['fraction', 0.85] or ['tokens', 10000]",
                },
                "keep": {
                    "type": "array",
                    "items": [
                        {"type": "string", "enum": ["fraction", "tokens"]},
                        {"type": "number"},
                    ],
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Amount to keep: ['fraction', 0.10] or ['tokens', 2000]",
                },
            },
            "required": ["model", "trigger", "keep"],
        },
        "example": {
            "model": "gpt-4o-mini",
            "trigger": ["fraction", 0.85],
            "keep": ["fraction", 0.10],
        },
        "recommended_priority": 60,
        "priority_rationale": "Should run after PII detection but before final output processing",
        "tested_version": "1.1.0",
    },
    "PII_DETECTION": {
        "schema": {
            "type": "object",
            "properties": {
                "patterns": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {"type": "string"},
                    },
                    "description": "Named regex patterns for PII detection",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["redact", "mask", "remove"],
                    "description": "Strategy for handling detected PII",
                },
                "apply_to_input": {
                    "type": "boolean",
                    "description": "Whether to apply PII detection to user input",
                },
                "apply_to_output": {
                    "type": "boolean",
                    "description": "Whether to apply PII detection to model output",
                },
            },
            "required": ["patterns", "strategy"],
        },
        "example": {
            "patterns": {
                "api_key": r"(sk-[a-zA-Z0-9]{32}|Bearer\s+eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36})",
                "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            },
            "strategy": "redact",
            "apply_to_input": True,
            "apply_to_output": False,
        },
        "recommended_priority": 50,
        "priority_rationale": "Should run early to prevent PII from being processed by downstream middleware",
        "tested_version": "1.1.0",
    },
    "TODO_LIST": {
        "schema": {
            "type": "object",
            "properties": {
                "apply_to_tool_calls_only": {
                    "type": "boolean",
                    "description": "Whether to only apply structured output to tool calls (not final responses)",
                },
            },
        },
        "example": {
            "apply_to_tool_calls_only": True,
        },
        "recommended_priority": 70,
        "priority_rationale": "Should run after summarization to ensure structured output is properly formatted",
        "tested_version": "1.1.0",
    },
    "MODEL_RETRY": {
        "schema": {
            "type": "object",
            "properties": {
                "max_retries": {"type": "integer", "minimum": 1, "maximum": 10},
                "retry_delay_seconds": {"type": "number", "minimum": 0},
                "backoff_multiplier": {"type": "number", "minimum": 1},
            },
            "required": ["max_retries"],
        },
        "example": {
            "max_retries": 3,
            "retry_delay_seconds": 1.0,
            "backoff_multiplier": 2.0,
        },
        "recommended_priority": 85,
        "priority_rationale": "Should run late to retry after all other middleware have processed the request",
        "tested_version": "1.1.0",
    },
    "TOOL_RETRY": {
        "schema": {
            "type": "object",
            "properties": {
                "max_retries": {"type": "integer", "minimum": 1, "maximum": 10},
                "retry_delay_seconds": {"type": "number", "minimum": 0},
                "backoff_multiplier": {"type": "number", "minimum": 1},
            },
            "required": ["max_retries"],
        },
        "example": {
            "max_retries": 3,
            "retry_delay_seconds": 1.0,
            "backoff_multiplier": 2.0,
        },
        "recommended_priority": 90,
        "priority_rationale": "Should run after model retry to handle tool-specific failures",
        "tested_version": "1.1.0",
    },
    "CONTEXT_EDITING": {
        "schema": {
            "type": "object",
            "properties": {
                "edit_rules": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "replacement": {"type": "string"},
                        },
                        "required": ["pattern", "replacement"],
                    },
                },
            },
            "required": ["edit_rules"],
        },
        "example": {
            "edit_rules": [
                {"pattern": r"password:\s*\S+", "replacement": "password: [REDACTED]"},
                {"pattern": r"token:\s*\S+", "replacement": "token: [REDACTED]"},
            ],
        },
        "recommended_priority": 65,
        "priority_rationale": "Should run after PII detection and summarization to clean up context",
        "tested_version": "1.1.0",
    },
    "MODEL_CALL_LIMIT": {
        "schema": {
            "type": "object",
            "properties": {
                "max_calls": {"type": "integer", "minimum": 1},
                "error_message": {"type": "string"},
            },
            "required": ["max_calls"],
        },
        "example": {
            "max_calls": 50,
            "error_message": "Maximum number of model calls exceeded. Please simplify your request.",
        },
        "recommended_priority": 5,
        "priority_rationale": "Should run first to prevent runaway loops before any processing",
        "tested_version": "1.1.0",
    },
    "TOOL_CALL_LIMIT": {
        "schema": {
            "type": "object",
            "properties": {
                "max_calls": {"type": "integer", "minimum": 1},
                "error_message": {"type": "string"},
            },
            "required": ["max_calls"],
        },
        "example": {
            "max_calls": 100,
            "error_message": "Maximum number of tool calls exceeded. Please simplify your request.",
        },
        "recommended_priority": 10,
        "priority_rationale": "Should run early but after model call limit to prevent excessive tool usage",
        "tested_version": "1.1.0",
    },
    "MODEL_FALLBACK": {
        "schema": {
            "type": "object",
            "properties": {
                "fallback_model": {"type": "string", "description": "Name of fallback LLM model"},
                "trigger_on_errors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of error types that trigger fallback",
                },
            },
            "required": ["fallback_model"],
        },
        "example": {
            "fallback_model": "gpt-4o-mini",
            "trigger_on_errors": ["RateLimitError", "ServiceUnavailableError"],
        },
        "recommended_priority": 95,
        "priority_rationale": "Should run last to catch all failures after retries",
        "tested_version": "1.1.0",
    },
}


def get_middleware_schema(middleware_name: str) -> dict:
    """Get the JSON schema for a middleware type.

    Args:
        middleware_name: Name of the middleware (e.g., 'SUMMARIZATION')

    Returns:
        dict: JSON schema for the middleware configuration

    Raises:
        KeyError: If middleware_name is not recognized
    """
    return MIDDLEWARE_SCHEMAS[middleware_name]["schema"]


def get_middleware_example(middleware_name: str) -> dict:
    """Get the example configuration for a middleware type.

    Args:
        middleware_name: Name of the middleware (e.g., 'SUMMARIZATION')

    Returns:
        dict: Example configuration

    Raises:
        KeyError: If middleware_name is not recognized
    """
    return MIDDLEWARE_SCHEMAS[middleware_name]["example"]


def get_recommended_priority(middleware_name: str) -> int:
    """Get the recommended priority for a middleware type.

    Args:
        middleware_name: Name of the middleware (e.g., 'SUMMARIZATION')

    Returns:
        int: Recommended priority value (1-100)

    Raises:
        KeyError: If middleware_name is not recognized
    """
    return MIDDLEWARE_SCHEMAS[middleware_name]["recommended_priority"]


# Mapping from middleware type names to their default configurations
# Based on LangChain middleware documentation
# Each config includes ALL available parameters with type hints to serve as a complete template
# Type indicators: "string", "number", "boolean", "array", "object", "null" (for optional fields)
MIDDLEWARE_TYPE_DEFAULTS = {
    "SummarizationMiddleware": {
        "model": "string",  # Required: Model to use for summarization (e.g., "openai:gpt-4o-mini")
        "trigger": ["string", "number"],  # When to trigger summarization [unit, value]
        "keep": ["string", "number"],  # How many recent messages to keep
        "token_counter": "callable|null",  # Optional: Custom token counter function
        "summary_prompt": "string|null",  # Optional: Custom summarization prompt
        "trim_tokens_to_summarize": "number|null",  # Optional: Max tokens to include in summary
    },
    "HumanInTheLoopMiddleware": {
        "interrupt_on": "object",  # Dict mapping event types to interrupt conditions
        "description_prefix": "string",  # Prefix for interrupt descriptions
    },
    "ModelCallLimitMiddleware": {
        "thread_limit": "number|null",  # Max model calls per thread (null = unlimited)
        "run_limit": "number|null",  # Max model calls per run (null = unlimited)
        "exit_behavior": "string",  # What to do when limit reached: "end" or "continue"
    },
    "ToolCallLimitMiddleware": {
        "tool_name": "string|null",  # Specific tool to limit (null = all tools)
        "thread_limit": "number|null",  # Max tool calls per thread (null = unlimited)
        "run_limit": "number|null",  # Max tool calls per run (null = unlimited)
        "exit_behavior": "string",  # What to do when limit reached: "end" or "continue"
    },
    "ModelFallbackMiddleware": {
        "first_model": "string",  # Required: Primary model to try first
        "fallback_models": "array",  # List of fallback models to try in order
    },
    "PIIMiddleware": {
        "pii_type": "string",  # Required: Type of PII (email, credit_card, ip, mac_address, url, or custom)
        "strategy": "string",  # How to handle PII: block, redact, mask, hash
        "detector": "string|callable|null",  # Optional: Custom detector function or regex pattern
        "apply_to_input": "boolean",  # Check user messages before model call
        "apply_to_output": "boolean",  # Check AI messages after model call
        "apply_to_tool_results": "boolean",  # Check tool results after execution
    },
    "TodoListMiddleware": {
        "system_prompt": "string|null",  # Optional: Custom system prompt for todo management
        "tool_description": "string|null",  # Optional: Custom tool description
    },
    "LLMToolSelectorMiddleware": {
        "model": "string|null",  # Optional: Model to use for tool selection (defaults to agent's model)
        "system_prompt": "string|null",  # Optional: Custom system prompt for tool selection
        "max_tools": "number|null",  # Max number of tools to select (null = no limit)
        "always_include": "array",  # List of tool names to always include
    },
    "ToolRetryMiddleware": {
        "max_retries": "number",  # Maximum number of retry attempts
        "tools": "array|null",  # Specific tools to retry (null = all tools)
        "retry_on": "array|null",  # Optional: List of exception types to retry on
        "on_failure": "string",  # What to do after max retries: "continue", "raise", "end"
        "backoff_factor": "number",  # Exponential backoff multiplier
        "initial_delay": "number",  # Initial delay in seconds before first retry
        "max_delay": "number",  # Maximum delay between retries in seconds
        "jitter": "boolean",  # Add random jitter to delay to avoid thundering herd
    },
    "ModelRetryMiddleware": {
        "max_retries": "number",  # Maximum number of retry attempts
        "retry_on": "array|null",  # Optional: List of exception types to retry on
        "on_failure": "string",  # What to do after max retries: "continue", "raise", "end"
        "backoff_factor": "number",  # Exponential backoff multiplier
        "initial_delay": "number",  # Initial delay in seconds before first retry
        "max_delay": "number",  # Maximum delay between retries in seconds
        "jitter": "boolean",  # Add random jitter to delay to avoid thundering herd
    },
    "LLMToolEmulator": {
        "tools": "array|null",  # Required: Tools to emulate (null = emulate all available tools)
        "model": "string",  # Required: Model to use for emulation (e.g., "anthropic:claude-sonnet-4-5")
    },
    "ContextEditingMiddleware": {
        "edits": "array",  # List of edit configurations with structure: [{"trigger": number, "clear_at_least": number, "keep": number, "clear_tool_inputs": boolean, "exclude_tools": array, "placeholder": string}]
        "token_count_method": "string|callable",  # Method to count tokens: "approximate" or custom function
    },
    "ShellToolMiddleware": {
        "workspace_root": "string|null",  # Root directory for shell commands (null = temp directory)
        "startup_commands": "array",  # List of commands to run on startup
        "shutdown_commands": "array",  # List of commands to run on shutdown
        "execution_policy": "callable|null",  # Optional: Policy controlling which commands can be executed
        "redaction_rules": "array|null",  # Optional: Rules for redacting sensitive info from output
        "tool_name": "string",  # Name of the shell tool
        "shell": "string|null",  # Optional: Shell to use (defaults to system shell)
        "timeout": "number|null",  # Optional: Command timeout in seconds
        "max_output_length": "number|null",  # Optional: Max length of command output to return
    },
    "FilesystemFileSearchMiddleware": {
        "root_path": "string",  # Required: Root directory path for file searches
        "use_ripgrep": "boolean",  # Use ripgrep for faster searches if available
        "max_file_size_mb": "number",  # Maximum file size to search (in MB)
        "excluded_dirs": "array|null",  # Optional: List of directory patterns to exclude
        "excluded_files": "array|null",  # Optional: List of file patterns to exclude
    },
}


def get_default_config_for_middleware(middleware_type_name: str) -> dict:
    """Get the default configuration for a middleware type to pre-populate forms.

    Args:
        middleware_type_name: Name of the middleware type (e.g., 'SummarizationMiddleware')

    Returns:
        dict: Default configuration dictionary for the middleware
    """
    return MIDDLEWARE_TYPE_DEFAULTS.get(middleware_type_name, {})
