# Architecture Overview

This document provides a comprehensive overview of the AI Ops App architecture.

## High-Level Architecture

The AI Ops App integrates multiple LLM providers with Nautobot through a multi-layered architecture with middleware support:

```
┌──────────────────────────────────────────────────────────────┐
│                        User Interface                         │
│  (Web UI / REST API / Chat Interface)                        │
└────────────────┬─────────────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────────────┐
│                     Nautobot Plugin Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Views      │  │     API      │  │    Jobs      │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────┐
│                      Application Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  AI Agents   │  │   Models     │  │   Helpers    │       │
│  │  (LangGraph) │  │ (LLMProvider,│  │(get_llm_     │       │
│  │  + Middleware│  │  LLMModel,   │  │ model,       │       │
│  │              │  │  Middleware, │  │ middleware)  │       │
│  │              │  │  MCPServer)  │  │              │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────┐
│                   Integration Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  LangChain   │  │    Redis     │  │  PostgreSQL  │       │
│  │   (MCP)      │  │(Checkpoints, │  │  (Models)    │       │
│  │              │  │  Middleware  │  │              │       │
│  │              │  │   Cache)     │  │              │       │
│  └──────┬───────┘  └──────────────┘  └──────────────┘       │
└─────────┼────────────────────────────────────────────────────┘
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                   External Services                            │
│  ┌─────────────────────────────────────────────────┐          │
│  │     LLM Providers (Multi-Provider Support)      │          │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐│          │
│  │  │ Ollama │  │ OpenAI │  │Azure AI│  │Anthropic│          │
│  │  └────────┘  └────────┘  └────────┘  └────────┘│          │
│  │  ┌────────┐  ┌────────┐                        │          │
│  │  │HuggingF│  │ Custom │                        │          │
│  │  └────────┘  └────────┘                        │          │
│  └─────────────────────────────────────────────────┘          │
│  ┌──────────────┐                                             │
│  │ MCP Servers  │                                             │
│  │ (Tools/Ctx)  │                                             │
│  └──────────────┘                                             │
└────────────────────────────────────────────────────────────────┘
```

## Middleware Architecture

The app supports a flexible middleware system that processes requests before and after they reach the LLM:

```
User Request
    ↓
┌───────────────────────────────────────┐
│        Middleware Chain               │
│  (Executed in Priority Order 1-100)  │
├───────────────────────────────────────┤
│  Priority 10: LoggingMiddleware      │ ← Log request
│  Priority 20: CacheMiddleware        │ ← Check cache
│  Priority 30: RetryMiddleware        │ ← Retry logic
│  Priority 40: ValidationMiddleware   │ ← Validate input
├───────────────────────────────────────┤
│              LLM Model                │ ← Process request
│      (Ollama/OpenAI/Azure/etc)       │
├───────────────────────────────────────┤
│  Priority 40: ValidationMiddleware   │ ← Validate output
│  Priority 30: RetryMiddleware        │ ← (if needed)
│  Priority 20: CacheMiddleware        │ ← Store in cache
│  Priority 10: LoggingMiddleware      │ ← Log response
└───────────────────────────────────────┘
    ↓
Response to User
```

## Component Architecture

### 1. User Interface Layer

#### Web UI
- **Chat Interface**: `/plugins/ai-ops/chat/` - Interactive chat widget
- **Provider Management**: List, create, edit, delete LLM providers
- **Model Management**: List, create, edit, delete LLM models
- **Middleware Management**: Configure middleware for models
- **Server Management**: Configure and monitor MCP servers
- **Navigation**: Integrated into Nautobot's navigation menu

#### REST API
- **LLM Providers API**: `/api/plugins/ai-ops/llm-providers/`
- **LLM Models API**: `/api/plugins/ai-ops/llm-models/`
- **Middleware Types API**: `/api/plugins/ai-ops/middleware-types/`
- **LLM Middleware API**: `/api/plugins/ai-ops/llm-middleware/`
- **MCP Servers API**: `/api/plugins/ai-ops/mcp-servers/`
- **Chat API**: `/plugins/ai-ops/api/chat/` - Programmatic chat access

