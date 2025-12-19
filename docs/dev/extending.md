# Extending the App

This document provides guidance on extending the AI Ops App functionality.

## Before You Begin

Extending the application is welcome! However, it's best to open an issue first to:

- Ensure a PR would be accepted
- Discuss the proposed feature or design
- Get feedback from maintainers
- Avoid duplicate work

## Extension Points

The AI Ops App provides several extension points:

### 1. Custom AI Agents

Create custom agents with specialized behavior:

```python
# ai_ops/agents/custom_agent.py
from langgraph.graph import StateGraph
from ai_ops.helpers.get_azure_model import get_azure_model_async
from ai_ops.agents.multi_mcp_agent import MessagesState

async def create_custom_agent():
    """Create a custom agent with specialized behavior."""
    
    # Get LLM model
    model = await get_azure_model_async(model_name="gpt-4o")
    
    # Define custom system prompt
    CUSTOM_PROMPT = """
    You are a specialized network automation assistant.
    Focus on: ...
    """
    
    # Create state graph
    workflow = StateGraph(MessagesState)
    
    # Add custom nodes and edges
    # ...
    
    return workflow.compile()
```

### 2. Custom MCP Servers

Develop MCP servers to provide domain-specific tools:

```python
# Example MCP server structure
from mcp.server import Server
from mcp.types import Tool

server = Server("my-custom-mcp")

@server.tool()
async def custom_tool(param1: str, param2: int) -> str:
    """Custom tool implementation."""
    # Your logic here
    return result

# Register in Nautobot:
# AI Platform > Configuration > MCP Servers
# Add your server URL
```

### 3. Custom System Prompts

Modify agent behavior by customizing prompts:

```python
# ai_ops/prompts/custom_prompt.py

CUSTOM_SYSTEM_PROMPT = """
You are an AI assistant specialized in [your domain].

Your responsibilities:
1. [Responsibility 1]
2. [Responsibility 2]

Guidelines:
- [Guideline 1]
- [Guideline 2]

Available tools: {tool_names}
"""
```

Then use in your agent:

```python
from ai_ops.prompts.custom_prompt import CUSTOM_SYSTEM_PROMPT

# In agent creation
system_message = CUSTOM_SYSTEM_PROMPT.format(
    tool_names=", ".join(tool.name for tool in tools)
)
```

### 4. Additional Models

Extend with custom database models:

```python
# ai_ops/models.py
from nautobot.apps.models import PrimaryModel

@extras_features("webhooks", "graphql")
class CustomModel(PrimaryModel):
    """Your custom model."""
    
    name = models.CharField(max_length=100)
    # Add your fields
    
    class Meta:
        ordering = ["name"]
```

Remember to create migrations:

```bash
nautobot-server makemigrations ai_ops
nautobot-server migrate ai_ops
```

### 5. Custom Views

Add custom views for new functionality:

```python
# ai_ops/views.py
from nautobot.apps.views import GenericView
from django.shortcuts import render

class CustomView(GenericView):
    """Custom view for specialized functionality."""
    
    template_name = "ai_ops/custom_template.html"
    
    def get(self, request):
        context = {
            # Your context data
        }
        return render(request, self.template_name, context)
```

Register in URLs:

```python
# ai_ops/urls.py
from django.urls import path
from ai_ops.views import CustomView

urlpatterns = [
    path("custom/", CustomView.as_view(), name="custom_view"),
    # ...
]
```

### 6. API Extensions

Extend the REST API with custom endpoints:

```python
# ai_ops/api/views.py
from rest_framework.decorators import action
from rest_framework.response import Response
from nautobot.apps.api import NautobotModelViewSet

class CustomModelViewSet(NautobotModelViewSet):
    """ViewSet with custom actions."""
    
    @action(detail=True, methods=['post'])
    def custom_action(self, request, pk=None):
        """Custom API action."""
        obj = self.get_object()
        # Your logic
        return Response({"status": "success"})
```

