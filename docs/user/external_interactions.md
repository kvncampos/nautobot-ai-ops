# External Interactions

This document describes external dependencies, prerequisites, and integrations for the AI Ops App.

## External System Integrations

### From the App to Other Systems

#### Azure OpenAI Service

The AI Ops App integrates with Azure OpenAI Service to provide LLM capabilities:

- **Purpose**: Large Language Model inference and chat completion
- **Protocol**: HTTPS REST API
- **Authentication**: API Key (stored in Nautobot Secrets)
- **Endpoints**: Configurable Azure OpenAI endpoint URLs
- **Models Supported**: GPT-4, GPT-4o, GPT-4-turbo, and other Azure OpenAI deployments

**Configuration Requirements**:
- Azure OpenAI resource provisioned
- Model deployment created in Azure
- API key with appropriate permissions
- Network connectivity from Nautobot to Azure OpenAI endpoints

**Data Flow**:
1. User sends message through chat interface
2. App retrieves LLM configuration from database
3. App constructs request with conversation history
4. Request sent to Azure OpenAI endpoint
5. Response returned and displayed to user

#### MCP (Model Context Protocol) Servers

The app can connect to external or internal MCP servers to extend agent capabilities:

- **Purpose**: Provide additional tools and context to the AI agent
- **Protocols**: HTTP or STDIO
- **Authentication**: Configured per MCP server
- **Health Monitoring**: Automatic health checks via `/health` endpoint

**MCP Server Types**:
- **Internal**: Servers hosted within your infrastructure
- **External**: Third-party MCP servers

**Data Flow**:
1. App queries healthy MCP servers on startup
2. Agent discovers available tools from each server
3. During conversation, agent invokes tools as needed
4. Tool results incorporated into agent responses

#### Redis

Redis is used for conversation checkpoint storage:

- **Purpose**: Store conversation history and agent state
- **Protocol**: Redis protocol
- **Database**: Separate database number (default: DB 2)
- **Configuration**: Shared with Nautobot's Redis infrastructure

**Data Stored**:
- Conversation messages per session
- Agent state and intermediate results
- Checkpoint metadata

### From Other Systems to the App

#### REST API Clients

External systems can interact with the AI Ops App via the Nautobot REST API:

**Available Endpoints**:

- `GET /api/plugins/ai-ops/llm-models/` - List LLM models
- `POST /api/plugins/ai-ops/llm-models/` - Create LLM model
- `GET /api/plugins/ai-ops/llm-models/{id}/` - Get model details
- `PATCH /api/plugins/ai-ops/llm-models/{id}/` - Update model
- `DELETE /api/plugins/ai-ops/llm-models/{id}/` - Delete model
- `GET /api/plugins/ai-ops/mcp-servers/` - List MCP servers
- `POST /api/plugins/ai-ops/mcp-servers/` - Create MCP server
- `GET /api/plugins/ai-ops/mcp-servers/{id}/` - Get server details
- `PATCH /api/plugins/ai-ops/mcp-servers/{id}/` - Update server
- `DELETE /api/plugins/ai-ops/mcp-servers/{id}/` - Delete server

**Authentication**: Token-based authentication (Nautobot API tokens)

#### Chat API

Applications can send chat messages programmatically:

- `POST /plugins/ai-ops/api/chat/` - Send message to AI agent

**Request Format**:
```json
{
  "message": "Your question here"
}
```

**Response Format**:
```json
{
  "response": "AI agent response",
  "thread_id": "session-identifier"
}
```

## Nautobot REST API Endpoints

### Authentication

All API requests require authentication using Nautobot API tokens:

```bash
curl -H "Authorization: Token YOUR_API_TOKEN" \
  https://nautobot.example.com/api/plugins/ai-ops/llm-models/
```

### LLM Model Endpoints

#### List All LLM Models

**Request**:
```bash
curl -X GET https://nautobot.example.com/api/plugins/ai-ops/llm-models/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Accept: application/json"
```

**Response**:
```json
{
  "count": 2,
  "results": [
    {
      "id": "uuid",
      "name": "gpt-4o",
      "description": "GPT-4 Optimized",
      "azure_endpoint": "https://your-resource.openai.azure.com/",
      "api_version": "2024-02-15-preview",
      "is_default": true,
      "temperature": 0.0
    }
  ]
}
```

#### Create LLM Model

**Request**:
```bash
curl -X POST https://nautobot.example.com/api/plugins/ai-ops/llm-models/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "gpt-4-turbo",
    "description": "Fast GPT-4 model",
    "model_secret_key": "azure_gpt4_api_key",
    "azure_endpoint": "https://your-resource.openai.azure.com/",
    "api_version": "2024-02-15-preview",
    "is_default": false,
    "temperature": 0.3
  }'
```

#### Update LLM Model

**Request**:
```bash
curl -X PATCH https://nautobot.example.com/api/plugins/ai-ops/llm-models/{id}/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 0.5,
    "description": "Updated description"
  }'
```

### MCP Server Endpoints

