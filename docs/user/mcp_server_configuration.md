# MCP Server Configuration Guide

This guide provides comprehensive instructions for configuring Model Context Protocol (MCP) servers with the AI Ops App. MCP servers extend the AI agent's capabilities by providing custom tools, context, and integrations.

## Overview

MCP (Model Context Protocol) is an open protocol that enables AI agents to interact with external tools and services. The AI Ops App can connect to multiple MCP servers simultaneously, allowing the agent to access a wide range of capabilities.

### What MCP Servers Provide

- **Custom Tools**: Execute actions like API calls, database queries, file operations
- **Context Access**: Retrieve information from external systems
- **Integrations**: Connect to third-party services (monitoring, ticketing, configuration management)
- **Automation**: Perform operational tasks on behalf of users

### MCP Server Types

| Type | Description | Examples |
|------|-------------|----------|
| **Internal** | Hosted within your infrastructure | Nautobot integrations, internal APIs |
| **External** | Third-party MCP servers | Public tools, vendor integrations |

## Prerequisites

Before configuring MCP servers:

- At least one LLM model configured
- Network connectivity to MCP server endpoints
- Health check endpoint available on MCP servers
- Authentication credentials (if required)

## Configuration Steps

### Step 1: Deploy MCP Server

Choose an MCP server implementation or create your own.

### Step 2: Add MCP Server in Nautobot

Navigate to **AI Platform > Configuration > MCP Servers**

Click **+ Add** to create a new server.

**Screenshot Placeholder:**
> _[Screenshot: MCP Server List View]_

### Step 3: Configure Health Monitoring

The app automatically monitors MCP server health via the configured health check endpoint.

### Step 4: Test Integration

Use the AI Chat Assistant to invoke tools from the MCP server.

## MCP Server Configuration

### Basic Configuration

```
Name: my-mcp-server
Status: Healthy
Protocol: HTTP
URL: http://mcp-server:8000
MCP Endpoint: /mcp
Health Check: /health
Description: Custom tools for network automation
MCP Type: Internal
```

**Screenshot Placeholder:**
> _[Screenshot: MCP Server Configuration Form]_

### Field Descriptions

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Unique identifier for the server | `nautobot-tools`, `github-integration` |
| **Status** | Server operational status | Healthy, Failed, Maintenance |
| **Protocol** | Connection type | HTTP, STDIO |
| **URL** | Base URL for the server | `http://mcp.example.com:8000` |
| **MCP Endpoint** | Path to MCP protocol endpoint | `/mcp`, `/api/mcp/v1` |
| **Health Check** | Health check endpoint path | `/health`, `/api/health` |
| **Description** | Purpose and capabilities | "GitHub API integration" |
| **MCP Type** | Server ownership | Internal, External |

## Example MCP Server Configurations

### Internal Nautobot Tools Server

Provides tools for querying and managing Nautobot data.

```
Name: nautobot-tools
Status: Healthy
Protocol: HTTP
URL: http://nautobot-mcp:8000
MCP Endpoint: /mcp
Health Check: /health
Description: Internal tools for Nautobot device management, IP address allocation, and configuration retrieval
MCP Type: Internal
```

**Available Tools:**
- `get_device_info` - Retrieve device details
- `list_devices` - List devices by site/role
- `get_ip_addresses` - Query IP address assignments
- `update_device_status` - Update device operational status
- `get_config_context` - Retrieve configuration context

**Screenshot Placeholder:**
> _[Screenshot: Nautobot Tools MCP Configuration]_

**Example Usage:**
```
User: What is the status of device SW-CORE-01?
Agent: [Uses get_device_info tool]
Agent: Device SW-CORE-01 is Active, located in DC1, running IOS-XE 17.3.1
```

---

### GitHub Integration Server

Provides tools for GitHub repository management.

```
Name: github-integration
Status: Healthy
Protocol: HTTP
URL: https://mcp-github.example.com
MCP Endpoint: /mcp/v1
Health Check: /api/health
Description: GitHub repository management, issue tracking, and PR automation
MCP Type: Internal
```

**Available Tools:**
- `create_issue` - Create GitHub issue
- `list_issues` - List issues with filters
- `create_pull_request` - Create PR
- `get_repository_info` - Get repo details
- `search_code` - Search code across repositories

**Screenshot Placeholder:**
> _[Screenshot: GitHub MCP Configuration]_

**Example Usage:**
```
User: Create an issue in the automation repo for updating device configs
Agent: [Uses create_issue tool]
Agent: Created issue #42 "Update device configuration templates"
```

---

### Monitoring Integration Server

Provides access to monitoring and alerting systems.

```
Name: monitoring-tools
Status: Healthy
Protocol: HTTP
URL: http://monitoring-mcp.internal:8080
MCP Endpoint: /mcp
Health Check: /health
Description: Network monitoring queries, alert management, and performance metrics
MCP Type: Internal
```

