# Deep Agent Architecture

## Overview

The Deep Agent is an advanced AI agent implementation in ai-ops that adopts the **deepagents framework** from the network-agent project. It provides significant enhancements over the standard agent including semantic caching, tool error retry, subagent delegation, skills system, and cross-conversation memory.

## Key Features

### 1. **Langfuse LLM Observability**
- Full LLM call tracing and monitoring
- Prompt management and versioning
- Token usage and cost tracking
- Performance analytics and debugging
- Web UI at http://localhost:8000
- Toggle-able with `ENABLE_LANGFUSE` environment variable
- Callbacks at graph level (propagate to all child runnables)

### 2. **Semantic Caching with Embeddings** 
- Caches final LLM responses using vector similarity
- Reduces costs by reusing semantically similar answers
- Configurable similarity threshold and TTL
- Only caches final responses (not intermediate planning steps)
- Requires Redis and embedding model

### 3. **Tool Error Retry with Backoff**
- Automatically retries transient tool errors
- Identifies retriable errors (connection, timeout, parsing)
- Configurable retry count and delay
- Returns graceful error messages on failure

### 4. **Subagent Delegation**
- Hierarchical agent system for specialized tasks
- YAML-based subagent configuration
- Each subagent can have its own tools and prompts
- Example subagents: nautobot-query, network-analyzer

### 5. **Skills System**
- Directory-based skills with markdown instructions
- Skills provide domain-specific guidance to the agent
- Example skill: nautobot-search for inventory queries
- Skills loaded automatically from `ai_ops/skills/` directory

### 6. **Cross-Conversation Memory (Store)**
- Redis-based persistent memory across conversations
- Stores user preferences, learned facts, context
- Accessible via `/memories/` path in backend
- Falls back to InMemoryStore if Redis unavailable

### 7. **Connection Pooling**
- Efficient database connection management
- Supports both PostgreSQL and Redis checkpointers
- Automatic Azure AD token refresh for PostgreSQL
- Configurable pool sizes and TTL

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Deep MCP Agent                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  create_deep_agent()                                  │   │
│  │  ├── LLM Model (from Django LLMModel)                │   │
│  │  ├── MCP Tools (from MCPServer with auth)            │   │
│  │  ├── Middleware                                        │   │
│  │  │   ├── SemanticCacheMiddleware (Redis + embeddings)│   │
│  │  │   └── ToolErrorHandlerMiddleware (retry logic)    │   │
│  │  ├── Checkpointer (Redis/PostgreSQL with pooling)    │   │
│  │  ├── Store (Redis/InMemory for cross-conv memory)    │   │
│  │  ├── Backend (CompositeBackend with routing)         │   │
│  │  │   ├── FilesystemBackend (skills, memory files)    │   │
│  │  │   └── StoreBackend (/memories/ → Redis)           │   │
│  │  ├── Skills (from ai_ops/skills/)                     │   │
│  │  ├── Memory (from ai_ops/prompts/)                    │   │
│  │  └── Subagents (from agents/subagents.yaml)          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
ai_ops/
├── agents/
│   ├── multi_mcp_agent.py      # Standard agent (existing)
│   ├── deep_mcp_agent.py        # Deep agent (new)
│   └── subagents.yaml           # Subagent configuration
├── helpers/
│   └── deep_agent/              # Deep agent utilities
│       ├── __init__.py
│       ├── checkpoint_factory.py    # Connection pooling
│       ├── store_factory.py         # Cross-conversation memory
│       ├── embedding_factory.py     # Embedding models
│       ├── middleware.py            # Semantic cache, tool retry
│       ├── mcp_tools_auth.py        # MCP tools with auth
│       ├── agents_loader.py         # Subagent configuration loader
│       └── backend_factory.py       # CompositeBackend setup
├── skills/                      # Skills directory
│   └── nautobot-search/
│       └── SKILL.md             # Skill instructions
└── prompts/                     # System prompts (memory files)
    └── *.md
```

## Configuration

### Environment Variables

```bash
# Langfuse Observability
ENABLE_LANGFUSE=true
LANGFUSE_PUBLIC_KEY=pk-lf-local-dev-key
LANGFUSE_SECRET_KEY=sk-lf-local-dev-secret
LANGFUSE_HOST=http://langfuse-web:3000

# Redis (required for caching, store, checkpointer)
REDIS_URL=redis://redis:6379

# Checkpointer settings
CHECKPOINT_TTL=3600              # 1 hour
CHECKPOINT_POOL_SIZE=10          # Max connections
CHECKPOINT_POOL_MIN_SIZE=2       # Min connections

# Semantic cache settings  
SEMANTIC_CACHE_TTL=3600          # 1 hour
SEMANTIC_CACHE_THRESHOLD=0.05    # Similarity threshold (0-1, lower = stricter)

# Tool retry settings
TOOL_MAX_RETRIES=2               # Retry attempts

# Embedding model (for semantic cache)
EMBEDDING_MODEL=mxbai-embed-large
EMBEDDING_BASE_URL=http://ollama:11434

# Optional: Azure AD for PostgreSQL
DB_AUTH_METHOD=basic             # or "service_principal"
```

### Django Settings

No Django settings changes required. The deep agent uses existing:
- `LLMModel` for LLM configuration
- `MCPServer` for MCP tool discovery
- `SystemPrompt` for system prompts
- Standard Django database settings

## Usage

### Using Deep Agent via API

The deep agent will be available alongside the standard agent. Users can select which agent to use:

```python
# In API views (to be implemented)
from ai_ops.agents import deep_mcp_agent

