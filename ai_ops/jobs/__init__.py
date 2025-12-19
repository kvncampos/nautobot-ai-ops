"""Jobs for ai_ops app."""

from nautobot.apps.jobs import register_jobs

from .checkpoint_cleanup import CleanupCheckpointsJob
from .mcp_health_check import MCPServerHealthCheckJob
from .middleware_cache_jobs import DefaultModelCacheWarmingJob, MiddlewareCacheInvalidationJob

jobs = [
    CleanupCheckpointsJob,
    MiddlewareCacheInvalidationJob,
    DefaultModelCacheWarmingJob,
    MCPServerHealthCheckJob,
]
register_jobs(*jobs)
