# Frequently Asked Questions

## General Questions

### What is the AI Ops App?

The AI Ops App is a Nautobot plugin that integrates Large Language Models (LLMs) from Azure OpenAI with Nautobot to provide AI-powered assistance for network operations tasks. It uses the LangChain and LangGraph frameworks to create conversational AI agents that can be extended with Model Context Protocol (MCP) servers.

### What Azure OpenAI models are supported?

The app supports any Azure OpenAI deployment, including:
- GPT-4
- GPT-4o (Optimized)
- GPT-4-turbo
- GPT-3.5-turbo
- Any custom Azure OpenAI deployments

You configure these through the LLM Models interface in Nautobot.

### Do I need Azure OpenAI to use this app?

Yes, the app currently requires an Azure OpenAI service subscription and at least one deployed model. The app does not support OpenAI's public API directly, only Azure OpenAI endpoints.

### What is MCP (Model Context Protocol)?

MCP (Model Context Protocol) is a protocol that allows AI agents to connect to external services and tools. MCP servers provide additional capabilities to the AI agent, such as access to databases, APIs, file systems, or custom business logic.

MCP servers are optional but extend the agent's capabilities beyond basic conversation.

## Installation and Configuration

### How do I get started with the app?

1. Install the app via pip: `pip install ai-ops`
2. Add `"ai_ops"` to the `PLUGINS` list in `nautobot_config.py`
3. Run `nautobot-server post_upgrade`
4. Restart Nautobot services
5. Configure at least one LLM Model through the UI
6. Access the AI Chat Assistant from the menu

See the [Installation Guide](../admin/install.md) for detailed instructions.

### Where should I store Azure OpenAI API keys?

In production environments, always store API keys in Nautobot Secrets:

1. Navigate to **Secrets > Secrets** in Nautobot
2. Create a new Secret with your API key
3. Reference the Secret name in your LLM Model configuration

In LAB/development environments, you can use environment variables, but Secrets are recommended for all environments.

### How do I configure multiple LLM models?

1. Navigate to **AI Platform > Configuration > LLM Models**
2. Create each model with its specific configuration
3. Mark one model as "default" by checking the "Is Default" checkbox
4. The default model is used when no specific model is requested

Different models can be used for different purposes (e.g., fast model for quick queries, detailed model for analysis).

### What Redis configuration is required?

The app uses Redis for conversation checkpointing. Configuration:

- Uses the same Redis instance as Nautobot's cache and Celery
- Requires a separate database number (default: DB 2)
- Configure via environment variables:
  - `NAUTOBOT_REDIS_HOST`
  - `NAUTOBOT_REDIS_PORT`
  - `NAUTOBOT_REDIS_PASSWORD`
  - `LANGGRAPH_REDIS_DB` (defaults to "2")

No additional Redis infrastructure needed beyond what Nautobot already uses.

## Usage Questions

### How do I use the AI Chat Assistant?

1. Navigate to **AI Platform > Chat & Assistance > AI Chat Assistant**
2. Type your question in the input box
3. Press Enter or click Send
4. The AI responds with assistance
5. Continue the conversation - context is maintained

See [Getting Started](app_getting_started.md) for detailed usage instructions.

### Does the AI remember previous messages?

Yes, the app maintains conversation history within a session:

- Each browser session has a unique thread ID
- Messages within that session are remembered
- Context is maintained across multiple turns
- Starting a new session (new browser tab, clearing cookies) starts fresh

### How long is conversation history kept?

Conversation history is stored in Redis with configurable retention:

- By default, checkpoints older than 30 days are eligible for cleanup
- Run the "Cleanup Old Checkpoints" job to remove old conversations
- Schedule the job to run automatically (recommended: daily or weekly)
- Active conversations are never removed

### Can I use the AI agent via API?

Yes, the app provides a REST API endpoint for programmatic access:

```bash
POST /plugins/ai-ops/api/chat/
Content-Type: application/json

{
  "message": "Your question here"
}
```

See [External Interactions](external_interactions.md) for API documentation and examples.

### What permissions are required to use the app?

- `ai_ops.view_llmmodel` - View LLM models
- `ai_ops.add_llmmodel` - Create LLM models
- `ai_ops.change_llmmodel` - Edit LLM models
- `ai_ops.delete_llmmodel` - Delete LLM models
- `ai_ops.view_mcpserver` - View MCP servers (also grants chat access)
- `ai_ops.add_mcpserver` - Create MCP servers
- `ai_ops.change_mcpserver` - Edit MCP servers
- `ai_ops.delete_mcpserver` - Delete MCP servers