response = await deep_mcp_agent.process_message(
    user_input="Find device RTR-NYC-01",
    thread_id="conversation_123",
    username="admin",
    user_token="Bearer token_here"
)
```

### Subagent Configuration

Define subagents in `ai_ops/agents/subagents.yaml`:

```yaml
nautobot-query:
  description: "Query Nautobot inventory"
  system_prompt: "You are a Nautobot query specialist..."
  tools:
    - mcp_tools

network-analyzer:
  description: "Analyze network topology"  
  system_prompt: "You are a network analysis specialist..."
  tools:
    - mcp_tools
```

### Creating Skills

Create a skill directory with SKILL.md:

```
ai_ops/skills/my-skill/
└── SKILL.md                    # Skill instructions and examples
```

The SKILL.md file should include:
- Description of the skill
- When to use it
- Available tools
- Best practices
- Examples

## Comparison: Standard Agent vs Deep Agent

| Feature | Standard Agent | Deep Agent |
|---------|---------------|------------|
| **Framework** | `create_agent` (LangChain) | `create_deep_agent` (deepagents) |
| **Caching** | None | Semantic cache with embeddings |
| **Tool Retry** | None | Automatic retry with backoff |
| **Subagents** | No | Yes, YAML-configured |
| **Skills** | No | Yes, directory-based |
| **Memory** | Checkpointer only | Checkpointer + Store |
| **Checkpointer** | MemorySaver (in-memory) | Redis/PostgreSQL with pooling |
| **MCP Tools** | Cached | Fresh per request (for auth) |
| **Backend** | N/A | CompositeBackend with routing |

## When to Use Each Agent

### Use Standard Agent When:
- Simple conversational queries  
- No need for semantic caching
- Basic tool usage without retry logic
- No subagent delegation needed
- Existing functionality is sufficient

### Use Deep Agent When:
- Complex multi-step workflows
- High volume → semantic caching saves costs
- Tools have transient failures → retry helps
- Need specialized subagents
- Want skills-based guidance
- Need cross-conversation memory

## Performance Considerations

### Semantic Cache
- **Cache Hit**: Sub-10ms response (no LLM call)
- **Cache Miss**: Normal LLM latency + cache write
- **Storage**: ~1KB per cached response in Redis
- **Recommendation**: Use for production with high query volume

### Connection Pooling
- **Without Pool**: New connection per request (~100ms overhead)
- **With Pool**: Reuse connection (~1ms overhead)
- **Recommendation**: Always enable in production
Running with Langfuse

Start the development environment with Langfuse:

```bash
cd development
docker-compose -f docker-compose.base.yml \
               -f docker-compose.postgres.yml \
               -f docker-compose.redis.yml \
               -f docker-compose.langfuse.yml up
```

Access Langfuse UI at: http://localhost:8000

**First-time setup:**
1. Open http://localhost:8000
2. Create an account (stored locally)
3. Create a project
4. Copy API keys to `creds.env`

**Optional: Disable Langfuse**
```bash
# In development.env or creds.env
ENABLE_LANGFUSE=false
```

## Troubleshooting

### Langfuse Not Receiving Traces
```bash
# Check Langfuse services are running
docker-compose ps langfuse-web langfuse-worker

# Check connection from agent
# Look for: "✓ Langfuse observability enabled"

# Verify environment variables
echo $LANGFUSE_PUBLIC_KEY
echo $LANGFUSE_SECRET_KEY
echo $LANGFUSE_HOST

# Check Langfuse logs
docker-compose logs langfuse-web
docker-compose logs langfuse-worker
```
### Tool Retry
- **Benefit**: Reduces failure rate for transient errors
- **Cost**: Additional latency on retry (retry_delay * attempts)
- **Recommendation**: Enable with 2-3 retries max

## Troubleshooting

### Semantic Cache Not Working
```bash
# Check Redis connection
redis-cli -h redis ping

# Check cache initialization in logs
# Look for: "Semantic cache initialized successfully"
```

### Subagents Not Loading
```bash
# Verify subagents.yaml exists
ls -la ai_ops/agents/subagents.yaml

# Check logs for subagent loading
# Look for: "Loaded N subagent(s) from..."
```

### MCP Tools Authentication Failures
```bash
# Verify MCPServer status in Django admin
# Check that servers have status="Healthy"

# Verify auth token is being passed
# Look in logs for: "Loaded N tools from N MCP server(s) with fresh auth token"
```

### Connection Pool Errors
```bash
# Check database connectivity
psql -h db -U nautobot -d nautobot

# Verify pool configuration
# CHECKPOINT_POOL_SIZE and CHECKPOINT_POOL_MIN_SIZE in .env
```

## Migration Guide

To migrate from standard agent to deep agent:

1. **Update dependencies**: Run `poetry install` to get deepagents packages
2. **Configure environment**: Add deep agent settings to `.env`
3. **Restart services**: Required for new dependencies
4. **Optional**: Create subagents.yaml and skills
5. **Test**: Try deep agent via API with test queries
6. **Monitor**: Watch logs for caching, retry behavior
7. **Optimize**: Adjust cache threshold and retry settings based on usage

## Future Enhancements

Planned improvements:
- [ ] RAG utilities for vector search (rag_utils.py)
- [ ] Database  migration for LLMModel fields  
- [ ] API endpoint for agent type selection
- [ ] Admin UI enhancements for deep agent config
- [ ] Performance metrics dashboard
- [ ] A/B testing framework for comparing agents

## References

- [deepagents Documentation](https://github.com/langchain-ai/deepagents)
- [LangGraph Checkpointer](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph Store](https://langchain-ai.github.io/langgraph/concepts/memory/)
- [redisvl Documentation](https://redis.io/docs/stack/search/clients/python/)
- network-agent implementation (internal reference)
