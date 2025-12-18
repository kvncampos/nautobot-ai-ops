"""Tests for views and filters."""

from django.test import TestCase

from ai_ops.filters import LLMModelFilterSet, LLMProviderFilterSet, MCPServerFilterSet
from ai_ops.models import LLMModel, LLMProvider, LLMProviderChoice, MCPServer


class LLMProviderFilterSetTestCase(TestCase):
    """Test cases for LLMProviderFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.provider1 = LLMProvider.objects.create(
            name=LLMProviderChoice.OLLAMA,
            description="Ollama provider",
            is_enabled=True,
        )
        self.provider2 = LLMProvider.objects.create(
            name=LLMProviderChoice.OPENAI,
            description="OpenAI provider",
            is_enabled=False,
        )

    def test_filter_by_name(self):
        """Test filtering providers by name."""
        filterset = LLMProviderFilterSet(
            data={"name": LLMProviderChoice.OLLAMA},
            queryset=LLMProvider.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.provider1)

    def test_filter_by_enabled(self):
        """Test filtering providers by enabled status."""
        filterset = LLMProviderFilterSet(
            data={"is_enabled": True},
            queryset=LLMProvider.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.provider1)

    def test_search_by_description(self):
        """Test searching providers by description."""
        filterset = LLMProviderFilterSet(
            data={"q": "Ollama"},
            queryset=LLMProvider.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.provider1)


class LLMModelFilterSetTestCase(TestCase):
    """Test cases for LLMModelFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.provider = LLMProvider.objects.create(
            name=LLMProviderChoice.OLLAMA,
            description="Test provider",
        )
        self.model1 = LLMModel.objects.create(
            llm_provider=self.provider,
            name="llama2",
            description="Llama model",
            is_default=True,
        )
        self.model2 = LLMModel.objects.create(
            llm_provider=self.provider,
            name="mistral",
            description="Mistral model",
            is_default=False,
        )

    def test_filter_by_provider(self):
        """Test filtering models by provider."""
        filterset = LLMModelFilterSet(
            data={"llm_provider": [str(self.provider.pk)]},
            queryset=LLMModel.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 2)

    def test_filter_by_default(self):
        """Test filtering models by default status."""
        filterset = LLMModelFilterSet(
            data={"is_default": True},
            queryset=LLMModel.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.model1)

    def test_search_by_name(self):
        """Test searching models by name."""
        filterset = LLMModelFilterSet(
            data={"q": "llama"},
            queryset=LLMModel.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.model1)


class MCPServerFilterSetTestCase(TestCase):
    """Test cases for MCPServerFilterSet."""

    def setUp(self):
        """Set up test data."""
        from nautobot.extras.models import Status

        self.status1 = Status.objects.get_for_model(MCPServer).first()
        self.server1 = MCPServer.objects.create(
            name="server1",
            status=self.status1,
            protocol="http",
            url="http://localhost:8000",
            mcp_type="internal",
        )
        self.server2 = MCPServer.objects.create(
            name="server2",
            status=self.status1,
            protocol="stdio",
            url="http://localhost:9000",
            mcp_type="external",
        )

    def test_filter_by_protocol(self):
        """Test filtering servers by protocol."""
        filterset = MCPServerFilterSet(
            data={"protocol": "http"},
            queryset=MCPServer.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.server1)

    def test_filter_by_type(self):
        """Test filtering servers by type."""
        filterset = MCPServerFilterSet(
            data={"mcp_type": "internal"},
            queryset=MCPServer.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.server1)

    def test_search_by_name(self):
        """Test searching servers by name."""
        filterset = MCPServerFilterSet(
            data={"q": "server1"},
            queryset=MCPServer.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.server1)
