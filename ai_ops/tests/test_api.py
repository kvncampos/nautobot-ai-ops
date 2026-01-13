"""Tests for AI Ops API."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from nautobot.core.choices import ColorChoices
from nautobot.extras.models import Status
from rest_framework import status
from rest_framework.test import APITestCase

from ai_ops.models import SystemPrompt
from ai_ops.tests.factories import TestDataMixin

User = get_user_model()


class SystemPromptAPITestCase(APITestCase, TestDataMixin):
    """Test cases for SystemPrompt API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self._create_system_prompt_statuses()
        self._create_test_user()
        self._create_test_prompt()

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
            obj, _ = Status.objects.get_or_create(
                name=config["name"],
                defaults={"color": config["color"]},
            )
            if system_prompt_ct not in obj.content_types.all():
                obj.content_types.add(system_prompt_ct)

    def _create_test_user(self):
        """Create test user with permissions using get_or_create."""
        self.user, _ = User.objects.get_or_create(
            username="api_testadmin",
            defaults={
                "email": "api_admin@test.com",
                "is_superuser": True,
                "is_staff": True,
            },
        )
        self.user.set_password("testpass123")
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def _create_test_prompt(self):
        """Create a test prompt using get_or_create."""
        self.approved_status = Status.objects.get(name="Approved")
        self.prompt, _ = SystemPrompt.objects.get_or_create(
            name="APITest_Prompt",
            defaults={
                "prompt_text": "You are a helpful assistant for API tests.",
                "status": self.approved_status,
            },
        )

    def test_list_system_prompts(self):
        """Test listing system prompts via API."""
        url = reverse("plugins-api:ai_ops-api:systemprompt-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_retrieve_system_prompt(self):
        """Test retrieving a single system prompt via API."""
        url = reverse("plugins-api:ai_ops-api:systemprompt-detail", kwargs={"pk": self.prompt.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "APITest_Prompt")

    def test_create_system_prompt(self):
        """Test creating a system prompt via API."""
        url = reverse("plugins-api:ai_ops-api:systemprompt-list")
        # Use a unique name with timestamp to avoid collisions
        import time

        unique_name = f"APITest_Create_{int(time.time())}"
        data = {
            "name": unique_name,
            "prompt_text": "You are a network automation expert.",
            "status": str(self.approved_status.pk),
            "is_file_based": False,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], unique_name)
        self.assertEqual(response.data["version"], 1)

    def test_update_system_prompt(self):
        """Test updating a system prompt via API."""
        # Create a fresh prompt for this test
        test_prompt, _ = SystemPrompt.objects.get_or_create(
            name="APITest_Update",
            defaults={
                "prompt_text": "Original text.",
                "status": self.approved_status,
            },
        )

        url = reverse("plugins-api:ai_ops-api:systemprompt-detail", kwargs={"pk": test_prompt.pk})
        data = {
            "name": "APITest_Update",
            "prompt_text": "Updated prompt text via API.",
            "status": str(self.approved_status.pk),
            "is_file_based": False,
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["prompt_text"], "Updated prompt text via API.")

    def test_delete_system_prompt(self):
        """Test deleting a system prompt via API."""
        # Create a fresh prompt specifically for deletion
        delete_prompt = SystemPrompt.objects.create(
            name="APITest_ToDelete",
            prompt_text="This will be deleted.",
            status=self.approved_status,
        )
        prompt_pk = delete_prompt.pk

        url = reverse("plugins-api:ai_ops-api:systemprompt-detail", kwargs={"pk": prompt_pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SystemPrompt.objects.filter(pk=prompt_pk).exists())

    def test_update_prompt_increments_version(self):
        """Test that updating prompt_text auto-increments version."""
        import time

        # Create a fresh prompt for this test
        test_prompt = SystemPrompt.objects.create(
            name=f"APITest_Version_{int(time.time())}",
            prompt_text="Original content.",
            status=self.approved_status,
        )
        original_version = test_prompt.version
        self.assertEqual(original_version, 1)

        # Update prompt_text via API
        url = reverse("plugins-api:ai_ops-api:systemprompt-detail", kwargs={"pk": test_prompt.pk})
        data = {
            "name": test_prompt.name,
            "prompt_text": "Updated content - should increment version.",
            "status": str(self.approved_status.pk),
            "is_file_based": False,
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], original_version + 1)

    def test_update_without_prompt_change_keeps_version(self):
        """Test that updating other fields does NOT increment version."""
        import time

        # Create a fresh prompt for this test
        testing_status = Status.objects.get(name="Testing")
        test_prompt = SystemPrompt.objects.create(
            name=f"APITest_NoVersion_{int(time.time())}",
            prompt_text="Content that won't change.",
            status=self.approved_status,
        )
        original_version = test_prompt.version

        # Update status only (not prompt_text) via API
        url = reverse("plugins-api:ai_ops-api:systemprompt-detail", kwargs={"pk": test_prompt.pk})
        data = {
            "name": test_prompt.name,
            "prompt_text": test_prompt.prompt_text,  # Same content
            "status": str(testing_status.pk),  # Different status
            "is_file_based": False,
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], original_version)  # Version unchanged


class LLMModelSystemPromptAPITestCase(APITestCase, TestDataMixin):
    """Test cases for LLMModel with SystemPrompt relationship via API."""

    def setUp(self):
        """Set up test data."""
        self.setup_test_data()
        self._create_system_prompt_statuses()
        self._create_test_user()
        self._create_test_prompt()

    def tearDown(self):
        """Clean up after tests."""
        # Clean model assignment
        self.llama2_model.system_prompt = None
        self.llama2_model.save()
        self.teardown_test_data()

    def _create_system_prompt_statuses(self):
        """Create required statuses for SystemPrompt."""
        system_prompt_ct = ContentType.objects.get_for_model(SystemPrompt)

        status_configs = [
            {"name": "Approved", "color": ColorChoices.COLOR_GREEN},
        ]

        for config in status_configs:
            obj, _ = Status.objects.get_or_create(
                name=config["name"],
                defaults={"color": config["color"]},
            )
            if system_prompt_ct not in obj.content_types.all():
                obj.content_types.add(system_prompt_ct)

    def _create_test_user(self):
        """Create test user with permissions using get_or_create."""
        self.user, _ = User.objects.get_or_create(
            username="api_testadmin2",
            defaults={
                "email": "api_admin2@test.com",
                "is_superuser": True,
                "is_staff": True,
            },
        )
        self.user.set_password("testpass123")
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def _create_test_prompt(self):
        """Create a test prompt using get_or_create."""
        approved_status = Status.objects.get(name="Approved")
        self.prompt, _ = SystemPrompt.objects.get_or_create(
            name="APITest_Model_Prompt",
            defaults={
                "prompt_text": "Custom prompt for model API tests.",
                "status": approved_status,
            },
        )

    def test_llm_model_includes_system_prompt(self):
        """Test that LLMModel API response includes system_prompt."""
        # Assign prompt to model
        self.llama2_model.system_prompt = self.prompt
        self.llama2_model.save()

        url = reverse("plugins-api:ai_ops-api:llmmodel-detail", kwargs={"pk": self.llama2_model.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("system_prompt", response.data)
        self.assertIsNotNone(response.data["system_prompt"])

    def test_llm_model_system_prompt_nullable(self):
        """Test that LLMModel API works with null system_prompt."""
        # Ensure no prompt assigned
        self.llama2_model.system_prompt = None
        self.llama2_model.save()

        url = reverse("plugins-api:ai_ops-api:llmmodel-detail", kwargs={"pk": self.llama2_model.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("system_prompt", response.data)
