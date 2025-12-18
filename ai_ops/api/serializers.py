"""API serializers for ai_ops."""

from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin

from ai_ops import models


class LLMProviderSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """LLMProvider Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.LLMProvider
        fields = "__all__"


class LLMModelSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """LLMModel Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.LLMModel
        fields = "__all__"

        # Option for disabling write for certain fields:
        # read_only_fields = []


class MiddlewareTypeSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """MiddlewareType Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.MiddlewareType
        fields = "__all__"


class LLMMiddlewareSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """LLMMiddleware Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.LLMMiddleware
        fields = "__all__"


class MCPServerSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):  # pylint: disable=too-many-ancestors
    """MCPServer Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.MCPServer
        fields = "__all__"