### 2. Application Layer

#### AI Agents

**Multi-MCP Agent** (`ai_ops/agents/multi_mcp_agent.py`):
- Production-ready agent implementation
- Supports multiple MCP servers simultaneously
- Application-level caching for performance
- Health-based server selection
- LangGraph state management
- Middleware integration

**Single-MCP Agent** (`ai_ops/agents/single_mcp_agent.py`):
- Simplified single-server implementation
- Development and testing scenarios

**Agent Features**:
- Conversation history via checkpointing
- Tool discovery from MCP servers
- Multi-provider LLM support (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace)
- Middleware chain execution
- Async/await architecture

#### Models

**LLMProvider**:
- Defines available LLM providers (Ollama, OpenAI, Azure AI, Anthropic, HuggingFace, Custom)
- Stores provider-specific configuration in JSON schema
- Has corresponding provider handler classes
- Enable/disable providers without deletion

**LLMModel**:
- Stores model configurations for any supported provider
- Environment-aware (LAB/NONPROD/PROD)
- Integrates with Nautobot Secrets
- Supports default model selection
- Can have multiple middleware configurations
- References LLMProvider via foreign key

**MiddlewareType**:
- Defines middleware types (built-in LangChain or custom)
- Reusable across multiple models
- Name validation and formatting

**LLMMiddleware**:
- Configures middleware instances for specific models
- Priority-based execution order (1-100)
- JSON configuration for flexibility
- Active/inactive toggle
- Critical flag for initialization requirements

**MCPServer**:
- Stores MCP server configurations
- Health status tracking with automated checks
- Protocol support (HTTP/STDIO)
- Type classification (Internal/External)

#### Helpers

**get_llm_model**:
- Environment detection
- Model configuration retrieval
- Azure OpenAI client creation
- Sync and async variants

**get_info**:
- Status retrieval utilities
- Default value providers

**Serializers**:
- LangGraph checkpoint serialization
- Custom data type handling

### 3. Integration Layer

#### LangChain & LangGraph

**LangChain**:
- Azure OpenAI integration
- Message handling
- Tool abstraction

**LangGraph**:
- State graph workflow
- Checkpointing system
- Conditional routing
- Tool node execution

**MCP Integration**:
- `langchain-mcp-adapters`: MCP client library
- `MultiServerMCPClient`: Multi-server support
- Tool discovery and execution

#### Redis

**Purpose**: Conversation checkpoint storage

**Configuration**:
- Database: Separate from cache/Celery (default DB 2)
- Key Pattern: `checkpoint:{thread_id}:{checkpoint_id}`
- TTL: Managed by cleanup job

**Data Stored**:
- Conversation messages
- Agent state
- Metadata (timestamps, user info)

#### PostgreSQL

**Purpose**: Application data storage

**Tables**:
- `ai_ops_llmmodel`: LLM configurations
- `ai_ops_mcpserver`: MCP server configurations
- Plus standard Nautobot tables (secrets, statuses, etc.)

### 4. External Services

#### Azure OpenAI

**Service**: Microsoft Azure OpenAI Service

**LLM Provider Support**:
- **Ollama**: Local open-source models
- **OpenAI**: GPT-4, GPT-4o, GPT-3.5-turbo
- **Azure AI**: Azure OpenAI Service
- **Anthropic**: Claude models
- **HuggingFace**: HuggingFace Hub models
- **Custom**: Extensible provider system

**Communication**:
- HTTPS REST API
- API Key authentication (via Secrets)
- Provider-specific endpoints
- Handler-based initialization

#### MCP Servers

**Purpose**: Extend agent capabilities with custom tools

**Types**:
- **Internal**: Hosted within infrastructure
- **External**: Third-party services

**Protocols**:
- **HTTP**: RESTful MCP servers
- **STDIO**: Process-based servers

**Health Monitoring**:
- Automatic health checks via scheduled job
- Status field in database
- Failed servers excluded from operations
- Parallel health checking with retry logic

## Data Flow

### Chat Message Flow with Middleware