### 7. Background Jobs

Add custom Nautobot Jobs:

```python
# ai_ops/jobs/custom_job.py
from nautobot.extras.jobs import Job

class CustomMaintenanceJob(Job):
    """Custom maintenance job."""
    
    class Meta:
        name = "Custom Maintenance"
        description = "Performs custom maintenance tasks"
    
    def run(self):
        """Job implementation."""
        self.logger.info("Starting custom maintenance...")
        # Your logic
        return "Maintenance completed"
```

Register the job:

```python
# ai_ops/jobs/__init__.py
from .custom_job import CustomMaintenanceJob

jobs = [CleanupCheckpointsJob, CustomMaintenanceJob]
register_jobs(*jobs)
```

### 8. Custom Filters

Add filtering capabilities:

```python
# ai_ops/filters.py
import django_filters
from nautobot.apps.filters import NautobotFilterSet

class CustomModelFilterSet(NautobotFilterSet):
    """Custom filters for CustomModel."""
    
    custom_field = django_filters.CharFilter(
        field_name="custom_field",
        lookup_expr="icontains"
    )
    
    class Meta:
        model = CustomModel
        fields = ["name", "custom_field"]
```

### 9. Signal Handlers

React to model events:

```python
# ai_ops/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from ai_ops.models import LLMModel

@receiver(post_save, sender=LLMModel)
def on_llm_model_save(sender, instance, created, **kwargs):
    """React to LLM model changes."""
    if created:
        logger.info(f"New LLM model created: {instance.name}")
    else:
        logger.info(f"LLM model updated: {instance.name}")
    
    # Your logic (e.g., invalidate caches)
```

## Common Extension Patterns

### Pattern 1: Specialized Agent

Create an agent for a specific domain:

```python
# ai_ops/agents/network_agent.py
"""Network-focused AI agent."""

NETWORK_PROMPT = """
You are a network operations assistant specializing in:
- Device configuration
- Troubleshooting connectivity
- Network design recommendations
"""

async def process_network_query(message: str, thread_id: str):
    """Process network-related queries."""
    model = await get_azure_model_async()
    # Custom agent logic
    return response
```

### Pattern 2: Domain-Specific MCP Server

Build an MCP server for your domain:

```python
# external_mcp_server/network_tools.py
from mcp.server import Server

server = Server("network-tools")

@server.tool()
async def check_device_status(device_name: str) -> dict:
    """Check network device status."""
    # Query Nautobot or network devices
    return {
        "device": device_name,
        "status": "active",
        "uptime": "30 days"
    }

@server.tool()
async def get_interface_stats(device_name: str, interface: str) -> dict:
    """Get interface statistics."""
    # Gather stats
    return stats
```

### Pattern 3: Custom Workflow

Create a multi-step workflow:

```python
# ai_ops/workflows/deployment_workflow.py
"""Deployment workflow automation."""

async def automated_deployment_workflow(config: dict):
    """Multi-step deployment workflow."""
    
    # Step 1: Validate configuration
    validation_result = await validate_config(config)
    
    # Step 2: Get AI recommendations
    recommendations = await get_ai_recommendations(config)
    
    # Step 3: Apply changes
    if validation_result["valid"]:
        result = await apply_deployment(config)
    
    return result
```

### Pattern 4: Custom Checkpointer

Implement alternative storage for checkpoints:

```python
# ai_ops/checkpointers/postgres_checkpointer.py
"""PostgreSQL-based checkpointer."""

from langgraph.checkpoint.postgres import PostgresSaver

async def get_postgres_checkpointer():
    """Get PostgreSQL checkpointer."""
    connection_string = get_database_connection_string()
    return PostgresSaver(connection_string)
```

## Development Workflow

### 1. Set Up Development Environment

Follow the [Development Environment](dev_environment.md) guide to set up your environment.

