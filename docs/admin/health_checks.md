# MCP Server Health Checks

The AI Ops app includes automated health check monitoring for MCP (Model Context Protocol) servers to ensure reliable agent operations.

## Overview

Health checks automatically verify the operational status of HTTP MCP servers by periodically querying their health endpoints. Servers that fail health checks are automatically marked as "Unhealthy" and excluded from agent operations until they recover.

## Features

- **Automated Scheduling**: Health checks run every minute (configurable)
- **Intelligent Retry Logic**: Status changes require verification to prevent false positives
- **Parallel Execution**: Multiple servers checked simultaneously for efficiency
- **Cache Invalidation**: MCP client cache automatically cleared when server statuses change
- **Selective Checking**: Skips servers with "Vulnerable" status or "stdio" protocol

## Health Check Process

### Basic Flow

1. **Query**: Fetch all HTTP MCP servers (excluding "Vulnerable" status)
2. **Check**: Send HTTP GET request to each server's health endpoint
3. **Evaluate**: HTTP 200 response = Healthy, otherwise = Unhealthy
4. **Update**: Change server status if needed (with verification)
5. **Invalidate**: Clear MCP client cache if any status changed

### Retry Logic

To prevent false positives from temporary network issues, the health check uses a verification process before changing server status:

**No Retry Scenarios** (Status matches check result):
- Server status is "Healthy" AND health check passes → No change needed
- Server status is "Unhealthy" AND health check fails → No change needed

**Verification Required** (Status differs from check result):
1. Initial health check indicates status should change
2. Wait 5 seconds, perform verification check #1
3. Wait 5 seconds, perform verification check #2
4. Evaluate all 3 checks (initial + 2 verifications)
5. If 2 out of 3 checks confirm the new status, flip the status
6. Otherwise, keep current status

**Example**: If a "Healthy" server fails the initial check:
- Wait 5s → Check again
- Wait 5s → Check again
- If 2 out of 3 checks failed → Mark as "Unhealthy"
- If only 1 out of 3 checks failed → Keep "Healthy"

### Parallel Execution

Health checks use parallel processing to efficiently handle multiple servers:

- **Worker Count**: Minimum 2 workers, maximum 50% of available CPU cores
- **Execution**: Uses Python's `ThreadPoolExecutor` for concurrent checks
- **Timeout**: Each individual check times out after 5 seconds

**Performance Impact**:
- 10 servers with 4 CPU cores → Uses 2 workers (50% of 4 = 2)
- 20 servers with 16 CPU cores → Uses 8 workers (50% of 16 = 8)
- Worst-case runtime per server: 15 seconds (initial + 2×5s verification)

## Configuration

### Scheduling

The health check job is automatically scheduled during app migrations and runs every minute by default.

**Current Schedule** (POC/Testing):
```
Crontab: * * * * *
Description: Every minute
```

**Production Recommendation**:
For production environments, update the scheduled job to run less frequently:

1. Navigate to **Jobs > Scheduled Jobs**
2. Find "MCP Server Health Check"
3. Edit the schedule
4. Change crontab to: `*/5 * * * *` (every 5 minutes)
5. Save changes

**Alternative Schedules**:
- Every 5 minutes: `*/5 * * * *`
- Every 10 minutes: `*/10 * * * *`
- Every 15 minutes: `*/15 * * * *`
- Every 30 minutes: `*/30 * * * *`

### Server Status Configuration

Health checks only process servers meeting these criteria:

- **Protocol**: Must be `http` (STDIO servers are skipped)
- **Status**: Must NOT be "Vulnerable" (these are excluded)
- **Health Endpoint**: Defaults to `/health` (configurable per server)

**Status Meanings**:
- **Healthy**: Server is operational and responding to health checks
- **Unhealthy**: Server failed health checks and is excluded from agent operations
- **Vulnerable**: Manually set status to exclude server from health checks entirely (e.g., known security issues)

### Health Check Endpoint

Each MCP server can specify its health check endpoint path:

- **Default**: `/health`
- **Configurable**: Set custom path in MCP Server configuration
- **URL Construction**: `{server.url.rstrip('/')}{server.health_check}`

**Example**:
```
Server URL: https://mcp-server.internal.com
Health Check Path: /health
Final URL: https://mcp-server.internal.com/health
```

### SSL Verification

SSL certificate verification behavior depends on server type:

- **Internal Servers** (`mcp_type="internal"`): SSL verification **disabled** (for self-signed certs)
- **External Servers** (`mcp_type="external"`): SSL verification **enabled**

## Monitoring

### Job Execution

Monitor health check execution through Nautobot's job system:

1. Navigate to **Jobs > Job Results**
2. Filter by job name: "MCP Server Health Check"
3. View execution logs and results

**Log Messages**:
- ✅ Success: `Health check completed: X checked, Y changed, Z failed`
- ⚠️ Status Change: `MCP Server status changed: {name} (Healthy → Unhealthy)`
- ❌ Failure: `Health check failed: {error}`

