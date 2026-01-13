"""Models for Ai Agents."""

# Python imports

# Django imports
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Nautobot imports
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.models import PrimaryModel, extras_features
from nautobot.extras.models import Secret, Status, StatusField

from ai_ops.helpers.get_info import get_default_status
from ai_ops.helpers.llm_providers.base import BaseLLMProviderHandler

# If you want to choose a specific model to overload in your class declaration, please reference the following documentation:
# how to chose a database model: https://docs.nautobot.com/projects/core/en/stable/plugins/development/#database-models
# If you want to use the extras_features decorator please reference the following documentation
# https://docs.nautobot.com/projects/core/en/stable/development/core/model-checklist/#extras-features


def get_default_system_prompt_status():
    """Get or create the default status for SystemPrompt (Approved).

    Returns:
        uuid: The primary key of the default Status (Approved).
    """
    approved_status, _ = Status.objects.get_or_create(
        name="Approved",
        defaults={"color": "4caf50"},  # Green
    )
    return approved_status.pk


@extras_features("custom_links", "custom_validators", "export_templates", "graphql", "statuses", "webhooks")
class SystemPrompt(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Model for storing system prompts for LLM models.

    System prompts define the behavior and persona of LLM agents.
    Prompts can be stored in the database (prompt_text) or loaded from code files (is_file_based).
    Only prompts with 'Approved' status are used by agents.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique descriptive name for this prompt (e.g., 'Multi-MCP Default', 'Network Specialist')",
    )
    prompt_text = models.TextField(
        null=True,
        blank=True,
        help_text="Prompt content. Supports variables: {current_date}, {current_month}, {model_name}. "
        "Leave blank if using file-based prompt.",
    )
    status = StatusField(
        to=Status,
        on_delete=models.PROTECT,
        default=get_default_system_prompt_status,
        help_text="Only prompts with 'Approved' status are used by agents.",
    )
    version = models.PositiveIntegerField(
        default=1,
        editable=False,
        help_text="Auto-incremented version number for tracking prompt changes.",
    )
    is_file_based = models.BooleanField(
        default=False,
        help_text="If True, loads prompt from code file (prompt_file_name); if False, uses prompt_text field.",
    )
    prompt_file_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Name of the Python file in ai_ops/prompts/ to load (without .py extension). "
        "Example: 'multi_mcp_system_prompt' will load get_multi_mcp_system_prompt() from that file.",
    )

    class Meta(PrimaryModel.Meta):
        """Meta class."""

        ordering = ["name", "-version"]
        verbose_name = "System Prompt"
        verbose_name_plural = "System Prompts"

    def __str__(self):
        """String representation."""
        status_name = self.status.name if self.status else "No Status"
        return f"{self.name} v{self.version} ({status_name})"

    def clean(self):
        """Validate SystemPrompt instance."""
        super().clean()

        # Require prompt_text when not file-based
        if not self.is_file_based and not self.prompt_text:
            raise ValidationError({"prompt_text": "Prompt text is required when not using a file-based prompt."})

        # Require prompt_file_name when file-based
        if self.is_file_based and not self.prompt_file_name:
            raise ValidationError({"prompt_file_name": "File name is required when using a file-based prompt."})

        # Validate file exists if file-based
        if self.is_file_based and self.prompt_file_name:
            try:
                import importlib

                module = importlib.import_module(f"ai_ops.prompts.{self.prompt_file_name}")
                func_name = f"get_{self.prompt_file_name}"
                if not hasattr(module, func_name):
                    raise ValidationError(
                        {
                            "prompt_file_name": f"Function '{func_name}' not found in ai_ops.prompts.{self.prompt_file_name}"
                        }
                    )
            except ImportError as e:
                raise ValidationError(
                    {"prompt_file_name": f"Could not import ai_ops.prompts.{self.prompt_file_name}: {e}"}
                ) from e

    def save(self, *args, **kwargs):
        """Override save to auto-increment version when prompt_text is updated."""
        if self.pk:  # Existing instance - check if prompt_text changed
            try:
                old_instance = SystemPrompt.objects.get(pk=self.pk)
                if old_instance.prompt_text != self.prompt_text:
                    self.version += 1
            except SystemPrompt.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    @property
    def rendered_prompt(self) -> str:
        """Get the prompt content, loading from file if necessary.

        For database-stored prompts, returns prompt_text directly.
        For file-based prompts, dynamically loads and executes the prompt function.

        Returns:
            str: The prompt content (may include template variables like {model_name}).
        """
        if not self.is_file_based:
            return self.prompt_text or ""

        # Load from file
        if not self.prompt_file_name:
            return "*No prompt file specified*"

        try:
            import importlib

            module = importlib.import_module(f"ai_ops.prompts.{self.prompt_file_name}")
            func_name = f"get_{self.prompt_file_name}"
            if hasattr(module, func_name):
                func = getattr(module, func_name)
                # Call with a placeholder model name for preview purposes
                return func(model_name="[Model Name]")
            return f"*Function '{func_name}' not found in module*"
        except ImportError as e:
            return f"*Error loading prompt file: {e}*"
        except Exception as e:  # pylint: disable=broad-except
            return f"*Error executing prompt function: {e}*"


