# Getting Started with the App

This document provides a step-by-step tutorial on how to get the AI Ops App configured and how to use it.

## Install the App

To install the App, please follow the instructions detailed in the [Installation Guide](../admin/install.md).

## First Steps with the App

After installing the app, follow these steps to get started:

### Step 1: Configure an LLM Provider and Model

Before you can use the AI Chat Assistant, you need to configure at least one LLM provider and model.

**Quick Start Options:**

**Option A: Local Development with Ollama (Recommended for testing)**
1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull a model: `ollama pull llama2`
3. Navigate to **AI Platform > Configuration > LLM Providers** and create an Ollama provider
4. Navigate to **AI Platform > Configuration > LLM Models** and create a model using the Ollama provider
5. No API keys needed - completely free!

**Option B: Production with Azure OpenAI**
1. Create Azure OpenAI resource and deploy a model
2. Navigate to **AI Platform > Configuration > LLM Providers** and create an Azure AI provider
3. Create a Secret in Nautobot with your Azure API key
4. Navigate to **AI Platform > Configuration > LLM Models** and create a model using the Azure AI provider

**Option C: Production with OpenAI**
1. Get an OpenAI API key from https://platform.openai.com
2. Navigate to **AI Platform > Configuration > LLM Providers** and create an OpenAI provider
3. Create a Secret in Nautobot with your OpenAI API key
4. Navigate to **AI Platform > Configuration > LLM Models** and create a model using the OpenAI provider

For comprehensive configuration instructions for all providers (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, Custom), see the **[LLM Provider Configuration Guide](provider_configuration.md)**.

### Basic Model Configuration

Navigate to **AI Platform > Configuration > LLM Models** and create a model:

   - **LLM Provider**: Select the provider (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, Custom)
   - **Name**: Model name (e.g., `gpt-4o`, `llama2`, `claude-3-opus-20240229`)
   - **Description**: A description of the model's purpose and capabilities
   - **Model Secret Key**: Name of the Nautobot Secret containing the API key (leave empty for Ollama)
   - **Endpoint**: LLM endpoint URL (varies by provider)
   - **API Version**: API version if required (e.g., `2024-02-15-preview` for Azure)
   - **Is Default**: Check this box to make this the default model
   - **Temperature**: Set the model temperature (0.0 for deterministic, 0.7-1.0 for creative)
   - **Cache TTL**: Cache time-to-live in seconds (default: 300)

!!! tip
    For your first model, mark it as the default model by checking the "Is Default" checkbox. This ensures the chat assistant knows which model to use.

!!! info "Provider-Specific Examples"
    - **Ollama**: Name: `llama2`, Endpoint: `http://localhost:11434`, No secret needed
    - **OpenAI**: Name: `gpt-4o`, Endpoint: `https://api.openai.com/v1`, Secret: `openai_api_key`
    - **Azure AI**: Name: `gpt-4o`, Endpoint: `https://your-resource.openai.azure.com/`, Secret: `azure_api_key`
    - **Anthropic**: Name: `claude-3-opus-20240229`, Endpoint: `https://api.anthropic.com`, Secret: `anthropic_api_key`

**For comprehensive provider configuration with detailed examples, see the [LLM Provider Configuration Guide](provider_configuration.md).**

### Step 2: Create Secrets for API Keys (if needed)

For cloud-based providers (OpenAI, Azure AI, Anthropic, HuggingFace), you should store API keys securely using Nautobot Secrets:

1. Navigate to **Secrets > Secrets** in Nautobot
2. Create a new Secret with your provider's API key
3. Name the secret descriptively (e.g., `openai_api_key`, `azure_gpt4o_api_key`, `anthropic_api_key`)
4. Configure the secret provider and value
5. Use this secret name in your LLM Model configuration

!!! note
    - **Ollama** does not require API keys or secrets
    - In LAB/development environments, the app can use environment variables for API keys instead of Secrets
    - For production, always use Nautobot Secrets for better security

### Step 3: Configure MCP Servers (Optional)

MCP (Model Context Protocol) servers extend the capabilities of your AI agent by providing additional tools and context:

