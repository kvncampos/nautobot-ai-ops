"""Signal handlers for ai_ops."""

import logging

from django.apps import apps as global_apps
from django.contrib.contenttypes.models import ContentType
from nautobot.core.choices import ColorChoices
from nautobot.extras.models import Status

from ai_ops import models
from ai_ops.constants.middleware_schemas import get_default_config_for_middleware
from ai_ops.helpers.job_utils import create_or_update_scheduled_job, enable_job_and_get_details

logger = logging.getLogger(__name__)


def assign_mcp_server_statuses(sender, apps=global_apps, **kwargs):  # pylint: disable=unused-argument
    """Assign default statuses for MCPServer model."""
    mcpserver_ct = ContentType.objects.get_for_model(models.MCPServer)

    status_configs = [
        {"name": "Healthy", "color": ColorChoices.COLOR_GREEN},
        {"name": "Unhealthy", "color": ColorChoices.COLOR_RED},
        {"name": "Vulnerable", "color": ColorChoices.COLOR_BLACK},
    ]

    for config in status_configs:
        status, _ = Status.objects.get_or_create(
            name=config["name"],
            defaults={
                "name": config["name"],
                "color": config["color"],
            },
        )
        # Always ensure the content type is associated with the MCPServer model
        if mcpserver_ct not in status.content_types.all():
            status.content_types.add(mcpserver_ct)


def assign_system_prompt_statuses(sender, apps=global_apps, **kwargs):  # pylint: disable=unused-argument
    """Assign default statuses for SystemPrompt model and create default prompt."""
    system_prompt_ct = ContentType.objects.get_for_model(models.SystemPrompt)

    # Define statuses for SystemPrompt lifecycle
    status_configs = [
        {"name": "Approved", "color": ColorChoices.COLOR_GREEN},
        {"name": "Testing", "color": ColorChoices.COLOR_AMBER},
        {"name": "Deprecated", "color": ColorChoices.COLOR_GREY},
    ]

    approved_status = None
    for config in status_configs:
        status, _ = Status.objects.get_or_create(
            name=config["name"],
            defaults={
                "color": config["color"],
            },
        )
        # Always ensure the content type is associated with the SystemPrompt model
        if system_prompt_ct not in status.content_types.all():
            status.content_types.add(system_prompt_ct)

        if config["name"] == "Approved":
            approved_status = status

    # Create default file-based system prompt if none exists
    if approved_status and not models.SystemPrompt.objects.exists():
        models.SystemPrompt.objects.create(
            name="Multi-MCP Default",
            is_file_based=True,
            prompt_file_name="multi_mcp_system_prompt",
            status=approved_status,
            prompt_text=None,
        )
        logger.info("Created default file-based system prompt: Multi-MCP Default")


def setup_checkpoint_cleanup_schedule(sender, **kwargs):  # pylint: disable=unused-argument
    """Enable and schedule the checkpoint cleanup job after migrations."""
    try:
        # Enable job and get all necessary details
        job, job_user, default_queue, task_class_path = enable_job_and_get_details(
            module_name="ai_ops.jobs.checkpoint_cleanup",
            job_class_name="CleanupCheckpointsJob",
        )

        if not job:
            return

        # Create or update the scheduled job
        create_or_update_scheduled_job(
            schedule_name="Hourly Checkpoint Cleanup",
            job=job,
            job_user=job_user,
            default_queue=default_queue,
            task_class_path=task_class_path,
            crontab="0 * * * *",
            description="Automatically clean up old LangGraph conversation checkpoints from Redis",
        )

    except Exception as e:
        logger.error(f"Failed to setup checkpoint cleanup schedule: {e}")


