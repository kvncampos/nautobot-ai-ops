# Models

This page documents the database models provided by the AI Ops App.

## Overview

The AI Ops App uses a flexible multi-provider architecture to support various LLM providers and middleware configurations:

- **LLMProvider**: Defines available LLM providers (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace)
- **LLMModel**: Stores specific model configurations for a provider
- **MiddlewareType**: Defines middleware types that can be applied to models
- **LLMMiddleware**: Configures middleware instances for specific models
- **MCPServer**: Manages Model Context Protocol server connections

## LLMProvider

::: ai_ops.models.LLMProvider
    options:
        show_root_heading: true
        show_source: false
        members:
          - get_handler

The `LLMProvider` class defines available LLM providers and their configurations. Each provider can have multiple LLM models configured with provider-specific settings.

### Key Features

- **Multiple Provider Support**: Ollama (default), OpenAI, Azure AI, Anthropic, HuggingFace, and Custom
- **Dynamic Configuration**: JSON schema for provider-specific settings
- **Provider Handlers**: Each provider has a dedicated handler class for initialization
- **Enable/Disable Support**: Toggle provider availability without deletion

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField (Choice) | Provider name (ollama, openai, azure_ai, anthropic, huggingface, custom) |
| `description` | CharField | Description of the provider and its capabilities |
| `documentation_url` | URLField | URL to provider's documentation |
| `config_schema` | JSONField | Provider-specific configuration as JSON |
| `is_enabled` | BooleanField | Whether this provider is available for use |

### Provider Choices

The available provider options are:

- **ollama**: Local open-source LLM runtime (default)
- **openai**: ChatGPT, GPT-4, and other OpenAI models
- **azure_ai**: Azure OpenAI Service deployments
- **anthropic**: Claude models from Anthropic
- **huggingface**: Models hosted on HuggingFace Hub
- **custom**: Custom provider implementations

### Usage Example

```python
from ai_ops.models import LLMProvider, LLMProviderChoice

# Create an Azure AI provider
azure_provider = LLMProvider.objects.create(
    name=LLMProviderChoice.AZURE_AI,
    description="Azure OpenAI Service for enterprise deployments",
    documentation_url="https://learn.microsoft.com/en-us/azure/ai-services/openai/",
    config_schema={
        "api_version": "2024-02-15-preview",
        "base_url": "https://your-resource.openai.azure.com/"
    },
    is_enabled=True
)

# Get the handler for this provider
handler = azure_provider.get_handler()

# Create an Ollama provider (local development)
ollama_provider = LLMProvider.objects.create(
    name=LLMProviderChoice.OLLAMA,
    description="Local Ollama installation for development",
    config_schema={"base_url": "http://localhost:11434"},
    is_enabled=True
)
```

### Configuration Schema Examples

**Azure AI Provider**:
```json
{
    "api_version": "2024-02-15-preview",
    "base_url": "https://your-resource.openai.azure.com/",
    "deployment_suffix": ""
}
```

**OpenAI Provider**:
```json
{
    "organization": "org-xxxxx",
    "base_url": "https://api.openai.com/v1"
}
```

**Ollama Provider**:
```json
{
    "base_url": "http://localhost:11434",
    "timeout": 300
}
```

## LLMModel

::: ai_ops.models.LLMModel
    options:
        show_root_heading: true
        show_source: false
        members:
          - get_default_model
          - get_all_models_summary
          - get_api_key
          - get_llm_provider_handler
          - config_dict
          - clean

The `LLMModel` class stores configurations for Large Language Models from any supported provider. It supports both LAB (local development) and production environments, with flexible configuration options.

### Key Features

- **Multi-Provider Support**: Works with any configured LLM provider
- **Multi-Environment Support**: Works in LAB, NONPROD, and PROD environments
- **Secret Management**: Integrates with Nautobot Secrets for API key storage
- **Default Model Selection**: Supports marking one model as the default
- **Temperature Control**: Configurable temperature for response variability
- **Middleware Support**: Can have multiple middleware configurations applied
- **Cache Control**: Configurable cache TTL for MCP client connections
- **Validation**: Automatic validation ensures only one default model exists

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `llm_provider` | ForeignKey | Reference to the LLM provider (Ollama, OpenAI, Azure AI, etc.) |
| `name` | CharField | Model name (e.g., gpt-4o, llama2, claude-3-opus) |
| `description` | CharField | Description of the LLM and its capabilities |
| `model_secret_key` | CharField | Name of the Secret object containing the API key |
| `endpoint` | URLField | LLM endpoint URL |
| `api_version` | CharField | API version (e.g., Azure OpenAI API version) |
| `is_default` | BooleanField | Whether this is the default model |
| `temperature` | FloatField | Temperature setting (0.0 to 2.0) |
| `cache_ttl` | IntegerField | Cache TTL for MCP connections (minimum 60 seconds) |

