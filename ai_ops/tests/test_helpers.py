"""Tests for helper functions."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from ai_ops.helpers.get_info import get_default_status


class GetDefaultStatusTestCase(TestCase):
    """Test cases for get_default_status helper."""

    def test_get_default_status(self):
        """Test getting default status."""
        from nautobot.extras.models import Status

        # Ensure Unhealthy status exists
        Status.objects.get_or_create(
            name="Unhealthy",
            defaults={"color": "red"},
        )

        status_pk = get_default_status()
        status = Status.objects.get(pk=status_pk)
        self.assertEqual(status.name, "Unhealthy")


class CheckpointerTestCase(TestCase):
    """Test cases for checkpointer functions."""

    def test_get_redis_uri(self):
        """Test Redis URI construction."""
        from ai_ops.checkpointer import get_redis_uri

        with patch.dict("os.environ", {"NAUTOBOT_REDIS_HOST": "testhost", "NAUTOBOT_REDIS_PORT": "6380"}):
            uri = get_redis_uri()
            self.assertIn("testhost", uri)
            self.assertIn("6380", uri)

    def test_get_redis_uri_with_password(self):
        """Test Redis URI construction with password."""
        from ai_ops.checkpointer import get_redis_uri

        with patch.dict(
            "os.environ",
            {
                "NAUTOBOT_REDIS_HOST": "testhost",
                "NAUTOBOT_REDIS_PORT": "6380",
                "NAUTOBOT_REDIS_PASSWORD": "secret",
            },
        ):
            uri = get_redis_uri()
            self.assertIn(":secret@testhost", uri)

    @patch("ai_ops.checkpointer.redis.Redis")
    def test_get_redis_connection(self, mock_redis):
        """Test getting Redis connection."""
        from ai_ops.checkpointer import get_redis_connection

        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance

        with patch.dict("os.environ", {"NAUTOBOT_REDIS_HOST": "testhost"}):
            result = get_redis_connection()

            self.assertEqual(result, mock_instance)
            mock_redis.assert_called_once()
