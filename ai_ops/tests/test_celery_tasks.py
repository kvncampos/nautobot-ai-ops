# """Tests for Celery tasks."""

# from unittest.mock import MagicMock, patch

# from django.test import TestCase


# class CleanupOldCheckpointsTaskTestCase(TestCase):
#     """Test cases for cleanup_old_checkpoints Celery task."""

#     @patch("ai_ops.celery_tasks.get_app_settings_or_config")
#     @patch("ai_ops.checkpointer.get_redis_connection")
#     def test_cleanup_old_checkpoints_success(self, mock_get_redis, mock_get_config):
#         """Test successful checkpoint cleanup."""
#         from ai_ops.celery_tasks import cleanup_old_checkpoints

#         # Mock config to return 7 days
#         mock_get_config.return_value = 7

#         mock_redis = MagicMock()
#         mock_get_redis.return_value = mock_redis

#         # Mock scan to return some checkpoint keys
#         mock_redis.scan.side_effect = [
#             (0, ["checkpoint:key1", "checkpoint:key2"]),
#         ]
#         mock_redis.ttl.side_effect = [-2, -1]  # First expired, second no TTL

#         result = cleanup_old_checkpoints()

#         self.assertTrue(result["success"])
#         self.assertEqual(result["retention_days"], 7)
#         mock_redis.delete.assert_called_once()
#         mock_redis.expire.assert_called_once()

#     @patch("ai_ops.checkpointer.get_redis_connection")
#     def test_cleanup_old_checkpoints_redis_error(self, mock_get_redis):
#         """Test cleanup handles Redis connection errors."""
#         from ai_ops.celery_tasks import cleanup_old_checkpoints

#         mock_get_redis.side_effect = Exception("Redis connection failed")

#         result = cleanup_old_checkpoints()

#         self.assertFalse(result["success"])
#         self.assertIn("error", result)


# class PerformMCPHealthChecksTaskTestCase(TestCase):
#     """Test cases for perform_mcp_health_checks Celery task."""

#     @patch("ai_ops.models.MCPServer")
#     @patch("nautobot.extras.models.Status")
#     @patch("ai_ops.celery_tasks.httpx.Client")
#     def test_health_check_no_servers(self, mock_httpx, mock_status, mock_mcp_server):
#         """Test health check with no servers."""
#         from ai_ops.celery_tasks import perform_mcp_health_checks

#         mock_mcp_server.objects.filter.return_value.exclude.return_value = []

#         result = perform_mcp_health_checks()

#         self.assertTrue(result["success"])
#         self.assertEqual(result["checked_count"], 0)

#     @patch("ai_ops.agents.multi_mcp_agent.clear_mcp_cache")
#     @patch("ai_ops.models.MCPServer")
#     @patch("nautobot.extras.models.Status")
#     @patch("ai_ops.celery_tasks.httpx.Client")
#     def test_health_check_with_servers(self, mock_httpx, mock_status, mock_mcp_server, mock_cache):
#         """Test health check with servers."""
#         from ai_ops.celery_tasks import perform_mcp_health_checks

#         # Mock healthy and unhealthy status
#         mock_healthy = MagicMock()
#         mock_unhealthy = MagicMock()
#         mock_status.objects.get.side_effect = lambda name: (mock_healthy if name == "Healthy" else mock_unhealthy)

#         # Mock a server
#         mock_server = MagicMock()
#         mock_server.url = "http://localhost:8000"
#         mock_server.health_check = "/health"
#         mock_server.status = mock_unhealthy
#         mock_server.id = 1
#         mock_mcp_server.objects.filter.return_value.exclude.return_value = [mock_server]

#         # Mock successful HTTP response
#         mock_response = MagicMock()
#         mock_response.status_code = 200
#         mock_httpx.return_value.__enter__.return_value.get.return_value = mock_response

#         # Mock the clear_mcp_cache function to return a count
#         mock_cache.return_value = 2

#         # Mock the check_mcp_server_health function to simulate status change
#         with patch("ai_ops.celery_tasks.check_mcp_server_health") as mock_check:
#             mock_check.return_value = {
#                 "success": True,
#                 "server_name": "test-server",
#                 "status_changed": True,
#                 "old_status": "Unhealthy",
#                 "new_status": "Healthy",
#                 "error": "",
#             }

#             result = perform_mcp_health_checks()

#             self.assertTrue(result["success"])
#             self.assertEqual(result["checked_count"], 1)
#             self.assertEqual(result["changed_count"], 1)


# class ClearMCPCacheTaskTestCase(TestCase):
#     """Test cases for clear_mcp_cache function called by Celery tasks."""