### Usage Example

```python
from ai_ops.models import LLMModel, LLMProvider

# Get the default model
default_model = LLMModel.get_default_model()
print(f"Using model: {default_model.name}")
print(f"Provider: {default_model.llm_provider.name}")

# Get model configuration
config = default_model.config_dict
api_key = default_model.get_api_key()

# Get provider handler
handler = default_model.get_llm_provider_handler()

# Create a new Azure AI model
azure_provider = LLMProvider.objects.get(name="azure_ai")
azure_model = LLMModel.objects.create(
    name="gpt-4o",
    llm_provider=azure_provider,
    description="GPT-4 Optimized model for production",
    model_secret_key="azure_api_key",
    endpoint="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview",
    is_default=True,
    temperature=0.3,
    cache_ttl=300
)

# Create an Ollama model for local development
ollama_provider = LLMProvider.objects.get(name="ollama")
ollama_model = LLMModel.objects.create(
    name="llama2",
    llm_provider=ollama_provider,
    description="Llama 2 model for local testing",
    endpoint="http://localhost:11434",
    temperature=0.7,
    cache_ttl=300
)
```

## MiddlewareType

::: ai_ops.models.MiddlewareType
    options:
        show_root_heading: true
        show_source: false
        members:
          - clean

The `MiddlewareType` class defines middleware types that can be applied to LLM models. Middleware can modify, enhance, or monitor interactions with LLM models.

### Key Features

- **Built-in & Custom Support**: Supports both LangChain middleware and custom implementations
- **Type Classification**: Distinguishes between built-in and custom middleware
- **Name Validation**: Automatically validates and formats middleware names
- **Reusable Definitions**: One type can be applied to multiple models

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Middleware class name (must end with 'Middleware', PascalCase) |
| `is_custom` | BooleanField | Whether this is custom (True) or built-in LangChain (False) |
| `description` | CharField | Description of middleware functionality |

### Name Validation

The middleware name is automatically validated and formatted:

- Must be a valid Python class name
- Automatically appends "Middleware" suffix if missing
- Converts to PascalCase if needed
- Must contain only alphanumeric characters

### Usage Example

```python
from ai_ops.models import MiddlewareType

# Create a built-in LangChain middleware type
cache_middleware = MiddlewareType.objects.create(
    name="CacheMiddleware",
    is_custom=False,
    description="Caches LLM responses to reduce API calls and costs"
)

# Create a custom middleware type
logging_middleware = MiddlewareType.objects.create(
    name="CustomLogging",  # Will become "CustomLoggingMiddleware"
    is_custom=True,
    description="Custom logging middleware for detailed request/response tracking"
)

# The name is automatically formatted
print(logging_middleware.name)  # Output: "CustomLoggingMiddleware"
```

### Built-in Middleware Types

Common LangChain middleware types include:

- **CacheMiddleware**: Response caching
- **RateLimitMiddleware**: Request rate limiting
- **RetryMiddleware**: Automatic retry logic
- **LoggingMiddleware**: Request/response logging
- **ValidationMiddleware**: Input/output validation

### Custom Middleware Types

Custom middleware can implement:

- Domain-specific transformations
- Custom monitoring and metrics
- Security scanning
- Content filtering
- Custom retry logic with backoff

## LLMMiddleware

::: ai_ops.models.LLMMiddleware
    options:
        show_root_heading: true
        show_source: false
        members:
          - display

The `LLMMiddleware` class configures middleware instances for specific LLM models. Middleware executes in priority order to process requests and responses.

### Key Features

