# Generated manually on 2026-02-08
# Migration to populate default data (LLM providers, middleware types, statuses)
# This replaces the signal-based default data creation

from django.db import migrations
from nautobot.core.choices import ColorChoices


# Status mappings for content types
system_prompt_status_mapping = {
    "ai_ops.SystemPrompt": ["Approved", "Testing", "Deprecated"],
}

mcp_server_status_mapping = {
    "ai_ops.MCPServer": ["Healthy", "Unhealthy", "Vulnerable"],
}


def populate_llm_providers(apps, schema_editor):
    """Create default LLM providers with documentation URLs."""
    LLMProvider = apps.get_model('ai_ops.LLMProvider')

    provider_configs = [
        {
            "name": "ollama",
            "description": "Open-source LLM inference platform for running models locally",
            "documentation_url": "https://python.langchain.com/docs/integrations/chat/ollama",
        },
        {
            "name": "openai",
            "description": "OpenAI API for accessing GPT models and other AI capabilities",
            "documentation_url": "https://python.langchain.com/docs/integrations/chat/openai",
        },
        {
            "name": "azure_ai",
            "description": "Microsoft Azure AI services including Azure OpenAI",
            "documentation_url": "https://python.langchain.com/docs/integrations/chat/azure_openai",
        },
        {
            "name": "anthropic",
            "description": "Anthropic API for accessing Claude models",
            "documentation_url": "https://python.langchain.com/docs/integrations/chat/anthropic",
        },
        {
            "name": "huggingface",
            "description": "Hugging Face hub for open-source models and model hosting",
            "documentation_url": "https://python.langchain.com/docs/integrations/chat/huggingface",
        },
    ]

    for config in provider_configs:
        LLMProvider.objects.get_or_create(
            name=config["name"],
            defaults={
                "description": config["description"],
                "documentation_url": config["documentation_url"],
                "is_enabled": True,
            },
        )


def reverse_populate_llm_providers(apps, schema_editor):
    """Remove default LLM providers."""
    LLMProvider = apps.get_model('ai_ops.LLMProvider')
    LLMProvider.objects.filter(
        name__in=['ollama', 'openai', 'azure_ai', 'anthropic', 'huggingface']
    ).delete()


def populate_middleware_types(apps, schema_editor):
    """Create default built-in middleware types from LangChain."""
    MiddlewareType = apps.get_model('ai_ops.MiddlewareType')

    # Import here to avoid issues during migration
    from ai_ops.constants.middleware_schemas import get_default_config_for_middleware

    middleware_configs = [
        {
            "name": "SummarizationMiddleware",
            "description": "Automatically summarize conversation history when approaching token limits, "
            "preserving recent messages while compressing older context.",
        },
        {
            "name": "HumanInTheLoopMiddleware",
            "description": "Pause agent execution for human approval, editing, or rejection of tool calls "
            "before they execute. Requires a checkpointer.",
        },
        {
            "name": "ModelCallLimitMiddleware",
            "description": "Limit the number of model calls to prevent infinite loops or excessive costs.",
        },
        {
            "name": "ToolCallLimitMiddleware",
            "description": "Control agent execution by limiting the number of tool calls, either globally "
            "across all tools or for specific tools.",
        },
        {
            "name": "ModelFallbackMiddleware",
            "description": "Automatically fallback to alternative models when the primary model fails.",
        },
        {
            "name": "PIIMiddleware",
            "description": "Detect and handle Personally Identifiable Information (PII) in conversations "
            "using configurable strategies.",
        },
        {
            "name": "TodoListMiddleware",
            "description": "Equip agents with task planning and tracking capabilities for complex multi-step tasks. "
            "Automatically provides agents with a write_todos tool.",
        },
        {
            "name": "LLMToolSelectorMiddleware",
            "description": "Use an LLM to intelligently select relevant tools before calling the main model. "
            "Useful for agents with many tools (10+).",
        },
        {
            "name": "ToolRetryMiddleware",
            "description": "Automatically retry failed tool calls with configurable exponential backoff.",
        },
        {
            "name": "ModelRetryMiddleware",
            "description": "Automatically retry failed model calls with configurable exponential backoff.",
        },
        {
            "name": "LLMToolEmulator",
            "description": "Emulate tool execution using an LLM for testing purposes, replacing actual tool calls "
            "with AI-generated responses.",
        },
        {
            "name": "ContextEditingMiddleware",
            "description": "Manage conversation context by clearing older tool call outputs when token limits are reached, "
            "while preserving recent results.",
        },
        {
            "name": "ShellToolMiddleware",
            "description": "Expose a persistent shell session to agents for command execution. "
            "Use appropriate execution policies for security.",
        },
        {
            "name": "FilesystemFileSearchMiddleware",
            "description": "Provide Glob and Grep search tools over a filesystem. "
            "Useful for code exploration and analysis.",
        },
        {
            "name": "PromptInjectionDetectionMiddleware",
            "description": "Detect and handle prompt injection attempts in user input. "
            "Configurable patterns for common injection techniques with block, warn, or sanitize strategies.",
        },
    ]

    for config in middleware_configs:
        middleware_type, created = MiddlewareType.objects.get_or_create(
            name=config["name"],
            defaults={
                "is_custom": False,
                "description": config["description"],
                "default_config": get_default_config_for_middleware(config["name"]),
            },
        )

        # Update default_config if it's empty (for existing records)
        if not middleware_type.default_config:
            middleware_type.default_config = get_default_config_for_middleware(config["name"])
            middleware_type.save(update_fields=["default_config"])


