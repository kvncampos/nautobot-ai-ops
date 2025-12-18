# LLMModel and get_azure_model Usage Examples

## Overview

The `LLMModel` and `get_azure_model` function have been enhanced to support dynamic configuration based on the environment (LAB vs Production).

## LLMModel Configuration

### Model Fields

- **name**: Azure deployment name (e.g., `gpt-4o`, `gpt-4-turbo`)
- **description**: Description of the LLM and its capabilities
- **model_secret_key**: Name of the Secret object in Nautobot containing the API key
- **azure_endpoint**: Azure OpenAI endpoint URL
- **api_version**: Azure OpenAI API version
- **is_default**: Boolean flag to mark the default model
- **temperature**: Temperature setting for the model (0.0 to 2.0)

### Setting Up Models in Production

```python
from ai_ops.models import LLMModel
from nautobot.extras.models import Secret

# Create a secret for the API key
api_secret = Secret.objects.create(
    name="azure_gpt4o_api_key",
    provider="environment-variable",
    # Configure the secret with your API key
)

# Create the default GPT-4o model
gpt4o = LLMModel.objects.create(
    name="gpt-4o",
    description="GPT-4 Optimized for production use",
    model_secret_key="azure_gpt4o_api_key",
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview",
    is_default=True,
    temperature=0.0
)

# Create an alternative model
gpt4_turbo = LLMModel.objects.create(
    name="gpt-4-turbo",
    description="GPT-4 Turbo for faster responses",
    model_secret_key="azure_gpt4_turbo_api_key",
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview",
    is_default=False,
    temperature=0.3
)
```

## Using get_azure_model()

### LAB Environment (Local Development)

In LAB environment, the function automatically uses environment variables from your `.env` file:

```python
from ai_ops.helpers.get_azure_model import get_azure_model

# Uses environment variables automatically
model = get_azure_model()

# Override temperature
model = get_azure_model(temperature=0.7)
```

### Production Environment (NONPROD/PROD)

In production, the function retrieves configuration from the database:

```python
from ai_ops.helpers.get_azure_model import get_azure_model

# Uses the default model from database
model = get_azure_model()

# Use a specific model by name
model = get_azure_model(model_name="gpt-4-turbo")

# Override specific parameters
model = get_azure_model(temperature=0.5)

# Fully manual configuration (bypasses database)
model = get_azure_model(
    azure_deployment="custom-deployment",
    azure_endpoint="https://custom-resource.openai.azure.com/",
    api_key="custom-api-key",
    api_version="2024-02-15-preview",
    temperature=0.0
)

# Pass additional kwargs to AzureChatOpenAI
model = get_azure_model(
    max_tokens=2000,
    request_timeout=30
)
```

## Helper Methods

### Get Default Model

```python
from ai_ops.models import LLMModel

# Get the default model (marked with is_default=True)
default_model = LLMModel.get_default_model()
print(f"Default model: {default_model.name}")
```

### Get All Models Summary

```python
from ai_ops.models import LLMModel

# Get a summary of all available models
models_summary = LLMModel.get_all_models_summary()
for model_info in models_summary:
    print(f"Model: {model_info['name']}")
    print(f"  Description: {model_info['description']}")
    print(f"  Default: {model_info['is_default']}")
    print(f"  Endpoint: {model_info['endpoint']}")
    print(f"  API Version: {model_info['api_version']}")
```

### Get Model Configuration

```python
from ai_ops.models import LLMModel

model = LLMModel.objects.get(name="gpt-4o")

# Get configuration as dictionary
config = model.config_dict
# Returns: {
#     "azure_deployment": "gpt-4o",
#     "azure_endpoint": "https://...",
#     "api_version": "2024-02-15-preview",
#     "temperature": 0.0
# }

# Get API key from Secret
api_key = model.get_api_key()
```

## Environment Detection

The system automatically detects the environment based on the hostname:

- **LAB**: Local development (uses `.env` variables)
- **NONPROD**: Non-production environment (uses database)
- **PROD**: Production environment (uses database)

## Best Practices

1. **Default Model**: Always mark one model as default for seamless operation
2. **Secret Management**: Store API keys in Nautobot Secrets, not in the model directly
3. **Temperature Settings**: Use lower temperatures (0.0-0.3) for deterministic outputs, higher (0.7-1.0) for creative tasks
4. **Error Handling**: Wrap `get_azure_model()` calls in try-except blocks to handle configuration errors gracefully

```python
from ai_ops.helpers.get_azure_model import get_azure_model

try:
    model = get_azure_model()
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Migration from Old Code

### Before
```python
model = get_azure_model()  # Always used .env variables
```

### After (LAB environment - no change needed)
```python
model = get_azure_model()  # Still uses .env variables in LAB
```

### After (Production - new functionality)
```python
# Uses database configuration automatically
model = get_azure_model()

# Or specify a particular model
model = get_azure_model(model_name="gpt-4-turbo")
```

## Validation

The `LLMModel` includes automatic validation:

- Only one model can be marked as default
- `model_secret_key` must be configured before retrieving API key
- All required fields are validated on save

```python
from ai_ops.models import LLMModel
from django.core.exceptions import ValidationError

try:
    model = LLMModel(
        name="test-model",
        is_default=True  # Error if another default exists
    )
    model.full_clean()  # Triggers validation
    model.save()
except ValidationError as e:
    print(f"Validation error: {e}")
```
