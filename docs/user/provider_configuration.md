# LLM Provider Configuration Guide

This guide provides comprehensive configuration examples for all supported LLM providers in the AI Ops App. Each provider has unique setup requirements, authentication methods, and configuration options.

## Overview

The AI Ops App supports multiple LLM providers through a flexible multi-provider architecture:

| Provider | Type | Best For | Cost | Setup Complexity |
|----------|------|----------|------|------------------|
| **Ollama** | Local | Development, testing, privacy | Free | Low |
| **OpenAI** | Cloud | Fast responses, general tasks | Pay-per-use | Medium |
| **Azure AI** | Cloud | Enterprise, compliance, SLAs | Pay-per-use | Medium-High |
| **Anthropic** | Cloud | Complex reasoning, analysis | Pay-per-use | Medium |
| **HuggingFace** | Cloud/Self-hosted | Open-source models, flexibility | Varies | Medium |
| **Custom** | Any | Special requirements | Varies | High |

## Provider Configuration Steps

For each provider, you'll need to:

1. **Create Provider** - Define the provider in Nautobot
2. **Create Secret(s)** - Store API keys securely (if required)
3. **Create Model(s)** - Configure specific models for the provider
4. **Test Configuration** - Verify the setup works

## Ollama (Local Development)

Ollama provides free, local LLM inference without cloud dependencies or API costs.

### Prerequisites

- Ollama installed locally or on accessible server
- At least one model pulled (e.g., `ollama pull llama2`)
- Network access to Ollama endpoint

### Installation

```bash
# Install Ollama (Linux/Mac)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama2
ollama pull mistral
ollama pull codellama

# Start Ollama server
ollama serve
```

### Configuration in Nautobot

#### 1. Create Ollama Provider

Navigate to **AI Platform > Configuration > LLM Providers**

```
Name: Ollama
Description: Local Ollama installation for development and testing
Documentation URL: https://ollama.com/
Config Schema:
{
  "base_url": "http://localhost:11434",
  "timeout": 300
}
Is Enabled: ✓
```

**Screenshot Placeholder:**
> _[Screenshot: Ollama Provider Configuration Form]_

#### 2. Create Ollama Models

Navigate to **AI Platform > Configuration > LLM Models**

**Model 1: Llama 2**
```
LLM Provider: Ollama
Name: llama2
Description: Meta Llama 2 - general purpose conversational model
Model Secret Key: (leave empty - no API key needed)
Endpoint: http://localhost:11434
API Version: (leave empty)
Is Default: ✓ (for development)
Temperature: 0.7
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Model 2: Mistral**
```
LLM Provider: Ollama
Name: mistral
Description: Mistral - efficient and capable model
Model Secret Key: (leave empty)
Endpoint: http://localhost:11434
API Version: (leave empty)
Is Default: ☐
Temperature: 0.5
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Model 3: Code Llama**
```
LLM Provider: Ollama
Name: codellama
Description: Code Llama - specialized for code generation
Model Secret Key: (leave empty)
Endpoint: http://localhost:11434
API Version: (leave empty)
Is Default: ☐
Temperature: 0.3
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Screenshot Placeholder:**
> _[Screenshot: Ollama Model Configuration Form]_

### Docker Deployment

For containerized deployments:

```yaml
# docker-compose.yml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0

volumes:
  ollama_data:
```

Update configuration to use `http://ollama:11434` if running in Docker network.

### Best Practices

- ✓ Use Ollama for local development to avoid API costs
- ✓ Pull multiple models for different use cases
- ✓ Increase timeout for larger models
- ✓ Use CPU-only mode on systems without GPU
- ✓ Monitor disk space - models can be large (2-7GB each)

---

## OpenAI

OpenAI provides cloud-based access to GPT-4, GPT-4o, and other advanced models.

### Prerequisites

- OpenAI API account
- API key generated
- Billing configured
- Network access to api.openai.com

### Configuration in Nautobot

#### 1. Create OpenAI Provider

Navigate to **AI Platform > Configuration > LLM Providers**

```
Name: OpenAI
Description: OpenAI GPT models for production workloads
Documentation URL: https://platform.openai.com/docs/
Config Schema:
{
  "organization": "org-xxxxxxxxxx",
  "base_url": "https://api.openai.com/v1"
}
Is Enabled: ✓
```