class LLMProviderChoice(models.TextChoices):
    """Choices for LLM provider types."""

    OLLAMA = "ollama", "Ollama"
    OPENAI = "openai", "OpenAI"
    AZURE_AI = "azure_ai", "Azure AI"
    ANTHROPIC = "anthropic", "Anthropic"
    HUGGINGFACE = "huggingface", "HuggingFace"
    CUSTOM = "custom", "Custom"


def get_default_llm_provider():
    """Get or create the default LLM provider (Ollama).

    Ensures the Ollama provider exists in the database and returns its primary key.
    This is used as the default for new LLMModel instances.

    Returns:
        uuid: The primary key of the default LLMProvider (Ollama).
    """
    provider, _ = LLMProvider.objects.get_or_create(
        name=LLMProviderChoice.OLLAMA,
        defaults={
            "description": "Default Ollama provider for local LLM deployment",
        },
    )
    return provider.pk


@extras_features("custom_links", "custom_validators", "export_templates", "graphql", "webhooks")
class LLMProvider(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Model for storing LLM provider configurations.

    This model defines available LLM providers (e.g., Ollama, OpenAI, Azure AI, Anthropic, HuggingFace).
    Each provider can have multiple LLM models configured with provider-specific settings.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        choices=LLMProviderChoice.choices,
        default=LLMProviderChoice.OLLAMA,
        help_text="Name of the LLM provider (e.g., ollama, openai, azure_ai, anthropic, huggingface)",
    )
    description = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        help_text="Description of the provider and its capabilities",
    )
    documentation_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="URL to the provider's documentation (e.g., LangChain integration docs)",
    )
    config_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON schema for provider-specific configuration. "
        "Example: {'api_version': '2024-02-15-preview', 'base_url': 'https://...'} for Azure. "
        "Used to store dynamic configuration without database schema changes.",
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether this provider is available for use",
    )

    class Meta(PrimaryModel.Meta):
        """Meta class."""

        ordering = ["name"]
        verbose_name = "LLM Provider"
        verbose_name_plural = "LLM Providers"

    def __str__(self):
        """String representation."""
        return f"{self.get_name_display()} (Provider)"  # type: ignore

    def get_handler(self) -> BaseLLMProviderHandler:
        """Get the handler for this provider.

        Returns:
            BaseLLMProviderHandler: The handler instance for this provider type.

        Raises:
            ValueError: If the provider type is not registered.
        """
        from ai_ops.helpers.llm_providers import get_llm_provider_handler

        return get_llm_provider_handler(self.name, config=self.config_schema)