**Available Tools:**
- `get_alerts` - Retrieve current alerts
- `acknowledge_alert` - Acknowledge alert
- `get_device_metrics` - Get performance metrics
- `check_interface_status` - Check interface operational status
- `get_bandwidth_usage` - Query bandwidth statistics

**Screenshot Placeholder:**
> _[Screenshot: Monitoring MCP Configuration]_

**Example Usage:**
```
User: Are there any critical alerts?
Agent: [Uses get_alerts tool]
Agent: Yes, 2 critical alerts:
- SW-CORE-01 Interface Gi0/1 down
- Router-01 CPU usage > 90%
```

---

### Configuration Management Server

Provides tools for device configuration management.

```
Name: config-manager
Status: Healthy
Protocol: HTTP
URL: http://netbox-automation:9000
MCP Endpoint: /mcp
Health Check: /health
Description: Device configuration backup, deployment, and compliance checking
MCP Type: Internal
```

**Available Tools:**
- `backup_config` - Backup device configuration
- `deploy_config` - Deploy configuration to device
- `compare_configs` - Compare configurations
- `check_compliance` - Verify configuration compliance
- `get_config_template` - Retrieve configuration template

**Screenshot Placeholder:**
> _[Screenshot: Config Management MCP Configuration]_

---

### External API Integration Server

Connects to external third-party services.

```
Name: external-apis
Status: Healthy
Protocol: HTTP
URL: https://api-gateway.example.com
MCP Endpoint: /mcp/v1
Health Check: /health
Description: Third-party API integrations for IPAM, DNS, and ticketing
MCP Type: External
```

**Available Tools:**
- `create_ticket` - Create ServiceNow ticket
- `update_dns_record` - Update DNS entry
- `allocate_ip_address` - Allocate IP from IPAM
- `query_cmdb` - Query CMDB for CI information
- `send_notification` - Send Slack/Teams notification

**Screenshot Placeholder:**
> _[Screenshot: External APIs MCP Configuration]_

---

### Code Execution Server (Sandboxed)

Provides safe code execution capabilities.

```
Name: code-execution
Status: Healthy
Protocol: HTTP
URL: http://sandbox-mcp:8000
MCP Endpoint: /mcp
Health Check: /health
Description: Sandboxed Python code execution for data analysis and automation
MCP Type: Internal
```

**Available Tools:**
- `execute_python` - Execute Python code in sandbox
- `validate_config` - Validate device configuration
- `parse_data` - Parse structured data
- `transform_data` - Transform data formats
- `generate_report` - Generate custom reports

**Screenshot Placeholder:**
> _[Screenshot: Code Execution MCP Configuration]_

**Security Considerations:**
- ⚠️ Use sandboxed environment only
- ⚠️ Implement resource limits (CPU, memory, time)
- ⚠️ Restrict network access from sandbox
- ⚠️ Validate all input before execution
- ⚠️ Log all execution requests

---

### STDIO Protocol Example

For local process-based MCP servers.

```
Name: local-file-tools
Status: Healthy
Protocol: STDIO
URL: file:///usr/local/bin/mcp-file-server
MCP Endpoint: (not used for STDIO)
Health Check: (not used for STDIO)
Description: Local file system operations
MCP Type: Internal
```

**Use Cases:**
- Local file operations
- Legacy tool integration
- Command-line utilities
- Local database access

**Screenshot Placeholder:**
> _[Screenshot: STDIO MCP Configuration]_

## MCP Server Implementation

### Creating a Simple MCP Server

Example using Python and the MCP SDK:

```python
# mcp_server.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import httpx

app = Server("nautobot-tools")

@app.tool()
async def get_device_info(device_name: str) -> str:
    """Get device information from Nautobot.
    
    Args:
        device_name: Name of the device to query
        
    Returns:
        Device information as JSON string
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://nautobot/api/dcim/devices/?name={device_name}",
            headers={"Authorization": "Token YOUR_TOKEN"}
        )
        return response.json()

@app.tool()
async def list_devices(site: str = None, role: str = None) -> str:
    """List devices with optional filters.
    
    Args:
        site: Filter by site name (optional)
        role: Filter by device role (optional)
        
    Returns:
        List of devices as JSON string
    """
    params = {}
    if site:
        params["site"] = site
    if role:
        params["role"] = role
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://nautobot/api/dcim/devices/",
            params=params,
            headers={"Authorization": "Token YOUR_TOKEN"}
        )
        return response.json()

@app.tool()
async def update_device_status(device_name: str, status: str) -> str:
    """Update device operational status.
    
    Args:
        device_name: Name of the device
        status: New status (Active, Offline, Maintenance)
        
    Returns:
        Success message
    """
    # Implementation
    pass

# Health check endpoint
@app.health()
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "tools": len(app.tools)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server.py .

EXPOSE 8000

CMD ["python", "mcp_server.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  nautobot-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NAUTOBOT_URL=http://nautobot:8080
      - NAUTOBOT_TOKEN=${NAUTOBOT_TOKEN}
    networks:
      - nautobot-network
    restart: unless-stopped

networks:
  nautobot-network:
    external: true
```

