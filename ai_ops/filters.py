"""Filtering for ai_ops."""

from django.db.models import Q
from nautobot.apps.filters import NameSearchFilterSet, NautobotFilterSet, StatusModelFilterSetMixin

from ai_ops import models


class LLMProviderFilterSet(NameSearchFilterSet, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for LLMProvider."""

    class Meta:
        """Meta attributes for filter."""

        model = models.LLMProvider
        fields = "__all__"


class LLMModelFilterSet(NameSearchFilterSet, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for LLMModel."""

    class Meta:
        """Meta attributes for filter."""

        model = models.LLMModel

        # add any fields from the model that you would like to filter your searches by using those
        fields = "__all__"


class MiddlewareTypeFilterSet(NameSearchFilterSet, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for MiddlewareType."""

    class Meta:
        """Meta attributes for filter."""

        model = models.MiddlewareType
        fields = ["id", "name", "is_custom"]


class LLMMiddlewareFilterSet(NameSearchFilterSet, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for LLMMiddleware."""

    class Meta:
        """Meta attributes for filter."""

        model = models.LLMMiddleware
        fields = ["id", "llm_model", "middleware", "is_active", "is_critical", "priority"]


class MCPServerFilterSet(NautobotFilterSet, NameSearchFilterSet, StatusModelFilterSetMixin):  # pylint: disable=too-many-ancestors
    """Filter for MCPServer."""

    class Meta:
        """Meta attributes for filter."""

        model = models.MCPServer
        fields = ["id", "name", "protocol", "url", "description", "status"]

    def search(self, queryset, name, value):
        """Override search to include URL field in Q search."""
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(url__icontains=value))