1. Navigate to **AI Platform > Configuration > MCP Servers**
2. Click **+ Add** to create a new server
3. Fill in the fields:
   - **Name**: Unique identifier for the server
   - **Status**: Select "Healthy" to enable the server
   - **Protocol**: Choose "HTTP" or "STDIO"
   - **URL**: Server endpoint URL
   - **Health Check**: Health check endpoint (default: `/health`)
   - **Description**: Purpose of this MCP server
   - **MCP Type**: "Internal" for internal servers, "External" for third-party

4. Click **Create** to save the server

!!! info
    MCP servers are **optional**. The AI Chat Assistant works with just a default LLM model configured. MCP servers provide additional capabilities like code execution, file access, or integration with external systems when needed.

**For comprehensive MCP server configuration with implementation examples, see the [MCP Server Configuration Guide](mcp_server_configuration.md).**

### Step 4: Configure Middleware (Optional)

Middleware can be applied to LLM models to add capabilities like caching, logging, retries, PII redaction, or custom processing.

!!! tip
    Start without middleware for your first setup. Add middleware later as you identify specific needs:
    - **CacheMiddleware**: Reduce API costs by caching responses
    - **RetryMiddleware**: Handle transient failures automatically
    - **LoggingMiddleware**: Track requests for debugging and monitoring
    - **ValidationMiddleware**: Security validation of inputs/outputs
    - **PIIRedactionMiddleware**: Detect and redact sensitive information

**For comprehensive middleware configuration with examples, see the [Middleware Configuration Guide](middleware_configuration.md).**

#### Adding Middleware to a Model

1. Navigate to **AI Platform > Configuration > LLM Middleware**
2. Click **+ Add** to create a new middleware instance
3. Fill in the required fields:
   - **LLM Model**: Select the model to apply this middleware to
   - **Middleware Type**: Choose from available middleware types (PIIMiddleware, RetryMiddleware, etc.)
   - **Priority**: Set execution order (lower numbers execute first, default: 100)
   - **Enabled**: Check to enable the middleware
   - **Config**: JSON configuration for the middleware

4. Click **Create** to save the middleware

#### Understanding the Config Field

When you select a **Middleware Type**, an **Example Config** appears showing all available configuration parameters:

```json
{
  "parameter1": "default_value",
  "parameter2": false,
  "parameter3": 10
}
```

**You can:**

- Leave **Config** empty to use default values
- Copy the example and modify only the parameters you need
- Start with an empty object `{}` and add only the parameters you want to customize

!!! tip "Configuration Best Practices"
    - The example config shows **all available parameters** for reference
    - You don't need to specify parameters if you're happy with the defaults
    - Only include parameters you want to override
    - Invalid JSON will be rejected with a helpful error message

#### Common Middleware Examples

**PIIMiddleware** - Redact sensitive information:
```json
{
  "pii_type": "email",
  "strategy": "redact",
  "detector": "builtin",
  "apply_to_input": true,
  "apply_to_output": false,
  "apply_to_tool_results": false
}
```

**ModelRetryMiddleware** - Add retry logic:
```json
{
  "max_attempts": 3,
  "initial_interval": 1.0,
  "backoff_factor": 2.0,
  "max_interval": 10.0
}
```

**SummarizationMiddleware** - Automatic conversation summarization:
```json
{
  "token_limit": 1000,
  "summary_model": "gpt-4o-mini"
}
```

#### Middleware Execution Order

Middleware executes in priority order (lowest to highest):

1. Priority 10: Input validation
2. Priority 20: PII redaction
3. Priority 30: Logging
4. Priority 40: Retry logic

Multiple middleware instances can have the same priority.

### Step 5: Configure System Prompts (Optional)

System prompts define the behavior and persona of your AI agent. The app provides flexible prompt management:

1. Navigate to **AI Platform > LLM > System Prompts**
2. Click **+ Add** to create a new prompt
3. Fill in the fields:
   - **Name**: Unique identifier (e.g., "Network Specialist", "Code Assistant")
   - **Prompt Text**: The system prompt content with optional variables
   - **Status**: Set to "Approved" to activate
   - **Is File Based**: Check if loading from a Python file

