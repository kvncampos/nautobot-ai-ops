"""Forms for ai_ops."""

import json

from django import forms
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.forms import (
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    StatusModelFilterFormMixin,
    TagsBulkEditFormMixin,
)

from ai_ops import models


class LLMProviderForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """LLMProvider creation/edit form."""

    class Meta:
        """Meta attributes."""

        model = models.LLMProvider
        fields = "__all__"


class LLMProviderBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """LLMProvider bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.LLMProvider.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    documentation_url = forms.URLField(required=False)
    is_enabled = forms.BooleanField(
        required=False,
        widget=forms.Select(
            choices=[
                (None, "---------"),
                (True, "Yes"),
                (False, "No"),
            ]
        ),
    )

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "description",
            "documentation_url",
        ]


class LLMProviderFilterForm(NautobotFilterForm):
    """LLMProvider filter form."""

    model = models.LLMProvider
    field_order = ["q", "name", "is_enabled"]

    q = forms.CharField(
        required=False,
        label="Search",
        help_text="Search within Name or Description.",
    )
    name = forms.CharField(required=False, label="Name")
    is_enabled = forms.BooleanField(
        required=False,
        label="Is Enabled",
        widget=forms.Select(
            choices=[
                ("", "---------"),
                ("true", "Yes"),
                ("false", "No"),
            ]
        ),
    )


class LLMModelForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """LLMModel creation/edit form."""

    class Meta:
        """Meta attributes."""

        model = models.LLMModel
        fields = "__all__"


class LLMModelBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """LLMModel bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.LLMModel.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    model_secret_key = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    azure_endpoint = forms.URLField(required=False)
    api_version = forms.CharField(required=False, max_length=50)
    is_default = forms.BooleanField(
        required=False,
        widget=forms.Select(
            choices=[
                (None, "---------"),
                (True, "Yes"),
                (False, "No"),
            ]
        ),
    )
    temperature = forms.FloatField(required=False, min_value=0.0, max_value=2.0)
    cache_ttl = forms.IntegerField(required=False, min_value=60)
    system_prompt = forms.ModelChoiceField(
        queryset=models.SystemPrompt.objects.all(),
        required=False,
        label="System Prompt",
        help_text="Assign a system prompt to selected models. Only 'Approved' prompts will be used.",
    )

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "description",
            "model_secret_key",
            "azure_endpoint",
            "api_version",
            "system_prompt",
        ]


class LLMModelFilterForm(NautobotFilterForm):
    """Filter form to filter searches."""

    model = models.LLMModel
    field_order = ["q", "name", "is_default", "api_version"]

    q = forms.CharField(
        required=False,
        label="Search",
        help_text="Search within Name, Description, or Azure Endpoint.",
    )
    name = forms.CharField(required=False, label="Name")
    is_default = forms.BooleanField(
        required=False,
        label="Is Default",
        widget=forms.Select(
            choices=[
                ("", "---------"),
                ("true", "Yes"),
                ("false", "No"),
            ]
        ),
    )
    api_version = forms.CharField(required=False, label="API Version")


# ==============================
# === MiddlewareType Forms === #
# ==============================


class MiddlewareTypeForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """MiddlewareType creation/edit form."""

    class Meta:
        """Meta attributes."""

        model = models.MiddlewareType
        fields = "__all__"


class MiddlewareTypeBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """MiddlewareType bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.MiddlewareType.objects.all(), widget=forms.MultipleHiddenInput)
    is_custom = forms.BooleanField(
        required=False,
        widget=forms.Select(
            choices=[
                (None, "---------"),
                (True, "Yes"),
                (False, "No"),
            ]
        ),
    )
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)

    class Meta:
        """Meta attributes."""

        nullable_fields = ["description"]


class MiddlewareTypeFilterForm(NautobotFilterForm):
    """Filter form to filter MiddlewareType searches."""

    model = models.MiddlewareType
    field_order = ["q", "name", "is_custom"]

    q = forms.CharField(
        required=False,
        label="Search",
        help_text="Search within Name or Description.",
    )
    name = forms.CharField(required=False, label="Name")
    is_custom = forms.BooleanField(
        required=False,
        label="Is Custom",
        widget=forms.Select(
            choices=[
                ("", "---------"),
                ("true", "Yes"),
                ("false", "No"),
            ]
        ),
    )


# ==============================
# === LLMMiddleware Forms === #
# ==============================


class LLMMiddlewareForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """LLMMiddleware creation/edit form."""

    # Add a readonly field to display the default config template (only shown when editing)
    default_config_display = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 8, "readonly": "readonly", "class": "form-control bg-light"}),
        label="Default Configuration Template",
        help_text="This is the recommended starting configuration for the selected middleware type. "
        "You can copy this to the Config field below and customize as needed.",
    )

    class Meta:
        """Meta attributes."""

        model = models.LLMMiddleware
        fields = "__all__"
        widgets = {
            "config": forms.Textarea(attrs={"rows": 10, "cols": 80, "class": "form-control"}),
        }
        help_texts = {
            "config": "JSON configuration for the middleware. For new middleware, you can leave this empty "
            "and edit after creation to see the default configuration template.",
            "priority": "Execution priority (1-100). Lower values execute first. Ties broken alphabetically.",
        }

    def __init__(self, *args, **kwargs):
        """Initialize form and populate default config display."""
        super().__init__(*args, **kwargs)

        # Reorder fields to place default_config_display after middleware field
        # Using OrderedDict pattern for explicit field ordering
        if "default_config_display" in self.fields and "middleware" in self.fields:
            # Extract the default_config_display field
            default_config_field = self.fields.pop("default_config_display")

            # Update label and help text
            default_config_field.label = "Example Configuration (Read-Only)"
            default_config_field.help_text = (
                "This shows the recommended configuration template for the selected middleware type. "
                "You can copy this to the Config field below, or leave Config empty and populate it when editing."
            )

            # Rebuild fields dict with default_config_display inserted after middleware
            ordered_fields = {}
            for field_name, field in self.fields.items():
                ordered_fields[field_name] = field
                if field_name == "middleware":
                    ordered_fields["default_config_display"] = default_config_field

            self.fields = ordered_fields

        # Update config help text
        self.fields["config"].help_text = (
            "JSON configuration for the middleware. Optional: You can leave this empty now and "
            "populate it when editing (the example configuration will be shown above)."
        )

        if self.instance.pk:
            # Editing existing instance - populate the default config display if middleware is set
            try:
                if self.instance.middleware and self.instance.middleware.default_config:
                    self.fields["default_config_display"].initial = json.dumps(
                        self.instance.middleware.default_config, indent=2
                    )

                    # If config is empty, pre-populate it with the default
                    if not self.instance.config or self.instance.config == {}:
                        self.initial["config"] = json.dumps(self.instance.middleware.default_config, indent=2)
            except models.MiddlewareType.DoesNotExist:
                pass
        else:
            # New instance - show placeholder text
            self.fields[
                "default_config_display"
            ].initial = "Select a middleware type above to see example configuration"


class LLMMiddlewareBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """LLMMiddleware bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.LLMMiddleware.objects.all(), widget=forms.MultipleHiddenInput)
    is_active = forms.BooleanField(
        required=False,
        widget=forms.Select(
            choices=[
                (None, "---------"),
                (True, "Yes"),
                (False, "No"),
            ]
        ),
    )
    is_critical = forms.BooleanField(
        required=False,
        widget=forms.Select(
            choices=[
                (None, "---------"),
                (True, "Yes"),
                (False, "No"),
            ]
        ),
    )
    priority = forms.IntegerField(required=False, min_value=1, max_value=100)

    class Meta:
        """Meta attributes."""

        nullable_fields = []


class LLMMiddlewareFilterForm(NautobotFilterForm):
    """Filter form to filter LLMMiddleware searches."""

    model = models.LLMMiddleware
    field_order = ["q", "llm_model", "middleware", "is_active", "is_critical"]

    q = forms.CharField(
        required=False,
        label="Search",
        help_text="Search within middleware name.",
    )
    llm_model = forms.ModelChoiceField(
        queryset=models.LLMModel.objects.all(),
        required=False,
        label="LLM Model",
    )
    middleware = forms.ModelChoiceField(
        queryset=models.MiddlewareType.objects.all(),
        required=False,
        label="Middleware Type",
    )
    is_active = forms.BooleanField(
        required=False,
        label="Is Active",
        widget=forms.Select(
            choices=[
                ("", "---------"),
                ("true", "Yes"),
                ("false", "No"),
            ]
        ),
    )
    is_critical = forms.BooleanField(
        required=False,
        label="Is Critical",
        widget=forms.Select(
            choices=[
                ("", "---------"),
                ("true", "Yes"),
                ("false", "No"),
            ]
        ),
    )


# =========================
# === MCPServer Forms === #
# =========================


class MCPServerForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """MCPServer creation/edit form."""

    class Meta:
        """Meta attributes."""

        model = models.MCPServer
        fields = [
            "name",
            "status",
            "protocol",
            "url",
            "mcp_endpoint",
            "health_check",
            "description",
            "mcp_type",
        ]
        help_texts = {
            "url": "Base URL for the MCP server (e.g., http://host.docker.internal:8000). Do not include the MCP endpoint path.",
            "mcp_endpoint": "Path to the MCP endpoint (default: /mcp). This will be appended to the base URL.",
            "health_check": "Path to the health check endpoint (default: /health). This will be appended to the base URL.",
            "status": "Status can only be manually changed to 'Vulnerable' for P1 security issues. Other statuses are managed automatically.",
        }


class MCPServerBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """MCPServer bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.MCPServer.objects.all(), widget=forms.MultipleHiddenInput)
    protocol = forms.ChoiceField(required=False, choices=[("", "---------")] + models.MCPServer.PROTOCOL_TYPE_CHOICES)
    description = forms.CharField(required=False)

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "description",
        ]


class MCPServerFilterForm(StatusModelFilterFormMixin, NautobotFilterForm):
    """Filter form to filter MCP server searches."""

    model = models.MCPServer
    field_order = ["q", "name", "protocol"]

    q = forms.CharField(
        required=False,
        label="Search",
        help_text="Search within Name or URL.",
    )
    name = forms.CharField(required=False, label="Name")
    protocol = forms.ChoiceField(
        required=False, choices=[("", "---------")] + models.MCPServer.PROTOCOL_TYPE_CHOICES, label="Protocol"
    )


# =============================
# === SystemPrompt Forms === #
# =============================


class SystemPromptForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """SystemPrompt creation/edit form."""

    class Meta:
        """Meta attributes."""

        model = models.SystemPrompt
        fields = [
            "name",
            "status",
            "is_file_based",
            "prompt_file_name",
            "prompt_text",
        ]
        # Exclude 'version' - it's auto-managed
        widgets = {
            "prompt_text": forms.Textarea(attrs={"rows": 15, "cols": 80, "class": "form-control"}),
        }
        help_texts = {
            "name": "Descriptive name for this prompt. Version is auto-incremented for prompts with the same name.",
            "is_file_based": "If enabled, loads prompt from a file instead of using prompt_text. Supports Python (.py) and template (.md/.j2) files.",
            "prompt_file_name": (
                "Name of file in ai_ops/prompts/ (for Python, omit .py; for templates, include .md or .j2). "
                "Example: 'multi_mcp_system_prompt' loads get_prompt() from ai_ops/prompts/multi_mcp_system_prompt.py. "
                "Example: 'multi_mcp_system_prompt.md' loads template from ai_ops/prompts/templates/multi_mcp_system_prompt.md."
            ),
            "prompt_text": "Prompt content. Supports variables: {current_date}, {current_month}, {model_name}. "
            "Leave blank if using file-based prompt.",
        }


class SystemPromptBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """SystemPrompt bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.SystemPrompt.objects.all(), widget=forms.MultipleHiddenInput)
    status = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        label="Status",
    )
    is_file_based = forms.BooleanField(
        required=False,
        widget=forms.Select(
            choices=[
                (None, "---------"),
                (True, "Yes"),
                (False, "No"),
            ]
        ),
    )

    class Meta:
        """Meta attributes."""

        nullable_fields = []

    def __init__(self, *args, **kwargs):
        """Initialize form with filtered status queryset."""
        super().__init__(*args, **kwargs)
        from django.contrib.contenttypes.models import ContentType
        from nautobot.extras.models import Status

        # Filter statuses to only those associated with SystemPrompt
        system_prompt_ct = ContentType.objects.get_for_model(models.SystemPrompt)
        self.fields["status"].queryset = Status.objects.filter(content_types=system_prompt_ct)


class SystemPromptFilterForm(StatusModelFilterFormMixin, NautobotFilterForm):
    """Filter form to filter SystemPrompt searches."""

    model = models.SystemPrompt
    field_order = ["q", "name", "status", "is_file_based", "version"]

    q = forms.CharField(
        required=False,
        label="Search",
        help_text="Search within Name or Prompt Text.",
    )
    name = forms.CharField(required=False, label="Name")
    is_file_based = forms.BooleanField(
        required=False,
        label="File-Based",
        widget=forms.Select(
            choices=[
                ("", "---------"),
                ("true", "Yes"),
                ("false", "No"),
            ]
        ),
    )
    version = forms.IntegerField(required=False, label="Version")