### 2. Create Feature Branch

```bash
git checkout -b feature/my-extension
```

### 3. Implement Extension

Follow the patterns above and existing code style.

### 4. Add Tests

```python
# tests/test_custom_feature.py
import pytest
from ai_ops.custom_module import custom_function

def test_custom_function():
    """Test custom functionality."""
    result = custom_function(param="value")
    assert result == expected_result

@pytest.mark.asyncio
async def test_async_custom_function():
    """Test async functionality."""
    result = await async_custom_function()
    assert result is not None
```

### 5. Update Documentation

Add documentation for your extension:

- Update relevant `.md` files
- Add code examples
- Document configuration
- Include usage instructions

### 6. Run Tests and Linting

```bash
# Run tests
invoke tests

# Run linting
invoke lint

# Format code
invoke format
```

### 7. Submit Pull Request

- Push your branch to GitHub
- Open a pull request
- Describe your changes
- Reference related issues

## Best Practices

### Code Style

1. **Follow PEP 8**: Python code style guidelines
2. **Use Type Hints**: Add type annotations
3. **Write Docstrings**: Document all public functions/classes
4. **Keep It Simple**: KISS principle

### Testing

1. **Write Unit Tests**: Test individual components
2. **Write Integration Tests**: Test component interactions
3. **Test Edge Cases**: Handle error conditions
4. **Mock External Services**: Use mocks for external APIs

### Documentation

1. **Document All Public APIs**: Clear function/class documentation
2. **Provide Examples**: Show how to use features
3. **Update User Docs**: If user-facing changes
4. **Keep It Current**: Update docs with code changes

### Security

1. **Validate Input**: Never trust user input
2. **Use Secrets Properly**: Store credentials securely
3. **Follow Least Privilege**: Minimal permissions
4. **Audit Logging**: Log security-relevant actions

### Performance

1. **Profile First**: Measure before optimizing
2. **Use Caching**: Cache expensive operations
3. **Async When Possible**: Use async for I/O operations
4. **Monitor Resources**: Track memory and CPU usage

## Common Tasks

### Adding a New Field to LLMModel

```python
# 1. Update model
class LLMModel(PrimaryModel):
    # ... existing fields ...
    new_field = models.CharField(max_length=100, blank=True)

# 2. Create migration
# nautobot-server makemigrations ai_ops

# 3. Update forms
class LLMModelForm(forms.NautobotModelForm):
    class Meta:
        fields = "__all__"  # Or add "new_field" explicitly

# 4. Update serializer
class LLMModelSerializer(serializers.NautobotModelSerializer):
    class Meta:
        model = LLMModel
        fields = "__all__"

# 5. Update tests and documentation
```

### Adding a Custom API Endpoint

```python
# ai_ops/api/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def custom_endpoint(request):
    """Custom API endpoint."""
    data = request.data
    # Process request
    result = process_data(data)
    return Response({"result": result})

# ai_ops/api/urls.py
from django.urls import path
from .views import custom_endpoint

urlpatterns = [
    # ... existing patterns ...
    path("custom-endpoint/", custom_endpoint, name="custom_endpoint"),
]
```

### Adding a New Navigation Item

```python
# ai_ops/navigation.py
from nautobot.apps.ui import NavMenuItem

new_item = NavMenuItem(
    link="plugins:ai_ops:custom_view",
    name="Custom Feature",
    permissions=["ai_ops.view_custommodel"],
)

# Add to appropriate group
configuration_items = (
    # ... existing items ...
    new_item,
)
```

## Extending LLM Providers

The AI Ops App supports multiple LLM providers and provides a flexible system for adding support for new providers without modifying core code.

### Supported Built-in Providers

The app includes built-in support for the following providers:

1. **Ollama** - Local open-source LLM runtime (default)
2. **OpenAI** - ChatGPT, GPT-4, and other OpenAI models
3. **Azure AI** - Azure OpenAI deployments
4. **Anthropic** - Claude models
5. **HuggingFace** - Models hosted on HuggingFace Hub