**Screenshot Placeholder:**
> _[Screenshot: OpenAI Provider Configuration Form]_

#### 2. Create OpenAI Secret

Navigate to **Secrets > Secrets**

```
Name: openai_api_key
Provider: Environment Variable (or Text File, AWS Parameter Store, etc.)
Description: OpenAI API key for GPT models
```

Set the secret value to your OpenAI API key (starts with `sk-`).

**Screenshot Placeholder:**
> _[Screenshot: Secret Creation Form for OpenAI]_

#### 3. Create OpenAI Models

Navigate to **AI Platform > Configuration > LLM Models**

**Model 1: GPT-4o (Optimized)**
```
LLM Provider: OpenAI
Name: gpt-4o
Description: GPT-4 Optimized - fastest GPT-4 class model
Model Secret Key: openai_api_key
Endpoint: https://api.openai.com/v1
API Version: (leave empty)
Is Default: ✓ (for production)
Temperature: 0.3
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Model 2: GPT-4 Turbo**
```
LLM Provider: OpenAI
Name: gpt-4-turbo
Description: GPT-4 Turbo - balanced performance and cost
Model Secret Key: openai_api_key
Endpoint: https://api.openai.com/v1
API Version: (leave empty)
Is Default: ☐
Temperature: 0.3
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Model 3: GPT-3.5 Turbo**
```
LLM Provider: OpenAI
Name: gpt-3.5-turbo
Description: GPT-3.5 Turbo - cost-effective for simple tasks
Model Secret Key: openai_api_key
Endpoint: https://api.openai.com/v1
API Version: (leave empty)
Is Default: ☐
Temperature: 0.5
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Screenshot Placeholder:**
> _[Screenshot: OpenAI Model Configuration Form]_

### Environment Variables (Development)

For development environments, you can use environment variables:

```bash
# .env file
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_ORGANIZATION=org-xxxxxxxxxxxxxxxx
```

### Best Practices

- ✓ Use GPT-4o for most production workloads
- ✓ Use GPT-3.5-turbo for cost-sensitive applications
- ✓ Enable caching middleware to reduce costs
- ✓ Monitor token usage and costs via OpenAI dashboard
- ✓ Set up billing alerts
- ✓ Use organization parameter for team management

### Cost Optimization

- Use middleware caching to reduce redundant API calls
- Set appropriate temperature values (lower = more deterministic, fewer retries)
- Consider GPT-3.5-turbo for simpler queries
- Implement request validation to prevent malformed queries

---

## Azure OpenAI

Azure OpenAI provides enterprise-grade access to OpenAI models with Microsoft SLAs and compliance.

### Prerequisites

- Azure subscription
- Azure OpenAI resource created
- Model deployments configured in Azure
- API key or Azure AD authentication
- Network access to your Azure OpenAI endpoint

### Configuration in Nautobot

#### 1. Create Azure AI Provider

Navigate to **AI Platform > Configuration > LLM Providers**

```
Name: Azure AI
Description: Azure OpenAI Service for enterprise deployments
Documentation URL: https://learn.microsoft.com/en-us/azure/ai-services/openai/
Config Schema:
{
  "api_version": "2024-02-15-preview",
  "base_url": "https://your-resource.openai.azure.com/"
}
Is Enabled: ✓
```

**Screenshot Placeholder:**
> _[Screenshot: Azure AI Provider Configuration Form]_

#### 2. Create Azure OpenAI Secrets

Navigate to **Secrets > Secrets**

Create secrets for each deployment or use one shared key:

```
Name: azure_gpt4o_api_key
Provider: Environment Variable
Description: Azure OpenAI API key for GPT-4o deployment
```

**Screenshot Placeholder:**
> _[Screenshot: Azure Secret Creation Form]_

#### 3. Create Azure OpenAI Models

Navigate to **AI Platform > Configuration > LLM Models**

**Model 1: Azure GPT-4o**
```
LLM Provider: Azure AI
Name: gpt-4o
Description: Azure GPT-4 Optimized deployment for production
Model Secret Key: azure_gpt4o_api_key
Endpoint: https://your-resource.openai.azure.com/
API Version: 2024-02-15-preview
Is Default: ✓
Temperature: 0.3
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Model 2: Azure GPT-4 Turbo**
```
LLM Provider: Azure AI
Name: gpt-4-turbo
Description: Azure GPT-4 Turbo deployment
Model Secret Key: azure_gpt4_turbo_api_key
Endpoint: https://your-resource.openai.azure.com/
API Version: 2024-02-15-preview
Is Default: ☐
Temperature: 0.3
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Screenshot Placeholder:**
> _[Screenshot: Azure Model Configuration Form]_

### Azure Resource Setup

1. **Create Azure OpenAI Resource**:
   ```bash
   az cognitiveservices account create \
     --name your-openai-resource \
     --resource-group your-rg \
     --kind OpenAI \
     --sku S0 \
     --location eastus
   ```

2. **Deploy Models**:
   - Navigate to Azure OpenAI Studio
   - Go to "Deployments"
   - Create deployment for gpt-4o, gpt-4-turbo, etc.
   - Note deployment names (use these as "Name" in Nautobot)

3. **Get API Key**:
   ```bash
   az cognitiveservices account keys list \
     --name your-openai-resource \
     --resource-group your-rg
   ```

### Best Practices

- ✓ Use separate deployments for dev/test/prod environments
- ✓ Enable Azure Private Link for secure access
- ✓ Use Azure Managed Identity instead of API keys when possible
- ✓ Set up Azure Monitor for usage tracking
- ✓ Configure regional deployments for redundancy
- ✓ Keep API versions up to date

### Multi-Region Setup

For high availability, configure multiple regional deployments:

```
# Primary Region (East US)
Name: gpt-4o-eastus
Endpoint: https://eastus-resource.openai.azure.com/