```
1. User submits message
   ↓
2. ChatMessageView receives request
   ↓
3. Session ID retrieved (thread_id)
   ↓
4. process_message() called
   ↓
5. MCP client cache checked/created
   ↓
6. LLM model configuration retrieved
   ↓
7. Middleware cache checked
   ↓
8. Middleware chain initialized (priority order)
   ↓
9. LangGraph state graph created with middleware
   ↓
10. Message added to state
    ↓
11. Middleware pre-processing (Priority 1 → 100)
    ↓
12. Agent processes message
    ↓
13. LLM provider handler creates model instance
    ↓
14. Model processes request
    ↓
15. Tools invoked if needed (via MCP)
    ↓
16. Middleware post-processing (Priority 100 → 1)
    ↓
17. Response generated by LLM
    ↓
18. State persisted to Redis
    ↓
19. Response returned to user
```

### Provider Selection Flow

```
1. Get LLM model (by name or default)
   ↓
2. Load model's provider relationship
   ↓
3. Get provider handler from registry
   ↓
4. Retrieve provider config_schema from database
   ↓
5. Get model's API key from Secret
   ↓
6. Provider handler initializes LLM
   │
   ├─ Ollama: ChatOllama(base_url, model_name)
   ├─ OpenAI: ChatOpenAI(api_key, model_name)
   ├─ Azure AI: AzureChatOpenAI(api_key, endpoint, deployment)
   ├─ Anthropic: ChatAnthropic(api_key, model_name)
   ├─ HuggingFace: ChatHuggingFace(api_key, model_name)
   └─ Custom: CustomHandler(config, api_key)
   ↓
7. Return initialized chat model instance
```

### Middleware Execution Flow

```
┌────────────────────────────────────────────┐
│  Request from Agent                        │
└───────────────┬────────────────────────────┘
                ↓
┌───────────────▼────────────────────────────┐
│  Load Model's Middleware Configurations    │
│  - Query LLMMiddleware.objects             │
│  - Filter: is_active=True                  │
│  - Order by: priority, middleware__name    │
└───────────────┬────────────────────────────┘
                ↓
┌───────────────▼────────────────────────────┐
│  Initialize Middleware Chain               │
│  For each middleware (priority order):     │
│    1. Load middleware type                 │
│    2. Get configuration JSON               │
│    3. Initialize middleware instance       │
│    4. Add to chain                         │
└───────────────┬────────────────────────────┘
                ↓
┌───────────────▼────────────────────────────┐
│  Pre-Processing Phase                      │
│  (Priority 1 → 100)                        │
│                                            │
│  Priority 10: LoggingMiddleware            │
│    - Log request timestamp                 │
│    - Log user info and message             │
│                                            │
│  Priority 20: CacheMiddleware              │
│    - Check if response cached              │
│    - If cached: return cached response     │
│    - If not: continue chain                │
│                                            │
│  Priority 30: ValidationMiddleware         │
│    - Validate input format                 │
│    - Check for malicious content           │
│    - Sanitize input if needed              │
└───────────────┬────────────────────────────┘
                ↓
┌───────────────▼────────────────────────────┐
│  LLM Processing                            │
│  - Model generates response                │
│  - Tools invoked if needed                 │
└───────────────┬────────────────────────────┘
                ↓
┌───────────────▼────────────────────────────┐
│  Post-Processing Phase                     │
│  (Priority 100 → 1)                        │
│                                            │
│  Priority 30: ValidationMiddleware         │
│    - Validate output format                │
│    - Check for sensitive data              │
│    - Filter response if needed             │
│                                            │
│  Priority 20: CacheMiddleware              │
│    - Store response in cache               │
│    - Set TTL from middleware config        │
│                                            │
│  Priority 10: LoggingMiddleware            │
│    - Log response timestamp                │
│    - Log token usage and latency           │
└───────────────┬────────────────────────────┘
                ↓
┌───────────────▼────────────────────────────┐
│  Response to User                          │
└────────────────────────────────────────────┘
```

### Chat Message Flow
   ↓
10. Tools invoked if needed (via MCP)
    ↓