### Understanding the Provider Architecture

The provider system consists of three components:

1. **Provider Model**: Stores provider configuration in the database
2. **Provider Handler**: Implements the actual LLM initialization logic
3. **Registry**: Maps provider names to handler classes for dynamic lookup

### Creating a Custom Provider

To add support for a new LLM provider (e.g., Cohere, Replicate, etc.):

#### Step 1: Create a Provider Handler

Create a new handler class that inherits from `BaseLLMProviderHandler`:

```python
# in your application or plugin
from ai_ops.helpers.providers.base import BaseLLMProviderHandler

class MyCustomProvider(BaseLLMProviderHandler):
    """Handler for MyCustomProvider LLM integration.
    
    Reference: https://docs.langchain.com/oss/python/integrations/chat/my_custom_provider
    """
    
    async def get_chat_model(
        self,
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ):
        """Get a chat model instance for MyCustomProvider.
        
        Args:
            model_name: The model identifier (e.g., 'model-name')
            api_key: API key for authentication
            temperature: Temperature setting (0.0 to 2.0)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            A LangChain chat model instance
            
        Raises:
            ImportError: If required libraries are not installed
            ValueError: If required configuration is missing
        """
        try:
            from langchain_my_custom import ChatMyCustom
        except ImportError as e:
            raise ImportError(
                "langchain-my-custom is required. "
                "Install it with: pip install langchain-my-custom"
            ) from e
        
        # Get required configuration from self.config or environment
        api_endpoint = self.config.get("api_endpoint")
        if not api_endpoint:
            raise ValueError("api_endpoint configuration is required")
        
        if not api_key:
            raise ValueError("API key is required")
        
        # Initialize and return the chat model
        return ChatMyCustom(
            model=model_name,
            api_key=api_key,
            api_endpoint=api_endpoint,
            temperature=temperature,
            **kwargs,
        )
    
    def validate_config(self) -> None:
        """Validate provider configuration (optional).
        
        Called during handler initialization to validate that
        required configuration values are present.
        
        Raises:
            ValueError: If configuration is invalid
        """
        required_fields = ["api_endpoint"]
        missing_fields = [f for f in required_fields if f not in self.config]
        if missing_fields:
            raise ValueError(
                f"Missing required configuration fields: {', '.join(missing_fields)}"
            )
```

#### Step 2: Register the Provider

Register your provider handler at application startup:

```python
# in your app's apps.py or initialization code
from ai_ops.helpers.providers import register_provider
from .my_providers import MyCustomProvider

class MyAppConfig(AppConfig):
    """Configuration for my app."""
    
    def ready(self):
        """Register custom providers when app is ready."""
        register_provider("my_custom", MyCustomProvider)
```

#### Step 3: Create a Provider Instance in the Database

Create the provider configuration through the Nautobot UI or Django admin:

```python
# Via Django shell or management command
from ai_ops.models import Provider

Provider.objects.create(
    name="my_custom",
    description="My Custom LLM Provider",
    documentation_url="https://docs.example.com/llm",
    config_schema={
        "api_endpoint": "https://api.example.com/v1",
        "additional_setting": "value",
    },
    is_enabled=True,
)
```

#### Step 4: Create an LLM Model Using Your Provider

Create an LLM model that uses your new provider:

```python
from ai_ops.models import LLMModel, Provider

provider = Provider.objects.get(name="my_custom")

LLMModel.objects.create(
    name="my-model",
    provider=provider,
    description="My custom model",
    model_secret_key="my-secret-api-key",  # Name of Secret object in Nautobot
    temperature=0.7,
    cache_ttl=300,
)
```

### Provider Configuration Schema

The `config_schema` JSONField in the Provider model stores provider-specific configuration. This allows admins to configure settings without code changes.

