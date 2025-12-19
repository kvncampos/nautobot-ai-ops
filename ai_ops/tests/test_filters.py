"""Tests for views and filters."""

from django.test import TestCase

from ai_ops.filters import LLMModelFilterSet, LLMProviderFilterSet, MCPServerFilterSet
from ai_ops.models import LLMModel, LLMProvider, LLMProviderChoice, MCPServer
from ai_ops.tests.factories import TestDataMixin


class LLMProviderFilterSetTestCase(TestCase, TestDataMixin):
    """Test cases for LLMProviderFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self.provider1 = self.ollama_provider
        self.provider2 = self.openai_provider

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

    def test_filter_by_name(self):
        """Test filtering providers by name."""
        filterset = LLMProviderFilterSet(
            data={"name": LLMProviderChoice.OLLAMA},
            queryset=LLMProvider.objects.all(),
        )
        self.assertGreaterEqual(filterset.qs.count(), 1)
        self.assertIn(self.provider1, filterset.qs)

    def test_filter_by_enabled(self):
        """Test filtering providers by enabled status."""
        filterset = LLMProviderFilterSet(
            data={"is_enabled": True},
            queryset=LLMProvider.objects.all(),
        )
        self.assertGreaterEqual(filterset.qs.count(), 1)
        # Check that our enabled provider is in the results
        enabled_providers = [p for p in filterset.qs if p.is_enabled]
        self.assertGreaterEqual(len(enabled_providers), 1)

    def test_search_by_description(self):
        """Test searching providers by description."""
        filterset = LLMProviderFilterSet(
            data={"q": "Ollama"},
            queryset=LLMProvider.objects.all(),
        )
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first(), self.provider1)


class LLMModelFilterSetTestCase(TestCase, TestDataMixin):
    """Test cases for LLMModelFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self.provider = self.ollama_provider
        self.model1 = self.llama2_model
        self.model2 = self.mistral_model

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

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


class MCPServerFilterSetTestCase(TestCase, TestDataMixin):
    """Test cases for MCPServerFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        from nautobot.extras.models import Status

        self.status1 = Status.objects.get_for_model(MCPServer).first()
        self.server1 = self.http_server
        self.server2 = self.stdio_server

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

    def test_filter_by_protocol(self):
        """Test filtering servers by protocol."""
        filterset = MCPServerFilterSet(
            data={"protocol": "http"},
            queryset=MCPServer.objects.all(),
        )
        self.assertGreaterEqual(filterset.qs.count(), 1)
        self.assertIn(self.server1, filterset.qs)

    def test_filter_by_type(self):
        """Test filtering servers by type."""
        filterset = MCPServerFilterSet(
            data={"mcp_type": "internal"},
            queryset=MCPServer.objects.all(),
        )
        self.assertGreaterEqual(filterset.qs.count(), 1)
        self.assertIn(self.server1, filterset.qs)

    def test_search_by_name(self):
        """Test searching servers by name."""
        # Make sure our test server exists and is searchable
        server_name = self.server1.name

        filterset = MCPServerFilterSet(
            data={"q": server_name},
            queryset=MCPServer.objects.all(),
        )

        # Check that at least one server matches the search
        self.assertGreaterEqual(filterset.qs.count(), 1)

        # Check that our specific server is in the results if it exists
        if MCPServer.objects.filter(name=server_name).exists():
            server_names = [server.name for server in filterset.qs]
            self.assertIn(server_name, server_names)
