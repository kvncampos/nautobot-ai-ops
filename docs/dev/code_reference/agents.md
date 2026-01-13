# AI Agents

This page documents the AI agent implementations in the AI Ops App.

## Overview

The AI Ops App uses LangGraph to create stateful AI agents that can interact with users and external systems. The app provides two agent implementations:

- **Multi-MCP Agent**: Production agent supporting multiple MCP servers (recommended)
- **Single-MCP Agent**: Simplified agent for single MCP server scenarios

## Multi-MCP Agent

The Multi-MCP Agent is the production-ready implementation that supports connecting to multiple Model Context Protocol servers simultaneously.

### Key Features

- **Multiple MCP Server Support**: Connect to any number of MCP servers
- **Application-Level Caching**: Caches MCP client and tools for performance
- **Health-Based Server Selection**: Only uses servers with "Healthy" status
- **Automatic Tool Discovery**: Discovers tools from all healthy MCP servers
- **Checkpointing**: Maintains conversation history using Redis
- **Graceful Degradation**: Continues working even if some MCP servers fail

### Architecture

```
User Message → Multi-MCP Agent → LangGraph State Graph
                      ↓
                Azure OpenAI Model
                      ↓
           ┌──────────┴──────────┐
           ↓                      ↓
    MCP Server 1             MCP Server 2
    (Tools A, B, C)          (Tools D, E, F)
           ↓                      ↓
           └──────────┬──────────┘
                      ↓
                  Response
```

### Core Functions

#### get_or_create_mcp_client

```python
async def get_or_create_mcp_client(
    force_refresh: bool = False
) -> Tuple[Optional[MultiServerMCPClient], List]:
    """Get or create MCP client with application-level caching.
    
    Args:
        force_refresh: Force cache refresh even if not expired
        
    Returns:
        Tuple of (client, tools) or (None, []) if no healthy servers
    """
```

**Cache Behavior**:
- Cache TTL: 5 minutes (300 seconds)
- Thread-safe with asyncio lock
- Invalidated on server status changes
- Force refresh available when needed

**Server Selection**:
- Queries for servers with `status="Healthy"`
- Protocol must be `"http"`
- Failed servers automatically excluded

#### warm_mcp_cache

```python
async def warm_mcp_cache():
    """Warm the MCP client cache on application startup."""
```

Called during app initialization to pre-populate the cache. Reduces first-request latency.

#### process_message

```python
async def process_message(
    user_message: str,
    thread_id: str,
    checkpointer=None
) -> str:
    """Process a user message through the multi-MCP agent.
    
    Args:
        user_message: The user's input message
        thread_id: Unique identifier for conversation thread
        checkpointer: LangGraph checkpointer for state persistence
        
    Returns:
        The agent's response as a string
    """
```

**Message Processing Flow**:
1. Get or create cached MCP client
2. Retrieve LLM model configuration
3. Create LangGraph state graph
4. Process message with conversation history
5. Return agent response

### State Management

The agent uses `MessagesState` for conversation tracking:

```python
class MessagesState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[List[BaseMessage], add_messages]
```

The `add_messages` reducer:
- Properly accumulates messages
- Works with checkpointers for persistence
- Maintains conversation context

### Configuration

#### Cache Settings

```python
# Cache TTL: 5 minutes
CACHE_TTL_SECONDS = 300

# Cache structure
_mcp_client_cache = {
    "client": None,
    "tools": None, 
    "timestamp": None,
    "server_count": 0,
}
```

#### HTTP Client Configuration

```python
def httpx_client_factory(**kwargs):
    """Factory for httpx client with SSL verification disabled.
    
    Note: verify=False is intentional for internal MCP servers
    with self-signed certificates.
    """
    return httpx.AsyncClient(verify=False, timeout=30.0, **kwargs)
```

### Usage Example

```python
from ai_ops.agents.multi_mcp_agent import process_message
from ai_ops.checkpointer import get_checkpointer

# Process a message with conversation history
async with get_checkpointer() as checkpointer:
    response = await process_message(
        user_message="What is the status of my network?",
        thread_id="user-session-123",
        checkpointer=checkpointer
    )
    print(response)
```

### Error Handling

The agent handles various error scenarios:

**No Healthy MCP Servers**:
- Returns None for client
- Agent continues without MCP tools
- Logs warning message

**MCP Server Connection Failures**:
- Failed servers excluded from operations
- Cache updated to reflect failures
- Agent uses remaining healthy servers

**LLM API Errors**:
- Errors propagated to caller
- Consider implementing retry logic
- Check Azure OpenAI rate limits