### Cache Invalidation

When server statuses change, the MCP client cache is automatically invalidated:

```
MCP client cache cleared due to status changes (was tracking X server(s))
```

This ensures the agent immediately picks up the new server configuration without requiring a manual cache clear.

## Manual Health Checks

In addition to automated health checks, you can manually check individual servers:

1. Navigate to **AI Platform > Configuration > MCP Servers**
2. Click on a specific MCP server
3. Click the **Check Health** button
4. View immediate health check results

Manual health checks:
- Do NOT trigger status changes
- Do NOT clear the MCP client cache
- Provide immediate feedback for troubleshooting

## Troubleshooting

### Health Check Not Running

**Verify Scheduled Job**:
1. Navigate to **Jobs > Scheduled Jobs**
2. Find "MCP Server Health Check"
3. Verify:
   - Status is "Enabled"
   - Crontab is correct
   - Start time is in the past
   - User is "JobRunner"

**Check Job Registration**:
- Verify job appears in **Jobs** list
- Module: `ai_ops.jobs.mcp_health_check`
- Class: `MCPServerHealthCheckJob`

### Server Stuck in Unhealthy Status

**Verify Server Accessibility**:
```bash
curl -i https://mcp-server.internal.com/health
```

Expected response: HTTP 200

**Common Issues**:
- Server is actually down
- Network connectivity problems
- Firewall blocking Nautobot → MCP server
- Health endpoint path incorrect
- SSL certificate issues (for external servers)

**Temporary Override**:
If server is actually healthy but status is stuck:
1. Edit the MCP server
2. Manually set status to "Healthy"
3. Save changes
4. Monitor next health check cycle

### All Health Checks Failing

**Check Nautobot Server**:
- Network connectivity working?
- DNS resolution working?
- Firewall rules correct?

**Check Celery Workers**:
```bash
# View Celery worker status
nautobot-server celery inspect active

# Check for stuck tasks
nautobot-server celery inspect scheduled
```

**Review Logs**:
```bash
# Check Nautobot logs for health check errors
tail -f /var/log/nautobot/nautobot.log | grep "health check"
```

## Performance Tuning

### Adjust Worker Count

Worker count is calculated automatically but can be influenced by system resources:

```python
# Current formula:
max_workers = max(2, min(cpu_count // 2, server_count))
```

**To modify** (requires code change):
1. Edit `ai_ops/celery_tasks.py`
2. Find `perform_mcp_health_checks()` function
3. Adjust the worker calculation formula
4. Restart Nautobot

### Adjust Check Frequency

For environments with many servers or slow networks, consider:

1. **Increase schedule interval**: Every 10-15 minutes instead of every minute
2. **Reduce verification checks**: Modify retry logic (requires code change)
3. **Increase timeout**: Modify 5-second timeout (requires code change)

### Exclude Servers from Checks

To permanently exclude a server from automated health checks:

1. Edit the MCP server
2. Set status to "Vulnerable"
3. Save changes

The server will be skipped in all future automated health checks.

## API Integration

### Celery Task Invocation

You can programmatically trigger health checks:

```python
from ai_ops.celery_tasks import perform_mcp_health_checks

# Trigger health checks
result = perform_mcp_health_checks()

# Check results
if result['success']:
    print(f"Checked: {result['checked_count']}")
    print(f"Changed: {result['changed_count']}")
    print(f"Failed: {result['failed_count']}")
    print(f"Cache cleared: {result['cache_cleared']}")
```

### Single Server Check

Check a specific server:

```python
from ai_ops.celery_tasks import check_mcp_server_health

# Check server by ID
result = check_mcp_server_health(server_id='uuid-here')

if result['success']:
    if result['status_changed']:
        print(f"Status changed: {result['old_status']} → {result['new_status']}")
    else:
        print(f"Status unchanged: {result['new_status']}")
```

## Best Practices

1. **Production Scheduling**: Use 5-15 minute intervals instead of every minute
2. **Monitor Failures**: Review job results regularly for persistent failures
3. **Use Vulnerable Status**: For servers with known issues that shouldn't be checked
4. **Test Health Endpoints**: Manually verify health endpoints work before registering servers
5. **SSL Certificates**: Use valid certificates for external servers, or mark as internal
6. **Network Requirements**: Ensure Nautobot can reach all MCP server URLs
7. **Resource Planning**: More servers = more workers = more CPU usage during checks

## Related Documentation

- [MCP Server Configuration](../user/app_overview.md#models)
- [External Interactions](../user/external_interactions.md#mcp-model-context-protocol-servers)
- [Job Scheduling](https://docs.nautobot.com/projects/core/en/stable/user-guide/platform-functionality/jobs/#scheduling-jobs)
- [Celery Configuration](https://docs.nautobot.com/projects/core/en/stable/development/apps/api/platform-features/jobs/#background-tasks)
