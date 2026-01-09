"""Job to dispatch chat session cleanup task."""

from nautobot.extras.jobs import Job

from ai_ops.celery_tasks import cleanup_expired_chat_sessions

name = "AI Agents"


class CleanupExpiredChatsJob(Job):
    """Job to clean up expired chat sessions from MemorySaver based on TTL."""

    class Meta:  # type: ignore
        """Meta class for CleanupExpiredChatsJob."""

        name = "Cleanup Expired Chat Sessions"
        description = "Clean up chat sessions older than configured TTL (chat_session_ttl_minutes)"
        has_sensitive_variables = False
        hidden = True

    def run(self):
        """Entry point for the job."""
        self.logger.info("Starting chat session cleanup task...")

        # Execute the cleanup task synchronously within the job
        result = cleanup_expired_chat_sessions()

        if result.get("success"):
            self.logger.info(
                f"✅ Chat session cleanup completed: "
                f"processed {result['processed_count']} sessions, "
                f"deleted {result['deleted_count']} expired sessions "
                f"(TTL: {result.get('ttl_minutes', 'N/A')} minutes)"
            )
        else:
            self.logger.error(f"❌ Chat session cleanup failed: {result.get('error')}")
            raise Exception(f"Cleanup failed: {result.get('error')}")

        return result
