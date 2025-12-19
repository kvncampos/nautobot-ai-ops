"""Job to perform automated MCP server health checks."""

from nautobot.extras.jobs import Job

from ai_ops.celery_tasks import perform_mcp_health_checks

name = "AI Agents"


class MCPServerHealthCheckJob(Job):
    """Job to perform automated health checks on MCP servers.

    This job checks all HTTP MCP servers (excluding those with Vulnerable status)
    and updates their health status based on HTTP health check results.

    Features:
    - Parallel execution using ThreadPoolExecutor (1 worker per server, max 4 workers)
    - Retry logic: 2 verification checks (5s apart) before status change
    - Cache invalidation: Clears MCP client cache if any status changes
    - Skips servers with "Vulnerable" status
    - Skips servers with "stdio" protocol (only checks HTTP servers)

    Status change logic:
    - Healthy server + successful check = no change
    - Unhealthy server + failed check = no change
    - Status differs = perform 2 verification checks, then flip if confirmed
    """

    class Meta:  # type: ignore
        """Meta class for MCPServerHealthCheckJob."""

        name = "MCP Server Health Check"
        description = (
            "Perform automated health checks on HTTP MCP servers with retry logic "
            "and parallel execution. Updates server status and invalidates cache if needed."
        )
        has_sensitive_variables = False
        hidden = True

    def run(self):
        """Entry point for the job."""
        self.logger.info("Starting MCP server health checks...")

        # Execute the health check task synchronously within the job
        result = perform_mcp_health_checks()

        if result.get("success"):
            checked = result.get("checked_count", 0)
            changed = result.get("changed_count", 0)
            failed = result.get("failed_count", 0)
            workers = result.get("worker_count", 0)
            cache_cleared = result.get("cache_cleared", False)

            self.logger.info(
                f"✅ MCP health check completed: "
                f"{checked} server(s) checked using {workers} worker(s), "
                f"{changed} status change(s), {failed} failure(s)"
            )

            if cache_cleared:
                self.logger.info("✅ MCP client cache cleared due to status changes")

            if changed > 0:
                self.logger.warning(f"⚠️ {changed} server(s) changed status - check logs for details")

        else:
            error_msg = result.get("error", "Unknown error")
            self.logger.error(f"❌ MCP health check failed: {error_msg}")
            raise Exception(f"Health check failed: {error_msg}")

        return result
