# Helper Modules

This page documents helper functions and utilities in the AI Ops App.

## Azure Model Helper

The `get_azure_model` module provides functions to retrieve and configure Azure OpenAI models.

### get_azure_model()

```python
def get_azure_model(
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    azure_deployment: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    api_version: Optional[str] = None,
    **kwargs
) -> AzureChatOpenAI:
    """Get Azure OpenAI model with environment-aware configuration.
    
    Args:
        model_name: Name of LLMModel to use (production only)
        temperature: Override temperature setting
        azure_deployment: Override deployment name
        azure_endpoint: Override endpoint URL
        api_key: Override API key
        api_version: Override API version
        **kwargs: Additional arguments for AzureChatOpenAI
        
    Returns:
        Configured AzureChatOpenAI instance
    """
```

### Environment Detection

The function automatically detects the environment based on hostname:

```python
def get_environment() -> str:
    """Detect the current environment.
    
    Returns:
        "LAB", "NONPROD", or "PROD"
    """
    hostname = socket.gethostname().lower()
    
    if "nonprod" in hostname:
        return "NONPROD"
    elif "prod" in hostname or "prd" in hostname:
        return "PROD"
    else:
        return "LAB"
```

### LAB Environment

In LAB (local development), uses environment variables:

```python
# Uses these environment variables:
# - AZURE_OPENAI_API_KEY
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_DEPLOYMENT_NAME
# - AZURE_OPENAI_API_VERSION (optional)

model = get_azure_model()  # Uses .env file
```

### Production Environment

In NONPROD/PROD, uses database configuration:

```python
from ai_ops.helpers.get_azure_model import get_azure_model

# Use default model
model = get_azure_model()

# Use specific model by name
model = get_azure_model(model_name="gpt-4-turbo")

# Override temperature
model = get_azure_model(temperature=0.7)

# Pass additional kwargs
model = get_azure_model(max_tokens=2000, request_timeout=30)
```

### Async Version

For async operations, use `get_azure_model_async()`:

```python
async def my_async_function():
    model = await get_azure_model_async()
    result = await model.ainvoke("Hello")
```

### Usage Examples

#### Basic Usage

```python
from ai_ops.helpers.get_azure_model import get_azure_model

# Get default model with default settings
model = get_azure_model()

# Use the model
response = model.invoke("What is Nautobot?")
print(response.content)
```

#### Custom Temperature

```python
# Creative responses
creative_model = get_azure_model(temperature=0.9)

# Deterministic responses  
deterministic_model = get_azure_model(temperature=0.0)
```

#### Specific Model Selection

```python
# Use a specific model from database
fast_model = get_azure_model(model_name="gpt-4-turbo")
detailed_model = get_azure_model(model_name="gpt-4o")
```

#### Complete Override

```python
# Completely manual configuration (bypasses database)
custom_model = get_azure_model(
    azure_deployment="my-deployment",
    azure_endpoint="https://my-resource.openai.azure.com/",
    api_key="my-api-key",
    api_version="2024-02-15-preview",
    temperature=0.5
)
```

#### With Additional Parameters

```python
# Pass AzureChatOpenAI parameters
model = get_azure_model(
    max_tokens=1000,
    request_timeout=60,
    max_retries=3,
    streaming=True
)
```

## Information Helpers

Provides utility functions for retrieving information from Nautobot.

### get_default_status()

```python
def get_default_status() -> Status:
    """Get or create the default 'Active' status.
    
    Returns:
        Status object for 'Active' status
    """
```

Used as default value for StatusField in models.

### Usage Example

```python
from ai_ops.helpers.get_info import get_default_status
from ai_ops.models import MCPServer

# Create MCP server with default status
server = MCPServer.objects.create(
    name="my-server",
    status=get_default_status(),  # Sets to 'Active' by default
    url="https://example.com"
)
```

## LangGraph Serializers

Custom serializers for LangGraph-specific data types.

### CheckpointTupleSerializer

Serializes LangGraph checkpoint tuples for Django REST Framework:

```python
class CheckpointTupleSerializer(serializers.Serializer):
    """Serializer for LangGraph CheckpointTuple objects."""
    
    checkpoint = serializers.JSONField()
    metadata = serializers.JSONField()
    parent_config = serializers.JSONField(required=False)
```

### Usage in API Views

```python
from ai_ops.helpers.langgraph_serializers import CheckpointTupleSerializer

# Serialize checkpoint data
checkpoint_data = {
    "checkpoint": {...},
    "metadata": {...},
    "parent_config": {...}
}

serializer = CheckpointTupleSerializer(data=checkpoint_data)
if serializer.is_valid():
    return Response(serializer.data)
```

