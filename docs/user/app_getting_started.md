# Getting Started with the App

This document provides a step-by-step tutorial on how to get the AI Ops App configured and how to use it.

## Install the App

To install the App, please follow the instructions detailed in the [Installation Guide](../admin/install.md).

## First Steps with the App

After installing the app, follow these steps to get started:

### Step 1: Configure an LLM Model

Before you can use the AI Chat Assistant, you need to configure at least one LLM model.

1. Navigate to **AI Platform > Configuration > LLM Models** in the Nautobot menu
2. Click the **+ Add** button to create a new model
3. Fill in the required fields:
   - **Name**: Azure deployment name (e.g., `gpt-4o`, `gpt-4-turbo`)
   - **Description**: A description of the model's purpose and capabilities
   - **Model Secret Key**: Name of the Nautobot Secret containing your Azure OpenAI API key
   - **Azure Endpoint**: Your Azure OpenAI endpoint URL (e.g., `https://your-resource.openai.azure.com/`)
   - **API Version**: API version (default: `2024-02-15-preview`)
   - **Is Default**: Check this box to make this the default model
   - **Temperature**: Set the model temperature (0.0 for deterministic, higher for creative)

4. Click **Create** to save the model

!!! tip
    For your first model, mark it as the default model by checking the "Is Default" checkbox. This ensures the chat assistant knows which model to use.

### Step 2: Create Secrets for API Keys (Production)

For production environments, you should store API keys securely using Nautobot Secrets:

1. Navigate to **Secrets > Secrets** in Nautobot
2. Create a new Secret with your Azure OpenAI API key
3. Name the secret (e.g., `azure_gpt4o_api_key`)
4. Configure the secret provider and value
5. Use this secret name in your LLM Model configuration

!!! note
    In LAB/development environments, the app can use environment variables for API keys instead of Secrets.

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
    MCP servers are optional. The AI Chat Assistant will work without them, but MCP servers can provide additional capabilities like code execution, file access, or integration with external systems.

### Step 4: Use the AI Chat Assistant

Now you're ready to use the AI Chat Assistant:

1. Navigate to **AI Platform > Chat & Assistance > AI Chat Assistant**
2. Type your question or request in the chat input box
3. Press **Enter** or click the **Send** button
4. The AI agent will process your message and respond

The chat interface maintains conversation history, allowing for contextual multi-turn conversations.

### Step 5: Monitor and Maintain

#### Check MCP Server Health

MCP server health is automatically monitored. You can view the status:

1. Go to **AI Platform > Configuration > MCP Servers**
2. Check the **Status** column for each server
3. Servers with "Healthy" status are actively used by the agent
4. Failed servers will be automatically excluded from agent operations

#### Schedule Checkpoint Cleanup

To prevent Redis from accumulating old conversation data:

1. Navigate to **Jobs > Jobs**
2. Find the job **AI Agents > Cleanup Old Checkpoints**
3. Click **Run Job Now** to run it manually, or
4. Click **Schedule Job** to set up automatic recurring execution

!!! tip
    Schedule the cleanup job to run daily or weekly depending on your usage patterns and storage constraints.

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