**Screenshot Placeholder:**
> _[Screenshot: MCP Server Container Logs]_

## Health Monitoring

### Automatic Health Checks

The AI Ops App performs automatic health checks on configured MCP servers:

- **Frequency**: Every 5 minutes (configurable)
- **Timeout**: 10 seconds
- **Retry Logic**: 3 attempts with exponential backoff
- **Status Updates**: Automatic status field updates

### Health Check Endpoint

MCP servers must implement a health check endpoint:

```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "tools_available": 5
    }
```

**Response Format:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-09T12:34:56.789Z",
  "version": "1.0.0",
  "tools_available": 5
}
```

### Status Management

#### Healthy Status
- Health check passes
- All tools accessible
- Server included in agent operations

#### Failed Status
- Health check fails
- Server excluded from agent operations
- Automatic retry attempts continue

#### Maintenance Status
- Manually disabled
- Server excluded from operations
- No automatic health checks

**Screenshot Placeholder:**
> _[Screenshot: MCP Server Status Dashboard]_

## Security Considerations

### Authentication

Implement authentication for MCP servers:

```python
from fastapi import Header, HTTPException

@app.tool()
async def secure_tool(
    param: str,
    authorization: str = Header(None)
) -> str:
    """Secured tool requiring authentication."""
    if not validate_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Tool logic
    pass
```

### Network Security

- ✓ Use HTTPS for external MCP servers
- ✓ Implement network segmentation
- ✓ Use internal DNS for internal servers
- ✓ Restrict access with firewall rules
- ✓ Use VPN for remote MCP servers

### Input Validation

```python
from pydantic import BaseModel, validator

class DeviceQuery(BaseModel):
    device_name: str
    
    @validator('device_name')
    def validate_device_name(cls, v):
        if not v.isalnum():
            raise ValueError('Device name must be alphanumeric')
        return v

@app.tool()
async def get_device(query: DeviceQuery) -> str:
    """Get device with validated input."""
    # Tool logic with validated query.device_name
    pass
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.tool()
@limiter.limit("10/minute")
async def rate_limited_tool(param: str) -> str:
    """Tool with rate limiting."""
    pass
```

## Troubleshooting

### MCP Server Connection Issues

**Symptom**: Server status shows "Failed"

**Check:**
1. Server is running: `curl http://mcp-server:8000/health`
2. Network connectivity: `ping mcp-server`
3. Firewall rules: Check port access
4. Health endpoint accessible: Check logs

**Fix:**
```bash
# Restart MCP server
docker restart nautobot-mcp

# Check logs
docker logs nautobot-mcp

# Verify health endpoint
curl http://mcp-server:8000/health
```

### Tool Discovery Issues

**Symptom**: Agent doesn't see available tools

**Check:**
1. MCP server status is "Healthy"
2. Tools properly registered in MCP server
3. Agent restart after MCP server changes
4. MCP endpoint URL correct

**Fix:**
```bash
# Restart Nautobot worker
systemctl restart nautobot-worker

# Check MCP server tools endpoint
curl http://mcp-server:8000/mcp/tools
```

### Authentication Errors

**Symptom**: 401 Unauthorized errors

**Check:**
1. API tokens configured correctly
2. Token has required permissions
3. Token not expired
4. Headers sent correctly

**Fix:**
```python
# Update token in environment
export MCP_AUTH_TOKEN="new-token-value"

# Restart MCP server
docker restart nautobot-mcp
```

### Performance Issues

**Symptom**: Slow tool execution

**Check:**
1. MCP server resource usage
2. Network latency
3. Database query performance
4. Tool timeout settings

**Optimize:**
```python
# Add caching
from functools import lru_cache

@lru_cache(maxsize=100)
@app.tool()
async def cached_tool(param: str) -> str:
    """Tool with response caching."""
    # Expensive operation
    pass
```

## Best Practices

### Development

- ✓ Start with HTTP protocol for easier debugging
- ✓ Implement comprehensive health checks
- ✓ Log all tool invocations
- ✓ Use async/await for I/O operations
- ✓ Implement proper error handling

### Security

- ✓ Always use HTTPS for external servers
- ✓ Implement authentication for all tools
- ✓ Validate all inputs
- ✓ Apply rate limiting
- ✓ Use least-privilege access

### Operations

