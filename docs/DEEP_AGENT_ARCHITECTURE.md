# Deep Agent Architecture

## Overview

The Deep Agent is an advanced AI agent implementation in ai-ops built on the **deepagents framework**. It provides significant enhancements over the standard agent including tool error retry with backoff, Redis-backed tool result caching, subagent delegation, a skills system, cross-conversation memory, and Langfuse LLM observability.

## Key Features

### 1. **Langfuse LLM Observability**

- Full LLM call tracing and monitoring (every prompt, token count, latency)
- Tool invocation spans with inputs and outputs
- Subagent delegation traces
- Anthropic prompt-cache metrics (`cache_creation_input_tokens`, `cache_read_input_tokens`)
- Web UI at `http://localhost:8000` (when running the Langfuse compose stack)
- Opt-in only: set `ENABLE_LANGFUSE=true` to activate
- Callbacks attached at graph level and propagated to all child runnables

### 2. **Tool Error Retry with Backoff** (`ToolErrorHandlerMiddleware`)

- Automatically retries transient tool errors (connection resets, timeouts, SSE errors, JSON parse failures)
- Configurable retry count (`max_retries`) and fixed delay (`retry_delay`)
- Returns a graceful `ToolMessage` with `status="error"` on final failure so the agent can recover without crashing

### 3. **Tool Result Caching** (`ToolResultCacheMiddleware`)

- Redis-backed per-tool result cache keyed on tool name + argument hash
- Configurable per-tool TTL; write operations (POST/PUT/DELETE/PATCH) are never cached
- Shared Redis connection pool across all per-request middleware instances to prevent connection leaks
- Silently disables itself when Redis is unavailable — no configuration changes required
- Default config caches both Nautobot MCP tools:
    - `mcp_nautobot_openapi_api_request_schema` — 600 s TTL
    - `mcp_nautobot_dynamic_api_request` — 60 s TTL (read-only only)

### 4. **Subagent Delegation**

- Hierarchical agent system for specialized tasks
- YAML-based subagent configuration (`ai_ops/agents/subagents.yaml`)
- Each subagent can receive its own injected tools (e.g. `mcp_tools`)
- Example subagent: `nautobot-query` for Nautobot inventory lookups

### 5. **Skills System**

- Directory-based skills with Markdown instruction files
- Skills provide domain-specific guidance to the agent at inference time
- Example skill: `nautobot-search` for structured inventory queries
- Skills loaded automatically from `ai_ops/skills/` via `FilesystemBackend`

### 6. **Cross-Conversation Memory (Store)**

- Persistent memory across conversations, stored under `/memories/` via `StoreBackend`
- Saves user preferences, learned facts, and session context
- Backend selection (controlled by `STORE_BACKEND`):
    - **Auto (default)**: PostgreSQL first → Redis fallback → InMemoryStore last resort
    - **Explicit `postgres`**: Always use `AsyncPostgresStore`
    - **Explicit `redis`**: Always use `AsyncRedisStore` (requires Redis Stack / RediSearch)
    - **Explicit `memory`**: `InMemoryStore` — data is lost on restart (dev/test only)

### 7. **Checkpointing with Connection Pooling**

