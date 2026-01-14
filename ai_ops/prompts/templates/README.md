# Prompt Templates

This directory contains Jinja2-based Markdown templates for system prompts.

## Overview

The prompt system uses **one `.md` file per prompt** for simplicity and maintainability. Templates support dynamic variable injection and use Jinja2 syntax.

## Usage

Agents automatically use `get_active_prompt(llm_model)` from `ai_ops/helpers/get_prompt.py`, which:

1. **Checks for Markdown template** first (e.g., `templates/multi_mcp_system_prompt.md`)
2. **Falls back to Python file** (e.g., `multi_mcp_system_prompt.py`) for backward compatibility
3. **Injects dynamic variables** like `{{ current_date }}` and `{{ model_name }}`

## Template Variables

All templates automatically have access to:

- `{{ model_name }}` - The LLM model name
- `{{ current_date }}` - Current date (default format: "January 14, 2026")
- `{{ current_datetime }}` - Full datetime object for custom formatting
- `{{ current_year }}` - Current year (e.g., 2026)
- `{{ timezone }}` - Configured timezone (default: "UTC")

### Custom Variables

You can add custom variables via SystemPrompt's `additional_kwargs` JSON field:

```json
{
  "timezone": "America/New_York",
  "date_format": "%Y-%m-%d",
  "template_vars": {
    "organization": "My Company",
    "environment": "production"
  }
}
```

## Creating a New Template

1. Create a new `.md` file in this directory (e.g., `my_prompt.md`)
2. Use Jinja2 syntax for variables: `{{ variable_name }}`
3. Create corresponding SystemPrompt record in database with `is_file_based=True` and `prompt_file_name="my_prompt"`

Example:

```markdown
You are an AI assistant for {{ organization }}.

MODEL: {{ model_name }}
DATE: {{ current_date }}

Your instructions here...
```

## Migration from Python Files

Legacy `.py` files (e.g., `system_prompt.py`, `multi_mcp_system_prompt.py`) are still supported but deprecated. The system automatically prefers `.md` templates when available.

To migrate:
1. Copy prompt content to new `.md` file
2. Replace `{variable}` with `{{ variable }}`
3. Remove hardcoded dates - use `{{ current_date }}` instead
4. Test with existing SystemPrompt records

## Benefits

- ✅ **Simple**: One file per prompt, easy to read and edit
- ✅ **Dynamic**: Variables injected at runtime, no hardcoded dates
- ✅ **Flexible**: Supports custom date formats and timezones
- ✅ **Version Control**: Plain text Markdown in Git
- ✅ **Backward Compatible**: Fallback to legacy `.py` files