**Example configurations:**

```python
# OpenAI
{
    "organization": "my-org-id",
}

# Azure AI
{
    "api_version": "2024-02-15-preview",
    "azure_endpoint": "https://my-resource.openai.azure.com/",
}

# Custom Provider
{
    "api_endpoint": "https://api.example.com/v1",
    "max_retries": 3,
    "timeout_seconds": 30,
}
```

The handler can access these values via `self.config`:

```python
async def get_chat_model(self, ...):
    api_endpoint = self.config.get("api_endpoint")
    max_retries = self.config.get("max_retries", 3)
    timeout = self.config.get("timeout_seconds", 30)
    # ...
```

### Provider Handler Best Practices

1. **Error Handling**: Raise clear, actionable errors with helpful messages
2. **Logging**: Log initialization and errors for debugging
3. **Configuration Validation**: Validate required config in `validate_config()`
4. **Documentation**: Include docstrings and reference links
5. **Async**: Implement `async def get_chat_model()` for proper async/await patterns
6. **Type Hints**: Use Python 3.10+ type hints (e.g., `str | None` not `Optional[str]`)
7. **Secrets Management**: Use the `model_secret_key` Secret object for API keys
8. **Kwargs Support**: Accept `**kwargs` to pass through additional parameters

### Using Custom Providers in Chat

Once registered and configured, custom providers are available for:

1. **Default Model Selection**: Set a model using your custom provider as the default
2. **Admin Provider Override**: Admins can select from enabled providers per-conversation
3. **API Calls**: Use the provider programmatically:

```python
from ai_ops.helpers.get_llm_model import get_llm_model_async

# Use specific model
llm = await get_llm_model_async(model_name="my-model")

# Override provider
llm = await get_llm_model_async(
    model_name="my-model",
    provider="my_custom"
)

# With temperature override
llm = await get_llm_model_async(
    model_name="my-model",
    temperature=0.5
)
```

### Example: Adding Cohere Support

Here's a complete example of adding Cohere provider support:

```python
# my_plugin/providers.py
from ai_ops.helpers.providers.base import BaseLLMProviderHandler
import logging

logger = logging.getLogger(__name__)

class CohereHandler(BaseLLMProviderHandler):
    """Handler for Cohere LLM provider."""
    
    async def get_chat_model(
        self,
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        **kwargs,
    ):
        try:
            from langchain_cohere import ChatCohere
        except ImportError as e:
            raise ImportError(
                "langchain-cohere is required. "
                "Install it with: pip install langchain-cohere"
            ) from e
        
        if not api_key:
            raise ValueError("Cohere API key is required")
        
        logger.info(f"Initializing ChatCohere with model={model_name}")
        
        return ChatCohere(
            model=model_name,
            cohere_api_key=api_key,
            temperature=temperature,
            **kwargs,
        )

# my_plugin/apps.py
from django.apps import AppConfig
from ai_ops.helpers.providers import register_provider

class MyPluginConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'my_plugin'
    
    def ready(self):
        from .providers import CohereHandler
        register_provider("cohere", CohereHandler)
```

Then create the provider in the database:

```python
Provider.objects.create(
    name="cohere",
    description="Cohere language models",
    documentation_url="https://docs.cohere.com/",
    config_schema={},
    is_enabled=True,
)
```

## Resources

- [Nautobot Apps Documentation](https://docs.nautobot.com/projects/core/en/stable/plugins/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Django Documentation](https://docs.djangoproject.com/)

## Getting Help

- **Open an Issue**: For bugs or feature requests
- **GitHub Discussions**: For questions and ideas
- **Code Review**: Request review from maintainers
- **Community**: Join the Nautobot community

## Contributing Guidelines

See [Contributing](contributing.md) for detailed contribution guidelines including:

- Code of conduct
- Development process
- Pull request requirements
- Review process

Thank you for contributing to the AI Ops App!