#     def test_clear_mcp_cache_called_by_health_checks(self):
#         """Test that clear_mcp_cache is called when health checks change status."""
#         from ai_ops.celery_tasks import perform_mcp_health_checks

#         with patch("ai_ops.agents.multi_mcp_agent.clear_mcp_cache") as mock_clear_cache:
#             with patch("ai_ops.celery_tasks.check_mcp_server_health") as mock_check:
#                 with patch("ai_ops.models.MCPServer.objects") as mock_mcp_objects:
#                     # Mock a server to trigger cache clearing
#                     mock_server = MagicMock()
#                     mock_server.id = 1
#                     mock_mcp_objects.filter.return_value.exclude.return_value = [mock_server]

#                     # Mock a successful health check with status change
#                     mock_check.return_value = {"success": True, "status_changed": True, "server_name": "test-server"}

#                     # Mock the cache clear function to return a count
#                     mock_clear_cache.return_value = 2

#                     result = perform_mcp_health_checks()

#                     # Verify the task succeeded
#                     self.assertTrue(result["success"])
#                     self.assertEqual(result["checked_count"], 1)
#                     self.assertEqual(result["changed_count"], 1)
#                     self.assertTrue(result["cache_cleared"])

#                     # Verify cache was cleared due to status change
#                     mock_clear_cache.assert_called_once()


# class CleanupExpiredChatSessionsTaskTestCase(TestCase):
#     """Test cases for cleanup_expired_chat_sessions Celery task."""

#     @patch("ai_ops.celery_tasks.get_app_settings_or_config")
#     @patch("ai_ops.checkpointer.cleanup_expired_checkpoints")
#     def test_cleanup_expired_chat_sessions_success(self, mock_cleanup, mock_get_config):
#         """Test successful chat session cleanup."""
#         from ai_ops.celery_tasks import cleanup_expired_chat_sessions

#         # Mock config to return 5 minutes
#         mock_get_config.return_value = 5

#         # Mock successful cleanup
#         mock_cleanup.return_value = {
#             "success": True,
#             "processed_count": 10,
#             "deleted_count": 3,
#             "ttl_minutes": 5,
#         }

#         result = cleanup_expired_chat_sessions()

#         self.assertTrue(result["success"])
#         self.assertEqual(result["ttl_minutes"], 5)
#         self.assertEqual(result["deleted_count"], 3)
#         mock_cleanup.assert_called_once_with(ttl_minutes=5)

#     @patch("ai_ops.celery_tasks.get_app_settings_or_config")
#     @patch("ai_ops.checkpointer.cleanup_expired_checkpoints")
#     def test_cleanup_expired_chat_sessions_custom_ttl(self, mock_cleanup, mock_get_config):
#         """Test cleanup with custom TTL configuration."""
#         from ai_ops.celery_tasks import cleanup_expired_chat_sessions

#         # Mock config to return 10 minutes
#         mock_get_config.return_value = 10

#         mock_cleanup.return_value = {
#             "success": True,
#             "processed_count": 5,
#             "deleted_count": 2,
#             "ttl_minutes": 10,
#         }

#         result = cleanup_expired_chat_sessions()

#         self.assertTrue(result["success"])
#         self.assertEqual(result["ttl_minutes"], 10)
#         mock_cleanup.assert_called_once_with(ttl_minutes=10)

#     @patch("ai_ops.checkpointer.cleanup_expired_checkpoints")
#     def test_cleanup_expired_chat_sessions_default_ttl(self, mock_cleanup):
#         """Test cleanup uses default TTL when not configured."""
#         from ai_ops.celery_tasks import cleanup_expired_chat_sessions

#         mock_cleanup.return_value = {
#             "success": True,
#             "processed_count": 0,
#             "deleted_count": 0,
#             "ttl_minutes": 5,
#         }

#         result = cleanup_expired_chat_sessions()

#         self.assertTrue(result["success"])
#         # Should use default of 5 minutes
#         mock_cleanup.assert_called_once_with(ttl_minutes=5)

#     @patch("ai_ops.checkpointer.cleanup_expired_checkpoints")
#     def test_cleanup_expired_chat_sessions_error(self, mock_cleanup):
#         """Test cleanup handles errors gracefully."""
#         from ai_ops.celery_tasks import cleanup_expired_chat_sessions

#         mock_cleanup.side_effect = Exception("Checkpoint cleanup failed")

#         result = cleanup_expired_chat_sessions()

#         self.assertFalse(result["success"])
#         self.assertIn("error", result)
