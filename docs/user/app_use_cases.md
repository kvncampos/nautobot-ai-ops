# Using the App

This document describes common use-cases and scenarios for the AI Ops App.

## General Usage

The AI Ops App provides an AI-powered chat interface that can assist with various operational tasks. The chat assistant uses configurable LLM models from multiple providers (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, or custom) and can be extended with MCP servers to provide additional capabilities.

### Basic Chat Interaction

1. Open the **AI Chat Assistant** from the navigation menu
2. Type a natural language question or request
3. The AI agent processes your message through configured middleware and LLM
4. The agent provides a response, with conversation context maintained
5. Continue the conversation - the agent maintains context from previous messages
6. Start a new conversation by refreshing the page or clearing your session

## Use-cases and common workflows

### Use Case 1: Information Retrieval

**Scenario**: You need to understand how a particular feature works in Nautobot or your infrastructure.

**Workflow**:
1. Open the AI Chat Assistant
2. Ask questions like:
   - "How do I configure a new device in Nautobot?"
   - "What are the best practices for IP address management?"
   - "Explain the difference between sites and locations in Nautobot"
3. The AI provides detailed explanations based on its training

**Example Interaction**:
```
User: What is the purpose of the LLMModel in this plugin?
AI: The LLMModel is a database model that stores configurations for 
    Large Language Models from any supported provider (Ollama, OpenAI,
    Azure AI, Anthropic, HuggingFace, or custom). It includes fields 
    for the model name, provider relationship, API endpoint, API keys 
    (via Secrets), temperature settings, cache TTL, and allows you to 
    designate a default model. The model can also have middleware 
    configurations applied for caching, logging, and other processing...
```

### Use Case 2: Troubleshooting Assistance

**Scenario**: You encounter an issue and need guidance on debugging or resolving it.

**Workflow**:
1. Describe the problem to the AI Chat Assistant
2. Provide error messages or symptoms
3. Follow the AI's step-by-step troubleshooting suggestions
4. Ask follow-up questions for clarification

### Use Case 3: Configuration Guidance

**Scenario**: You need help configuring the AI Ops App or understanding configuration options.

**Workflow**:
1. Ask about configuration parameters
2. Request examples of proper configuration
3. Get recommendations for your specific use case

### Use Case 4: MCP Server Integration

**Scenario**: You want to extend the AI agent's capabilities with custom tools via MCP servers.

**Workflow**:
1. Configure MCP servers in the app
2. The agent automatically discovers available tools from healthy MCP servers
3. Ask the agent to perform tasks that require those tools
4. The agent uses MCP tools transparently to accomplish the task

### Use Case 5: Multi-Turn Conversations

**Scenario**: You have a complex task that requires multiple steps and ongoing dialogue.

**Workflow**:
1. Start a conversation with the initial request
2. The AI provides information or asks clarifying questions
3. Continue the conversation with follow-ups and refinements
4. The agent maintains context throughout the session

### Use Case 6: Multi-Provider LLM Management

**Scenario**: Managing multiple LLM providers and models for different purposes.

**Workflow**:
1. Configure LLM providers (e.g., Ollama for development, Azure AI for production)
2. Create multiple LLM models under different providers
3. Designate one model as the default for general use
4. Use provider-specific configurations for specialized tasks

**Use Cases for Multiple Providers**:
- **Ollama (llama2)**: Local development and testing without API costs
- **OpenAI (gpt-4o)**: Fast, production-quality responses
- **Azure AI (gpt-4-turbo)**: Enterprise deployment with Azure compliance
- **Anthropic (claude-3-opus)**: Complex reasoning tasks requiring deep analysis

### Use Case 7: Middleware Configuration

**Scenario**: Applying middleware to models for caching, logging, validation, and retry logic.

**Workflow**:
1. Create middleware types (built-in or custom)
2. Configure middleware instances for specific models
3. Set execution priorities (lower numbers execute first)
4. Enable/disable middleware as needed without deletion

**Common Middleware Chains**:

**Production Model** (gpt-4o):
- Priority 10: LoggingMiddleware (request/response tracking)
- Priority 20: CacheMiddleware (reduce API calls, 1-hour TTL)
- Priority 30: RetryMiddleware (3 retries with exponential backoff)
- Priority 40: ValidationMiddleware (input/output validation)

**Development Model** (ollama:llama2):
- Priority 10: LoggingMiddleware (verbose debugging)
- Priority 20: ValidationMiddleware (input validation only)

### Use Case 8: Provider-Specific Deployments

**Scenario**: Different environments use different LLM providers.

**Deployment Examples**:

