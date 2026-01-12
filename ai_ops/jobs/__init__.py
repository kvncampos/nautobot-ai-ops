"""Jobs for ai_ops app."""

from nautobot.apps.jobs import register_jobs

from .checkpoint_cleanup import CleanupCheckpointsJob
from .mcp_health_check import MCPServerHealthCheckJob

jobs = [
    CleanupCheckpointsJob,
    MCPServerHealthCheckJob,
]
register_jobs(*jobs)