#### List All MCP Servers

**Request**:
```bash
curl -X GET https://nautobot.example.com/api/plugins/ai-ops/mcp-servers/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Accept: application/json"
```

**Response**:
```json
{
  "count": 1,
  "results": [
    {
      "id": "uuid",
      "name": "internal-mcp-1",
      "status": {"name": "Healthy"},
      "protocol": "http",
      "url": "https://mcp-server.internal.com",
      "health_check": "/health",
      "mcp_type": "internal"
    }
  ]
}
```

#### Create MCP Server

**Request**:
```bash
curl -X POST https://nautobot.example.com/api/plugins/ai-ops/mcp-servers/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new-mcp-server",
    "protocol": "http",
    "url": "https://mcp.example.com",
    "health_check": "/health",
    "description": "External MCP server",
    "mcp_type": "external",
    "status": "healthy-status-id"
  }'
```

### Python Examples

#### Using Python Requests Library

```python
import requests

# Configuration
BASE_URL = "https://nautobot.example.com"
API_TOKEN = "your-api-token-here"
headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json",
}

# List all LLM models
response = requests.get(
    f"{BASE_URL}/api/plugins/ai-ops/llm-models/",
    headers=headers
)
models = response.json()
print(f"Found {models['count']} models")

# Get default model
default_model = next(
    (m for m in models['results'] if m['is_default']), 
    None
)
if default_model:
    print(f"Default model: {default_model['name']}")

# Create new MCP server
new_server = {
    "name": "monitoring-mcp",
    "protocol": "http",
    "url": "https://monitoring.internal.com",
    "health_check": "/health",
    "description": "Monitoring tools MCP",
    "mcp_type": "internal"
}
response = requests.post(
    f"{BASE_URL}/api/plugins/ai-ops/mcp-servers/",
    headers=headers,
    json=new_server
)
if response.status_code == 201:
    print("MCP server created successfully")
    server = response.json()
    print(f"Server ID: {server['id']}")

# Send chat message
chat_response = requests.post(
    f"{BASE_URL}/plugins/ai-ops/api/chat/",
    headers=headers,
    json={"message": "What is the status of my infrastructure?"}
)
if chat_response.status_code == 200:
    result = chat_response.json()
    print(f"AI Response: {result['response']}")
```

#### Using pynautobot

```python
from pynautobot import api

# Initialize API connection
nautobot = api(
    url="https://nautobot.example.com",
    token="your-api-token-here"
)

# Access AI Ops plugin endpoints
ai_ops = nautobot.plugins.ai_ops

# List LLM models
models = ai_ops.llm_models.all()
for model in models:
    print(f"Model: {model.name} - Default: {model.is_default}")

# Create MCP server
new_server = ai_ops.mcp_servers.create(
    name="analytics-mcp",
    protocol="http",
    url="https://analytics.internal.com",
    health_check="/health",
    mcp_type="internal"
)
print(f"Created server: {new_server.name}")

# Update server
new_server.description = "Analytics and reporting MCP"
new_server.save()
```

## Network Requirements

### Firewall Rules

**Outbound from Nautobot**:
- Azure OpenAI endpoints (HTTPS/443)
- MCP server endpoints (protocol-specific ports)

**Inbound to Nautobot**:
- Standard Nautobot ports for API access
- No additional ports required for AI Ops

### DNS Requirements

- Azure OpenAI endpoint resolution
- MCP server endpoint resolution
- Standard Nautobot DNS requirements

## Security Considerations

### API Key Management

- Store Azure OpenAI API keys in Nautobot Secrets
- Use Secret providers appropriate for your environment
- Rotate API keys according to security policy
- Never commit API keys to source control

### MCP Server Security

- Use HTTPS for HTTP-based MCP servers
- Implement authentication on MCP servers
- Limit MCP server access to trusted networks
- Monitor MCP server access logs

### API Access Control

- Use Nautobot's permission system for API access
- Create dedicated API tokens for external integrations
- Limit token permissions to required operations
- Regularly audit API token usage

### Data Privacy

- Conversation history stored in Redis
- Configure appropriate Redis retention policies
- Consider data residency requirements for Azure OpenAI
- Review and comply with data protection regulations

## Monitoring and Troubleshooting

### Health Checks

Monitor these components:

1. **Azure OpenAI Connectivity**: Test API endpoint accessibility
2. **MCP Server Health**: Check server status in UI or via API
3. **Redis Connectivity**: Verify checkpoint storage is working
4. **API Response Times**: Monitor for performance issues

### Common Issues

**API Key Errors**:
- Verify Secret configuration
- Check API key permissions in Azure
- Ensure API key is not expired

**MCP Server Connection Failures**:
- Check server URL accessibility
- Verify health check endpoint
- Review firewall rules
- Check MCP server logs

**Slow Response Times**:
- Check Azure OpenAI rate limits
- Monitor Redis performance
- Review MCP server response times
- Consider adjusting timeout settings

For additional troubleshooting, see the [FAQ](faq.md).