- **Priority-Based Execution**: Lower priority values execute first (1-100)
- **Model-Specific Configuration**: Each model can have unique middleware setups
- **Active/Inactive Toggle**: Enable or disable middleware without deletion
- **Critical Flag**: Mark middleware as critical for initialization
- **Unique Constraint**: Each middleware type can only be configured once per model
- **JSON Configuration**: Flexible configuration storage
- **Fresh Instantiation**: Middleware instances created fresh for each request to prevent state leaks

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `llm_model` | ForeignKey | The LLM model this middleware applies to |
| `middleware` | ForeignKey | The middleware type to apply |
| `config` | JSONField | JSON configuration for the middleware |
| `config_version` | CharField | LangChain version this config is compatible with |
| `is_active` | BooleanField | Whether this middleware is currently active |
| `is_critical` | BooleanField | If True, agent fails if middleware can't load |
| `priority` | IntegerField | Execution priority (1-100, lower executes first) |

### Execution Order

Middleware executes in priority order:

1. Priority 1 middleware execute first
2. Priority 10 middleware execute next
3. Priority 100 middleware execute last
4. Ties are broken alphabetically by middleware name

### Usage Example

```python
from ai_ops.models import LLMModel, MiddlewareType, LLMMiddleware

# Get model and middleware type
model = LLMModel.objects.get(name="gpt-4o")
cache_type = MiddlewareType.objects.get(name="CacheMiddleware")
logging_type = MiddlewareType.objects.get(name="CustomLoggingMiddleware")

# Configure cache middleware (executes first)
cache_config = LLMMiddleware.objects.create(
    llm_model=model,
    middleware=cache_type,
    config={
        "cache_backend": "redis",
        "max_entries": 10000,
        "ttl_seconds": 3600
    },
    config_version="1.1.0",
    is_active=True,
    is_critical=False,
    priority=10
)

# Configure logging middleware (executes second)
logging_config = LLMMiddleware.objects.create(
    llm_model=model,
    middleware=logging_type,
    config={
        "log_level": "INFO",
        "include_tokens": True,
        "log_to_file": True,
        "file_path": "/var/log/ai_ops/llm_requests.log"
    },
    is_active=True,
    is_critical=True,  # Critical - agent won't start without it
    priority=20
)

# Query active middleware for a model
active_middleware = LLMMiddleware.objects.filter(
    llm_model=model,
    is_active=True
).order_by('priority', 'middleware__name')

for mw in active_middleware:
    print(f"Priority {mw.priority}: {mw.middleware.name}")
```

### Configuration Examples

**Cache Middleware**:
```json
{
    "cache_backend": "redis",
    "max_entries": 10000,
    "ttl_seconds": 3600,
    "key_prefix": "llm_cache"
}
```

**Retry Middleware**:
```json
{
    "max_retries": 3,
    "initial_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2,
    "retry_on": ["rate_limit", "timeout", "connection_error"]
}
```

**Rate Limit Middleware**:
```json
{
    "requests_per_minute": 60,
    "requests_per_hour": 1000,
    "burst_size": 10
}
```

**Custom Logging Middleware**:
```json
{
    "log_level": "INFO",
    "include_tokens": true,
    "include_latency": true,
    "log_to_file": true,
    "file_path": "/var/log/ai_ops/requests.log"
}
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

The AI Ops models form a hierarchical structure:

```
LLMProvider (1) ───→ (N) LLMModel (1) ───→ (N) LLMMiddleware
                                ↓
                          MiddlewareType (N) ←─┘

MCPServer (independent)

Status ←──── MCPServer
Secret ←──── LLMModel
```

### LLMProvider → LLMModel Relationship

Each LLM model belongs to one provider:

```python
from ai_ops.models import LLMProvider, LLMModel

# Get all models for a provider
azure_provider = LLMProvider.objects.get(name="azure_ai")
azure_models = azure_provider.llm_models.all()

for model in azure_models:
    print(f"Model: {model.name}")
    
# Get provider from model
model = LLMModel.objects.get(name="gpt-4o")
provider = model.llm_provider
print(f"Provider: {provider.get_name_display()}")
```

### LLMModel → LLMMiddleware Relationship

Each model can have multiple middleware configurations:

```python
from ai_ops.models import LLMModel, LLMMiddleware

