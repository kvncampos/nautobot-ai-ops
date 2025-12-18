# Using the App

This document describes common use-cases and scenarios for the AI Ops App.

## General Usage

The AI Ops App provides an AI-powered chat interface that can assist with various operational tasks. The chat assistant uses Azure OpenAI models (GPT-4, GPT-4o, etc.) and can be extended with MCP servers to provide additional capabilities.

### Basic Chat Interaction

1. Open the **AI Chat Assistant** from the navigation menu
2. Type a natural language question or request
3. The AI agent processes your message and provides a response
4. Continue the conversation - the agent maintains context from previous messages
5. Start a new conversation by refreshing the page or clearing your session

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
    Azure OpenAI language models. It includes fields for the deployment 
    name, API endpoint, API keys (via Secrets), temperature settings, 
    and allows you to designate a default model...
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

### Use Case 6: LLM Model Management

**Scenario**: Managing multiple LLM models for different purposes.

**Workflow**:
1. Create multiple LLM models with different configurations
2. Designate one as the default for general use
3. Use model-specific configurations for specialized tasks
4. Monitor model performance and adjust settings

**Use Cases for Multiple Models**:
- **GPT-4o (default)**: Fast, cost-effective for routine queries
- **GPT-4-turbo**: Quick responses when speed is critical
- **GPT-4 (high-temp)**: Creative tasks requiring varied responses

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

## Limitations and Considerations

- **Model Knowledge Cutoff**: LLM models have a training data cutoff date
- **Context Window**: Very long conversations may exceed context limits
- **Rate Limits**: Azure OpenAI has API rate limits that may affect response times
- **Accuracy**: Always verify critical information from AI responses
- **MCP Server Dependency**: Some capabilities require healthy MCP servers

For additional examples and advanced usage, refer to the [Developer Guide](../dev/extending.md).