# Secondary Region (West Europe)
Name: gpt-4o-westeu
Endpoint: https://westeu-resource.openai.azure.com/
```

---

## Anthropic

Anthropic provides Claude models known for strong reasoning and large context windows.

### Prerequisites

- Anthropic API account
- API key generated
- Billing configured
- Network access to api.anthropic.com

### Configuration in Nautobot

#### 1. Create Anthropic Provider

Navigate to **AI Platform > Configuration > LLM Providers**

```
Name: Anthropic
Description: Anthropic Claude models for complex reasoning
Documentation URL: https://docs.anthropic.com/
Config Schema:
{
  "api_base": "https://api.anthropic.com",
  "max_tokens_to_sample": 4096
}
Is Enabled: ✓
```

**Screenshot Placeholder:**
> _[Screenshot: Anthropic Provider Configuration Form]_

#### 2. Create Anthropic Secret

Navigate to **Secrets > Secrets**

```
Name: anthropic_api_key
Provider: Environment Variable
Description: Anthropic API key for Claude models
```

Set the secret value to your Anthropic API key.

**Screenshot Placeholder:**
> _[Screenshot: Anthropic Secret Creation Form]_

#### 3. Create Anthropic Models

Navigate to **AI Platform > Configuration > LLM Models**

**Model 1: Claude 3 Opus**
```
LLM Provider: Anthropic
Name: claude-3-opus-20240229
Description: Claude 3 Opus - most capable model for complex reasoning
Model Secret Key: anthropic_api_key
Endpoint: https://api.anthropic.com
API Version: 2023-06-01
Is Default: ☐
Temperature: 0.7
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Model 2: Claude 3 Sonnet**
```
LLM Provider: Anthropic
Name: claude-3-sonnet-20240229
Description: Claude 3 Sonnet - balanced performance and cost
Model Secret Key: anthropic_api_key
Endpoint: https://api.anthropic.com
API Version: 2023-06-01
Is Default: ☐
Temperature: 0.5
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Model 3: Claude 3 Haiku**
```
LLM Provider: Anthropic
Name: claude-3-haiku-20240307
Description: Claude 3 Haiku - fastest and most cost-effective
Model Secret Key: anthropic_api_key
Endpoint: https://api.anthropic.com
API Version: 2023-06-01
Is Default: ☐
Temperature: 0.5
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Screenshot Placeholder:**
> _[Screenshot: Anthropic Model Configuration Form]_

### Best Practices

- ✓ Use Claude 3 Opus for complex analysis and reasoning
- ✓ Use Claude 3 Sonnet for balanced workloads
- ✓ Use Claude 3 Haiku for simple, fast responses
- ✓ Leverage long context windows (200K tokens)
- ✓ Configure appropriate max_tokens_to_sample
- ✓ Monitor API usage via Anthropic console

### Context Window Sizes

