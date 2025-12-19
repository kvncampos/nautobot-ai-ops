"""Utility functions for retrieving default model information."""

import logging

from nautobot.extras.models import JobQueue, Status

logger = logging.getLogger(__name__)


def get_default_status():
    """Get the default 'Unhealthy' status for MCPServer."""
    return Status.objects.get(name="Unhealthy").pk


def get_default_job_queue():
    """Get the default JobQueue for scheduled jobs.

    Returns:
        JobQueue: The default job queue instance
    """
    try:
        default_queue = JobQueue.objects.get(name="default", queue_type="celery")
        return default_queue
    except JobQueue.DoesNotExist:
        logger.error("Default job queue does not exist. It should be created automatically by Nautobot.")
        raise
    except Exception as e:
        logger.error(f"Failed to get default job queue: {e}")
        raise