## Single-MCP Agent

The Single-MCP Agent is a simplified implementation for scenarios with only one MCP server.

### Key Features

- **Single Server Focus**: Designed for one MCP server
- **Simpler Configuration**: Less complex than multi-server setup
- **Same LangGraph Architecture**: Uses LangGraph state management
- **Production-Ready**: Suitable for focused use cases

### When to Use

Use the Single-MCP Agent when:
- You have only one MCP server
- Simpler architecture is preferred
- You want explicit server selection
- Testing and development scenarios

Use the Multi-MCP Agent when:
- You have multiple MCP servers
- Dynamic server management needed
- Production deployment with scaling
- Automatic failover desired

## System Prompts

The agents use system prompts to define their behavior. Prompts can be managed via the UI or stored in code files.

### Dynamic System Prompt Loading

The `get_active_prompt()` helper function loads prompts using a fallback hierarchy:

```python
from ai_ops.helpers.get_prompt import get_active_prompt

# Load prompt for a specific model
system_prompt = get_active_prompt(llm_model)
```

**Fallback Hierarchy:**

1. **Model-Assigned Prompt**: If the LLM Model has a `system_prompt` FK with "Approved" status
2. **Global File-Based Prompt**: The first approved prompt with `is_file_based=True`
3. **Code Fallback**: Built-in `get_multi_mcp_system_prompt()` function

### Prompt Helper Functions

The `ai_ops/helpers/get_prompt.py` module provides:

| Function | Description |
|----------|-------------|
| `get_active_prompt(llm_model)` | Main entry point - loads prompt with fallback hierarchy |
| `_load_prompt_content(prompt_obj, model_name)` | Loads content from file or database |
| `_render_prompt_variables(prompt_text, model_name)` | Substitutes runtime variables |
| `_get_fallback_prompt(model_name)` | Returns code-based fallback prompt |

### Template Variables

Runtime variables are substituted in prompt text:

| Variable | Description | Example |
|----------|-------------|---------|
| `{current_date}` | Current date in "Month DD, YYYY" format | January 13, 2026 |
| `{current_month}` | Current month in "Month YYYY" format | January 2026 |
| `{model_name}` | Name of the LLM model | gpt-4o |

### Multi-MCP System Prompt

For file-based prompts, the default implementation is in:

```python
# ai_ops/prompts/multi_mcp_system_prompt.py
SYSTEM_PROMPT = """
You are a helpful AI assistant powered by Azure OpenAI...
"""
```

The multi-MCP prompt:
- Explains multi-server capabilities
- Provides guidance on tool usage
- Sets expectations for responses
- Defines assistant personality

### Single System Prompt

```python
# ai_ops/prompts/system_prompt.py  
SYSTEM_PROMPT = """
You are a helpful AI assistant...
"""
```

Simpler prompt for single-server scenarios.

### Customizing Prompts

Prompts can be customized in two ways:

**Option 1: Via Nautobot UI (Recommended)**

1. Navigate to **AI Platform > LLM > System Prompts**
2. Create a new prompt with your custom instructions
3. Set status to "Approved"
4. Optionally assign to a specific model

**Option 2: Code-Based (for version control)**

1. Create a Python file in `ai_ops/prompts/`
2. Define a `get_<filename>()` function
3. Create a SystemPrompt record with `is_file_based=True`

**Example file-based prompt:**
```python
# ai_ops/prompts/network_specialist.py

def get_network_specialist(model_name: str = "AI Assistant") -> str:
    """Return the network specialist system prompt."""
    return f"""You are {model_name}, a network operations AI assistant.

Your capabilities include:
- Analyzing network configurations
- Troubleshooting connectivity issues
- Suggesting automation improvements

Always follow RFC standards when applicable.
"""
```

### Agent Integration

The `build_agent()` function automatically loads the appropriate prompt:

```python
async def build_agent(llm_model=None, checkpointer=None, provider=None):
    # ... setup code ...
    
    # Get system prompt from database or fallback to code-based prompt
    system_prompt = await sync_to_async(get_active_prompt)(llm_model)
    
    # Create agent with the loaded prompt
    graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )
    return graph
```

## LangGraph Integration

### State Graph Structure

Both agents use LangGraph's StateGraph:

```python
from langgraph.graph import StateGraph

# Create graph
workflow = StateGraph(MessagesState)

# Add nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

# Add edges
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

# Compile with checkpointer
graph = workflow.compile(checkpointer=checkpointer)
```

### Message Flow

