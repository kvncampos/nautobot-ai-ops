# System Prompt Configuration Guide

This guide explains how to configure and manage system prompts for AI agents in the AI Ops App. System prompts define the behavior, persona, and capabilities of your AI assistants.

## Overview

The AI Ops App provides a flexible system prompt management feature that allows you to:

- Create and manage prompts directly from the Nautobot UI
- Assign specific prompts to individual LLM models
- Use template variables for dynamic content
- Store prompts in the database or load from code files
- Control prompt usage through status-based approval workflow
- Track prompt versions automatically

## Key Concepts

### Prompt Storage Options

System prompts can be stored in two ways:

| Storage Type | Description | Use Case |
|--------------|-------------|----------|
| **Database** | Prompt text stored in the `prompt_text` field | Simple prompts, quick edits, non-technical users |
| **File-Based** | Prompt loaded from Python file in `ai_ops/prompts/` | Complex prompts, version control, code review |

### Status-Based Approval

Only prompts with **"Approved"** status are used by AI agents. This provides a review workflow:

- **Draft**: Prompt is being developed
- **Approved**: Prompt is active and ready for use
- **Deprecated**: Prompt is no longer recommended

### Prompt Fallback Hierarchy

When an AI agent needs a system prompt, it follows this priority order:

1. **Model-Assigned Prompt**: If the LLM Model has a `system_prompt` assigned with "Approved" status
2. **Global File-Based Prompt**: The first approved prompt with `is_file_based=True`
3. **Code Fallback**: Built-in `get_multi_mcp_system_prompt()` function

This ensures agents always have a valid prompt, even if no prompts are configured.

## Creating System Prompts

### Step 1: Navigate to System Prompts

1. Go to **AI Platform > Configuration > System Prompts**
2. Click **+ Add** to create a new prompt

**Screenshot Placeholder:**
> _[Screenshot: system-prompt-list-view.png - System Prompt list view showing existing prompts]_

### Step 2: Configure the Prompt

Fill in the following fields:

| Field | Required | Description |
|-------|----------|-------------|
| **Name** | Yes | Unique identifier (e.g., "Multi-MCP Default", "Network Specialist") |
| **Prompt Text** | Conditional | The prompt content (required unless using file-based) |
| **Status** | Yes | Select "Approved" to activate the prompt |
| **Is File Based** | No | Check if loading from a Python file |
| **Prompt File Name** | Conditional | Python file name without `.py` (required if file-based) |

**Screenshot Placeholder:**
> _[Screenshot: system-prompt-create-form.png - System Prompt create/edit form]_

### Step 3: Write Your Prompt

Use the text area to write your prompt. You can use template variables that are replaced at runtime:

```
You are an AI assistant powered by {model_name}.

Today is {current_date} ({current_month}).

Your role is to help network engineers with:
- Device configuration questions
- Troubleshooting connectivity issues
- Best practices for network automation
- Nautobot data queries

Always:
- Provide step-by-step guidance
- Cite sources when possible
- Admit when you're unsure
- Suggest consulting documentation for critical decisions
```

### Step 4: Save and Verify

1. Click **Create** to save the prompt
2. Verify the prompt appears in the list view
3. Check the detail view to preview the rendered markdown

**Screenshot Placeholder:**
> _[Screenshot: system-prompt-detail-view.png - System Prompt detail view with markdown preview]_

## Template Variables

System prompts support runtime variable substitution. Use these placeholders in your prompt text:

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{current_date}` | Current date in "Month DD, YYYY" format | January 13, 2026 |
| `{current_month}` | Current month in "Month YYYY" format | January 2026 |
| `{model_name}` | Name of the LLM model being used | gpt-4o |

### Example with Variables

```
You are {model_name}, a network operations AI assistant.

Current date: {current_date}
Current period: {current_month}

When providing time-sensitive information, reference the current date above.
```

**Rendered Output:**
```
You are gpt-4o, a network operations AI assistant.

Current date: January 13, 2026
Current period: January 2026

When providing time-sensitive information, reference the current date above.
```

## Assigning Prompts to Models

You can assign a specific system prompt to an LLM Model:

1. Navigate to **AI Platform > Configuration > LLM Models**
2. Edit the model you want to configure
3. Select a prompt from the **System Prompt** dropdown
4. Save the model

**Screenshot Placeholder:**
> _[Screenshot: model-system-prompt-field.png - LLM Model form showing system_prompt dropdown]_

When a user interacts with this model, it will use the assigned prompt (if "Approved").

## File-Based Prompts

For complex prompts that benefit from version control and code review:

### Creating a File-Based Prompt

1. Create a Python file in `ai_ops/prompts/` (e.g., `custom_prompt.py`)
2. Define a function named `get_<filename>()`:

```python
# ai_ops/prompts/custom_prompt.py