11. Response generated by LLM
    ↓
12. State persisted to Redis
    ↓
13. Response returned to user
```

### Model Configuration Flow

**LAB Environment**:
```
get_llm_model()
  ↓
Detect environment → "LAB"
  ↓
Read environment variables
  ↓
Create model via default provider (typically Ollama)
  ↓
Return model
```

**Production Environment**:
```
get_llm_model()
  ↓
Detect environment → "PROD"
  ↓
Query LLMModel.get_default_model()
  ↓
Load model's provider relationship
  ↓
Get provider handler from registry
  ↓
Retrieve Secret for API key
  ↓
Build configuration dict from provider config_schema
  ↓
Provider handler creates model instance
  ↓
Return model
```

### MCP Server Discovery Flow

```
1. App startup or cache expiry
   ↓
2. Query MCPServer.objects.filter(status__name="Active")
   ↓
3. Build connections dict
   ↓
4. Create MultiServerMCPClient
   ↓
5. Discover tools from each server
   ↓
6. Cache client and tools (5 min TTL)
   ↓
7. Tools available to agent
```

### Middleware Cache Flow

```
1. Agent needs to process request
   ↓
2. Check middleware cache for model
   ↓
3. If cache miss:
   │  a. Query LLMMiddleware for model
   │  b. Filter: is_active=True
   │  c. Order by: priority, middleware__name
   │  d. Initialize each middleware with config
   │  e. Store in cache with TTL
   ↓
4. If cache hit:
   │  a. Validate cache not expired
   │  b. Return cached middleware chain
   ↓
5. Apply middleware chain to request
```

### Health Check Flow (Scheduled Job)

```
1. MCPServerHealthCheckJob triggered (scheduled)
   ↓
2. Query all HTTP MCP servers (exclude STDIO, Vulnerable)
   ↓