## Common Utilities

The `ai_ops/helpers/common/` package provides shared utilities.

### API Handler

Provides utilities for API interactions and HTTP requests.

### Constants

Application-wide constants and configuration values.

### Encoders

Custom JSON encoders for complex data types.

### Enums

Enumeration classes for the application.

### Exceptions

Custom exception classes.

### Helper Functions

General-purpose helper functions.

## Usage Examples

### Complete Workflow Example

```python
from ai_ops.helpers.get_azure_model import get_azure_model
from ai_ops.models import LLMModel, MCPServer
from ai_ops.helpers.get_info import get_default_status

# Create LLM model
model_config = LLMModel.objects.create(
    name="gpt-4o",
    description="Production GPT-4o model",
    model_secret_key="azure_api_key",
    azure_endpoint="https://my-resource.openai.azure.com/",
    api_version="2024-02-15-preview",
    is_default=True,
    temperature=0.3
)

# Create MCP server
mcp_server = MCPServer.objects.create(
    name="my-mcp",
    status=get_default_status(),
    protocol="http",
    url="https://mcp.internal.com",
    mcp_type="internal"
)

# Get Azure model
azure_model = get_azure_model()  # Uses default model from DB

# Use the model
response = azure_model.invoke("Explain Nautobot plugins")
print(response.content)
```

### Error Handling Example

```python
from ai_ops.helpers.get_azure_model import get_azure_model
from ai_ops.models import LLMModel
from django.core.exceptions import ValidationError

try:
    # Try to get model
    model = get_azure_model(model_name="nonexistent-model")
except LLMModel.DoesNotExist:
    print("Model not found, using default")
    model = get_azure_model()
except ValidationError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Async Helper Example

```python
from ai_ops.helpers.get_azure_model import get_azure_model_async
from ai_ops.agents.multi_mcp_agent import process_message
from ai_ops.checkpointer import get_checkpointer

async def chat_workflow(user_message: str, session_id: str):
    """Complete async chat workflow."""
    
    # Get model asynchronously
    model = await get_azure_model_async()
    
    # Process message with conversation history
    async with get_checkpointer() as checkpointer:
        response = await process_message(
            user_message=user_message,
            thread_id=session_id,
            checkpointer=checkpointer
        )
    
    return response

# Usage
import asyncio
response = asyncio.run(chat_workflow(
    "What devices are in my network?",
    "user-123"
))
```

## Environment Variables

### Required Variables (LAB)

```bash
# .env file for local development
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Required Variables (Production)

```bash
# Redis configuration
NAUTOBOT_REDIS_HOST=redis.internal.com
NAUTOBOT_REDIS_PORT=6379
NAUTOBOT_REDIS_PASSWORD=secure-password
LANGGRAPH_REDIS_DB=2

# Environment detection
# (Hostname-based, no variable needed)
```

## Best Practices

### Model Configuration

1. **Use Database in Production**: Store configurations in LLMModel
2. **Use Environment Variables in LAB**: Keep development flexible
3. **Secure API Keys**: Always use Secrets in production
4. **Test Both Paths**: Verify LAB and production configurations

### Error Handling

1. **Wrap Helper Calls**: Use try/except for error handling
2. **Provide Fallbacks**: Default to safe configurations
3. **Log Errors**: Help debugging with clear error messages
4. **Validate Inputs**: Check parameters before using

### Performance

1. **Cache Models**: Reuse model instances when possible
2. **Async When Possible**: Use async versions for async contexts
3. **Monitor API Calls**: Track Azure OpenAI usage
4. **Optimize Temperature**: Lower values can be faster

### Testing

1. **Mock External Calls**: Mock Azure API in tests
2. **Test Both Environments**: LAB and production code paths
3. **Validate Configuration**: Test model configuration retrieval
4. **Handle Failures**: Test error scenarios

## Troubleshooting

### Common Issues

**"No LLMModel instances exist in the database"**
- Create at least one LLM model in the database
- Mark one as default with `is_default=True`

**"model_secret_key is not configured"**
- Set the `model_secret_key` field in LLMModel
- Create the referenced Secret in Nautobot

**Environment variable not found (LAB)**
- Check `.env` file exists
- Verify variable names are correct
- Environment variables should be set in your shell or `.env` file (LAB environments may use python-dotenv for loading)

**Wrong environment detected**
- Check hostname matches environment patterns
- Override by modifying `get_environment()` function
- Verify environment-specific configuration

## Related Documentation

- [Models](models.md) - Database models
- [Agents](agents.md) - AI agent implementations
- Usage Examples - Practical examples (see `ai_ops/helpers/USAGE_EXAMPLES.md`)
- [API](api.md) - REST API documentation
