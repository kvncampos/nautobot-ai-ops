# Architecture Overview

This document provides a comprehensive overview of the AI Ops App architecture.

## High-Level Architecture

The AI Ops App integrates Azure OpenAI services with Nautobot through a multi-layered architecture:

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
│  │  (LangGraph) │  │ (LLMModel,   │  │(get_azure_   │       │
│  │              │  │  MCPServer)  │  │ model, etc)  │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────┐
│                   Integration Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  LangChain   │  │    Redis     │  │  PostgreSQL  │       │
│  │   (MCP)      │  │(Checkpoints) │  │  (Models)    │       │
│  └──────┬───────┘  └──────────────┘  └──────────────┘       │
└─────────┼────────────────────────────────────────────────────┘
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                   External Services                            │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │Azure OpenAI  │  │ MCP Servers  │                          │
│  │ (GPT Models) │  │ (Tools/Ctx)  │                          │
│  └──────────────┘  └──────────────┘                          │
└────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. User Interface Layer

#### Web UI
- **Chat Interface**: `/plugins/ai-ops/chat/` - Interactive chat widget
- **Model Management**: List, create, edit, delete LLM models
- **Server Management**: Configure and monitor MCP servers
- **Navigation**: Integrated into Nautobot's navigation menu

#### REST API
- **LLM Models API**: `/api/plugins/ai-ops/llm-models/`
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

**Single-MCP Agent** (`ai_ops/agents/single_mcp_agent.py`):
- Simplified single-server implementation
- Development and testing scenarios

**Agent Features**:
- Conversation history via checkpointing
- Tool discovery from MCP servers
- Azure OpenAI model integration
- Async/await architecture

#### Models

**LLMModel**:
- Stores Azure OpenAI model configurations
- Environment-aware (LAB/NONPROD/PROD)
- Integrates with Nautobot Secrets
- Supports default model selection

**MCPServer**:
- Stores MCP server configurations
- Health status tracking
- Protocol support (HTTP/STDIO)
- Type classification (Internal/External)

#### Helpers

**get_azure_model**:
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

**Models Supported**:
- GPT-4
- GPT-4o (Optimized)
- GPT-4-turbo
- GPT-3.5-turbo

**Communication**:
- HTTPS REST API
- API Key authentication
- Configured endpoints per model

#### MCP Servers

**Purpose**: Extend agent capabilities with custom tools

**Types**:
- **Internal**: Hosted within infrastructure
- **External**: Third-party services

**Protocols**:
- **HTTP**: RESTful MCP servers
- **STDIO**: Process-based servers

**Health Monitoring**:
- Automatic health checks
- Status field in database
- Failed servers excluded from operations

## Data Flow

### Chat Message Flow

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
6. Azure model configuration retrieved
   ↓
7. LangGraph state graph created
   ↓
8. Message added to state
   ↓
9. Agent processes message
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
get_azure_model()
  ↓
Detect environment → "LAB"
  ↓
Read environment variables
  ↓
Create AzureChatOpenAI client
  ↓
Return model
```

**Production Environment**:
```
get_azure_model()
  ↓
Detect environment → "PROD"
  ↓
Query LLMModel.get_default_model()
  ↓
Retrieve Secret for API key
  ↓
Build configuration dict
  ↓
Create AzureChatOpenAI client
  ↓
Return model
```

### MCP Server Discovery Flow

```
1. App startup or cache expiry
   ↓
2. Query MCPServer.objects.filter(status="Healthy")
   ↓
3. Build connections dict
   ↓
4. Create MultiServerMCPClient
   ↓
5. Discover tools from each server
   ↓
6. Cache client and tools
   ↓
7. Tools available to agent
```

## State Management

### Conversation State

**Storage**: Redis checkpoints via LangGraph

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
- Each session has unique thread_id
- Sessions don't interfere
- Parallel conversations supported

**Persistence**:
- Automatic via LangGraph checkpointer
- Survives application restarts
- Cleaned up by maintenance job

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

**Cache Invalidation**:
- Time-based (5 minute TTL)
- Manual refresh available
- Server status changes trigger refresh

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
- `ai_ops.view_llmmodel`
- `ai_ops.add_llmmodel`
- `ai_ops.change_llmmodel`
- `ai_ops.delete_llmmodel`
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
- HTTPS for Azure OpenAI
- HTTPS for MCP servers (recommended)
- TLS for Redis connections (optional)

**At Rest**:
- PostgreSQL encryption (via deployment)
- Redis encryption (via deployment)
- Nautobot Secrets encryption

### Network Security

**Firewall Rules**:
- Outbound to Azure OpenAI (443)
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