# Get all middleware for a model
model = LLMModel.objects.get(name="gpt-4o")
middlewares = model.middlewares.filter(is_active=True).order_by('priority')

for mw in middlewares:
    print(f"Priority {mw.priority}: {mw.middleware.name}")
    
# Query models using specific middleware
cache_models = LLMModel.objects.filter(
    middlewares__middleware__name="CacheMiddleware",
    middlewares__is_active=True
).distinct()
```

### MiddlewareType → LLMMiddleware Relationship

Each middleware type can be configured for multiple models:

```python
from ai_ops.models import MiddlewareType

# Get all models using a middleware type
cache_type = MiddlewareType.objects.get(name="CacheMiddleware")
configurations = cache_type.middleware_instances.filter(is_active=True)

for config in configurations:
    print(f"Model: {config.llm_model.name}, Config: {config.config}")
```

### LLMModel and Secrets

`LLMModel` integrates with Nautobot's Secrets management:

```python
from ai_ops.models import LLMModel, LLMProvider
from nautobot.extras.models import Secret

# Create a secret
secret = Secret.objects.create(
    name="azure_gpt4_api_key",
    provider="environment-variable",
)

# Reference the secret in LLMModel
azure_provider = LLMProvider.objects.get(name="azure_ai")
model = LLMModel.objects.create(
    name="gpt-4o",
    llm_provider=azure_provider,
    model_secret_key="azure_gpt4_api_key",
    endpoint="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview",
    is_default=True,
    temperature=0.3
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

# Query servers by status
healthy_servers = MCPServer.objects.filter(status__name="Active")
failed_servers = MCPServer.objects.filter(status__name="Failed")
```

## Extras Features

All models support Nautobot's extras features:

- **Custom Links**: Create custom links for models
- **Custom Validators**: Add validation rules
- **Export Templates**: Define export templates
- **GraphQL**: Full GraphQL API support
- **Webhooks**: Receive notifications on changes

### LLMProvider Extras

```python
@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks"
)
class LLMProvider(PrimaryModel):
    ...
```

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

### MiddlewareType Extras

```python
@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks"
)
class MiddlewareType(PrimaryModel):
    ...
```

### LLMMiddleware Extras

```python
@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks"
)
class LLMMiddleware(PrimaryModel):
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

All models include validation logic to ensure data integrity:

### LLMProvider Validation

- Provider name must be one of the supported choices
- Config schema must be valid JSON
- Enabled/disabled state controls provider availability

### LLMModel Validation

- Only one model can be marked as `is_default=True`
- Prevents multiple default models
- Cache TTL must be at least 60 seconds
- Must reference a valid LLM provider

### MiddlewareType Validation

- Middleware name must be valid Python identifier
- Automatically formats name to PascalCase
- Automatically appends "Middleware" suffix if missing
- Name must contain only alphanumeric characters

### LLMMiddleware Validation

- Each middleware type can only be configured once per model (unique_together constraint)
- Priority must be between 1 and 100
- Critical flag determines initialization behavior

### MCPServer Validation

- URL field is required
- Endpoint paths automatically prefixed with `/` if needed
- Ensures proper server configuration

## Best Practices

### LLMProvider Best Practices

1. **Use descriptive names**: Make provider purpose clear
2. **Document configuration**: Provide detailed config_schema documentation
3. **Disable rather than delete**: Use is_enabled flag to temporarily disable providers
4. **Keep documentation_url current**: Link to provider's official docs

### LLMModel Best Practices

1. **Always have a default model**: Mark one model as default for fallback
2. **Use Secrets for API keys**: Never store keys directly in the database
3. **Temperature settings**: Use 0.0-0.3 for deterministic, 0.7-1.0 for creative
4. **Document model purposes**: Use descriptive names and descriptions
5. **Set appropriate cache TTL**: Balance performance vs freshness
6. **Group by provider**: Use consistent naming within provider groups

### MiddlewareType Best Practices

1. **Clear naming**: Use descriptive names that explain functionality
2. **Distinguish custom vs built-in**: Set is_custom flag correctly
3. **Document thoroughly**: Explain what the middleware does
4. **Follow naming convention**: Always end with "Middleware"

### LLMMiddleware Best Practices

