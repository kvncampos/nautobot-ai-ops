# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.

!!! warning "Developer Note - Remove Me!"
    Detailed instructions on installing the App. You will need to update this section based on any additional dependencies or prerequisites.

## Prerequisites

- The app is compatible with Nautobot 3.0.0 and higher.
- Databases supported: PostgreSQL, MySQL

!!! note
    Please check the [dedicated page](compatibility_matrix.md) for a full compatibility matrix and the deprecation policy.

### Access Requirements

!!! warning "Developer Note - Remove Me!"
    What external systems (if any) it needs access to in order to work.

## Install Guide

!!! note
    Apps can be installed from the [Python Package Index](https://pypi.org/) or locally. See the [Nautobot documentation](https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/installation/app-install/) for more details. The pip package name for this app is [`ai-ops`](https://pypi.org/project/ai-ops/).

The app is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install ai-ops
```

To ensure AI Ops is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `ai-ops` package:

```shell
echo ai-ops >> local_requirements.txt
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

### Redis Configuration

The app uses Redis for conversation checkpointing. Ensure Redis is configured in your `nautobot_config.py`:

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

# Celery (uses Redis)
CELERY_BROKER_URL = "redis://localhost:6379/1"
```

### Environment Variables

The following environment variables should be set:

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
    In production (NONPROD/PROD environments), LLM models should be configured through the Nautobot UI rather than environment variables. See [Getting Started](../user/app_getting_started.md) for configuration steps.

## Post-Installation Configuration

After installing the app, you need to configure:

### 1. Create LLM Models

At least one LLM Model must be configured:

1. Navigate to **AI Platform > Configuration > LLM Models**
2. Click **+ Add**
3. Configure:
   - **Name**: Azure deployment name (e.g., `gpt-4o`)
   - **Model Secret Key**: Reference to Nautobot Secret with API key
   - **Azure Endpoint**: Your Azure OpenAI endpoint
   - **Is Default**: Mark one model as default
   - **Temperature**: Set model temperature (0.0-2.0)

### 2. Create Secrets (Production)

In production, store API keys in Nautobot Secrets:

1. Navigate to **Secrets > Secrets**
2. Create a new Secret:
   - **Name**: `azure_gpt4_api_key` (or your chosen name)
   - **Provider**: Choose appropriate provider
   - **Value**: Your Azure OpenAI API key
3. Reference this Secret name in your LLM Model configuration

### 3. Configure MCP Servers (Optional)

To extend agent capabilities:

1. Navigate to **AI Platform > Configuration > MCP Servers**
2. Create MCP server configurations as needed
3. Ensure servers have "Healthy" status to be used by agents

### 4. Schedule Cleanup Job (Recommended)

To prevent Redis from growing indefinitely:

1. Navigate to **Jobs > Jobs**
2. Find **AI Agents > Cleanup Old Checkpoints**
3. Click **Schedule Job**
4. Configure to run daily or weekly

See [Getting Started](../user/app_getting_started.md) for detailed configuration instructions.