3. Parallel execution (ThreadPoolExecutor, max 4 workers)
   │  For each server:
   │    a. Send GET to {url}{health_check}
   │    b. If status differs from database:
   │       - Wait 5 seconds
   │       - Verify (check #1)
   │       - Wait 5 seconds
   │       - Verify (check #2)
   │       - If both confirm: update database
   ↓
4. If any status changed:
   │  a. Clear MCP client cache
   │  b. Log cache invalidation
   ↓
5. Return summary:
   │  - checked_count
   │  - changed_count
   │  - failed_count
   │  - cache_cleared
```

## State Management

### Conversation State

**Storage**: MemorySaver (in-memory) for short-term session storage

**State Structure**:
```python
{
    "messages": [
        HumanMessage(content="User question"),
        AIMessage(content="AI response"),
        ...
    ]
}
```

**Thread Isolation**:
- Each session has unique thread_id (Django session key)
- Sessions don't interfere
- Parallel conversations supported

**Persistence & TTL**:
- **Backend (MemorySaver)**: In-memory storage with timestamp tracking
  - Checkpoints tracked with creation timestamps
  - Automatic cleanup every 5 minutes via scheduled job
  - Expires after configured TTL (default: 5 minutes) + 30s grace period
  - Lost on application restart
- **Frontend (localStorage)**: Browser-based message display
  - Messages filtered by age on page load
  - Synced with backend TTL configuration
  - Cleared automatically when expired
  - Inactivity timer for auto-clearing (matches TTL config)

**TTL Configuration**:
```python
# In nautobot_config.py
PLUGINS_CONFIG = {
    "ai_ops": {
        "chat_session_ttl_minutes": 5,  # Default: 5 minutes
    }
}
```

**Cleanup Process**:
1. **Frontend TTL Check** (on page load):
   - Filters messages older than TTL + grace period
   - Shows expiry message if conversation expired
   - Calls backend clear API if all messages expired

2. **Backend Scheduled Cleanup** (every 5 minutes):
   - Scans all MemorySaver checkpoints
   - Removes checkpoints older than TTL + grace period
   - Logs processed and deleted counts

3. **Inactivity Timer** (frontend):
   - Resets on any user activity
   - Triggers after TTL minutes of no interaction
   - Clears both frontend and backend state

**Migration Path**:
- Current: MemorySaver (session-based, in-memory)
- Future Option 1: Redis Stack with RediSearch (persistent, cached)
- Future Option 2: PostgreSQL (persistent, database)
- See TODOs in `checkpointer.py` for implementation details

### Application State

**MCP Client Cache**:
```python
{
    "client": MultiServerMCPClient,
    "tools": [Tool1, Tool2, ...],
    "timestamp": datetime,
    "server_count": int
}
```

**MCP Cache Invalidation**:
- Time-based (5 minute TTL)
- Manual refresh available
- Server status changes trigger refresh (via health check job)

**Middleware Cache**:
```python
{
    model_id: {
        "middlewares": [Middleware1, Middleware2, ...],
        "timestamp": datetime,
        "config_hashes": {middleware_id: hash, ...}
    }
}
```

**Middleware Cache Invalidation**:
- Automatic via JobHookReceiver on LLMMiddleware changes
- Cache cleared when middleware created/updated/deleted
- Cache warmed when new default model set
- Ensures middleware changes take effect immediately

## Security Architecture

### Authentication & Authorization

**User Authentication**:
- Nautobot's built-in authentication
- LDAP/SAML support via Nautobot
- Session management

**API Authentication**:
- Token-based (Nautobot API tokens)
- Per-request authentication
- Token permissions enforced

**Permissions**:
- `ai_ops.view_llmprovider`
- `ai_ops.add_llmprovider`
- `ai_ops.change_llmprovider`
- `ai_ops.delete_llmprovider`
- `ai_ops.view_llmmodel`
- `ai_ops.add_llmmodel`
- `ai_ops.change_llmmodel`
- `ai_ops.delete_llmmodel`
- `ai_ops.view_middlewaretype`
- `ai_ops.add_middlewaretype`
- `ai_ops.change_middlewaretype`
- `ai_ops.delete_middlewaretype`
- `ai_ops.view_llmmiddleware`
- `ai_ops.add_llmmiddleware`
- `ai_ops.change_llmmiddleware`
- `ai_ops.delete_llmmiddleware`
- `ai_ops.view_mcpserver`
- `ai_ops.add_mcpserver`
- `ai_ops.change_mcpserver`
- `ai_ops.delete_mcpserver`

### Secrets Management

**API Keys**:
- Stored in Nautobot Secrets
- Never in code or database directly
- Provider-agnostic (environment, HashiCorp Vault, etc.)

**Access Control**:
- Secrets retrieved at runtime
- Minimal exposure
- Audit trail via Nautobot

### Data Security

**In Transit**:
- HTTPS for all LLM providers (Ollama, OpenAI, Azure AI, Anthropic, etc.)
- HTTPS for MCP servers (recommended)
- TLS for Redis connections (optional)

**At Rest**:
- PostgreSQL encryption (via deployment)
- Redis encryption (via deployment)
- Nautobot Secrets encryption

### Network Security

**Firewall Rules**:
- Outbound to LLM provider APIs (443)
  - Ollama: Configurable port (default 11434)
  - OpenAI: api.openai.com:443
  - Azure AI: *.openai.azure.com:443
  - Anthropic: api.anthropic.com:443
  - HuggingFace: huggingface.co:443
- Outbound to MCP servers (various)
- Inbound to Nautobot (80/443)

**Internal Communication**:
- PostgreSQL: local or internal network
- Redis: local or internal network
- MCP servers: internal network (typically)

## Scalability & Performance

### Caching Strategy

**MCP Client Cache**:
- Application-level
- 5-minute TTL
- Reduces initialization overhead
- Thread-safe

**Model Instances**:
- Reusable within agent lifecycle
- Not cached globally (created per request)
- Stateless between requests

### Async Architecture

**Benefits**:
- Non-blocking I/O
- Concurrent request handling
- Better resource utilization

**Implementation**:
- Django async views
- Async agent processing
- Async MCP client operations

### Database Optimization

**Indexes**:
- Primary keys (UUID)
- Status field (MCPServer)
- is_default field (LLMModel)

**Queries**:
- Filtered by status for MCP servers
- Default model query optimized
- Minimal database round trips

### Redis Optimization

**Checkpoint Cleanup**:
- Scheduled job removes old data
- Prevents unbounded growth
- Configurable retention period

**Key Structure**:
- Efficient key patterns
- SCAN for safe iteration
- Separate database number

## Monitoring & Observability

### Logging

**Log Levels**:
- INFO: Normal operations
- WARNING: Degraded conditions
- ERROR: Failures

**Log Locations**:
- Nautobot logs directory
- Application-specific logger: `ai_ops`

**Key Events**:
- Agent message processing
- MCP cache operations
- Model configuration retrieval
- Health check failures

### Metrics

**Application Metrics**:
- Request count
- Response times
- Error rates

**System Metrics**:
- Redis memory usage
- PostgreSQL connection pool
- Azure OpenAI API usage

### Health Checks

**MCP Server Health**:
- Automatic health check requests
- Status field updated
- Failed servers excluded

**System Health**:
- Redis connectivity
- PostgreSQL connectivity
- Azure OpenAI API accessibility

## Error Handling

### Graceful Degradation

**No MCP Servers**:
- Agent continues without tools
- Basic conversation capabilities maintained
- Warning logged

**Model Configuration Missing**:
- Error raised early
- Clear error message
- LAB fallback to environment variables

**Azure API Failures**:
- Errors propagated to user
- Rate limit handling recommended
- Retry logic (external implementation)

### Error Recovery

**Transient Failures**:
- MCP server temporarily unavailable → Excluded until healthy
- Redis connection issue → Conversation history unavailable but agent works
- Azure API timeout → User notified, can retry

**Permanent Failures**:
- Invalid API key → Configuration error, admin must fix
- Model not found → Create model or use default
- Server consistently failing → Update status to Maintenance

## Deployment Considerations

### Environment Requirements

**Minimum**:
- Python 3.10+
- PostgreSQL 12+ or MySQL 8+
- Redis 6+
- Nautobot 2.4.22+

**Recommended**:
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Dedicated Redis for checkpoints

### Scaling

**Horizontal Scaling**:
- Multiple Nautobot workers
- Shared Redis for checkpoints
- Shared PostgreSQL database
- MCP client cache per worker

**Vertical Scaling**:
- More CPU for LLM processing
- More memory for Redis checkpoints
- More connections to PostgreSQL

### High Availability

**Components**:
- **Nautobot**: Load balanced, multiple workers
- **PostgreSQL**: Primary/replica setup
- **Redis**: Redis Sentinel or Cluster
- **MCP Servers**: Multiple instances with health checks

**Failure Scenarios**:
- Single worker failure → Other workers handle requests
- Redis failure → Conversation history lost, functionality continues
- PostgreSQL failure → Application unavailable (required)
- MCP server failure → Other servers continue, failed server excluded

## Future Architecture Enhancements

### Planned Improvements

1. **PostgreSQL Checkpointing**: Replace Redis with PostgreSQL for persistence
2. **Conversation History UI**: View and manage past conversations
3. **Model Performance Metrics**: Track model usage and performance
4. **Advanced Caching**: Redis caching for model responses
5. **Streaming Responses**: Real-time streaming of AI responses
6. **Multi-Tenancy**: Tenant-specific models and configurations
7. **Custom Agent Types**: Support for specialized agent implementations
8. **Tool Usage Analytics**: Track and visualize tool invocations

### Integration Opportunities

- **ITSM Integration**: ServiceNow, Jira ticket creation
- **Monitoring Systems**: Integration with Prometheus, Grafana
- **ChatOps**: Slack, Teams integration
- **Workflow Automation**: Ansible, Terraform integration

## Related Documentation

- [Models](code_reference/models.md) - Database models
- [Agents](code_reference/agents.md) - AI agent implementations
- [Helpers](code_reference/helpers.md) - Helper modules
- [Jobs](code_reference/jobs.md) - Background jobs
- [External Interactions](../user/external_interactions.md) - External system integrations
