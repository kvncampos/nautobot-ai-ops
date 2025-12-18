# Models

This page documents the database models provided by the AI Ops App.

## LLMModel

::: ai_ops.models.LLMModel
    options:
        show_root_heading: true
        show_source: false
        members:
          - get_default_model
          - get_all_models_summary
          - get_api_key
          - config_dict
          - clean

The `LLMModel` class stores configurations for Azure OpenAI Large Language Models. It supports both LAB (local development) and production environments, with flexible configuration options.

### Key Features

- **Multi-Environment Support**: Works in LAB, NONPROD, and PROD environments
- **Secret Management**: Integrates with Nautobot Secrets for API key storage
- **Default Model Selection**: Supports marking one model as the default
- **Temperature Control**: Configurable temperature for response variability
- **Validation**: Automatic validation ensures only one default model exists

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Azure deployment name (e.g., gpt-4o, gpt-4-turbo) |
| `description` | CharField | Description of the LLM and its capabilities |
| `model_secret_key` | CharField | Name of the Secret object containing the API key |
| `azure_endpoint` | URLField | Azure OpenAI endpoint URL |
| `api_version` | CharField | Azure OpenAI API version |
| `is_default` | BooleanField | Whether this is the default model |
| `temperature` | FloatField | Temperature setting (0.0 to 2.0) |

### Usage Example

```python
from ai_ops.models import LLMModel

# Get the default model
default_model = LLMModel.get_default_model()
print(f"Using model: {default_model.name}")

# Get model configuration
config = default_model.config_dict
api_key = default_model.get_api_key()

# Create a new model
new_model = LLMModel.objects.create(
    name="gpt-4-turbo",
    description="Fast GPT-4 model",
    model_secret_key="azure_api_key",
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview",
    is_default=False,
    temperature=0.3
)
```

## MCPServer

::: ai_ops.models.MCPServer
    options:
        show_root_heading: true
        show_source: false
        members:
          - clean

The `MCPServer` class stores configurations for Model Context Protocol servers that extend the AI agent's capabilities.

### Key Features

- **Status Tracking**: Uses Nautobot Status field for health monitoring
- **Protocol Support**: Supports HTTP and STDIO protocols
- **Health Checks**: Automatic health check endpoint monitoring
- **Type Classification**: Distinguishes between internal and external servers

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Unique name for the MCP server |
| `status` | StatusField | Server status (Healthy, Failed, Maintenance) |
| `protocol` | CharField | Connection type (STDIO or HTTP) |
| `url` | URLField | MCP server endpoint URL |
| `health_check` | CharField | Health check endpoint path |
| `description` | CharField | Optional description |
| `mcp_type` | CharField | Server type (internal or external) |

### Status Meanings

- **Healthy**: Server is operational and responding to health checks
- **Failed**: Health check failed; server excluded from agent operations
- **Maintenance**: Manually disabled for maintenance

### Usage Example

```python
from ai_ops.models import MCPServer
from nautobot.extras.models import Status

# Get healthy status
healthy_status = Status.objects.get(name="Healthy")

# Create a new MCP server
mcp_server = MCPServer.objects.create(
    name="monitoring-mcp",
    status=healthy_status,
    protocol="http",
    url="https://monitoring.internal.com",
    health_check="/health",
    description="Monitoring and alerting MCP",
    mcp_type="internal"
)

# Query healthy servers
healthy_servers = MCPServer.objects.filter(status__name="Healthy")
for server in healthy_servers:
    print(f"Server: {server.name} - {server.url}")
```

## Model Relationships

### LLMModel and Secrets

`LLMModel` integrates with Nautobot's Secrets management:

```python
from ai_ops.models import LLMModel
from nautobot.extras.models import Secret

# Create a secret
secret = Secret.objects.create(
    name="azure_gpt4_api_key",
    provider="environment-variable",
)

# Reference the secret in LLMModel
model = LLMModel.objects.create(
    name="gpt-4o",
    model_secret_key="azure_gpt4_api_key",
    # ... other fields
)

# Retrieve API key from secret
api_key = model.get_api_key()
```

### MCPServer and Status

`MCPServer` uses Nautobot's Status model for health tracking:

```python
from ai_ops.models import MCPServer
from nautobot.extras.models import Status

# Update server status
server = MCPServer.objects.get(name="my-mcp")
failed_status = Status.objects.get(name="Failed")
server.status = failed_status
server.save()
```

## Extras Features

Both models support Nautobot's extras features:

- **Custom Links**: Create custom links for models
- **Custom Validators**: Add validation rules
- **Export Templates**: Define export templates
- **GraphQL**: Full GraphQL API support
- **Webhooks**: Receive notifications on changes

### LLMModel Extras

```python
@extras_features(
    "custom_links",
    "custom_validators", 
    "export_templates",
    "graphql",
    "webhooks"
)
class LLMModel(PrimaryModel):
    ...
```

### MCPServer Extras

```python
@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates", 
    "graphql",
    "statuses",
    "webhooks"
)
class MCPServer(PrimaryModel):
    ...
```

## Database Migrations

The models are defined in migration `0001_initial.py`. To create the database tables:

```bash
nautobot-server migrate ai_ops
```

## Model Validation

Both models include validation logic:

### LLMModel Validation

- Only one model can be marked as `is_default=True`
- Prevents multiple default models

### MCPServer Validation

- URL field is required
- Ensures proper server configuration

## Best Practices

### LLMModel Best Practices

1. **Always have a default model**: Mark one model as default for fallback
2. **Use Secrets for API keys**: Never store keys directly in the database
3. **Temperature settings**: Use 0.0-0.3 for deterministic, 0.7-1.0 for creative
4. **Document model purposes**: Use descriptive names and descriptions

### MCPServer Best Practices

1. **Monitor health status**: Regularly check server health
2. **Use descriptive names**: Clear naming helps management
3. **Set appropriate status**: Use Maintenance status during upgrades
4. **Test health checks**: Verify health check endpoints work correctly
5. **Document server purpose**: Clear descriptions aid troubleshooting

## Related Documentation

- [Helpers](helpers.md) - Helper functions for working with models
- [API](api.md) - REST API documentation
- Usage Examples - Practical examples (see `ai_ops/helpers/USAGE_EXAMPLES.md`)