| Model | Context Window | Best For |
|-------|----------------|----------|
| Claude 3 Opus | 200K tokens | Long documents, deep analysis |
| Claude 3 Sonnet | 200K tokens | General purpose, balanced |
| Claude 3 Haiku | 200K tokens | Fast responses, simple tasks |

---

## HuggingFace

HuggingFace provides access to thousands of open-source models and inference endpoints.

### Prerequisites

- HuggingFace account
- API token (User Access Token)
- Inference endpoint configured (for Inference API)
- Network access to huggingface.co or your inference endpoint

### Configuration in Nautobot

#### 1. Create HuggingFace Provider

Navigate to **AI Platform > Configuration > LLM Providers**

```
Name: HuggingFace
Description: HuggingFace models and inference endpoints
Documentation URL: https://huggingface.co/docs/
Config Schema:
{
  "huggingfacehub_api_token": "hf_xxxxxxxxxx",
  "repo_id": "default-repo"
}
Is Enabled: ✓
```

**Screenshot Placeholder:**
> _[Screenshot: HuggingFace Provider Configuration Form]_

#### 2. Create HuggingFace Secret

Navigate to **Secrets > Secrets**

```
Name: huggingface_api_token
Provider: Environment Variable
Description: HuggingFace API token for model access
```

**Screenshot Placeholder:**
> _[Screenshot: HuggingFace Secret Creation Form]_

#### 3. Create HuggingFace Models

Navigate to **AI Platform > Configuration > LLM Models**

**Model 1: Llama 2 (via HuggingFace)**
```
LLM Provider: HuggingFace
Name: meta-llama/Llama-2-7b-chat-hf
Description: Meta Llama 2 7B Chat model via HuggingFace
Model Secret Key: huggingface_api_token
Endpoint: https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-chat-hf
API Version: (leave empty)
Is Default: ☐
Temperature: 0.7
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Model 2: Mistral (via HuggingFace)**
```
LLM Provider: HuggingFace
Name: mistralai/Mistral-7B-Instruct-v0.1
Description: Mistral 7B Instruct model
Model Secret Key: huggingface_api_token
Endpoint: https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1
API Version: (leave empty)
Is Default: ☐
Temperature: 0.5
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Model 3: CodeLlama (via HuggingFace)**
```
LLM Provider: HuggingFace
Name: codellama/CodeLlama-7b-Instruct-hf
Description: CodeLlama 7B for code generation
Model Secret Key: huggingface_api_token
Endpoint: https://api-inference.huggingface.co/models/codellama/CodeLlama-7b-Instruct-hf
API Version: (leave empty)
Is Default: ☐
Temperature: 0.3
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Screenshot Placeholder:**
> _[Screenshot: HuggingFace Model Configuration Form]_

### HuggingFace Inference Endpoints

For dedicated inference endpoints:

```
Endpoint: https://xxxxxx.us-east-1.aws.endpoints.huggingface.cloud
```

### Best Practices

- ✓ Use Inference API for quick testing
- ✓ Set up dedicated Inference Endpoints for production
- ✓ Choose models based on your hardware capabilities
- ✓ Consider self-hosting for sensitive data
- ✓ Monitor API rate limits
- ✓ Cache model responses to reduce API calls

### Self-Hosted Option

For self-hosted HuggingFace models:

```bash
# Install text-generation-inference
docker run --gpus all \
  -p 8080:80 \
  -v $PWD/data:/data \
  ghcr.io/huggingface/text-generation-inference:latest \
  --model-id meta-llama/Llama-2-7b-chat-hf
```

Update endpoint to your self-hosted URL.

---

## Custom Provider

For specialized LLM providers or custom implementations not covered by the built-in providers.

### Prerequisites

- Custom LLM endpoint or service
- Authentication mechanism defined
- Compatible API interface

### Configuration in Nautobot

#### 1. Create Custom Provider

Navigate to **AI Platform > Configuration > LLM Providers**

```
Name: Custom
Description: Custom LLM provider implementation
Documentation URL: https://your-docs.example.com
Config Schema:
{
  "base_url": "https://your-custom-llm.example.com",
  "api_version": "v1",
  "custom_headers": {
    "X-Custom-Header": "value"
  }
}
Is Enabled: ✓
```

**Screenshot Placeholder:**
> _[Screenshot: Custom Provider Configuration Form]_

#### 2. Implement Custom Handler

Create a custom handler in your code:

```python
# ai_ops/helpers/llm_providers/custom.py
from ai_ops.helpers.llm_providers.base import BaseLLMProviderHandler

