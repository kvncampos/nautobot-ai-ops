"""Tests for AI Ops jobs."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from ai_ops.jobs.checkpoint_cleanup import CleanupCheckpointsJob
from ai_ops.jobs.mcp_health_check import MCPServerHealthCheckJob


class CleanupCheckpointsJobTestCase(TestCase):
    """Test cases for CleanupCheckpointsJob."""

    @patch("ai_ops.jobs.checkpoint_cleanup.cleanup_old_checkpoints")
    def test_job_success(self, mock_cleanup):
        """Test job runs successfully."""
        mock_cleanup.return_value = {
            "success": True,
            "processed_count": 10,
            "retention_days": 30,
        }

        job = CleanupCheckpointsJob()
        job.logger = MagicMock()
        result = job.run()

        self.assertTrue(result["success"])
        self.assertEqual(result["processed_count"], 10)
        job.logger.info.assert_called()

    @patch("ai_ops.jobs.checkpoint_cleanup.cleanup_old_checkpoints")
    def test_job_failure(self, mock_cleanup):
        """Test job handles failures."""
        mock_cleanup.return_value = {
            "success": False,
            "error": "Redis connection failed",
        }

        job = CleanupCheckpointsJob()
        job.logger = MagicMock()

        with self.assertRaises(Exception) as context:
            job.run()

        self.assertIn("Cleanup failed", str(context.exception))
        job.logger.error.assert_called()


class MCPServerHealthCheckJobTestCase(TestCase):
    """Test cases for MCPServerHealthCheckJob."""

    @patch("ai_ops.jobs.mcp_health_check.perform_mcp_health_checks")
    def test_job_success(self, mock_health_check):
        """Test job runs successfully."""
        mock_health_check.return_value = {
            "success": True,
            "checked_count": 5,
            "changed_count": 2,
            "failed_count": 1,
            "worker_count": 4,
            "cache_cleared": True,
        }

        job = MCPServerHealthCheckJob()
        job.logger = MagicMock()
        result = job.run()

        self.assertTrue(result["success"])
        self.assertEqual(result["checked_count"], 5)
        self.assertEqual(result["changed_count"], 2)
        job.logger.info.assert_called()
        job.logger.warning.assert_called()

    @patch("ai_ops.jobs.mcp_health_check.perform_mcp_health_checks")
    def test_job_no_status_changes(self, mock_health_check):
        """Test job with no status changes."""
        mock_health_check.return_value = {
            "success": True,
            "checked_count": 5,
            "changed_count": 0,
            "failed_count": 0,
            "worker_count": 4,
            "cache_cleared": False,
        }

        job = MCPServerHealthCheckJob()
        job.logger = MagicMock()
        result = job.run()

        self.assertTrue(result["success"])
        self.assertEqual(result["changed_count"], 0)
        self.assertFalse(result["cache_cleared"])

    @patch("ai_ops.jobs.mcp_health_check.perform_mcp_health_checks")
    def test_job_failure(self, mock_health_check):
        """Test job handles failures."""
        mock_health_check.return_value = {
            "success": False,
            "error": "Network error",
        }

        job = MCPServerHealthCheckJob()
        job.logger = MagicMock()

        with self.assertRaises(Exception) as context:
            job.run()

        self.assertIn("Health check failed", str(context.exception))
        job.logger.error.assert_called()
