# Quick Start Guide

Get the AI Ops App up and running in 5 minutes!

## Prerequisites

- Nautobot 3.0.0+ installed
- Azure OpenAI subscription with a deployed model
- Redis server accessible
- Admin access to Nautobot

## Step 1: Install the App (2 minutes)

```bash
# Install from PyPI
pip install nautobot-ai-ops

# Add to nautobot_config.py
PLUGINS = ["ai_ops"]

# Run migrations
nautobot-server post_upgrade

# Restart services
sudo systemctl restart nautobot nautobot-worker
```

## Step 2: Create a Secret (1 minute)

1. Navigate to **Secrets > Secrets** in Nautobot
2. Click **+ Add**
3. Fill in:
   - **Name**: `azure_gpt4_api_key`
   - **Provider**: Choose your provider (e.g., Environment Variable)
   - **Parameters**: Configure according to provider
4. Click **Create**

## Step 3: Configure LLM Model (1 minute)

1. Navigate to **AI Platform > Configuration > LLM Models**
2. Click **+ Add**
3. Fill in:
   - **Name**: `gpt-4o` (your Azure deployment name)
   - **Description**: `Production GPT-4o model`
   - **Model Secret Key**: `azure_gpt4_api_key`
   - **Azure Endpoint**: `https://your-resource.openai.azure.com/`
   - **API Version**: `2024-02-15-preview`
   - **Is Default**: ☑️ Check this box
   - **Temperature**: `0.3`
4. Click **Create**

## Step 4: Test the Chat (1 minute)

1. Navigate to **AI Platform > Chat & Assistance > AI Chat Assistant**
2. Type a test message: `Hello! Can you help me?`
3. Press **Enter** or click **Send**
4. You should receive a response from the AI!

## Step 5: Optional - Add MCP Server

If you have an MCP server to connect:

1. Navigate to **AI Platform > Configuration > MCP Servers**
2. Click **+ Add**
3. Configure your server details
4. Set **Status** to **Healthy**
5. Click **Create**

The agent will automatically use tools from this server!

## That's It!

You're now ready to use the AI Ops App. Here's what you can do next:

### Explore Features
- Try asking complex questions
- Test multi-turn conversations
- Explore the REST API

### Learn More
- [User Guide](app_overview.md) - Complete feature overview
- [Use Cases](app_use_cases.md) - Real-world examples
- [FAQ](faq.md) - Common questions answered

### Configure More
- Add additional LLM models for different use cases
- Connect more MCP servers for extended capabilities
- Schedule the cleanup job for maintenance

## Quick Troubleshooting

### Chat not responding?

**Check**:
1. Is the LLM Model marked as default? ✓
2. Does the Secret exist and have the correct API key? ✓
3. Is the Azure endpoint accessible? ✓
4. Check Nautobot logs for errors

**Fix**: Navigate to LLM Models, verify configuration, test Azure connectivity

### "No LLMModel instances exist"

**Fix**: Create at least one LLM Model and mark it as default

### MCP Server shows "Failed"

**Fix**: 
1. Verify URL is accessible: `curl https://your-mcp-server/health`
2. Check firewall rules
3. Review MCP server logs

## Environment Variables (Development Only)

For local development, you can skip Steps 2-3 and use environment variables:

```bash
# .env file
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

The app automatically detects LAB environment and uses these variables.

## Production Checklist

Before going to production:

- [ ] Store API keys in Nautobot Secrets (not environment variables)
- [ ] Configure Redis properly in `nautobot_config.py`
- [ ] Set up multiple LLM models for redundancy
- [ ] Configure MCP servers with health checks
- [ ] Schedule the cleanup job (weekly recommended)
- [ ] Test error scenarios (invalid API key, network failures)
- [ ] Review security settings and permissions
- [ ] Set up monitoring for Redis and PostgreSQL

## Getting Help

- **Documentation**: [Full User Guide](app_overview.md)
- **FAQ**: [Frequently Asked Questions](faq.md)
- **Issues**: [GitHub Issues](https://github.com/kvncampos/nautobot-ai-ops/issues)
- **Contact**: See [Authors and Maintainers](app_overview.md#authors-and-maintainers)

## Next Steps

Now that you're up and running:

1. **Explore Use Cases**: Check [Use Cases](app_use_cases.md) for examples
2. **Configure API Access**: See [External Interactions](external_interactions.md)
3. **Learn the Architecture**: Review [Architecture Overview](../dev/architecture.md)
4. **Extend the App**: Read [Extending Guide](../dev/extending.md)

Happy chatting! 🤖
