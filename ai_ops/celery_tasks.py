"""Celery tasks for ai_ops app.

These tasks can be executed:
1. Manually via Nautobot Jobs (recommended) - see ai_ops.jobs.CleanupCheckpointsJob
2. Programmatically from code
3. Via scheduled execution through Nautobot's job scheduling

Note: Do NOT use CELERY_BEAT_SCHEDULE in nautobot_config.py as Nautobot uses
a custom scheduler that requires tasks to be created through the database.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from django.conf import settings
from nautobot.core.celery import app

logger = logging.getLogger(__name__)


@app.task
def cleanup_old_checkpoints():
    """Clean up old LangGraph conversation checkpoints from Redis.

    Runs periodically to remove checkpoints older than the configured
    retention period (default: 7 days).

    Note: Currently using MemorySaver (in-memory checkpoints), so this task
    won't find any Redis checkpoints to clean up. This task will be active
    when switching to Redis Stack (RedisSaver) or PostgreSQL (AsyncPostgresSaver)
    for persistent checkpoint storage.

    For Redis checkpoints, this task:
    - Scans for checkpoint keys matching pattern: checkpoint:*
    - Deletes expired keys (TTL = -2)
    - Sets TTL on keys without expiration (TTL = -1)
    - Leaves keys with existing TTL alone

    Returns:
        dict: Cleanup results with processed/deleted counts and retention period
    """
    try:
        from ai_ops.checkpointer import get_redis_connection

        # Get retention days from plugin config
        app_config = settings.PLUGINS_CONFIG.get("ai_ops", {})
        retention_days = app_config.get("checkpoint_retention_days", 7)

        # Calculate retention period in seconds
        retention_seconds = retention_days * 86400

        logger.info(f"Starting checkpoint cleanup (retention: {retention_days} days)")

        # Get Redis connection
        redis_client = get_redis_connection()

        # Scan for checkpoint keys
        # LangGraph stores checkpoints with pattern: checkpoint:*
        deleted_count = 0
        processed_count = 0
        cursor = 0

        while True:
            cursor, keys = redis_client.scan(cursor, match="checkpoint:*", count=100)

            for key in keys:
                processed_count += 1
                try:
                    # Get the TTL for the key
                    ttl = redis_client.ttl(key)

                    # Delete keys that have expired (TTL = -2) or will expire soon
                    # Or set TTL on keys without expiration (TTL = -1)
                    if ttl == -2:
                        # Key already expired, delete it
                        redis_client.delete(key)
                        deleted_count += 1
                    elif ttl == -1:
                        # Key has no expiration, set TTL based on retention policy
                        # This ensures old checkpoints without TTL will eventually expire
                        redis_client.expire(key, retention_seconds)
                    # Keys with positive TTL are already managed, leave them alone

                except Exception as e:
                    logger.warning(f"Error processing checkpoint key {key}: {e}", exc_info=True)
                    continue

            if cursor == 0:
                break

        logger.info(
            f"Checkpoint cleanup completed: processed {processed_count} keys, "
            f"deleted {deleted_count} expired keys, set TTL on keys without expiration"
        )

        return {
            "success": True,
            "processed_count": processed_count,
            "deleted_count": deleted_count,
            "retention_days": retention_days,
        }

    except Exception as e:
        logger.error(f"Failed to cleanup old checkpoints: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.task
def check_mcp_server_health(server_id):
    """Check health of a single MCP server with retry logic.

    Performs HTTP health check on the server. If the check result differs from
    the current status, performs 2 additional verification checks (5 seconds apart)
    before changing the status.

    Retry logic:
    - If server is Healthy and check passes: return immediately (no retry)
    - If server is Unhealthy and check fails: return immediately (no retry)
    - If status differs: wait 5s, check again, wait 5s, check final time, then flip

    Args:
        server_id: ID of the MCPServer to check

    Returns:
        dict: Health check results with status change information
    """
    from nautobot.extras.models import Status

    from ai_ops.models import MCPServer

    try:
        # Fetch the server
        try:
            server = MCPServer.objects.get(id=server_id)
        except MCPServer.DoesNotExist:
            logger.warning(f"MCP Server with ID {server_id} no longer exists, skipping health check")
            return {
                "success": False,
                "server_name": f"Unknown (ID: {server_id})",
                "status_changed": False,
                "old_status": "Unknown",
                "new_status": "Unknown",
                "error": "Server no longer exists",
            }

        server_name = server.name
        current_status = server.status.name
        logger.info(f"Starting health check for MCP server: {server_name} (current status: {current_status})")

        # Build health check URL
        health_path = getattr(server, "health_check", "/health")
        health_url = f"{server.url.rstrip('/')}{health_path}"

        # Determine SSL verification based on server type
        verify_ssl = server.mcp_type != "internal"

        def perform_check():
            """Perform a single health check and return True if healthy, False otherwise."""
            try:
                with httpx.Client(verify=verify_ssl, timeout=5.0) as client:
                    response = client.get(health_url)
                    return response.status_code == 200
            except httpx.TimeoutException:
                logger.warning(f"Health check timed out for {server_name} at {health_url}")
                return False
            except Exception as e:
                logger.warning(f"Health check failed for {server_name}: {e}")
                return False

        # Perform initial health check
        is_healthy = perform_check()
        logger.debug(f"Initial check for {server_name}: {'healthy' if is_healthy else 'unhealthy'}")

        # Determine if status matches current state
        status_matches = (is_healthy and current_status == "Healthy") or (
            not is_healthy and current_status == "Unhealthy"
        )

        if status_matches:
            # Status matches current state, no change needed
            logger.info(f"Health check for {server_name}: status unchanged ({current_status})")
            return {
                "success": True,
                "server_name": server_name,
                "status_changed": False,
                "old_status": current_status,
                "new_status": current_status,
                "error": "",
            }

        # Status differs - perform verification checks before flipping
        logger.info(
            f"Health check for {server_name}: status differs (current: {current_status}, "
            f"check result: {'Healthy' if is_healthy else 'Unhealthy'}). Starting verification checks..."
        )

        # First verification check after 5 seconds
        time.sleep(5)
        verification_1 = perform_check()
        logger.debug(f"Verification check 1/2 for {server_name}: {'healthy' if verification_1 else 'unhealthy'}")

        # Second verification check after another 5 seconds
        time.sleep(5)
        verification_2 = perform_check()
        logger.debug(f"Verification check 2/2 for {server_name}: {'healthy' if verification_2 else 'unhealthy'}")

        # Determine final status based on majority (2 out of 3 checks)
        checks = [is_healthy, verification_1, verification_2]
        healthy_count = sum(checks)
        final_is_healthy = healthy_count >= 2

        logger.info(
            f"Verification complete for {server_name}: {healthy_count}/3 checks passed. "
            f"Final status: {'Healthy' if final_is_healthy else 'Unhealthy'}"
        )

        # Determine if we should flip the status
        should_flip = (final_is_healthy and current_status == "Unhealthy") or (
            not final_is_healthy and current_status == "Healthy"
        )

        if should_flip:
            # Flip the status
            new_status_name = "Healthy" if final_is_healthy else "Unhealthy"
            new_status = Status.objects.get(name=new_status_name)
            server.status = new_status
            server.save()

            logger.warning(f"⚠️ MCP Server status changed: {server_name} ({current_status} → {new_status_name})")

            return {
                "success": True,
                "server_name": server_name,
                "status_changed": True,
                "old_status": current_status,
                "new_status": new_status_name,
                "error": "",
            }
        else:
            # Status remains the same after verification
            logger.info(
                f"Health check for {server_name}: verification checks did not confirm status change. "
                f"Status remains {current_status}"
            )
            return {
                "success": True,
                "server_name": server_name,
                "status_changed": False,
                "old_status": current_status,
                "new_status": current_status,
                "error": "",
            }

    except Exception as e:
        logger.error(f"Unexpected error during health check for server ID {server_id}: {e}", exc_info=True)
        return {
            "success": False,
            "server_name": f"Unknown (ID: {server_id})",
            "status_changed": False,
            "old_status": "Unknown",
            "new_status": "Unknown",
            "error": str(e),
        }


@app.task
def perform_mcp_health_checks():
    """Perform health checks on all HTTP MCP servers (excluding Vulnerable status).

    Uses parallel execution with ThreadPoolExecutor to check multiple servers
    simultaneously. Worker count defaults to 1, increases by 1 per MCP server, with a maximum of 4 workers.

    Invalidates MCP client cache if any server status changes.

    Returns:
        dict: Summary of health check results including counts and cache status
    """
    from ai_ops.models import MCPServer

    try:
        # Query for HTTP MCP servers, excluding those with Vulnerable status
        servers = list(MCPServer.objects.filter(protocol="http").exclude(status__name="Vulnerable"))

        if not servers:
            logger.info("No HTTP MCP servers found for health check (excluding Vulnerable)")
            return {
                "success": True,
                "checked_count": 0,
                "changed_count": 0,
                "failed_count": 0,
                "cache_cleared": False,
                "worker_count": 0,
            }

        # Calculate worker count: default 1, add 1 per MCP server, max 4 workers
        max_workers = min(len(servers), 4)

        logger.info(f"Starting health checks for {len(servers)} MCP server(s) using {max_workers} worker(s)")

        # Perform health checks in parallel
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            server_ids = [server.id for server in servers]
            results = list(executor.map(check_mcp_server_health, server_ids))

        # Aggregate results
        checked_count = len(results)
        changed_count = sum(1 for r in results if r.get("status_changed", False))
        failed_count = sum(1 for r in results if not r.get("success", False))

        logger.info(f"Health check completed: {checked_count} checked, {changed_count} changed, {failed_count} failed")

        # If any status changed, invalidate MCP client cache
        cache_cleared = False
        if changed_count > 0:
            try:
                from ai_ops.agents.multi_mcp_agent import clear_mcp_cache

                cleared_count = asyncio.run(clear_mcp_cache())
                cache_cleared = True
                logger.info(f"MCP client cache cleared due to status changes (was tracking {cleared_count} server(s))")
            except Exception as e:
                logger.error(f"Failed to clear MCP client cache: {e}", exc_info=True)

        return {
            "success": True,
            "checked_count": checked_count,
            "changed_count": changed_count,
            "failed_count": failed_count,
            "cache_cleared": cache_cleared,
            "worker_count": max_workers,
        }

    except Exception as e:
        logger.error(f"Failed to perform MCP health checks: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "checked_count": 0,
            "changed_count": 0,
            "failed_count": 0,
            "cache_cleared": False,
            "worker_count": 0,
        }
