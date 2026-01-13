"""Tests for views and filters."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from nautobot.core.choices import ColorChoices
from nautobot.extras.models import Status

from ai_ops.filters import LLMModelFilterSet, LLMProviderFilterSet, MCPServerFilterSet, SystemPromptFilterSet
from ai_ops.models import LLMModel, LLMProvider, LLMProviderChoice, MCPServer, SystemPrompt
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


class SystemPromptFilterSetTestCase(TestCase, TestDataMixin):
    """Test cases for SystemPromptFilterSet."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self._create_system_prompt_statuses()
        self._create_test_prompts()

    def tearDown(self):
        """Clean up after tests."""
        self.teardown_test_data()

    def _create_system_prompt_statuses(self):
        """Create required statuses for SystemPrompt."""
        system_prompt_ct = ContentType.objects.get_for_model(SystemPrompt)

        status_configs = [
            {"name": "Approved", "color": ColorChoices.COLOR_GREEN},
            {"name": "Testing", "color": ColorChoices.COLOR_AMBER},
            {"name": "Deprecated", "color": ColorChoices.COLOR_GREY},
        ]

        for config in status_configs:
            status, _ = Status.objects.get_or_create(
                name=config["name"],
                defaults={"color": config["color"]},
            )
            if system_prompt_ct not in status.content_types.all():
                status.content_types.add(system_prompt_ct)

    def _create_test_prompts(self):
        """Create test prompts using get_or_create for --keepdb compatibility."""
        approved = Status.objects.get(name="Approved")
        testing = Status.objects.get(name="Testing")

        self.prompt1, _ = SystemPrompt.objects.get_or_create(
            name="FilterTest_Network Assistant",
            version=1,
            defaults={
                "prompt_text": "You are a network expert for filter tests.",
                "status": approved,
                "is_file_based": False,
            },
        )
        self.prompt2, _ = SystemPrompt.objects.get_or_create(
            name="FilterTest_Security Analyst",
            version=1,
            defaults={
                "prompt_text": "You analyze security issues for filter tests.",
                "status": testing,
                "is_file_based": False,
            },
        )
        self.prompt3, _ = SystemPrompt.objects.get_or_create(
            name="FilterTest_File Based",
            version=1,
            defaults={
                "is_file_based": True,
                "prompt_file_name": "multi_mcp_system_prompt",
                "status": approved,
            },
        )

    def test_filter_by_name(self):
        """Test filtering prompts by name."""
        filterset = SystemPromptFilterSet(
            data={"name": "FilterTest_Network Assistant"},
            queryset=SystemPrompt.objects.all(),
        )
        self.assertGreaterEqual(filterset.qs.count(), 1)
        self.assertIn(self.prompt1, filterset.qs)

    def test_filter_by_status(self):
        """Test filtering prompts by status."""
        approved = Status.objects.get(name="Approved")
        # Filter only our test prompts to avoid interference from other data
        filterset = SystemPromptFilterSet(
            data={"status": [str(approved.pk)]},
            queryset=SystemPrompt.objects.filter(name__startswith="FilterTest_"),
        )
        # prompt1 and prompt3 are Approved
        self.assertGreaterEqual(filterset.qs.count(), 2)
        self.assertIn(self.prompt1, filterset.qs)
        self.assertIn(self.prompt3, filterset.qs)

    def test_filter_by_is_file_based(self):
        """Test filtering prompts by is_file_based."""
        # Filter only our test prompts
        filterset = SystemPromptFilterSet(
            data={"is_file_based": True},
            queryset=SystemPrompt.objects.filter(name__startswith="FilterTest_"),
        )
        self.assertGreaterEqual(filterset.qs.count(), 1)
        self.assertIn(self.prompt3, filterset.qs)

    def test_filter_by_version(self):
        """Test filtering prompts by version."""
        # Filter for version 1 prompts from our test set
        filterset = SystemPromptFilterSet(
            data={"version": 1},
            queryset=SystemPrompt.objects.filter(name__startswith="FilterTest_"),
        )
        self.assertGreaterEqual(filterset.qs.count(), 3)
        self.assertIn(self.prompt1, filterset.qs)

    def test_search_by_name(self):
        """Test searching prompts by name."""
        filterset = SystemPromptFilterSet(
            data={"q": "FilterTest_Network"},
            queryset=SystemPrompt.objects.all(),
        )
        self.assertGreaterEqual(filterset.qs.count(), 1)
        self.assertIn(self.prompt1, filterset.qs)

    def test_search_by_prompt_text(self):
        """Test searching prompts by prompt_text content."""
        # Use unique text that only exists in our test prompt
        filterset = SystemPromptFilterSet(
            data={"q": "security issues for filter tests"},
            queryset=SystemPrompt.objects.all(),
        )
        self.assertGreaterEqual(filterset.qs.count(), 1)
        self.assertIn(self.prompt2, filterset.qs)
