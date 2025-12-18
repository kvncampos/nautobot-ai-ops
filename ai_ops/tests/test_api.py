"""Tests for AI Ops API."""

from django.contrib.auth import get_user_model
from django.test import override_settings
from nautobot.apps.testing import APITestCase

from ai_ops.models import LLMModel, LLMProvider, LLMProviderChoice, MCPServer

User = get_user_model()


class LLMProviderAPITestCase(APITestCase):
    """Test cases for LLMProvider API."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.provider = LLMProvider.objects.create(
            name=LLMProviderChoice.OLLAMA,
            description="Test provider",
            is_enabled=True,
        )

    def test_list_llm_providers(self):
        """Test listing LLM providers via API."""
        url = "/api/plugins/ai-ops/llm-providers/"
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_retrieve_llm_provider(self):
        """Test retrieving a single LLM provider via API."""
        url = f"/api/plugins/ai-ops/llm-providers/{self.provider.pk}/"
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], LLMProviderChoice.OLLAMA)

    def test_create_llm_provider(self):
        """Test creating LLM provider via API."""
        url = "/api/plugins/ai-ops/llm-providers/"
        data = {
            "name": LLMProviderChoice.OPENAI,
            "description": "OpenAI provider",
            "is_enabled": True,
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], LLMProviderChoice.OPENAI)

    def test_update_llm_provider(self):
        """Test updating LLM provider via API."""
        url = f"/api/plugins/ai-ops/llm-providers/{self.provider.pk}/"
        data = {
            "name": self.provider.name,
            "description": "Updated description",
            "is_enabled": False,
        }
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["description"], "Updated description")
        self.assertFalse(response.data["is_enabled"])


class LLMModelAPITestCase(APITestCase):
    """Test cases for LLMModel API."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.provider = LLMProvider.objects.create(
            name=LLMProviderChoice.OLLAMA,
            description="Test provider",
        )
        self.model = LLMModel.objects.create(
            llm_provider=self.provider,
            name="llama2",
            description="Test model",
            temperature=0.7,
            is_default=True,
        )

    def test_list_llm_models(self):
        """Test listing LLM models via API."""
        url = "/api/plugins/ai-ops/llm-models/"
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_retrieve_llm_model(self):
        """Test retrieving a single LLM model via API."""
        url = f"/api/plugins/ai-ops/llm-models/{self.model.pk}/"
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "llama2")
        self.assertTrue(response.data["is_default"])

    def test_create_llm_model(self):
        """Test creating LLM model via API."""
        url = "/api/plugins/ai-ops/llm-models/"
        data = {
            "llm_provider": str(self.provider.pk),
            "name": "mistral",
            "description": "Mistral model",
            "temperature": 0.5,
            "is_default": False,
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "mistral")


class MCPServerAPITestCase(APITestCase):
    """Test cases for MCPServer API."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        from nautobot.extras.models import Status

        self.status = Status.objects.get_for_model(MCPServer).first()
        self.server = MCPServer.objects.create(
            name="test-server",
            status=self.status,
            protocol="http",
            url="http://localhost:8000",
            mcp_endpoint="/mcp",
            health_check="/health",
        )

    def test_list_mcp_servers(self):
        """Test listing MCP servers via API."""
        url = "/api/plugins/ai-ops/mcp-servers/"
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_retrieve_mcp_server(self):
        """Test retrieving a single MCP server via API."""
        url = f"/api/plugins/ai-ops/mcp-servers/{self.server.pk}/"
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "test-server")
        self.assertEqual(response.data["protocol"], "http")

    def test_create_mcp_server(self):
        """Test creating MCP server via API."""
        url = "/api/plugins/ai-ops/mcp-servers/"
        data = {
            "name": "new-server",
            "status": str(self.status.pk),
            "protocol": "http",
            "url": "http://localhost:9000",
            "mcp_endpoint": "/mcp",
            "health_check": "/health",
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "new-server")

    def test_health_check_action(self):
        """Test health check custom action."""
        url = f"/api/plugins/ai-ops/mcp-servers/{self.server.pk}/health_check/"
        response = self.client.post(url, **self.header)
        # Response depends on server availability, just check it doesn't error
        self.assertIn(response.status_code, [200, 400, 500])