**Local Development**:
```python
# Ollama provider for cost-free local testing
Provider: Ollama
Model: llama2
Endpoint: http://localhost:11434
Middleware: LoggingMiddleware only
```

**Non-Production**:
```python
# Azure AI with caching for cost control
Provider: Azure AI
Model: gpt-3.5-turbo
Endpoint: https://nonprod.openai.azure.com/
Middleware: LoggingMiddleware, CacheMiddleware (4-hour TTL)
```

**Production**:
```python
# Azure AI with full middleware stack
Provider: Azure AI
Model: gpt-4o
Endpoint: https://prod.openai.azure.com/
Middleware: LoggingMiddleware, CacheMiddleware, RetryMiddleware, ValidationMiddleware
```

## Tips for Effective Use

### Getting Better Responses

1. **Be Specific**: Provide clear, detailed questions
2. **Provide Context**: Include relevant information about your environment
3. **Use Follow-ups**: Don't hesitate to ask for clarification or more details
4. **Try Different Phrasings**: If you don't get the answer you need, rephrase your question

### Leveraging Conversation History

- The agent remembers previous messages in the same session
- Reference earlier parts of the conversation naturally
- Build on previous responses to dig deeper into topics
- Start fresh by clearing your session when changing topics

### Provider Selection Guide

Different providers excel at different tasks:

#### Development & Testing
**Ollama (Local)**
- ✓ Best for: Local development, testing without API costs
- ✓ No API keys needed, completely free
- ✓ Privacy - data never leaves your network
- ✓ Good for: Development, experimentation, learning
- ✗ Performance depends on local hardware
- ✗ Limited to available open-source models

**Example Use Cases:**
```
- Testing new prompts and configurations
- Learning how the AI assistant works
- Development without internet connectivity
- Privacy-sensitive environments
```

#### General Production Use
**OpenAI**
- ✓ Best for: Fast responses, general-purpose tasks
- ✓ Excellent for code generation and explanations
- ✓ Regular model updates with improvements
- ✓ Good documentation and community support
- $ Pay-per-use pricing
- ⚠️ May have availability issues during high demand

**Example Use Cases:**
```
- General network queries and troubleshooting
- Configuration generation and validation
- Documentation assistance
- Quick operational questions
```

#### Enterprise Production
**Azure AI**
- ✓ Best for: Enterprise deployments with SLAs
- ✓ Microsoft compliance standards (HIPAA, SOC 2, etc.)
- ✓ Regional deployments for data residency
- ✓ Integration with Azure ecosystem
- ✓ Private endpoints and VNet integration
- $ Higher cost than direct OpenAI
- ⚠️ Requires Azure subscription and setup

**Example Use Cases:**
```
- Regulated industry deployments
- Enterprise-scale production workloads
- Integration with Azure services
- Multi-region high-availability deployments
```

#### Complex Reasoning
**Anthropic (Claude)**
- ✓ Best for: Complex analysis and reasoning tasks
- ✓ Exceptional context understanding
- ✓ Largest context window (200K tokens)
- ✓ Strong analytical capabilities
- $ Higher cost per token
- ⚠️ May be slower than other providers

**Example Use Cases:**
```
- Complex troubleshooting scenarios
- Multi-step operational procedures
- Analyzing large configuration files
- Strategic planning and recommendations
```

#### Open Source & Specialized
**HuggingFace**
- ✓ Best for: Access to specialized open-source models
- ✓ Self-hosting options for data control
- ✓ Wide variety of models for specific tasks
- ✓ Cost-effective with dedicated endpoints
- ⚠️ Variable quality across models
- ⚠️ May require more setup

**Example Use Cases:**
```
- Domain-specific fine-tuned models
- Self-hosted deployments for compliance
- Experimentation with cutting-edge models
- Cost optimization with smaller models
```

### Middleware Best Practices

- **Logging**: Always enable for production debugging
- **Caching**: Use for models with API costs to reduce expenses
  - Set longer TTL (4-24 hours) for stable data
  - Set shorter TTL (5-60 minutes) for dynamic data
- **Retry**: Critical for production reliability
  - Enable for cloud providers (transient failures)
  - Not needed for local Ollama
- **Validation**: Essential for security and data integrity
- **PII Redaction**: Required for sensitive data handling
- **Priority Order**: Logging (10) → Validation (15) → Cache (20) → Retry (30)

### Cost Optimization Strategies

#### For OpenAI and Azure AI
```
1. Enable CacheMiddleware with appropriate TTL
2. Use lower temperature for deterministic responses (fewer retries)
3. Implement request validation to prevent malformed queries
4. Monitor token usage via middleware
5. Consider GPT-3.5-turbo for simpler queries
6. Set up billing alerts in provider console
```