class CustomLLMProviderHandler(BaseLLMProviderHandler):
    """Handler for custom LLM provider."""
    
    def initialize_model(self, model_instance):
        """Initialize the custom LLM."""
        # Your custom initialization logic
        pass
```

#### 3. Create Custom Models

Navigate to **AI Platform > Configuration > LLM Models**

```
LLM Provider: Custom
Name: custom-model-v1
Description: Custom LLM implementation
Model Secret Key: custom_api_key
Endpoint: https://your-custom-llm.example.com/v1
API Version: v1
Is Default: ☐
Temperature: 0.5
Cache TTL: 300
System Prompt: (optional - select a custom prompt or leave empty for default)
```

**Screenshot Placeholder:**
> _[Screenshot: Custom Model Configuration Form]_

### Use Cases for Custom Provider

- Internal LLM deployments
- Research models not available through standard providers
- Specialized fine-tuned models
- Legacy systems integration
- Custom model serving infrastructure

---

## Multi-Provider Strategy

Many organizations use multiple providers for different purposes:

### Development Environment
```
Primary: Ollama (llama2) - Free local testing
Backup: None needed
```

### Staging Environment
```
Primary: OpenAI (gpt-3.5-turbo) - Cost-effective testing
Backup: Azure AI (gpt-3.5-turbo) - Redundancy
```

### Production Environment
```
Primary: Azure AI (gpt-4o) - Enterprise SLAs
Backup: OpenAI (gpt-4o) - Failover
Specialized: Anthropic (claude-3-opus) - Complex reasoning
Code Generation: OpenAI (gpt-4-turbo) - Code-specific tasks
```

### Configuration Example

**Screenshot Placeholder:**
> _[Screenshot: Multi-Provider Dashboard View]_

## Provider Comparison

### Performance

| Provider | Response Time | Context Window | Streaming |
|----------|---------------|----------------|-----------|
| Ollama | Varies (local) | Model-dependent | ✓ |
| OpenAI | Fast | 128K tokens | ✓ |
| Azure AI | Fast | 128K tokens | ✓ |
| Anthropic | Medium | 200K tokens | ✓ |
| HuggingFace | Varies | Model-dependent | Varies |
| Custom | Varies | Implementation-dependent | Varies |

### Pricing (Approximate)

| Provider | Input Cost | Output Cost | Free Tier |
|----------|------------|-------------|-----------|
| Ollama | Free | Free | N/A |
| OpenAI | $0.01-0.10/1K tokens | $0.03-0.30/1K tokens | $5 credit |
| Azure AI | $0.01-0.10/1K tokens | $0.03-0.30/1K tokens | None |
| Anthropic | $0.015-0.075/1K tokens | $0.075-0.225/1K tokens | None |
| HuggingFace | Varies | Varies | Limited |
| Custom | N/A | N/A | N/A |

## Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
systemctl restart ollama
```

### OpenAI API Errors

- **401 Unauthorized**: Check API key in Secret
- **429 Rate Limit**: Reduce request rate or upgrade plan
- **500 Server Error**: Retry with exponential backoff

### Azure Authentication Issues

```bash
# Test Azure endpoint
curl https://your-resource.openai.azure.com/openai/deployments?api-version=2024-02-15-preview \
  -H "api-key: YOUR_API_KEY"
```

### Anthropic Rate Limits

- Check usage tier in Anthropic console
- Implement request queuing
- Use caching middleware

### HuggingFace Model Loading

- Ensure model supports Inference API
- Check if model requires authentication
- Verify endpoint URL format

## Next Steps

After configuring your providers:

1. [Configure Middleware](middleware_configuration.md) - Add caching, logging, retry logic
2. [Set up MCP Servers](mcp_server_configuration.md) - Extend capabilities with tools
3. [Using the App](app_use_cases.md) - Learn how to use different providers effectively
4. [Troubleshooting](faq.md) - Common issues and solutions

## Related Documentation

- [Models Reference](../dev/code_reference/models.md) - Detailed model documentation
- [External Interactions](external_interactions.md) - API integration details
- [Architecture Overview](../dev/architecture.md) - System design and provider architecture