Typically, users need `view_mcpserver` permission to access the chat interface.

## MCP Server Questions

### What are MCP servers used for?

MCP servers extend the AI agent's capabilities by providing:

- Additional tools the agent can use
- Access to external systems and APIs
- Custom business logic and workflows
- Integration with internal services

Examples: code execution, file access, database queries, monitoring system integration.

### Are MCP servers required?

No, MCP servers are optional. The AI Chat Assistant works without them, providing conversational assistance based on the LLM's training. MCP servers are only needed if you want to extend the agent with additional capabilities.

### How do I know if an MCP server is working?

Check the MCP server status:

1. Navigate to **AI Platform > Configuration > MCP Servers**
2. Check the **Status** column
3. "Healthy" status means the server is working
4. "Failed" status indicates connection issues

Health checks run automatically. Failed servers are excluded from agent operations.

### Can I use external MCP servers?

Yes, you can configure both:

- **Internal** MCP servers: Hosted within your infrastructure
- **External** MCP servers: Third-party or cloud-hosted services

Set the "MCP Type" field accordingly when creating the server configuration.

### What protocols do MCP servers use?

The app supports:

- **HTTP**: RESTful MCP servers (most common)
- **STDIO**: Process-based MCP servers

Most deployments use HTTP MCP servers.

## Troubleshooting

### The chat interface isn't responding. What should I check?

1. **Verify LLM Model Configuration**:
   - At least one model exists
   - One model is marked as default
   - API credentials are correct

2. **Check Nautobot Logs**:
   - Look for error messages
   - Check for API key or connection issues

3. **Test Azure OpenAI Connectivity**:
   - Verify the endpoint URL is accessible
   - Confirm API key has proper permissions
   - Check for Azure service issues

4. **Verify Permissions**:
   - User has `ai_ops.view_mcpserver` permission

### My MCP server shows "Failed" status. How do I fix it?

1. **Verify URL Accessibility**:
   - Test the URL from the Nautobot server
   - Ensure network connectivity
   - Check firewall rules

2. **Check Health Endpoint**:
   - Verify the health check path is correct
   - Test: `curl https://mcp-server.example.com/health`
   - Health check should return HTTP 200

3. **Review Server Logs**:
   - Check MCP server logs for errors
   - Look for authentication issues
   - Verify server is running

4. **Update Status Manually** (if needed):
   - Edit the MCP server
   - Change status to "Maintenance" while troubleshooting
   - Change back to "Healthy" when fixed

### Conversation history is not persisting. What's wrong?

1. **Check Redis Configuration**:
   - Verify Redis is running
   - Test Redis connectivity
   - Check `LANGGRAPH_REDIS_DB` setting

2. **Review Environment Variables**:
   - `NAUTOBOT_REDIS_HOST`
   - `NAUTOBOT_REDIS_PORT`
   - `NAUTOBOT_REDIS_PASSWORD`

3. **Check Redis Database**:
   - Ensure database number is not in use by another service
   - Default: DB 2 (DB 0: cache, DB 1: Celery)

4. **Review Logs**:
   - Look for checkpoint-related errors
   - Check Redis connection errors

### I'm getting Azure OpenAI rate limit errors. What should I do?

Azure OpenAI has rate limits based on your subscription:

1. **Check Azure Portal**:
   - Review your quota and rate limits
   - Monitor current usage

2. **Request Quota Increase**:
   - Submit a request in Azure Portal
   - Specify your use case and needs

3. **Optimize Usage**:
   - Use lower temperature for deterministic responses (faster)
   - Configure multiple models to distribute load
   - Implement retry logic in custom integrations

4. **Contact Azure Support**:
   - For persistent rate limit issues
   - To discuss enterprise quotas

### The AI is giving incorrect or outdated information. Why?

LLM models have limitations:

1. **Training Data Cutoff**:
   - Models are trained on data up to a certain date
   - They don't have real-time information
   - Check your model's training data date

2. **Hallucinations**:
   - LLMs can generate plausible but incorrect information
   - Always verify critical information
   - Use MCP servers for real-time data access

3. **Context Limitations**:
   - Very long conversations may exceed context window
   - Start a new conversation for fresh context
   - Break complex tasks into smaller conversations