@extras_features("custom_links", "custom_validators", "export_templates", "graphql", "webhooks")
class LLMModel(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Model for storing LLM (Large Language Model) configurations.

    This model supports both LAB (local development) and production environments.
    In LAB, environment variables are used. In production, values are retrieved from the database.
    """

    llm_provider = models.ForeignKey(
        "LLMProvider",
        on_delete=models.CASCADE,
        related_name="llm_models",
        default=get_default_llm_provider,
        help_text="The LLM provider for this model (e.g., Ollama, OpenAI, Azure AI)",
    )
    name = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, unique=True, help_text="Model name (e.g., gpt-4o, gpt-4-turbo, ollama:llama2)"
    )
    description = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Description of the LLM and its capabilities"
    )
    model_secret_key = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        help_text="Name of the Secret object in Nautobot that contains the API key",
    )
    endpoint = models.URLField(
        max_length=500,
        blank=True,
        help_text="LLM Endpoint URL (e.g., https://your-resource.openai.azure.com/, https://openai.com/api/v1/)",
    )
    api_version = models.CharField(
        max_length=50, blank=True, default="", help_text="Azure OpenAI API version (e.g., 2024-02-15-preview)"
    )
    is_default = models.BooleanField(
        default=False, help_text="Whether this is the default model to use when no model is specified"
    )
    temperature = models.FloatField(default=0.0, help_text="Temperature setting for the model (0.0 to 2.0)")
    cache_ttl = models.IntegerField(
        default=300,
        help_text="Cache time-to-live in seconds for MCP client connections (minimum 60 seconds)",
        validators=[MinValueValidator(60)],
    )
    system_prompt = models.ForeignKey(
        "SystemPrompt",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_models",
        help_text="System prompt to use for this model. If not set, uses the default file-based prompt.",
    )

    class Meta(PrimaryModel.Meta):
        """Meta class."""

        ordering = ["-is_default", "name"]
        verbose_name = "LLM Model"
        verbose_name_plural = "LLM Models"

    def __str__(self):
        """String representation."""
        default_indicator = " (default)" if self.is_default else ""
        return f"{self.name}{default_indicator}"

    @classmethod
    def get_default_model(cls) -> "LLMModel":
        """Get the default LLM model.

        Returns the model marked as default, or the first available model if none are marked as default.

        Returns:
            LLMModel: The default model instance.

        Raises:
            LLMModel.DoesNotExist: If no models exist in the database.
        """
        default_model = (
            cls.objects.filter(is_default=True)
            .select_related("llm_provider", "system_prompt", "system_prompt__status")
            .first()
        )
        if default_model:
            return default_model
        first_model = cls.objects.select_related("llm_provider", "system_prompt", "system_prompt__status").first()
        if first_model:
            return first_model
        raise cls.DoesNotExist(
            "No LLMModel instances exist in the database. Please create at least one model before attempting to retrieve the default."
        )

    @classmethod
    def get_all_models_summary(cls) -> list[dict]:
        """Get a summary of all available models.

        Returns:
            list[dict]: List of dictionaries containing model information.
        """
        models = cls.objects.select_related("llm_provider").all()
        return [
            {
                "name": model.name,
                "description": model.description,
                "is_default": model.is_default,
                "llm_provider": model.llm_provider.name,
                "endpoint": model.endpoint,
                "api_version": model.api_version,
            }
            for model in models
        ]

    def get_api_key(self) -> str:
        """Retrieve the API key from the Secret object.

        Returns:
            str: The API key value.

        Raises:
            Secret.DoesNotExist: If the secret doesn't exist.
            ValidationError: If model_secret_key is not configured.
        """
        if not self.model_secret_key:
            raise ValidationError("model_secret_key is not configured for this LLM model.")
        secret = Secret.objects.get(name=self.model_secret_key)
        return secret.get_value()

    def get_llm_provider_handler(self) -> "BaseLLMProviderHandler":
        """Get the LLM provider handler for this model.

        Returns:
            BaseLLMProviderHandler: The handler instance for this model's LLM provider.
        """
        return self.llm_provider.get_handler()

    def clean(self):
        """Validate LLMModel instance."""
        super().clean()

        # Ensure only one model is marked as default
        if self.is_default:
            existing_default = LLMModel.objects.filter(is_default=True).exclude(pk=self.pk).first()
            if existing_default:
                raise ValidationError(
                    f"Another model '{existing_default.name}' is already marked as default. "
                    "Only one model can be the default."
                )


@extras_features("custom_links", "custom_validators", "export_templates", "graphql", "webhooks")
class MiddlewareType(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Model for storing middleware type definitions.

    This model defines available middleware types that can be used with LLM models.
    Middleware can be either built-in LangChain middleware or custom middleware classes.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the middleware class (e.g., 'SummarizationMiddleware', 'CustomLoggingMiddleware'). "
        "Must be a valid Python class name in PascalCase ending with 'Middleware'.",
    )
    is_custom = models.BooleanField(
        default=False,
        help_text="Whether this is a custom middleware (True) or a built-in LangChain middleware (False)",
    )
    description = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        help_text="Description of what this middleware does",
    )
    default_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default JSON configuration template for this middleware type. "
        "This will be used as a starting point when creating new middleware instances.",
    )

    class Meta(PrimaryModel.Meta):
        """Meta class."""

        ordering = ["name"]
        verbose_name = "Middleware Type"
        verbose_name_plural = "Middleware Types"

    def clean(self):
        """Validate MiddlewareType instance."""
        super().clean()

        # Validate middleware name format
        if self.name:
            # Auto-capitalize if needed (convert to PascalCase)
            if not self.name.endswith("Middleware"):
                self.name = f"{self.name}Middleware"

            # Ensure it's in PascalCase format
            if not self.name[0].isupper():
                # Capitalize first letter
                self.name = self.name[0].upper() + self.name[1:]

            # Validate it's a valid Python identifier
            if not self.name.replace("_", "").replace("Middleware", "").isalnum():
                raise ValidationError(
                    {"name": "Middleware name must be a valid Python class name (alphanumeric only)."}
                )

    def __str__(self):
        """String representation."""
        custom_indicator = "[Custom]" if self.is_custom else "[Built-in]"
        return f"{self.name} {custom_indicator}"


@extras_features("custom_links", "custom_validators", "export_templates", "graphql", "webhooks")
class LLMMiddleware(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Model for storing LLM middleware configurations.

    Middleware execute in priority order (lowest to highest) for each LLM model.
    Each middleware type can only be configured once per model.

    Supports both built-in LangChain middleware and custom middleware classes.
    """

    llm_model = models.ForeignKey(
        "LLMModel",
        on_delete=models.CASCADE,
        related_name="middlewares",
        help_text="The LLM model this middleware applies to",
    )
    middleware = models.ForeignKey(
        "MiddlewareType",
        on_delete=models.PROTECT,
        related_name="middleware_instances",
        help_text="The middleware type to apply to this LLM model",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON configuration for the middleware (see documentation for schema per middleware type)",
    )
    config_version = models.CharField(
        max_length=20,
        default="1.1.0",
        help_text="LangChain version this configuration is compatible with",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this middleware is currently active",
    )
    is_critical = models.BooleanField(
        default=False,
        help_text="If True, agent initialization will fail if this middleware cannot be loaded. "
        "If False, errors will be logged but initialization will continue.",
    )
    priority = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Execution priority (1-100). Lower values execute first. Ties are broken alphabetically.",
    )

    class Meta(PrimaryModel.Meta):
        """Meta class."""

        ordering = ["priority", "middleware__name"]
        verbose_name = "LLM Middleware"
        verbose_name_plural = "LLM Middlewares"
        unique_together = [["llm_model", "middleware"]]

    @property
    def display(self) -> str:
        """User-friendly display name for the middleware instance.

        Returns:
            str: Display name combining model and middleware.
        """
        return f"{self.llm_model.name} - {self.middleware.name}"

    def __str__(self):
        """String representation."""
        status = "✓" if self.is_active else "✗"
        critical = "!" if self.is_critical else ""
        return f"{status} {self.middleware.name} (P{self.priority}){critical} - {self.llm_model.name}"