**Template Variables**: Use these placeholders in your prompts:
- `{current_date}` - Current date (e.g., "January 13, 2026")
- `{current_month}` - Current month (e.g., "January 2026")
- `{model_name}` - Name of the LLM model

**Example Prompt**:
```
You are {model_name}, a network operations AI assistant.
Today is {current_date}.

Your role is to help engineers with:
- Network troubleshooting
- Configuration assistance
- Automation guidance
```

!!! tip "Prompt Assignment"
    You can assign a specific prompt to an LLM Model by editing the model and selecting from the **System Prompt** dropdown. If no prompt is assigned, the agent uses a default prompt.

**For comprehensive prompt configuration with best practices, see the [System Prompt Configuration Guide](system_prompt_configuration.md).**

### Step 6: Use the AI Chat Assistant

Now you're ready to use the AI Chat Assistant:

1. Navigate to **AI Platform > Chat & Assistance > AI Chat Assistant**
2. Type your question or request in the chat input box
3. Press **Enter** or click the **Send** button
4. The AI agent will process your message and respond

**Chat Session Behavior:**

- **Conversation History**: The chat maintains context within a session for multi-turn conversations
- **Session Expiry**: Chat sessions automatically expire after a period of inactivity (default: 5 minutes)
- **Storage**: Messages are stored in your browser's localStorage for continuity across page refreshes
- **Privacy**: Chat history is session-based and automatically cleaned up - nothing is permanently stored
- **Manual Clear**: Click the "Clear History" button to immediately clear the conversation

!!! tip "Session TTL Configuration"
    Administrators can adjust the chat session timeout in `nautobot_config.py`:
    ```python
    PLUGINS_CONFIG = {
        "ai_ops": {
            "chat_session_ttl_minutes": 10,  # Extend to 10 minutes
        }
    }
    ```

### Step 7: Monitor and Maintain

#### Check MCP Server Health

MCP server health is automatically monitored. You can view the status:

1. Go to **AI Platform > Configuration > MCP Servers**
2. Check the **Status** column for each server
3. Servers with "Healthy" status are actively used by the agent
4. Failed servers will be automatically excluded from agent operations

#### Automatic Cleanup Jobs

The app automatically schedules background jobs to maintain system health:

**Chat Session Cleanup** (Runs every 5 minutes)
- Removes expired chat sessions from memory based on configured TTL
- Prevents memory accumulation from inactive sessions
- No user action required - fully automatic

**Checkpoint Cleanup** (Runs hourly)
- Cleans up old Redis checkpoints if using persistent storage
- Only applies when migrated from MemorySaver to Redis/PostgreSQL
- Configurable retention period (default: 7 days)

You can view and manually trigger these jobs:

1. Navigate to **Jobs > Jobs**
2. Look for jobs under **AI Agents**:
   - **Cleanup Expired Chat Sessions**
   - **Cleanup Old Checkpoints**
3. Click **Run Job Now** to run manually
4. Jobs are automatically scheduled - no additional configuration needed

## What are the next steps?

After completing the initial setup, you can:

- **Explore Use Cases**: Check out the [Use Cases](app_use_cases.md) section for examples of what you can do with the AI Chat Assistant
- **Configure Multiple Models**: Set up different models for different use cases (e.g., fast model for quick responses, larger model for complex analysis)
- **Integrate MCP Servers**: Add MCP servers to extend agent capabilities with custom tools and integrations
- **Review API Documentation**: Learn about the REST API in [External Interactions](external_interactions.md)
- **Customize Prompts**: Advanced users can modify system prompts in the code (see Developer Guide)

## Troubleshooting

### Common Issues

**Chat not responding?**

- Verify that at least one LLM Model exists and is marked as default
- Check that the API key Secret is configured correctly
- Review Nautobot logs for error messages

**MCP Server showing as Failed?**

- Verify the server URL is accessible from the Nautobot instance
- Check the health check endpoint returns a successful response
- Review the MCP server logs for connection issues

**Conversation history not persisting?**

- Ensure Redis is properly configured in `nautobot_config.py`
- Verify the Redis connection using the checkpointer configuration
- Check that LANGGRAPH_REDIS_DB environment variable is set

For more help, check the [FAQ](faq.md) or contact your administrator.