4. **Model Selection**:
   - Different models have different capabilities
   - GPT-4 is generally more accurate than GPT-3.5
   - Adjust model selection based on task requirements

## Performance Questions

### How can I improve response times?

1. **Use Faster Models**:
   - GPT-4-turbo is faster than GPT-4
   - GPT-3.5-turbo is fastest but less capable

2. **Optimize Temperature**:
   - Lower temperature (0.0-0.3) can be faster
   - Higher temperature requires more generation time

3. **Reduce MCP Server Count**:
   - Fewer MCP servers = faster tool discovery
   - Disable unused MCP servers

4. **Monitor Azure Performance**:
   - Check Azure OpenAI service status
   - Review your region selection
   - Consider deploying models in multiple regions

### How much does it cost to run this app?

Costs depend on Azure OpenAI usage:

1. **Azure OpenAI Charges**:
   - Pay per token (input and output)
   - Varies by model (GPT-4 more expensive than GPT-3.5)
   - Check Azure OpenAI pricing page

2. **Infrastructure Costs**:
   - Nautobot hosting (unchanged)
   - Redis (minimal - shared with existing Nautobot Redis)
   - MCP servers (if self-hosted)

3. **Cost Optimization**:
   - Use GPT-3.5-turbo for simple queries
   - Reserve GPT-4 for complex tasks
   - Monitor usage in Azure Portal
   - Set up budget alerts

## Advanced Questions

### Can I customize the AI agent's behavior?

The agent's behavior is defined by system prompts in the code:

- `ai_ops/prompts/multi_mcp_system_prompt.py`
- `ai_ops/prompts/system_prompt.py`

Modifying these requires code changes and app redeployment. See the [Developer Guide](../dev/extending.md) for details.

### Can I use different LLM providers besides Azure OpenAI?

Currently, the app is designed for Azure OpenAI. Supporting other providers would require code modifications:

- Modify `ai_ops/helpers/get_azure_model.py`
- Update model configuration in `ai_ops/models.py`
- Adjust API calls in agent code

This is not currently supported out-of-the-box.

### How is conversation data secured?

Security measures:

1. **API Keys**: Stored in Nautobot Secrets
2. **Conversation Data**: Stored in Redis (encrypted in transit)
3. **Access Control**: Nautobot permission system
4. **Audit Trails**: All actions logged in Nautobot

Review the [External Interactions](external_interactions.md#security-considerations) security section for details.

### Can I deploy the app in an air-gapped environment?

Partial air-gapped deployment is possible:

**Possible**:
- Install app from pip package (downloaded elsewhere)
- Use self-hosted MCP servers
- Internal Redis

**Not Possible Without Workarounds**:
- Requires connectivity to Azure OpenAI endpoints
- Azure OpenAI doesn't support on-premises deployment

**Workarounds**:
- Use Azure Private Link for Azure OpenAI
- Configure proxy for Azure connectivity
- Consider Azure Government Cloud for sensitive environments

### How do I backup conversation history?

Conversation history is stored in Redis:

1. **Redis Backup**:
   - Use Redis persistence (RDB or AOF)
   - Regular Redis backups
   - Include LANGGRAPH_REDIS_DB in backup scope

2. **Cleanup Considerations**:
   - Old conversations removed by cleanup job
   - Backup before running cleanup if history is important

3. **Alternative Storage**:
   - For permanent archival, consider custom development
   - Export conversations to file or database
   - Not built-in to current version

## Getting Help

### Where can I find more documentation?

- [App Overview](app_overview.md) - Feature overview
- [Getting Started](app_getting_started.md) - Setup guide
- [Use Cases](app_use_cases.md) - Usage examples
- [External Interactions](external_interactions.md) - API documentation
- [Developer Guide](../dev/extending.md) - Customization and development

### How do I report bugs or request features?

Open an issue on the GitHub repository:

- **Repository**: [kvncampos/nautobot-ai-ops](https://github.com/kvncampos/nautobot-ai-ops)
- Include version information
- Provide reproduction steps
- Include relevant logs (sanitize sensitive data)

### Where can I get support?

- **Internal Team**: See [Authors and Maintainers](app_overview.md#authors-and-maintainers) for contact information
- **GitHub Issues**: For bugs and feature requests on [GitHub](https://github.com/kvncampos/nautobot-ai-ops/issues)
- **Nautobot Community**: For general Nautobot questions

### Can I contribute to the project?

Yes! Contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

See the [Contributing Guide](../dev/contributing.md) for details.
