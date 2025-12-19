"""Forms for ai_ops."""

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

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "description",
            "model_secret_key",
            "azure_endpoint",
            "api_version",
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

    class Meta:
        """Meta attributes."""

        model = models.LLMMiddleware
        fields = "__all__"
        widgets = {
            "config": forms.Textarea(attrs={"rows": 10, "cols": 80, "class": "form-control"}),
        }
        help_texts = {
            "config": "JSON configuration for the middleware. See documentation for schema per middleware type.",
            "priority": "Execution priority (1-100). Lower values execute first. Ties broken alphabetically.",
        }


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