1. **START → agent**: Initial message routing
2. **agent → tools** (conditional): If tool calls needed
3. **tools → agent**: Tool results fed back
4. **agent → END**: Final response

### Checkpointing

Conversation state persisted using Redis:

```python
from ai_ops.checkpointer import get_checkpointer

async with get_checkpointer() as checkpointer:
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"configurable": {"thread_id": thread_id}}
    )
```

**Thread IDs**:
- Unique identifier per conversation
- Typically uses session ID
- Enables multi-user support
- Isolates conversations

## MCP Client Integration

### MultiServerMCPClient

The langchain-mcp-adapters library provides MCP integration:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

# Create client
client = MultiServerMCPClient(
    connections={
        "server1": {"url": "https://mcp1.example.com"},
        "server2": {"url": "https://mcp2.example.com"},
    },
    httpx_client_factory=httpx_client_factory
)

# Get tools
async with client:
    tools = await client.get_tools()
```

### Tool Discovery

Tools are automatically discovered from MCP servers:

```python
# Tools include metadata
for tool in tools:
    print(f"Tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Schema: {tool.args_schema}")
```

### Tool Execution

LangGraph automatically handles tool execution:

1. Agent decides to call tool
2. ToolNode executes tool call
3. Results returned to agent
4. Agent incorporates results in response

## Performance Considerations

### Caching Strategy

**Why Cache?**
- MCP client initialization is expensive
- Tool discovery requires network calls
- Multiple users share the same servers

**Cache Invalidation**:
- Time-based (5 minute TTL)
- Manual refresh via `force_refresh=True`
- Server status changes (handled by health checks)

### Async Architecture

All agent operations are async:

```python
# Good - async/await
async def handle_message(message):
    response = await process_message(message, thread_id)
    return response

# Bad - blocking
def handle_message(message):
    # This won't work - process_message is async
    response = process_message(message, thread_id)
```

### Rate Limiting

Consider Azure OpenAI rate limits:

- Monitor API usage
- Implement retry logic
- Use appropriate models for workload
- Request quota increases if needed

## Testing Agents

### Unit Testing

```python
import pytest
from ai_ops.agents.multi_mcp_agent import get_or_create_mcp_client

@pytest.mark.asyncio
async def test_mcp_client_cache():
    # First call - cache miss
    client1, tools1 = await get_or_create_mcp_client()
    
    # Second call - cache hit
    client2, tools2 = await get_or_create_mcp_client()
    
    # Should return same client
    assert client1 is client2
```

### Integration Testing

```python
@pytest.mark.asyncio  
async def test_process_message():
    from ai_ops.agents.multi_mcp_agent import process_message
    from ai_ops.checkpointer import get_checkpointer
    
    async with get_checkpointer() as checkpointer:
        response = await process_message(
            user_message="Hello",
            thread_id="test-thread",
            checkpointer=checkpointer
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
```

## Troubleshooting

### Agent Not Responding

Check these items:

1. **LLM Model Configuration**: Verify default model exists
2. **Azure Connectivity**: Test API endpoint access
3. **Logs**: Review for error messages
4. **Permissions**: Ensure proper API key permissions

### MCP Tools Not Available

Verify:

1. **Server Health**: Check MCP server status
2. **Cache State**: Try force refresh
3. **Network**: Test server URL accessibility
4. **Protocol**: Ensure HTTP protocol selected

### Conversation History Lost

Check:

1. **Redis Connection**: Verify Redis is running
2. **Thread IDs**: Ensure consistent thread_id usage
3. **Checkpointer**: Confirm checkpointer passed correctly
4. **Cleanup Job**: Check if cleanup removed history

## Best Practices

### Agent Usage

1. **Use Multi-MCP Agent**: For production deployments
2. **Implement Error Handling**: Wrap agent calls in try/except
3. **Monitor Performance**: Track response times and errors
4. **Cache Awareness**: Understand caching behavior

### Prompt Engineering

1. **Be Specific**: Clear instructions in system prompts
2. **Provide Context**: Include relevant background
3. **Set Boundaries**: Define what agent should/shouldn't do
4. **Test Thoroughly**: Validate prompt changes

### Production Deployment

1. **Scale Redis**: Ensure adequate Redis capacity
2. **Monitor Rate Limits**: Watch Azure OpenAI usage
3. **Health Checks**: Regular MCP server monitoring
4. **Logging**: Comprehensive logging for debugging

## Related Documentation

- [Models](models.md) - Database models documentation
- [Helpers](helpers.md) - Helper functions
- Checkpointer - Checkpoint configuration (see `ai_ops/checkpointer.py`)