def reverse_populate_middleware_types(apps, schema_editor):
    """Remove default middleware types."""
    MiddlewareType = apps.get_model('ai_ops.MiddlewareType')
    MiddlewareType.objects.filter(is_custom=False).delete()


def populate_system_prompt_statuses(apps, schema_editor):
    """Add SystemPrompt content types to statuses and create default prompt."""
    Status = apps.get_model("extras.Status")
    SystemPrompt = apps.get_model("ai_ops.SystemPrompt")
    ContentType = apps.get_model("contenttypes.ContentType")

    # Define status colors for new statuses
    status_colors = {
        "Approved": ColorChoices.COLOR_GREEN,
        "Testing": ColorChoices.COLOR_AMBER,
        "Deprecated": ColorChoices.COLOR_GREY,
    }

    approved_status = None
    for model, statuses in system_prompt_status_mapping.items():
        model_class = apps.get_model(model)
        for status_name in statuses:
            status_record, _ = Status.objects.get_or_create(
                name=status_name,
                defaults={"color": status_colors.get(status_name, ColorChoices.COLOR_GREY)},
            )
            status_record.content_types.add(ContentType.objects.get_for_model(model_class))

            if status_name == "Approved":
                approved_status = status_record

    # Create default file-based system prompt if none exists
    if approved_status and not SystemPrompt.objects.exists():
        SystemPrompt.objects.create(
            name="Multi-MCP Default",
            is_file_based=True,
            prompt_file_name="multi_mcp_system_prompt",
            status=approved_status,
            prompt_text=None,
        )


def reverse_populate_system_prompt_statuses(apps, schema_editor):
    """Remove SystemPrompt content types from statuses."""
    Status = apps.get_model("extras.Status")
    SystemPrompt = apps.get_model("ai_ops.SystemPrompt")
    ContentType = apps.get_model("contenttypes.ContentType")

    for model, statuses in system_prompt_status_mapping.items():
        model_class = apps.get_model(model)
        for status_name in statuses:
            status_record, _ = Status.objects.get_or_create(name=status_name)
            status_record.content_types.remove(ContentType.objects.get_for_model(model_class))

    # Remove default system prompt
    SystemPrompt.objects.filter(name="Multi-MCP Default").delete()


def populate_mcp_server_statuses(apps, schema_editor):
    """Add MCPServer content types to statuses."""
    Status = apps.get_model("extras.Status")
    ContentType = apps.get_model("contenttypes.ContentType")

    # Define status colors for new statuses
    status_colors = {
        "Healthy": ColorChoices.COLOR_GREEN,
        "Unhealthy": ColorChoices.COLOR_RED,
        "Vulnerable": ColorChoices.COLOR_BLACK,
    }

    for model, statuses in mcp_server_status_mapping.items():
        model_class = apps.get_model(model)
        for status_name in statuses:
            status_record, _ = Status.objects.get_or_create(
                name=status_name,
                defaults={"color": status_colors.get(status_name, ColorChoices.COLOR_GREY)},
            )
            status_record.content_types.add(ContentType.objects.get_for_model(model_class))


def reverse_populate_mcp_server_statuses(apps, schema_editor):
    """Remove MCPServer content types from statuses."""
    Status = apps.get_model("extras.Status")
    ContentType = apps.get_model("contenttypes.ContentType")

    for model, statuses in mcp_server_status_mapping.items():
        model_class = apps.get_model(model)
        for status_name in statuses:
            status_record, _ = Status.objects.get_or_create(name=status_name)
            status_record.content_types.remove(ContentType.objects.get_for_model(model_class))


class Migration(migrations.Migration):

    dependencies = [
        ('ai_ops', '0005_move_endpoint_to_model_config'),
        ('extras', '0125_jobresult_date_started'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        # Populate LLM providers with documentation URLs
        migrations.RunPython(
            code=populate_llm_providers,
            reverse_code=reverse_populate_llm_providers,
        ),

        # Populate middleware types with default configs
        migrations.RunPython(
            code=populate_middleware_types,
            reverse_code=reverse_populate_middleware_types,
        ),

        # Populate statuses for SystemPrompt and create default prompt
        migrations.RunPython(
            code=populate_system_prompt_statuses,
            reverse_code=reverse_populate_system_prompt_statuses,
        ),

        # Populate statuses for MCPServer
        migrations.RunPython(
            code=populate_mcp_server_statuses,
            reverse_code=reverse_populate_mcp_server_statuses,
        ),
    ]
