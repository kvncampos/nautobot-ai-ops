"""Tables for ai_ops."""

import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ButtonsColumn, StatusTableMixin, ToggleColumn

from ai_ops import models


class LLMProviderTable(BaseTable):
    # pylint: disable=R0903
    """Table for LLMProvider list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    description = tables.Column(verbose_name="Description")
    is_enabled = tables.BooleanColumn(verbose_name="Enabled")
    actions = ButtonsColumn(
        models.LLMProvider,
        pk_field="pk",
    )

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.LLMProvider
        fields = (
            "pk",
            "name",
            "description",
            "is_enabled",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "is_enabled",
        )


class LLMModelTable(BaseTable):
    # pylint: disable=R0903
    """Table for list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    is_default = tables.BooleanColumn(verbose_name="Default")
    azure_endpoint = tables.Column(verbose_name="Azure Endpoint")
    api_version = tables.Column(verbose_name="API Version")
    temperature = tables.Column(verbose_name="Temperature")
    cache_ttl = tables.Column(verbose_name="Cache TTL (s)")
    actions = ButtonsColumn(
        models.LLMModel,
        pk_field="pk",
    )

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.LLMModel
        fields = (
            "pk",
            "name",
            "description",
            "is_default",
            "azure_endpoint",
            "api_version",
            "model_secret_key",
            "temperature",
            "cache_ttl",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "is_default",
            "azure_endpoint",
            "api_version",
            "temperature",
            "cache_ttl",
        )


class MiddlewareTypeTable(BaseTable):
    # pylint: disable=R0903
    """Table for MiddlewareType list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    is_custom = tables.BooleanColumn(verbose_name="Custom")
    description = tables.Column(verbose_name="Description")
    actions = ButtonsColumn(
        models.MiddlewareType,
        pk_field="pk",
    )

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.MiddlewareType
        fields = (
            "pk",
            "name",
            "is_custom",
            "description",
        )
        default_columns = (
            "pk",
            "name",
            "is_custom",
            "description",
        )


class LLMMiddlewareTable(BaseTable):
    # pylint: disable=R0903
    """Table for LLMMiddleware list view."""

    pk = ToggleColumn()
    display = tables.Column(linkify=True, verbose_name="Display Name", accessor="display")
    middleware = tables.Column(linkify=True, verbose_name="Middleware Type")
    llm_model = tables.Column(linkify=True, verbose_name="LLM Model")
    priority = tables.Column(verbose_name="Priority")
    is_active = tables.BooleanColumn(verbose_name="Active")
    is_critical = tables.BooleanColumn(verbose_name="Critical")
    actions = ButtonsColumn(
        models.LLMMiddleware,
        pk_field="pk",
    )

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.LLMMiddleware
        fields = (
            "pk",
            "display",
            "middleware",
            "llm_model",
            "priority",
            "is_active",
            "is_critical",
            "config_version",
        )
        default_columns = (
            "pk",
            "display",
            "middleware",
            "llm_model",
            "priority",
            "is_active",
            "is_critical",
        )


class MCPServerTable(StatusTableMixin, BaseTable):
    # pylint: disable=R0903
    """Table for MCP Server list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(
        models.MCPServer,
        pk_field="pk",
    )

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = models.MCPServer
        fields = (
            "pk",
            "name",
            "status",
            "protocol",
            "url",
            "mcp_endpoint",
            "health_check",
            "description",
        )

        default_columns = (
            "pk",
            "name",
            "status",
            "protocol",
            "url",
            "mcp_endpoint",
        )
