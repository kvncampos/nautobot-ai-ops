# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the AI Ops App within your Nautobot environment.

## Prerequisites

- The app is compatible with Nautobot 2.4.0 and higher (tested up to 3.x.x).
- Databases supported: PostgreSQL, MySQL
- Redis instance required for conversation checkpointing and LangGraph integration
- At least one LLM provider configured (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, or Custom)

!!! note
    Please check the [dedicated page](compatibility_matrix.md) for a full compatibility matrix and the deprecation policy.

### Access Requirements

The app requires external access to:

- **LLM Providers**: Depending on your configured provider
  - Azure OpenAI: `*.openai.azure.com` (HTTPS)
  - OpenAI: `api.openai.com` (HTTPS)
  - Anthropic: `api.anthropic.com` (HTTPS)
  - HuggingFace: `api-inference.huggingface.co` (HTTPS)
  - Ollama: Local or network-accessible Ollama instance
  - Custom: Your custom LLM provider endpoint

- **MCP Servers** (if configured): Depends on your MCP server setup
  - HTTP/STDIO based servers as configured

## Install Guide

!!! note
    Apps can be installed from the [Python Package Index](https://pypi.org/) or locally. See the [Nautobot documentation](https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/installation/app-install/) for more details. The pip package name for this app is [`nautobot-ai-ops`](https://pypi.org/project/nautobot-ai-ops/).

The app is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install nautobot-ai-ops
```

To ensure AI Ops is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `nautobot-ai-ops` package:

```shell
echo nautobot-ai-ops >> local_requirements.txt
```

Once installed, the app needs to be enabled in your Nautobot configuration. The following block of code below shows the additional configuration required to be added to your `nautobot_config.py` file:

- Append `"ai_ops"` to the `PLUGINS` list.
- Append the `"ai_ops"` dictionary to the `PLUGINS_CONFIG` dictionary and override any defaults.

```python
# In your nautobot_config.py
PLUGINS = ["ai_ops"]

# PLUGINS_CONFIG = {
#   "ai_ops": {
#     ADD YOUR SETTINGS HERE
#   }
# }
```

Once the Nautobot configuration is updated, run the Post Upgrade command (`nautobot-server post_upgrade`) to run migrations and clear any cache:

```shell
nautobot-server post_upgrade
```

Then restart (if necessary) the Nautobot services which may include:

- Nautobot
- Nautobot Workers
- Nautobot Scheduler

```shell
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```

## App Configuration

The AI Ops App requires minimal configuration in `nautobot_config.py`. The app uses Nautobot's existing infrastructure (PostgreSQL, Redis) and doesn't require additional plugin settings.

```python
# In your nautobot_config.py
PLUGINS = ["ai_ops"]

# PLUGINS_CONFIG = {
#   "ai_ops": {
#     # No additional configuration required
#   }
# }
```

### Database Configuration

The app automatically creates all required tables during the migration process. No manual database configuration is needed beyond Nautobot's standard setup.

### Redis Configuration

The app uses Redis for conversation checkpointing through LangGraph. Ensure Redis is configured in your `nautobot_config.py`:

```python
# Redis configuration (shared with Nautobot)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Celery configuration (uses Redis)
CELERY_BROKER_URL = "redis://localhost:6379/1"
```

### Environment Variables

For production deployments, configure the following environment variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `NAUTOBOT_REDIS_HOST` | Yes | Redis server hostname | `localhost` or `redis.internal.com` |
| `NAUTOBOT_REDIS_PORT` | Yes | Redis server port | `6379` |
| `NAUTOBOT_REDIS_PASSWORD` | No | Redis password (if required) | `your-secure-password` |
| `LANGGRAPH_REDIS_DB` | No | Redis database number for checkpoints | `2` (default) |

### LAB Environment Variables (Development Only)

For local development (LAB environment), you can use environment variables instead of database configuration:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AZURE_OPENAI_API_KEY` | Yes (LAB) | Azure OpenAI API key | `your-api-key` |
| `AZURE_OPENAI_ENDPOINT` | Yes (LAB) | Azure OpenAI endpoint URL | `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Yes (LAB) | Model deployment name | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | No | API version | `2024-02-15-preview` |

!!! note "Production Configuration"
    In production (NONPROD/PROD environments), LLM models should be configured through the Nautobot UI rather than environment variables. See [Post-Installation Configuration](#post-installation-configuration) for configuration steps.

## Post-Installation Configuration

After installing the app, you need to configure the LLM providers and models. The configuration follows this hierarchy:

1. **LLM Providers** - Define available provider types (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, Custom)
2. **LLM Models** - Create specific model deployments using a provider
3. **Middleware Types** (Optional) - Define middleware for request/response processing
4. **LLM Middleware** (Optional) - Apply middleware to specific models
5. **MCP Servers** (Optional) - Configure Model Context Protocol servers for extended capabilities

### 1. Create LLM Provider

First, define which LLM provider you'll use:

1. Navigate to **AI Platform > LLM > LLM Providers**
2. Click **+ Add**
3. Select a provider:
   - **Name**: Choose from Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, or Custom
   - **Description**: Optional description of the provider setup
   - **Documentation URL**: Optional link to provider documentation
   - **Config Schema**: Provider-specific configuration (e.g., Azure API version, base URL)
   - **Is Enabled**: Check to enable this provider

### 2. Create LLM Model

Create at least one LLM Model for your selected provider:

1. Navigate to **AI Platform > LLM > LLM Models**
2. Click **+ Add**
3. Configure:
   - **LLM Provider**: Select the provider created in step 1
   - **Name**: Model name (e.g., `gpt-4o`, `llama2`, or your Azure deployment name)
   - **Description**: Optional description of the model's capabilities
   - **Model Secret Key**: (Production only) Name of Nautobot Secret containing API key
   - **Endpoint**: Model endpoint URL (required for some providers)
   - **API Version**: API version string (e.g., `2024-02-15-preview` for Azure)
   - **Is Default**: Check to make this the default model
   - **Temperature**: Model temperature setting (0.0-2.0, default 0.0)
   - **Cache TTL**: Cache duration in seconds (minimum 60)

### 3. Create Secrets (Production Only)

For production deployments, store API keys securely in Nautobot Secrets:

1. Navigate to **Secrets > Secrets**
2. Click **+ Add**
3. Create a new Secret:
   - **Name**: `azure_gpt4_api_key` (or your chosen name - must match Model Secret Key)
   - **Provider**: Choose appropriate provider
   - **Value**: Your Azure OpenAI API key (or other provider credentials)
4. Reference this Secret name in your LLM Model's **Model Secret Key** field

### 4. Configure Middleware Types (Optional)

To add request/response processing capabilities:

1. Navigate to **AI Platform > Middleware > Middleware Types**
2. Click **+ Add**
3. Define middleware:
   - **Name**: Middleware class name (e.g., `SummarizationMiddleware`, auto-suffixed with "Middleware")
   - **Is Custom**: Check if this is a custom middleware (unchecked for built-in LangChain middleware)
   - **Description**: What this middleware does

### 5. Apply LLM Middleware (Optional)

Apply middleware to specific models:

1. Navigate to **AI Platform > Middleware > LLM Middleware**
2. Click **+ Add**
3. Configure:
   - **LLM Model**: Select the model to apply middleware to
   - **Middleware**: Select the middleware type
   - **Config**: JSON configuration for the middleware
   - **Config Version**: LangChain version compatibility (default: 1.1.0)
   - **Is Active**: Check to enable this middleware
   - **Is Critical**: Check if initialization should fail if this middleware fails
   - **Priority**: Execution order (1-100, lower executes first)
   - **TTL**: Time-to-live for middleware data in seconds

### 6. Configure MCP Servers (Optional)

To extend agent capabilities with Model Context Protocol servers:

1. Navigate to **AI Platform > Middleware > MCP Servers**
2. Click **+ Add**
3. Configure:
   - **Name**: Unique name for the server
   - **Status**: Set to Active (or use other status options)
   - **Protocol**: STDIO or HTTP
   - **URL**: Base URL for the MCP server
   - **MCP Endpoint**: Path to MCP endpoint (default: `/mcp`)
   - **Health Check**: Path to health check endpoint (default: `/health`)
   - **Description**: Optional description
   - **MCP Type**: Internal or External
4. Click the health check button to verify server connectivity

### 7. Schedule Cleanup Job (Recommended)

To prevent Redis checkpoint storage from growing indefinitely:

1. Navigate to **Jobs > Jobs**
2. Find **AI Agents > Cleanup Old Checkpoints**
3. Click **Schedule Job**
4. Configure to run daily or weekly

## Configuration Examples

### Local Development (LAB Environment)

For local development, you can skip database configuration and use environment variables:

```bash
# .env file
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

The app automatically detects LAB environment based on hostname and uses these variables.

### Production (NONPROD/PROD Environment)

For production deployments:
- Configure LLM Providers and Models through the Nautobot UI
- Store API keys in Nautobot Secrets (not environment variables)
- Configure Redis for conversation checkpointing
- Set up multiple models for redundancy

See [Getting Started](../user/app_getting_started.md) for additional configuration instructions and best practices.