#### For Anthropic
```
1. Leverage large context window to avoid multiple requests
2. Use Claude Haiku for simple, fast responses
3. Reserve Claude Opus for complex reasoning tasks
4. Enable caching for repeated analysis
```

#### Mixed Strategy
```
Development: Ollama (free)
Staging: OpenAI GPT-3.5-turbo (cost-effective)
Production: Azure AI GPT-4o (enterprise)
Complex Analysis: Anthropic Claude 3 Opus (specialized)
```

## Limitations and Considerations

- **Model Knowledge Cutoff**: LLM models have a training data cutoff date
- **Context Window**: Very long conversations may exceed context limits
- **Rate Limits**: LLM provider APIs have rate limits that may affect response times
- **Provider Costs**: OpenAI, Azure AI, and Anthropic have per-token costs
- **Ollama Performance**: Local models may be slower than cloud providers
- **Accuracy**: Always verify critical information from AI responses
- **MCP Server Dependency**: Some capabilities require healthy MCP servers
- **Middleware Overhead**: Each middleware adds processing time
- **Network Latency**: Cloud providers require internet connectivity

## Provider-Specific Notes

### Ollama
- ✓ Free and private
- ✓ No rate limits
- ✗ Requires local installation and sufficient hardware
- ✗ Performance depends on CPU/GPU
- ✗ Limited to available open-source models
- **Best Models**: llama2 (general), mistral (efficient), codellama (code)

### OpenAI
- ✓ Fast response times
- ✓ Latest models (GPT-4o, GPT-4-turbo)
- ✗ Pay-per-use pricing ($0.03-0.30/1K tokens)
- ✗ May have availability issues during peak times
- ✗ Regular model deprecations
- **Best Models**: gpt-4o (balanced), gpt-4-turbo (speed), gpt-3.5-turbo (cost)

### Azure AI
- ✓ Enterprise SLAs (99.9% uptime)
- ✓ Regional deployments
- ✓ Microsoft compliance standards
- ✓ Private Link support
- ✗ More expensive than OpenAI direct
- ✗ Requires Azure subscription
- ✗ Model availability varies by region
- **Best Models**: gpt-4o (production), gpt-4-turbo (balanced)

### Anthropic
- ✓ Strong analytical capabilities
- ✓ Longer context windows (200K tokens)
- ✓ Good for complex reasoning
- ✗ Higher cost per token ($0.015-0.225/1K tokens)
- ✗ Smaller model selection
- ✗ May be slower for simple queries
- **Best Models**: claude-3-opus (complex), claude-3-sonnet (balanced), claude-3-haiku (fast)

### HuggingFace
- ✓ Wide model selection
- ✓ Self-hosting options
- ✓ Free tier available
- ✗ Variable quality across models
- ✗ May require technical expertise
- ✗ Inference API rate limits
- **Best Models**: Llama 2 (general), Mistral (efficient), CodeLlama (code)

## Real-World Usage Examples

### Example 1: Daily Operations (Development)
```
Environment: Development
Provider: Ollama
Model: llama2
Middleware: LoggingMiddleware only
Cost: $0/month

Usage:
- Testing new configurations
- Learning the system
- Experimenting with prompts
- No API costs
```

### Example 2: Production Operations (Enterprise)
```
Environment: Production
Provider: Azure AI
Model: gpt-4o
Middleware: LoggingMiddleware, CacheMiddleware, RetryMiddleware, ValidationMiddleware
Cost: ~$500/month (10K requests, avg 1K tokens)

Usage:
- Troubleshooting network issues
- Configuration assistance
- Documentation queries
- Compliance requirements met
```

### Example 3: Complex Analysis (Specialized)
```
Environment: Production
Provider: Anthropic
Model: claude-3-opus
Middleware: LoggingMiddleware, RetryMiddleware
Cost: ~$200/month (2K requests, avg 2K tokens)

Usage:
- Root cause analysis
- Strategic planning
- Policy recommendations
- Large document analysis
```

### Example 4: Multi-Provider Strategy
```
Development: Ollama llama2 (free)
Testing: OpenAI gpt-3.5-turbo (cost-effective)
Production Simple: OpenAI gpt-4o (fast)
Production Complex: Anthropic claude-3-opus (reasoning)
Total Cost: ~$600/month

Benefit: Right tool for each job, cost optimization
```

For detailed configuration instructions, refer to the [Provider Configuration Guide](provider_configuration.md), [Middleware Configuration Guide](middleware_configuration.md), and [MCP Server Configuration Guide](mcp_server_configuration.md).