- ✓ Monitor MCP server health
- ✓ Set up alerts for failures
- ✓ Implement automated backups
- ✓ Version control MCP server code
- ✓ Document available tools

### Performance

- ✓ Cache expensive operations
- ✓ Use connection pooling
- ✓ Implement pagination for large results
- ✓ Set appropriate timeouts
- ✓ Monitor resource usage

## Multi-MCP Server Architecture

### Complementary Servers

Configure multiple servers for different domains:

```
1. nautobot-tools (Internal)
   - Device management
   - IP address allocation
   - Configuration context

2. monitoring-tools (Internal)
   - Alert queries
   - Performance metrics
   - Interface status

3. github-integration (Internal)
   - Issue management
   - PR automation
   - Code search

4. external-apis (External)
   - Ticketing system
   - DNS management
   - CMDB queries
```

**Screenshot Placeholder:**
> _[Screenshot: Multi-MCP Server Dashboard]_

### Load Balancing

For high-availability deployments:

```
# Multiple instances of same MCP server
nautobot-tools-1: http://mcp-1:8000
nautobot-tools-2: http://mcp-2:8000
nautobot-tools-3: http://mcp-3:8000
```

Use external load balancer or DNS round-robin.

## Advanced Configuration

### Custom Tool Parameters

```python
from typing import Optional, List
from pydantic import BaseModel, Field

class DeviceFilter(BaseModel):
    site: Optional[str] = Field(None, description="Site name")
    role: Optional[str] = Field(None, description="Device role")
    status: Optional[str] = Field("Active", description="Device status")
    tags: Optional[List[str]] = Field(None, description="Device tags")

@app.tool()
async def search_devices(filters: DeviceFilter) -> str:
    """Advanced device search with multiple filters."""
    # Complex query logic
    pass
```

### Streaming Responses

```python
@app.tool()
async def stream_logs(device_name: str):
    """Stream device logs in real-time."""
    async for log_line in get_device_logs(device_name):
        yield log_line
```

### Tool Composition

```python
@app.tool()
async def troubleshoot_device(device_name: str) -> str:
    """Comprehensive device troubleshooting."""
    # Compose multiple tools
    info = await get_device_info(device_name)
    alerts = await get_device_alerts(device_name)
    metrics = await get_device_metrics(device_name)
    
    return {
        "device_info": info,
        "alerts": alerts,
        "metrics": metrics,
        "recommendation": generate_recommendation(info, alerts, metrics)
    }
```

## Testing MCP Servers

### Unit Tests

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_device_info():
    """Test device info retrieval."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/mcp/tools/get_device_info",
            json={"device_name": "SW-CORE-01"}
        )
        assert response.status_code == 200
        assert "device" in response.json()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_mcp_integration():
    """Test full MCP integration."""
    # Test health check
    health = await test_client.get("/health")
    assert health.status_code == 200
    
    # Test tool discovery
    tools = await test_client.get("/mcp/tools")
    assert len(tools.json()) > 0
    
    # Test tool execution
    result = await test_client.post(
        "/mcp/tools/get_device_info",
        json={"device_name": "test-device"}
    )
    assert result.status_code == 200
```

## Monitoring and Observability

### Metrics Collection

```python
from prometheus_client import Counter, Histogram

tool_calls = Counter('mcp_tool_calls_total', 'Total tool calls', ['tool_name'])
tool_duration = Histogram('mcp_tool_duration_seconds', 'Tool execution duration', ['tool_name'])

@app.tool()
async def monitored_tool(param: str) -> str:
    """Tool with metrics."""
    tool_calls.labels(tool_name='monitored_tool').inc()
    with tool_duration.labels(tool_name='monitored_tool').time():
        # Tool logic
        pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

@app.tool()
async def logged_tool(param: str) -> str:
    """Tool with comprehensive logging."""
    logger.info(f"Tool called with param: {param}")
    try:
        result = await execute_logic(param)
        logger.info(f"Tool succeeded: {result}")
        return result
    except Exception as e:
        logger.error(f"Tool failed: {str(e)}", exc_info=True)
        raise
```

## Next Steps

After configuring MCP servers:

1. [Test Integration](app_use_cases.md) - Use tools via AI Chat Assistant
2. [Monitor Health](../admin/health_checks.md) - Track server health and performance
3. [Develop Custom Tools](../dev/extending.md) - Create your own MCP servers
4. [Security Hardening](../admin/install.md) - Implement security best practices

## Related Documentation

- [Provider Configuration](provider_configuration.md) - LLM provider setup
- [Middleware Configuration](middleware_configuration.md) - Middleware setup
- [Architecture Overview](../dev/architecture.md) - MCP integration architecture
- [External Interactions](external_interactions.md) - Integration details
- [Code Reference](../dev/code_reference/index.md) - Technical implementation details