- Short-term per-thread conversation state stored via LangGraph checkpointer
- Redis (`AsyncRedisSaver`) tried first when `CHECKPOINT_REDIS_URL` or `REDIS_URL` is set
- PostgreSQL (`AsyncPostgresSaver` + `psycopg_pool.AsyncConnectionPool`) used as fallback or primary
- Checkpointers are cached globally per agent name; stale connections are detected via the event loop's `is_closed()` flag and recreated automatically

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Deep MCP Agent                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  create_deep_agent()                                  │   │
│  │  ├── LLM Model (from Django LLMModel)                │   │
│  │  ├── MCP Tools (from MCPServer with fresh auth)      │   │
│  │  ├── Middleware (loaded fresh from DB per request)    │   │
│  │  │   ├── ToolResultCacheMiddleware (Redis cache)     │   │
│  │  │   └── ToolErrorHandlerMiddleware (retry logic)    │   │
│  │  ├── Checkpointer (Redis → PostgreSQL with pooling)  │   │
│  │  ├── Store (PostgreSQL → Redis → InMemory)           │   │
│  │  ├── Backend (CompositeBackend with routing)         │   │
│  │  │   ├── FilesystemBackend (skills, memory files)    │   │
│  │  │   └── StoreBackend (/memories/ → Store)           │   │
│  │  ├── Skills (from ai_ops/skills/)                     │   │
│  │  ├── Memory (from ai_ops/memory/*.md)                │   │
│  │  └── Subagents (from agents/subagents.yaml)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Langfuse callback attached via graph.with_config()          │
│  (propagates to all LLM calls, tools, and subagents)         │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
ai_ops/
├── agents/
│   ├── multi_mcp_agent.py       # Standard agent (LangChain create_agent)
│   ├── deep_mcp_agent.py        # Deep agent (deepagents framework)
│   └── subagents.yaml           # Subagent configuration
├── helpers/
│   └── deep_agent/              # Deep agent utilities
│       ├── __init__.py          # Public API exports
│       ├── _utils.py            # Shared env/loop/Redis/Postgres helpers
│       ├── agents_loader.py     # Loads subagents from YAML
│       ├── backend_factory.py   # CompositeBackend (Filesystem + StoreBackend)
│       ├── checkpoint_factory.py # Checkpointer: Redis → PostgreSQL (pooled, cached)
│       ├── mcp_tools_auth.py    # MCP tools with Bearer auth
│       ├── middleware.py        # ToolErrorHandlerMiddleware + ToolResultCacheMiddleware
│       └── store_factory.py     # Store: PostgreSQL → Redis → InMemory
├── memory/                      # Domain knowledge markdown files
│   ├── nautobot_api_patterns.md
│   ├── nautobot_data_model.md
│   ├── network_concepts.md
│   ├── network_troubleshooting.md
│   └── operational_runbooks.md
├── skills/                      # Skills directory
│   └── nautobot-search/
│       └── SKILL.md             # Skill instructions
└── prompts/                     # System prompt templates
    └── *.md
```

## State Management

### Short-Term Memory (Checkpointer)

The checkpointer stores per-thread conversation history (the `messages` list). It is keyed by `thread_id` and scoped to a single conversation session.

**Backend selection order:**

| Condition | Checkpointer used |
|---|---|
| `CHECKPOINT_REDIS_URL` or `REDIS_URL` is set | `AsyncRedisSaver` (tried first) |
| Redis unavailable / not configured | `AsyncPostgresSaver` (connection-pooled) |

**Important notes:**

- Redis must use `db=0` — RediSearch index creation fails on any other logical database.
- Use `CHECKPOINT_REDIS_URL` to configure the checkpointer's Redis; `DATABASE_URL` is reserved for the Langfuse server.
- Use `CHECKPOINT_DB_URL` to point the checkpointer at a specific PostgreSQL DSN (defaults to Django's `DATABASES["default"]`).

**TTL / pool configuration:**

```bash
CHECKPOINT_TTL=3600          # Checkpoint expiry in seconds (default: 1 hour)
CHECKPOINT_POOL_SIZE=10      # Maximum PostgreSQL connections in pool
CHECKPOINT_POOL_MIN_SIZE=2   # Minimum PostgreSQL connections in pool
```

### Long-Term Memory (Store)

The store persists facts, preferences, and cross-session context under the `/memories/` path. It survives conversation boundaries.

**Backend selection (`STORE_BACKEND` env var):**

| `STORE_BACKEND` | Backend | Notes |
|---|---|---|
| *(unset — auto)* | PostgreSQL → Redis → InMemory | Tries each in order |
| `postgres` | `AsyncPostgresStore` | Persistent; no Redis modules needed |
| `redis` | `AsyncRedisStore` | Requires Redis Stack with RediSearch |
| `memory` | `InMemoryStore` | Data lost on restart — dev/test only |

**Why PostgreSQL is preferred in auto-mode:** PostgreSQL requires no special Redis modules (unlike `AsyncRedisStore`, which requires Redis Stack's RediSearch), and keeps long-term memory storage separate from the Redis checkpointer to avoid resource contention.

**Configuration:**

```bash
STORE_BACKEND=postgres       # Optional explicit override
STORE_DB_URL=postgresql://nautobot:password@db:5432/nautobot  # Optional; defaults to Django DB
STORE_REDIS_URL=redis://:password@redis:6379/0                 # Optional; defaults to REDIS_URL
```

### Event-Loop Recreation

Django creates a **new** event loop per async request and closes it when the response is sent. To handle this efficiently:

- Checkpointers and stores are cached globally per agent name.
- On each request, the factory checks `stored_loop.is_closed()` rather than comparing loop identity.
- When the stored loop is closed (previous request finished), the cached connection is recreated automatically.
- This avoids both "Event loop is closed" `RuntimeError`s and unnecessary connection churn on every request.

## Middleware

Middleware classes implement `AgentMiddleware` from `langchain.agents.middleware` and are loaded fresh from the database on every request to prevent state leaks.

### `ToolErrorHandlerMiddleware`

Wraps every tool call with retry logic for transient errors.

```python
from ai_ops.helpers.deep_agent.middleware import ToolErrorHandlerMiddleware

# Default: 2 retries, 1 second delay
middleware = [ToolErrorHandlerMiddleware()]

# Custom: 3 retries, 2 second delay
middleware = [ToolErrorHandlerMiddleware(max_retries=3, retry_delay=2.0)]
```

**Retriable error keywords:** `eof while parsing`, `invalid json`, `validationerror`, `connection`, `timeout`, `broken pipe`, `sse`, `streamable_http`

**Env var fallback** (when no DB middleware is configured):

```bash
TOOL_MAX_RETRIES=2   # Default retry count
```

### `ToolResultCacheMiddleware`

Caches tool call results in Redis to reduce redundant MCP server round-trips.

```python
from ai_ops.helpers.deep_agent.middleware import ToolResultCacheMiddleware

# Default config — caches both Nautobot MCP tools
middleware = [ToolResultCacheMiddleware()]

# Custom per-tool configuration
middleware = [ToolResultCacheMiddleware(tool_cache_config={
    "mcp_nautobot_openapi_api_request_schema": {"ttl": 600},
    "mcp_nautobot_dynamic_api_request": {
        "ttl": 60,
        "skip_methods": ["POST", "PUT", "DELETE", "PATCH"],
    },
})]
```

**Redis URL resolution:** `TOOL_CACHE_REDIS_URL` → `REDIS_URL` → disabled (caching silently turns off if neither is set)

## Configuration

### Environment Variables

```bash
# ── Langfuse Observability ────────────────────────────────────────────────────
ENABLE_LANGFUSE=true                          # Set to true to enable (default: false)
LANGFUSE_PUBLIC_KEY=pk-lf-your-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-here
LANGFUSE_HOST=http://langfuse-web:3000        # Internal Docker network address

# ── Shared Redis fallback (used by all subsystems when specific URL not set) ──
REDIS_URL=redis://:password@redis:6379/0      # Must be db=0 for RediSearch

# ── Checkpointer ──────────────────────────────────────────────────────────────
CHECKPOINT_REDIS_URL=redis://:password@redis:6379/0  # Preferred over REDIS_URL
CHECKPOINT_DB_URL=postgresql://nautobot:pw@db:5432/nautobot  # Falls back to Django DB
CHECKPOINT_TTL=3600              # Checkpoint expiry in seconds (default: 1 hour)
CHECKPOINT_POOL_SIZE=10          # Max PostgreSQL connections in pool
CHECKPOINT_POOL_MIN_SIZE=2       # Min PostgreSQL connections in pool

# ── Store (cross-conversation memory) ────────────────────────────────────────
STORE_BACKEND=                   # Unset = auto (postgres→redis→memory)
                                  # Or: postgres | redis | memory
STORE_DB_URL=postgresql://nautobot:pw@db:5432/nautobot   # Optional; defaults to Django DB
STORE_REDIS_URL=redis://:password@redis:6379/0            # Optional; defaults to REDIS_URL

# ── Tool Result Cache ─────────────────────────────────────────────────────────
TOOL_CACHE_REDIS_URL=redis://:password@redis:6379/0  # Optional; defaults to REDIS_URL

# ── Tool Retry ────────────────────────────────────────────────────────────────
TOOL_MAX_RETRIES=2               # Retry attempts (default: 2)

# ── Agent Execution Limits ────────────────────────────────────────────────────
AGENT_REQUEST_TIMEOUT=120        # Request timeout in seconds (default: 120)
AGENT_RECURSION_LIMIT=100        # LangGraph recursion limit (default: 100)
```

!!! warning "DATABASE_URL is reserved for Langfuse"
    `DATABASE_URL` is consumed by the Langfuse server container. Use `CHECKPOINT_DB_URL`
    and `STORE_DB_URL` for the deep agent's PostgreSQL connections.

### Django Settings

No additional Django settings are required. The deep agent uses existing models:

- `LLMModel` — LLM configuration and provider selection
- `MCPServer` — MCP tool discovery with health-check status
- `SystemPrompt` — System prompt template management
- `LLMMiddleware` — Per-model middleware configuration stored in the database

## Usage

### Using Deep Agent via API

```python
from ai_ops.agents.deep_mcp_agent import process_message

response = await process_message(
    user_input="Find device RTR-NYC-01",
    thread_id="conversation_123",
    username="admin",
    user_token="Bearer <nautobot-api-token>",
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
```

### Creating Skills

Create a skill directory with a `SKILL.md` file:

```
ai_ops/skills/my-skill/
└── SKILL.md    # Skill instructions, examples, and best practices
```

### Running with Langfuse

Start the development environment with the Langfuse observability stack:

```bash
cd development
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.postgres.yml \
  -f docker-compose.redis.yml \
  -f docker-compose.langfuse.yml \
  -f docker-compose.dev.yml \
  up
```

Access Langfuse UI at: `http://localhost:8000`

**First-time setup:**

1. Open `http://localhost:8000`
2. Create an account (stored locally in PostgreSQL)
3. Create a project
4. Go to **Settings → API Keys** and copy the keys to `creds.env`

**Disable Langfuse:**

```bash
# development.env or creds.env
ENABLE_LANGFUSE=false
```

For detailed Langfuse setup instructions, see [Langfuse Observability Setup](langfuse_setup.md).

## Comparison: Standard Agent vs Deep Agent

| Feature | Standard Agent | Deep Agent |
|---|---|---|
| **Framework** | `create_agent` (LangChain) | `create_deep_agent` (deepagents) |
| **Tool Result Cache** | None | Redis-backed per-tool cache |
| **Tool Retry** | None | Automatic retry with configurable backoff |
| **Subagents** | No | Yes, YAML-configured |
| **Skills** | No | Yes, directory-based Markdown files |
| **Memory** | Checkpointer only | Checkpointer + persistent Store |
| **Checkpointer** | `MemorySaver` (in-memory) | Redis or PostgreSQL with connection pooling |
| **MCP Tools** | Cached at startup | Fresh per request (for per-user auth) |
| **Backend** | N/A | `CompositeBackend` with path routing |
| **Observability** | Structured logs only | Langfuse full trace (opt-in) |

## When to Use Each Agent

### Use Standard Agent When:

- Simple conversational queries with no subagent delegation
- Basic tool usage where transient failures are acceptable
- Minimal infrastructure requirements (no Redis or PostgreSQL needed)

### Use Deep Agent When:

- Complex multi-step workflows needing subagent delegation
- MCP tools have transient failures → retry reduces error rate
- High-volume read queries → tool result caching reduces latency and cost
- Need cross-conversation memory (user preferences, learned facts)
- Want Langfuse observability for debugging or cost analysis

## Performance Considerations

### Tool Result Cache

- **Cache Hit**: Result returned from Redis without calling the MCP server (~1–5 ms)
- **Cache Miss**: Normal MCP round-trip + cache write
- **Write operations**: Never cached (POST/PUT/DELETE/PATCH always bypass the cache)
- **Recommendation**: Leave default config enabled in production for Nautobot read queries

### Connection Pooling

- **Without Pool**: New PostgreSQL connection per request (~100 ms overhead)
- **With Pool**: Connection reused from pool (~1 ms overhead)
- **Recommendation**: Always use pool in production (`CHECKPOINT_POOL_SIZE=10` is a safe default)

### Tool Retry

- **Benefit**: Reduces failure rate for transient MCP server errors
- **Cost**: Additional latency on retry (`retry_delay * attempts`)
- **Recommendation**: Keep `TOOL_MAX_RETRIES=2` (3 total attempts) for most workloads

## Warmup and Shutdown

```python
from ai_ops.agents.deep_mcp_agent import warmup_deep_agent_connections, shutdown_deep_agent

# Pre-warm connections at ASGI lifespan startup
# (Not useful inside Django WSGI/AppConfig.ready() — see docstring for details)
await warmup_deep_agent_connections()

# Graceful shutdown — close all pools and stores
await shutdown_deep_agent()
```

## Troubleshooting

### Langfuse Not Receiving Traces

```bash
# Verify services are running
docker compose ps langfuse-web langfuse-worker

# Check for the success log line
# Look for: "[deep_agent] Langfuse callback attached to graph"

# Verify environment variables
echo $LANGFUSE_PUBLIC_KEY
echo $LANGFUSE_SECRET_KEY
echo $LANGFUSE_HOST

# Check Langfuse container logs
docker compose logs langfuse-web
docker compose logs langfuse-worker
```

### Tool Result Cache Not Working

```bash
# Check Redis connectivity
redis-cli -h redis -a <password> ping
# Expected: PONG

# Check for the cache log lines
# Cache hit:  "[TOOL_CACHE] HIT tool=<name> key=tool_cache:<hash>"
# Cache miss: "[TOOL_CACHE] MISS tool=<name> key=tool_cache:<hash>"
# Disabled:   "[TOOL_CACHE] No TOOL_CACHE_REDIS_URL or REDIS_URL configured, caching disabled"
```

### Subagents Not Loading

```bash
# Verify the config file exists
ls -la ai_ops/agents/subagents.yaml

# Look for the log line at startup
# "[deep_agent] Subagents loaded: N"
```

### MCP Tools Authentication Failures

```bash
# Verify MCPServer entries in Django admin (status should be "Healthy")
# Look for: "Retrieved N MCP tools"
# If 0 tools: check MCPServer status and that the Nautobot API token is valid
```

### Connection Pool / Event Loop Errors

```bash
# Check database connectivity
psql -h db -U nautobot -d nautobot

# Look for event-loop recovery log lines:
# "[event_loop_error] Cleared cached checkpointers/stores — will recreate on next request"
# The next request will automatically recreate the connections.

# Verify pool configuration in development.env
# CHECKPOINT_POOL_SIZE and CHECKPOINT_POOL_MIN_SIZE
```

### `InMemoryStore` Warning in Logs

```
[deep_agent] Both PostgreSQL and Redis unavailable — using InMemoryStore.
Long-term memory will NOT persist across restarts.
```

This warning appears when neither `STORE_DB_URL`/Django DB nor `STORE_REDIS_URL`/`REDIS_URL` resolves successfully. To suppress it, ensure your database is reachable or set `STORE_BACKEND=memory` explicitly to acknowledge the limitation.

## Migration Guide

To migrate from the standard agent to the deep agent:

1. **Install dependencies**: `poetry install` (deepagents, langgraph-checkpoint-redis, langgraph-checkpoint-postgres, etc.)
2. **Configure environment**: Add deep agent env vars to `development.env` (see Configuration section)
3. **Restart services**: New dependencies require a restart
4. **Verify checkpointer**: Watch logs for `"Checkpointer initialised: AsyncRedisSaver"` or `"AsyncPostgresSaver"`
5. **Optional**: Add `subagents.yaml` and skill directories
6. **Optional**: Deploy Langfuse stack and set `ENABLE_LANGFUSE=true`
7. **Monitor**: Check logs for cache hits, retry events, and tool errors

## References

- [deepagents Documentation](https://github.com/langchain-ai/deepagents)
- [LangGraph Checkpointer Concepts](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph Store Concepts](https://langchain-ai.github.io/langgraph/concepts/memory/)
- [Langfuse Self-Hosting](https://langfuse.com/self-hosting/configuration)
- [langgraph-checkpoint-redis](https://github.com/langchain-ai/langgraph-redis)
- [langgraph-checkpoint-postgres](https://github.com/langchain-ai/langgraph-postgres)