def get_custom_prompt(model_name: str = "AI Assistant") -> str:
    """Return the custom system prompt.
    
    Args:
        model_name: Name of the LLM model.
        
    Returns:
        str: The formatted system prompt.
    """
    return f"""You are {model_name}, a specialized network automation assistant.

Your capabilities include:
- Analyzing network configurations
- Suggesting automation improvements
- Explaining complex networking concepts

Always follow best practices and cite RFC standards when applicable.
"""
```

3. In Nautobot, create a SystemPrompt with:
   - **Is File Based**: ✓ Checked
   - **Prompt File Name**: `custom_prompt` (without `.py`)
   - **Status**: Approved

### File-Based Prompt Validation

The system validates file-based prompts:
- Checks that the file exists in `ai_ops/prompts/`
- Verifies the expected function (`get_<filename>`) is defined
- Returns an error if validation fails

## Version Tracking

The system automatically tracks prompt versions:

- **Initial Version**: Starts at version 1
- **Auto-Increment**: Version increases when `prompt_text` changes
- **Audit Trail**: Version history helps track changes

!!! note
    Version is read-only and managed automatically. You cannot manually set the version number.

## Best Practices

### Writing Effective Prompts

1. **Be Specific**: Clearly define the assistant's role and capabilities
2. **Set Boundaries**: Specify what the assistant should and shouldn't do
3. **Provide Context**: Include relevant background information
4. **Use Variables**: Leverage template variables for dynamic content
5. **Test Thoroughly**: Verify prompt behavior with various inputs

### Prompt Structure Template

```
# Role Definition
You are [role name], a [description of capabilities].

# Current Context
Today is {current_date}. You are powered by {model_name}.

# Capabilities
Your capabilities include:
- [Capability 1]
- [Capability 2]
- [Capability 3]

# Guidelines
Always:
- [Guideline 1]
- [Guideline 2]

Never:
- [Restriction 1]
- [Restriction 2]

# Response Format
When responding:
- [Format instruction 1]
- [Format instruction 2]
```

### Managing Multiple Prompts

- **Use descriptive names**: "Network Specialist", "Code Assistant", "General Helper"
- **Document purpose**: Add descriptions explaining when to use each prompt
- **Control access**: Use status to enable/disable prompts without deletion
- **Assign appropriately**: Match prompts to model capabilities

## Troubleshooting

### Prompt Not Being Used

**Symptoms**: Agent uses default prompt instead of your custom prompt.

**Solutions**:
1. Verify prompt status is "Approved"
2. Check if prompt is assigned to the model
3. Ensure `prompt_text` is not empty (for database prompts)
4. Verify `prompt_file_name` is correct (for file-based prompts)

### File-Based Prompt Errors

**Symptoms**: Error loading file-based prompt.

**Solutions**:
1. Verify file exists at `ai_ops/prompts/<name>.py`
2. Check function is named `get_<filename>()`
3. Ensure function accepts `model_name` parameter
4. Review Nautobot logs for import errors

### Variables Not Rendering

**Symptoms**: Variables appear as `{current_date}` instead of actual values.

**Solutions**:
1. Check variable spelling matches exactly
2. Verify using database prompt (not file-based with hardcoded text)
3. Ensure prompt is loaded through `get_active_prompt()` helper

## API Access

System prompts are available via the REST API:

```bash
# List all system prompts
GET /api/plugins/ai-ops/system-prompts/

# Get specific prompt
GET /api/plugins/ai-ops/system-prompts/{id}/

# Create prompt
POST /api/plugins/ai-ops/system-prompts/
Content-Type: application/json

{
    "name": "Custom Prompt",
    "prompt_text": "You are a helpful assistant...",
    "status": "approved"
}

# Update prompt
PATCH /api/plugins/ai-ops/system-prompts/{id}/
Content-Type: application/json

{
    "prompt_text": "Updated prompt content..."
}
```

## Related Documentation

- [App Overview](app_overview.md) - Feature overview
- [Getting Started](app_getting_started.md) - Initial setup guide
- [LLM Provider Configuration](provider_configuration.md) - Model configuration
- [AI Agents Reference](../dev/code_reference/agents.md) - Agent implementation details