@extras_features("custom_links", "custom_validators", "export_templates", "graphql", "statuses", "webhooks")
class MCPServer(PrimaryModel):  # pylint: disable=too-many-ancestors
    """Model for MCP Server configurations.

    Status can be automatically updated based on health check results:
    - Active: Server is healthy and responding
    - Failed: Health check failed
    - Maintenance: Manually disabled for maintenance
    """

    PROTOCOL_TYPE_CHOICES = [
        ("stdio", "STDIO"),
        ("http", "HTTP"),
    ]

    TYPE_CHOICES = [
        ("internal", "Internal"),
        ("external", "External"),
    ]

    name = models.CharField(max_length=100, unique=True, help_text="Unique name for the MCP server")
    status = StatusField(to=Status, on_delete=models.PROTECT, default=get_default_status)
    protocol = models.CharField(
        max_length=10,
        choices=PROTOCOL_TYPE_CHOICES,
        default="http",
        help_text="MCP server connection type (STDIO or HTTP)",
    )
    url = models.URLField(
        max_length=500, help_text="Base URL for the MCP server (e.g., http://host.docker.internal:8000)"
    )
    mcp_endpoint = models.CharField(
        max_length=100, default="/mcp", help_text="MCP endpoint path to append to base URL (default: /mcp)"
    )
    health_check = models.CharField(
        max_length=50, default="/health", help_text="Health check endpoint path (default: /health)"
    )
    description = models.CharField(max_length=200, blank=True, help_text="Optional description of the MCP server")
    mcp_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default="internal",
        help_text="Indicates if the MCP server is internal or external",
    )

    class Meta(PrimaryModel.Meta):
        """Meta class."""

        ordering = ["name"]
        verbose_name = "MCP Server"
        verbose_name_plural = "MCP Servers"

    def clean(self):
        """Validate MCPServer instance."""
        super().clean()

        # URL is always required
        if not self.url:
            raise ValidationError({"url": "URL is required for MCP server."})

        # Ensure mcp_endpoint starts with /
        if self.mcp_endpoint and not self.mcp_endpoint.startswith("/"):
            self.mcp_endpoint = f"/{self.mcp_endpoint}"

        # Ensure health_check starts with /
        if self.health_check and not self.health_check.startswith("/"):
            self.health_check = f"/{self.health_check}"


# TODO: Explore Redis vs localStorage for multi-session support. Current localStorage approach works for
# single-session chat but consider Redis/PostgreSQL for persistent multi-user conversations with proper TTL
# and data retention policies.
