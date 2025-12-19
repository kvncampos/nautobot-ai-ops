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