def setup_mcp_health_check_schedule(sender, **kwargs):  # pylint: disable=unused-argument
    """Enable and schedule the MCP health check job after migrations."""
    try:
        # Enable job and get all necessary details
        job, job_user, default_queue, task_class_path = enable_job_and_get_details(
            module_name="ai_ops.jobs.mcp_health_check",
            job_class_name="MCPServerHealthCheckJob",
        )

        if not job:
            return

        # Create or update the scheduled job
        create_or_update_scheduled_job(
            schedule_name="MCP Server Health Check",
            job=job,
            job_user=job_user,
            default_queue=default_queue,
            task_class_path=task_class_path,
            crontab="*/5 * * * *",  # Run every 5 minutes (POC frequency)
            description="Automatically perform health checks on HTTP MCP servers with retry logic and cache invalidation",
        )

    except Exception as e:
        logger.error(f"Failed to setup MCP health check schedule: {e}")


def setup_chat_session_cleanup_schedule(sender, **kwargs):  # pylint: disable=unused-argument
    """Enable and schedule the chat session cleanup job after migrations."""
    try:
        # Enable job and get all necessary details
        job, job_user, default_queue, task_class_path = enable_job_and_get_details(
            module_name="ai_ops.jobs.chat_session_cleanup",
            job_class_name="CleanupExpiredChatsJob",
        )

        if not job:
            return

        # Create or update the scheduled job
        # Note: This schedule (how often cleanup runs) is separate from chat_session_ttl_minutes (what age to delete).
        # Default every-5-minutes is optimal for typical TTLs of 5-15 minutes.
        # If you significantly increase TTL via Constance (e.g., 1+ hours), consider adjusting this schedule
        # via Jobs UI to match (e.g., hourly) to avoid unnecessary cleanup checks.
        create_or_update_scheduled_job(
            schedule_name="Chat Session Cleanup",
            job=job,
            job_user=job_user,
            default_queue=default_queue,
            task_class_path=task_class_path,
            crontab="*/5 * * * *",  # Run every 5 minutes
            description="Automatically clean up expired chat sessions based on configured TTL (chat_session_ttl_minutes)",
        )

    except Exception as e:
        logger.error(f"Failed to setup chat session cleanup schedule: {e}")


def create_default_llm_providers(sender, apps=global_apps, **kwargs):  # pylint: disable=unused-argument
    """Create default LLM providers after database is ready."""
    llm_provider_configs = [
        {
            "name": models.LLMProviderChoice.OLLAMA,
            "description": "Open-source LLM inference platform for running models locally",
            "documentation_url": "https://docs.langchain.com/oss/python/integrations/chat/ollama",
        },
        {
            "name": models.LLMProviderChoice.OPENAI,
            "description": "OpenAI API for accessing GPT models and other AI capabilities",
            "documentation_url": "https://docs.langchain.com/oss/python/integrations/chat/openai",
        },
        {
            "name": models.LLMProviderChoice.AZURE_AI,
            "description": "Microsoft Azure AI services including Azure OpenAI",
            "documentation_url": "https://docs.langchain.com/oss/python/integrations/providers/azure_ai",
        },
        {
            "name": models.LLMProviderChoice.ANTHROPIC,
            "description": "Anthropic API for accessing Claude models",
            "documentation_url": "https://docs.langchain.com/oss/python/integrations/chat/anthropic",
        },
        {
            "name": models.LLMProviderChoice.HUGGINGFACE,
            "description": "Hugging Face hub for open-source models and model hosting",
            "documentation_url": "https://docs.langchain.com/oss/python/integrations/chat/huggingface",
        },
    ]

    for config in llm_provider_configs:
        models.LLMProvider.objects.get_or_create(
            name=config["name"],
            defaults={
                "description": config["description"],
                "documentation_url": config["documentation_url"],
                "is_enabled": True,
            },
        )
        logger.info(f"Created or verified LLM provider: {config['name']}")


def create_default_middleware_types(sender, apps=global_apps, **kwargs):  # pylint: disable=unused-argument
    """Create default built-in middleware types from LangChain."""
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
        middleware_type, created = models.MiddlewareType.objects.get_or_create(
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
            logger.info(f"Updated default_config for middleware type: {config['name']}")

        if created:
            logger.info(f"Created middleware type: {config['name']}")
        else:
            logger.debug(f"Verified middleware type: {config['name']}")
