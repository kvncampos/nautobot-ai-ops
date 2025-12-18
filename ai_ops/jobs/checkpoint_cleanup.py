"""Job to dispatch checkpoint cleanup task."""

from nautobot.extras.jobs import Job

from ai_ops.celery_tasks import cleanup_old_checkpoints

name = "AI Agents"


class CleanupCheckpointsJob(Job):
    """Job to clean up old conversation checkpoints from Redis."""

    class Meta:  # type: ignore
        """Meta class for CleanupCheckpointsJob."""

        name = "Cleanup Old Checkpoints"
        description = "Clean up old LangGraph conversation checkpoints from Redis based on retention policy"
        has_sensitive_variables = False
        hidden = True

    def run(self):
        """Entry point for the job."""
        self.logger.info("Starting checkpoint cleanup task...")

        # Execute the cleanup task synchronously within the job
        result = cleanup_old_checkpoints()

        if result.get("success"):
            self.logger.info(
                f"✅ Checkpoint cleanup completed: "
                f"processed {result['processed_count']} keys "
                f"(retention: {result['retention_days']} days)"
            )
        else:
            self.logger.error(f"❌ Checkpoint cleanup failed: {result.get('error')}")
            raise Exception(f"Cleanup failed: {result.get('error')}")

        return result