1. **Set appropriate priorities**: Lower numbers for foundational middleware (caching, auth)
2. **Use critical flag wisely**: Only for essential middleware
3. **Document configuration**: Comment complex config JSON
4. **Test middleware chains**: Verify middleware execute in correct order
5. **Monitor performance**: Track middleware overhead
6. **Version compatibility**: Keep config_version current with LangChain
7. **Set reasonable TTLs**: Balance cache performance with data freshness

### MCPServer Best Practices

1. **Monitor health status**: Regularly check server health
2. **Use descriptive names**: Clear naming helps management
3. **Set appropriate status**: Use Maintenance status during upgrades
4. **Test health checks**: Verify health check endpoints work correctly
5. **Document server purpose**: Clear descriptions aid troubleshooting
6. **Use internal for trusted**: Mark organization-owned servers as internal

## Common Workflows

### Setting Up a New Provider

```python
from ai_ops.models import LLMProvider, LLMModel, LLMProviderChoice
from nautobot.extras.models import Secret

# 1. Create provider
anthropic_provider = LLMProvider.objects.create(
    name=LLMProviderChoice.ANTHROPIC,
    description="Anthropic Claude models",
    documentation_url="https://docs.anthropic.com/",
    config_schema={"api_base": "https://api.anthropic.com"},
    is_enabled=True
)

# 2. Create secret for API key
api_secret = Secret.objects.create(
    name="anthropic_api_key",
    provider="environment-variable",
)

# 3. Create model
claude_model = LLMModel.objects.create(
    name="claude-3-opus",
    llm_provider=anthropic_provider,
    description="Claude 3 Opus for complex reasoning",
    model_secret_key="anthropic_api_key",
    temperature=0.7,
    cache_ttl=300
)
```

### Configuring Middleware Chain

```python
from ai_ops.models import LLMModel, MiddlewareType, LLMMiddleware

model = LLMModel.objects.get(name="gpt-4o")

# Create middleware types
cache_type = MiddlewareType.objects.get_or_create(
    name="CacheMiddleware",
    defaults={"is_custom": False, "description": "Response caching"}
)[0]

retry_type = MiddlewareType.objects.get_or_create(
    name="RetryMiddleware",
    defaults={"is_custom": False, "description": "Automatic retry with backoff"}
)[0]

logging_type = MiddlewareType.objects.get_or_create(
    name="LoggingMiddleware",
    defaults={"is_custom": False, "description": "Request/response logging"}
)[0]

# Configure middleware chain (execution order: logging -> cache -> retry)
LLMMiddleware.objects.create(
    llm_model=model,
    middleware=logging_type,
    priority=10,
    config={"log_level": "INFO"},
    is_active=True,
    is_critical=False
)

LLMMiddleware.objects.create(
    llm_model=model,
    middleware=cache_type,
    priority=20,
    config={"ttl_seconds": 3600, "max_entries": 10000},
    is_active=True,
    is_critical=False
)

LLMMiddleware.objects.create(
    llm_model=model,
    middleware=retry_type,
    priority=30,
    config={"max_retries": 3, "initial_delay": 1.0},
    is_active=True,
    is_critical=True
)
```

### Managing MCP Servers

```python
from ai_ops.models import MCPServer
from ai_ops.helpers.get_info import get_default_status

# Create internal MCP server
internal_server = MCPServer.objects.create(
    name="nautobot-tools",
    status=get_default_status(),
    protocol="http",
    url="http://mcp-internal:8000",
    mcp_endpoint="/mcp",
    health_check="/health",
    description="Internal Nautobot integration tools",
    mcp_type="internal"
)

# Create external MCP server
external_server = MCPServer.objects.create(
    name="network-monitoring",
    status=get_default_status(),
    protocol="http",
    url="https://monitoring.example.com",
    mcp_endpoint="/mcp/v1",
    health_check="/api/health",
    description="External network monitoring integration",
    mcp_type="external"
)
```

## Related Documentation

- [LLM Providers](../extending.md#extending-llm-providers) - Custom provider development
- [Middleware Development](../extending.md) - Creating custom middleware
- [Helpers](helpers.md) - Helper functions for working with models
- [API](api.md) - REST API documentation
- [Agents](agents.md) - AI agent implementations
- Usage Examples - Practical examples (see `ai_ops/helpers/USAGE_EXAMPLES.md`)
