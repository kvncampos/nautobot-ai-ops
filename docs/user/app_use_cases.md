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

### Provider Selection

- **Ollama**: Best for local development, no API costs, privacy
- **OpenAI**: Fast responses, good for general tasks
- **Azure AI**: Enterprise features, compliance, SLAs
- **Anthropic**: Strong reasoning, context handling
- **HuggingFace**: Access to open-source models

### Middleware Best Practices

- **Logging**: Always enable for production debugging
- **Caching**: Use for models with API costs to reduce expenses
- **Retry**: Critical for production reliability
- **Validation**: Essential for security and data integrity
- **Priority Order**: Logging (10) → Cache (20) → Retry (30) → Validation (40)

## Limitations and Considerations

- **Model Knowledge Cutoff**: LLM models have a training data cutoff date
- **Context Window**: Very long conversations may exceed context limits
- **Rate Limits**: LLM provider APIs have rate limits that may affect response times
- **Provider Costs**: OpenAI, Azure AI, and Anthropic have per-token costs
- **Ollama Performance**: Local models may be slower than cloud providers
- **Accuracy**: Always verify critical information from AI responses
- **MCP Server Dependency**: Some capabilities require healthy MCP servers
- **Middleware Overhead**: Each middleware adds processing time

## Provider-Specific Notes

### Ollama
- Free and private
- Requires local installation
- Performance depends on hardware
- Good for development and testing

### OpenAI
- Pay-per-use pricing
- Fast response times
- May have availability issues during high demand
- Regular model updates

### Azure AI
- Enterprise SLAs
- Regional deployments
- Microsoft compliance standards
- More expensive than OpenAI direct

### Anthropic
- Strong analytical capabilities
- Longer context windows
- Good for complex reasoning
- Higher cost per token

For additional examples and advanced usage, refer to the [Developer Guide](../dev/extending.md).
