# Human→Agent Orchestration Analysis & Improvement Plan

**Date:** February 2026  
**Version:** 1.0  
**Status:** Analysis & Recommendations

---

## Executive Summary

This document provides a comprehensive analysis of the current human→agent orchestration patterns in the nautobot-ai-ops plugin and proposes concrete improvements using modern agentic frameworks (LangChain, LangGraph, and multi-agent patterns).

### Key Findings

✅ **Strengths:**
- Already using LangGraph for agent orchestration (via `create_agent()`)
- Well-structured middleware system with priority-based execution
- Clean separation between providers, models, and middleware
- Production-ready MCP client caching and health monitoring
- Proper async/await patterns throughout

⚠️ **Areas for Improvement:**
- Manual orchestration logic in `multi_mcp_agent.py` could leverage more LangGraph patterns
- State management is implicit (dict-based) rather than typed (Pydantic models)
- No explicit workflow graphs for complex multi-step operations
- Limited use of LangGraph's advanced features (conditional routing, parallelization, human-in-the-loop)
- Middleware instantiation could benefit from LangChain Expression Language (LCEL) patterns
- MCP tool selection is automatic but lacks intelligent routing/planning

---

## 1. Current Architecture Review

### 1.1 Human Entry Points

The plugin provides multiple entry points for human→agent interaction:

#### Primary Entry Points

1. **Web Chat Interface** (`views.py::AIChatBotGenericView`)
   - URL: `/plugins/ai-ops/chat/`
   - Method: GET (render UI), POST via AJAX (message processing)
   - Handler: `ChatMessageView.post()` → `multi_mcp_agent.process_message()`
   - Features: Session-based conversation, provider selection (admin only)

2. **REST API Endpoints** (`api/views.py`)
   - Provider Management: `/api/plugins/ai-ops/llm-providers/`
   - Model Management: `/api/plugins/ai-ops/llm-models/`
   - MCP Server Management: `/api/plugins/ai-ops/mcp-servers/`
   - Middleware Management: `/api/plugins/ai-ops/llm-middleware/`
   - Health Check: `/api/plugins/ai-ops/mcp-servers/{id}/health-check/` (POST)

3. **Scheduled Jobs** (`jobs/`)
   - `MCPServerHealthCheckJob`: Automated health monitoring
   - `checkpoint_cleanup.py`: Conversation history cleanup
   - `chat_session_cleanup.py`: Session TTL enforcement

4. **Admin Actions**
   - Clear MCP Cache: `ClearMCPCacheView.post()`
   - Clear Chat History: `ChatClearView.post()`

### 1.2 Agent / Orchestration Logic

**Core Orchestration File:** `ai_ops/agents/multi_mcp_agent.py`

#### Current Flow

```python
# Simplified flow from views.py → multi_mcp_agent.py
1. User sends message via ChatMessageView.post()
2. Extract message, thread_id (session key), optional provider override
3. Call process_message(user_input, thread_id, provider, username, cancellation_check)
   ├─ Generate correlation_id for tracing
   ├─ Get checkpointer from singleton MemorySaver
   ├─ Build agent:
   │   ├─ Get MCP client & tools (cached, with TTL)
   │   ├─ Get LLM model (with optional provider override)
   │   ├─ Get middleware in priority order (fresh instances)
   │   ├─ Get system prompt (from DB or fallback)
   │   └─ create_agent(model, tools, system_prompt, middleware, checkpointer)
   ├─ Create RunnableConfig with thread_id & ToolLoggingCallback
   └─ Invoke: graph.ainvoke({"messages": [HumanMessage(...)]}, config)
4. Return last message content to user
```

#### Key Orchestration Components

**MCP Client Management** (`get_or_create_mcp_client()`)
- Application-level cache with TTL (default 300s from LLMModel.cache_ttl)
- Discovers healthy MCP servers from database (`status.name == "Healthy"`)
- Builds `MultiServerMCPClient` with HTTP connections
- Thread-safe via event loop-bound locks
- Force refresh on health check failures

**Middleware Pipeline** (`helpers/get_middleware.py`)
- Loads middleware from `LLMMiddleware` model (filtered by `is_active=True`)
- Ordered by priority (1-100, lower = earlier execution)
- Fresh instances per request (prevents state leaks)
- Dynamic import from `langchain.agents.middleware` or `ai_ops.middleware`
- Graceful degradation for non-critical middleware

**LLM Model Selection** (`helpers/get_llm_model.py`)
- Provider-agnostic interface: `get_llm_model_async(model_name, provider, temperature)`
- Supports provider override (admin-only feature)
- Retrieves API keys from Nautobot Secret objects
- Dynamic provider handler selection via `LLMProvider.get_handler()`

**System Prompt Management** (`helpers/get_prompt.py`)
- Hierarchy: Model-assigned prompt → Global approved prompt → Code fallback
- Supports template rendering (Jinja2 .md/.j2 files)
- Runtime variable substitution: `{current_date}`, `{model_name}`, `{tools}`
- Only uses prompts with `status == "Approved"`

### 1.3 MCP / Tooling Integration

**MCP Tool Discovery Flow:**

```python
# In get_or_create_mcp_client():
1. Query MCPServer.objects.filter(status__name="Healthy", protocol="http")
2. Build connections dict for MultiServerMCPClient
   - Each server: {"transport": "streamable_http", "url": ..., "httpx_client_factory": ...}
3. Create MultiServerMCPClient(connections)
4. Fetch tools: client.get_tools()
5. Cache (client, tools) with timestamp
```

**Tool Invocation:**
- Handled automatically by LangChain's `create_agent()` + `MultiServerMCPClient`
- No explicit tool selection logic (LLM decides via ReAct-style reasoning)
- Tool results logged via `ToolLoggingCallback`

**MCP Health Monitoring:**
- Scheduled job checks HTTP `/health` endpoint for each server
- Retry logic: 2 verification checks (5s apart) before status flip
- Parallel execution: ThreadPoolExecutor (1 worker/server, max 4)
- Cache invalidation on status changes

**Error Handling:**
- SSL verification disabled for internal MCP servers (intentional)
- Correlation ID + username headers for cross-service tracing
- Timeout: 5s for health checks
- Graceful degradation: Agent works without MCP tools

### 1.4 State & Context Management

**Conversation State:**
- **Storage:** MemorySaver (in-memory, non-persistent)
- **Keying:** Session key (`request.session.session_key`) as `thread_id`
- **Structure:** LangGraph's internal checkpointing format
- **TTL:** Configurable via `chat_session_ttl_minutes` (Constance config)
- **Cleanup:** Scheduled job scans and deletes expired checkpoints

**Context Passing:**
```python
# Implicit state blob in graph.ainvoke():
{
    "messages": [
        HumanMessage(content=user_input),
        AIMessage(...),  # from previous turns
        ToolMessage(...),  # tool results
        ...
    ]
}
```

**Issues with Current State Management:**
1. **Untyped:** State is a dict with `messages` key (no Pydantic model)
2. **No explicit state schema:** Hard to extend with custom fields
3. **No checkpointing for long-running ops:** All processing is synchronous within 120s timeout
4. **Limited observability:** No structured logging of state transitions

**Cancellation Handling:**
- Redis-backed cancellation flags (`CANCELLATION_CACHE_PREFIX + thread_id`)
- Checked before processing starts (not during graph execution)
- TODO comment in code: "Enhance with interrupt support within graph execution"

---

## 2. Current Issues & Pain Points

### 2.1 Orchestration Complexity

**Issue:** Manual orchestration in `process_message()` mixes concerns
- Agent building logic (get tools, model, middleware, prompt)
- Configuration retrieval (database queries)
- Error handling (try/except, logging)
- Timeout management (asyncio.wait_for)

**Impact:** 
- Hard to test individual steps
- Difficult to add conditional flows (e.g., "if tool fails, try alternative")
- No parallelization of independent tasks

### 2.2 State Management Limitations

**Issue:** Implicit dict-based state makes it hard to:
- Add custom state fields (e.g., `current_task_plan`, `tool_results_summary`)
- Validate state shape at runtime
- Serialize/deserialize complex objects
- Implement conditional routing based on state

**Example:**
```python
# Current: Implicit state
result = await graph.ainvoke({"messages": [...]}, config)

# Desired: Typed state with custom fields
result = await graph.ainvoke({
    "messages": [...],
    "task_plan": ["step1", "step2"],  # ❌ Can't add this easily
    "context": {"device_id": "...", "location": "..."},  # ❌ No schema
}, config)
```

### 2.3 No Explicit Workflow Graphs

**Issue:** Complex workflows (e.g., "analyze topology → identify issue → propose fix → confirm with user") are handled linearly by the LLM via tool calls.

**Limitations:**
- No visual representation of workflow steps
- Can't parallelize independent tool calls
- No conditional branching based on intermediate results
- Human-in-the-loop approval gates require custom implementation

### 2.4 Tool Selection & Routing

**Issue:** Tool selection is delegated entirely to the LLM (ReAct pattern).

**Problems:**
- LLM may choose suboptimal tools
- No routing layer (e.g., "for topology questions, prefer graph tools over API tools")
- No fallback strategies (e.g., "if primary tool fails, try alternative")
- No cost optimization (e.g., "prefer cheaper local tools over API calls")

### 2.5 Limited Multi-Agent Patterns

**Issue:** Single-agent architecture doesn't leverage specialization.

**Missed Opportunities:**
- **Planner/Executor:** One agent plans steps, another executes with tools
- **Specialist Agents:** Topology expert, telemetry analyzer, remediation planner
- **Reflection/Critique:** Second agent reviews first agent's output
- **Hierarchical:** Manager agent delegates to worker agents

---

## 3. Proposed Improvements

### 3.1 Adopt LangGraph State Graphs for Complex Workflows

#### Recommendation: Introduce Typed State Models

**Current:**
```python
# Untyped state dict
result = await graph.ainvoke({"messages": [HumanMessage(...)]}, config)
```

**Proposed:**
```python
from typing import Annotated
from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

class NautobotAgentState(MessagesState):
    """Typed state for Nautobot AI agent workflows."""
    
    # Inherited from MessagesState
    messages: Annotated[list, "Conversation messages"]
    
    # Custom fields for Nautobot context
    nautobot_context: dict = Field(
        default_factory=dict,
        description="Device IDs, location, IP ranges, etc."
    )
    task_plan: list[str] = Field(
        default_factory=list,
        description="Planned steps for multi-step workflows"
    )
    tool_results: dict = Field(
        default_factory=dict,
        description="Cache of tool call results for reuse"
    )
    requires_approval: bool = Field(
        default=False,
        description="Flag for human-in-the-loop approval"
    )
    current_step: int = Field(
        default=0,
        description="Current step in multi-step workflow"
    )
```

**Benefits:**
- Type safety via Pydantic
- Easy to extend with new fields
- Better IDE support (autocomplete, type checking)
- Enables conditional routing based on state fields

#### Example: Multi-Step Workflow with LangGraph

**Use Case:** "Analyze network topology → Identify bottlenecks → Propose remediation → Get approval → Execute changes"

```python
from langgraph.graph import StateGraph, END

def create_topology_analysis_workflow(checkpointer):
    """Create a workflow graph for topology analysis with human approval."""
    
    workflow = StateGraph(NautobotAgentState)
    
    # Define nodes
    workflow.add_node("plan_analysis", plan_topology_analysis)
    workflow.add_node("fetch_topology", fetch_topology_data)
    workflow.add_node("analyze_topology", analyze_topology)
    workflow.add_node("identify_issues", identify_bottlenecks)
    workflow.add_node("propose_remediation", propose_fixes)
    workflow.add_node("await_approval", await_human_approval)
    workflow.add_node("execute_changes", execute_remediation)
    workflow.add_node("report_results", generate_report)
    
    # Define edges
    workflow.set_entry_point("plan_analysis")
    workflow.add_edge("plan_analysis", "fetch_topology")
    workflow.add_edge("fetch_topology", "analyze_topology")
    workflow.add_edge("analyze_topology", "identify_issues")
    
    # Conditional routing based on state
    workflow.add_conditional_edges(
        "identify_issues",
        should_propose_fixes,  # Returns "propose_remediation" or "report_results"
        {
            "propose": "propose_remediation",
            "report": "report_results"
        }
    )
    
    workflow.add_edge("propose_remediation", "await_approval")
    
    # Human-in-the-loop approval gate
    workflow.add_conditional_edges(
        "await_approval",
        check_approval_status,  # Returns "approved" or "rejected"
        {
            "approved": "execute_changes",
            "rejected": "report_results"
        }
    )
    
    workflow.add_edge("execute_changes", "report_results")
    workflow.add_edge("report_results", END)
    
    return workflow.compile(checkpointer=checkpointer)


# Node implementations
async def plan_topology_analysis(state: NautobotAgentState) -> NautobotAgentState:
    """Generate a plan for topology analysis based on user input."""
    user_message = state["messages"][-1].content
    
    # Use LLM to generate plan
    planner_llm = await get_llm_model_async(model_name="gpt-4")
    plan_prompt = f"Create a step-by-step plan to: {user_message}"
    response = await planner_llm.ainvoke(plan_prompt)
    
    state["task_plan"] = response.content.split("\n")
    state["current_step"] = 0
    return state


async def fetch_topology_data(state: NautobotAgentState) -> NautobotAgentState:
    """Fetch topology data from Nautobot via MCP tools."""
    # Use MCP tools to fetch device topology
    client, tools = await get_or_create_mcp_client()
    
    # Find topology tool
    topology_tool = next((t for t in tools if "topology" in t.name.lower()), None)
    if topology_tool:
        result = await client.call_tool(topology_tool.name, {})
        state["tool_results"]["topology"] = result
    
    state["current_step"] += 1
    return state


def should_propose_fixes(state: NautobotAgentState) -> str:
    """Decide whether to propose fixes based on analysis results."""
    issues = state["tool_results"].get("identified_issues", [])
    return "propose" if issues else "report"


async def check_approval_status(state: NautobotAgentState) -> str:
    """Check if human approved the remediation plan."""
    # In practice, this would check a database flag or interrupt signal
    return "approved" if state.get("requires_approval") == False else "rejected"
```

**Usage:**
```python
# In views.py or API endpoint
async def handle_topology_analysis_request(request):
    workflow = create_topology_analysis_workflow(checkpointer)
    
    result = await workflow.ainvoke(
        {
            "messages": [HumanMessage(content="Analyze network topology for bottlenecks")],
            "nautobot_context": {"location_id": "..."},
        },
        config={"configurable": {"thread_id": request.session.session_key}}
    )
    
    return JsonResponse({"report": result["tool_results"]["report"]})
```

### 3.2 Leverage LangChain for Tool Wrappers & Chains

#### Recommendation: Create Structured Tool Wrappers

**Current:** MCP tools are used directly via `MultiServerMCPClient`

**Proposed:** Wrap MCP tools with LangChain's `@tool` decorator for better control

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class TopologyQueryInput(BaseModel):
    """Input schema for topology query tool."""
    device_filter: str = Field(description="Device name pattern (e.g., 'core-*')")
    depth: int = Field(default=2, description="Topology depth (1-5)")
    include_inactive: bool = Field(default=False, description="Include inactive devices")


@tool(args_schema=TopologyQueryInput)
async def query_nautobot_topology(device_filter: str, depth: int = 2, include_inactive: bool = False) -> dict:
    """Query Nautobot device topology with filtering and depth control.
    
    Use this tool to discover network topology around specific devices.
    Returns a graph structure with nodes (devices) and edges (connections).
    """
    client, tools = await get_or_create_mcp_client()
    
    # Find MCP topology tool
    mcp_tool = next((t for t in tools if t.name == "mcp_nautobot_topology"), None)
    if not mcp_tool:
        raise ValueError("Topology tool not available")
    
    # Call MCP tool with validated params
    result = await client.call_tool(mcp_tool.name, {
        "device_filter": device_filter,
        "depth": depth,
        "include_inactive": include_inactive
    })
    
    return result


# Register tool with agent
tools = [query_nautobot_topology, ...]
graph = create_agent(model=llm, tools=tools, ...)
```

**Benefits:**
- **Input validation:** Pydantic schemas prevent invalid tool calls
- **Better LLM prompting:** Schema helps LLM understand tool parameters
- **Error handling:** Centralized place for retry logic, fallbacks
- **Logging & monitoring:** Track tool usage, latency, errors

#### Recommendation: Use LCEL for Pre/Post-Processing Chains

**Example: Input Validation Chain**

```python
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate

# Define a chain for input sanitization and context enrichment
input_processing_chain = (
    RunnablePassthrough.assign(
        sanitized_input=RunnableLambda(sanitize_user_input),
        nautobot_context=RunnableLambda(fetch_user_context)
    )
    | RunnableLambda(validate_permissions)
)

# Use in agent flow
processed_input = await input_processing_chain.ainvoke({
    "user_input": raw_message,
    "user_id": request.user.id
})

result = await agent_graph.ainvoke(processed_input, config)
```

**Example: Response Formatting Chain**

```python
# Define a chain for response post-processing
response_chain = (
    RunnableLambda(extract_agent_response)
    | RunnableLambda(format_markdown)
    | RunnableLambda(add_citations)
)

formatted_response = await response_chain.ainvoke(agent_result)
```

### 3.3 Implement Multi-Agent Architecture

#### Pattern 1: Planner/Executor

**Problem:** Current agent tries to both plan and execute in one pass, leading to suboptimal tool usage.

**Solution:** Separate planning from execution

```python
from langgraph.graph import StateGraph, END

class PlanExecuteState(NautobotAgentState):
    """State for planner/executor pattern."""
    plan: list[dict] = Field(default_factory=list, description="Execution plan steps")
    current_step_index: int = Field(default=0)
    execution_results: list[dict] = Field(default_factory=list)


def create_planner_executor_workflow():
    """Create a planner/executor multi-agent workflow."""
    
    workflow = StateGraph(PlanExecuteState)
    
    # Define agents
    workflow.add_node("planner", planner_agent)
    workflow.add_node("executor", executor_agent)
    workflow.add_node("replanner", replanner_agent)
    workflow.add_node("responder", response_generator)
    
    # Workflow edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "executor")
    
    workflow.add_conditional_edges(
        "executor",
        check_execution_status,
        {
            "continue": "executor",  # Continue to next step
            "replan": "replanner",    # Replanning needed
            "done": "responder"       # All steps complete
        }
    )
    
    workflow.add_edge("replanner", "executor")
    workflow.add_edge("responder", END)
    
    return workflow.compile()


async def planner_agent(state: PlanExecuteState) -> PlanExecuteState:
    """Generate an execution plan using a planning-specialized LLM."""
    planner_llm = await get_llm_model_async(model_name="gpt-4", temperature=0.0)
    
    planning_prompt = f"""
    You are a planning specialist for network operations.
    Create a detailed, step-by-step plan for: {state["messages"][-1].content}
    
    Each step should specify:
    1. Action to take
    2. Required tools
    3. Expected output
    4. Success criteria
    
    Return a JSON list of steps.
    """
    
    response = await planner_llm.ainvoke(planning_prompt)
    state["plan"] = json.loads(response.content)
    return state


async def executor_agent(state: PlanExecuteState) -> PlanExecuteState:
    """Execute the current step in the plan using available tools."""
    current_step = state["plan"][state["current_step_index"]]
    
    # Get executor LLM with tools
    executor_llm = await get_llm_model_async()
    client, tools = await get_or_create_mcp_client()
    executor = create_agent(model=executor_llm, tools=tools, ...)
    
    # Execute step
    result = await executor.ainvoke({
        "messages": [HumanMessage(content=current_step["action"])]
    })
    
    state["execution_results"].append({
        "step": current_step,
        "result": result
    })
    state["current_step_index"] += 1
    
    return state
```

#### Pattern 2: Specialist Agents

**Problem:** Single generalist agent may not be optimal for specialized Nautobot tasks.

**Solution:** Create specialist agents for different domains

```python
class AgentRole(str, Enum):
    """Specialist agent roles."""
    TOPOLOGY_EXPERT = "topology_expert"
    TELEMETRY_ANALYZER = "telemetry_analyzer"
    CONFIG_SPECIALIST = "config_specialist"
    REMEDIATION_PLANNER = "remediation_planner"


class SpecialistAgentConfig(BaseModel):
    """Configuration for a specialist agent."""
    role: AgentRole
    system_prompt: str
    tools: list[str]  # Tool names this agent can use
    model_override: Optional[str] = None  # Use specific model for this agent


# Define specialists
SPECIALISTS = {
    AgentRole.TOPOLOGY_EXPERT: SpecialistAgentConfig(
        role=AgentRole.TOPOLOGY_EXPERT,
        system_prompt="""You are a network topology specialist.
        Your expertise: device connectivity, link analysis, path finding.
        Always use topology tools before making recommendations.""",
        tools=["query_topology", "find_path", "identify_loops"]
    ),
    
    AgentRole.TELEMETRY_ANALYZER: SpecialistAgentConfig(
        role=AgentRole.TELEMETRY_ANALYZER,
        system_prompt="""You are a telemetry and monitoring specialist.
        Your expertise: metric analysis, anomaly detection, performance trends.
        Use time-series tools to analyze historical data.""",
        tools=["query_metrics", "detect_anomalies", "compare_baselines"]
    ),
}


async def route_to_specialist(user_query: str) -> AgentRole:
    """Route user query to appropriate specialist agent."""
    router_llm = await get_llm_model_async(temperature=0.0)
    
    routing_prompt = f"""
    Classify this user query into one of these categories:
    - topology_expert: Network topology, connectivity, device relationships
    - telemetry_analyzer: Metrics, performance, monitoring, anomalies
    - config_specialist: Configuration management, compliance
    - remediation_planner: Issue fixing, change planning
    
    Query: {user_query}
    
    Return only the category name.
    """
    
    response = await router_llm.ainvoke(routing_prompt)
    return AgentRole(response.content.strip())


async def invoke_specialist(role: AgentRole, state: NautobotAgentState):
    """Invoke a specialist agent for a specific task."""
    config = SPECIALISTS[role]
    
    # Get LLM and tools for this specialist
    llm = await get_llm_model_async(model_name=config.model_override)
    client, all_tools = await get_or_create_mcp_client()
    
    # Filter tools for this specialist
    specialist_tools = [t for t in all_tools if t.name in config.tools]
    
    # Create specialist agent
    agent = create_agent(
        model=llm,
        tools=specialist_tools,
        system_prompt=config.system_prompt
    )
    
    return await agent.ainvoke(state)
```

### 3.4 Enhanced Safety, Observability & Robustness

#### Recommendation: Structured Error Handling with Middleware

**Current:** Error handling is scattered across try/except blocks

**Proposed:** Centralized error handling middleware

```python
from langchain.agents.middleware import BaseMiddleware
from typing import Any, Callable, Awaitable

class ErrorHandlingMiddleware(BaseMiddleware):
    """Middleware for structured error handling with retries."""
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        fallback_response: Optional[str] = None
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.fallback_response = fallback_response or "An error occurred. Please try again."
    
    async def process_request(self, messages: list, **kwargs) -> list:
        """Pre-process: Log request for audit."""
        logger.info(f"[Request] messages={len(messages)}, user={kwargs.get('user')}")
        return messages
    
    async def process_response(self, response: Any, **kwargs) -> Any:
        """Post-process: Validate and handle errors."""
        if hasattr(response, "error"):
            logger.error(f"[Error] {response.error}")
            # Retry logic here
            ...
        return response


# Register in database
LLMMiddleware.objects.create(
    llm_model=model,
    middleware=MiddlewareType.objects.get(name="ErrorHandlingMiddleware"),
    priority=10,  # Run early
    is_active=True,
    is_critical=True,
    config={
        "max_retries": 3,
        "retry_delay": 1.0,
        "fallback_response": "Sorry, I encountered an error. Please try again."
    }
)
```

#### Recommendation: LangSmith Integration for Observability

```python
from langsmith import Client
from langchain_core.tracers import LangChainTracer

# In multi_mcp_agent.py::process_message()
async def process_message_with_tracing(
    user_input: str,
    thread_id: str,
    provider: str | None = None,
    username: str | None = None,
) -> str:
    """Process message with LangSmith tracing."""
    
    # Initialize LangSmith tracer
    tracer = LangChainTracer(
        project_name="nautobot-ai-ops",
        client=Client(api_key=os.getenv("LANGCHAIN_API_KEY"))
    )
    
    async with get_checkpointer() as checkpointer:
        graph = await build_agent(checkpointer=checkpointer, provider=provider)
        
        config = RunnableConfig(
            configurable={"thread_id": thread_id},
            callbacks=[ToolLoggingCallback(), tracer],  # Add tracer
            tags=["mcp-agent", f"user:{username}"],
            metadata={
                "thread_id": thread_id,
                "user": username,
                "provider": provider,
                "correlation_id": get_correlation_id()
            }
        )
        
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config
        )
        
        return str(result["messages"][-1].content)
```

#### Recommendation: Token & Cost Tracking Middleware

```python
class TokenTrackingMiddleware(BaseMiddleware):
    """Track token usage and estimated costs per request."""
    
    def __init__(self, cost_per_1k_tokens: dict[str, float]):
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.token_counter = TokenCounter()
    
    async def process_request(self, messages: list, **kwargs) -> list:
        """Count input tokens."""
        self.token_counter.count_messages(messages)
        return messages
    
    async def process_response(self, response: Any, **kwargs) -> Any:
        """Count output tokens and calculate cost."""
        self.token_counter.count_response(response)
        
        total_tokens = self.token_counter.total_tokens
        estimated_cost = self.calculate_cost(total_tokens)
        
        logger.info(f"[Tokens] total={total_tokens}, cost=${estimated_cost:.4f}")
        
        # Store in database for billing/analytics
        await self.save_usage_record(total_tokens, estimated_cost)
        
        return response
```

---

## 4. Code-Level Examples

### Example 1: Refactored build_agent() with LangGraph State

**File:** `ai_ops/agents/multi_mcp_agent_v2.py`

```python
"""Enhanced Multi-MCP Agent with typed state and advanced LangGraph patterns."""

from typing import Annotated, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, MessagesState, END
from langchain_core.messages import HumanMessage, AIMessage

class NautobotAgentState(MessagesState):
    """Typed state for Nautobot AI agent."""
    
    messages: Annotated[list, "Conversation messages"]
    nautobot_context: dict = Field(default_factory=dict)
    tool_results: dict = Field(default_factory=dict)
    current_task: Optional[str] = Field(default=None)
    requires_approval: bool = Field(default=False)
    error_count: int = Field(default=0)


async def build_agent_v2(
    llm_model=None,
    checkpointer=None,
    provider: str | None = None,
) -> StateGraph:
    """Build agent using StateGraph with typed state.
    
    This is the v2 approach that uses explicit state graphs for better
    observability, conditional routing, and parallelization.
    """
    from ai_ops.models import LLMModel
    from ai_ops.helpers.get_middleware import get_middleware
    from ai_ops.helpers.get_prompt import get_active_prompt
    
    # Get LLM model
    if llm_model is None:
        llm_model = await sync_to_async(LLMModel.get_default_model)()
    
    # Get MCP client and tools
    client, tools = await get_or_create_mcp_client()
    
    # Get LLM with optional provider override
    llm = await get_llm_model_async(model_name=llm_model.name, provider=provider)
    
    # Get middleware
    middleware = await get_middleware(llm_model)
    
    # Get system prompt
    system_prompt = await sync_to_async(get_active_prompt)(llm_model, tools=tools)
    
    # Create graph
    workflow = StateGraph(NautobotAgentState)
    
    # Define nodes
    workflow.add_node("preprocess", create_preprocess_node(middleware))
    workflow.add_node("agent", create_agent_node(llm, tools, system_prompt))
    workflow.add_node("postprocess", create_postprocess_node(middleware))
    workflow.add_node("error_handler", create_error_handler_node())
    
    # Define edges
    workflow.set_entry_point("preprocess")
    workflow.add_edge("preprocess", "agent")
    
    # Conditional routing based on errors
    workflow.add_conditional_edges(
        "agent",
        should_retry_or_complete,
        {
            "postprocess": "postprocess",
            "error_handler": "error_handler",
        }
    )
    
    workflow.add_edge("error_handler", "agent")  # Retry after error handling
    workflow.add_edge("postprocess", END)
    
    return workflow.compile(checkpointer=checkpointer)


def create_agent_node(llm, tools, system_prompt):
    """Create the main agent node."""
    from langchain.agents import create_agent
    
    agent_graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )
    
    async def agent_node(state: NautobotAgentState) -> NautobotAgentState:
        """Execute agent with tools."""
        try:
            result = await agent_graph.ainvoke({"messages": state["messages"]})
            state["messages"] = result["messages"]
            state["error_count"] = 0  # Reset on success
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            state["error_count"] += 1
            state["messages"].append(AIMessage(content=f"Error: {str(e)}"))
        
        return state
    
    return agent_node


def should_retry_or_complete(state: NautobotAgentState) -> str:
    """Decide whether to retry, handle error, or complete."""
    max_retries = 3
    
    if state["error_count"] > 0:
        if state["error_count"] < max_retries:
            return "error_handler"
        else:
            # Max retries exceeded, complete with error message
            return "postprocess"
    
    return "postprocess"
```

### Example 2: Human-in-the-Loop Approval Workflow

**File:** `ai_ops/agents/workflows/approval_workflow.py`

```python
"""Workflow for operations requiring human approval."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from ai_ops.agents.multi_mcp_agent_v2 import NautobotAgentState


class ApprovalState(NautobotAgentState):
    """State for approval workflows."""
    proposed_action: dict = Field(default_factory=dict)
    approval_status: Optional[str] = Field(default=None)  # "pending", "approved", "rejected"
    approver_comment: Optional[str] = Field(default=None)


def create_approval_workflow():
    """Create a workflow that requires human approval before executing changes."""
    
    workflow = StateGraph(ApprovalState)
    
    # Nodes
    workflow.add_node("analyze", analyze_request)
    workflow.add_node("propose_action", propose_action)
    workflow.add_node("await_approval", await_approval)
    workflow.add_node("execute_action", execute_action)
    workflow.add_node("report_result", report_result)
    
    # Edges
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "propose_action")
    workflow.add_edge("propose_action", "await_approval")
    
    # Conditional routing based on approval
    workflow.add_conditional_edges(
        "await_approval",
        check_approval,
        {
            "pending": "await_approval",  # Loop until decision
            "approved": "execute_action",
            "rejected": "report_result"
        }
    )
    
    workflow.add_edge("execute_action", "report_result")
    workflow.add_edge("report_result", END)
    
    return workflow.compile(checkpointer=MemorySaver())


async def propose_action(state: ApprovalState) -> ApprovalState:
    """Generate a proposed action based on analysis."""
    llm = await get_llm_model_async()
    
    proposal_prompt = f"""
    Based on the analysis, propose a specific action to take.
    Include:
    1. What will be changed
    2. Why this change is needed
    3. Potential risks
    4. Rollback procedure
    
    User request: {state["messages"][-1].content}
    """
    
    response = await llm.ainvoke(proposal_prompt)
    
    state["proposed_action"] = {
        "description": response.content,
        "timestamp": datetime.now().isoformat(),
    }
    state["approval_status"] = "pending"
    
    # Add message to conversation
    state["messages"].append(AIMessage(
        content=f"Proposed action:\n\n{response.content}\n\n"
                "Please review and approve or reject this action."
    ))
    
    return state


async def await_approval(state: ApprovalState) -> ApprovalState:
    """Wait for human approval (this is called repeatedly until approval is given)."""
    # In practice, this would check a database flag or interrupt signal
    # For now, we'll use the Interrupt pattern from LangGraph
    
    # This node is effectively a "breakpoint" where the graph pauses
    # and waits for external input (approval decision)
    
    # The frontend would call the graph's update_state() method to set
    # approval_status to "approved" or "rejected"
    
    return state


def check_approval(state: ApprovalState) -> str:
    """Check approval status."""
    status = state.get("approval_status", "pending")
    
    if status == "approved":
        logger.info("Action approved by user")
        return "approved"
    elif status == "rejected":
        logger.info("Action rejected by user")
        return "rejected"
    else:
        return "pending"


# Usage in view:
async def handle_approval_workflow_request(request):
    """Handle requests that require approval."""
    workflow = create_approval_workflow()
    thread_id = request.session.session_key
    
    # Initial invocation
    if request.POST.get("action") == "start":
        result = await workflow.ainvoke(
            {
                "messages": [HumanMessage(content=request.POST.get("message"))],
            },
            config={"configurable": {"thread_id": thread_id}}
        )
        
        return JsonResponse({
            "status": "pending_approval",
            "proposed_action": result["proposed_action"],
            "thread_id": thread_id
        })
    
    # Handle approval decision
    elif request.POST.get("action") == "approve":
        # Update state with approval
        workflow.update_state(
            config={"configurable": {"thread_id": thread_id}},
            values={"approval_status": "approved"}
        )
        
        # Continue execution
        result = await workflow.ainvoke(
            None,  # Continue from current state
            config={"configurable": {"thread_id": thread_id}}
        )
        
        return JsonResponse({
            "status": "completed",
            "result": result["messages"][-1].content
        })
```

### Example 3: Parallel Tool Execution with LangGraph

**File:** `ai_ops/agents/workflows/parallel_workflow.py`

```python
"""Workflow demonstrating parallel tool execution for independent tasks."""

from langgraph.graph import StateGraph, END


def create_parallel_data_gathering_workflow():
    """Create a workflow that gathers data from multiple sources in parallel."""
    
    workflow = StateGraph(NautobotAgentState)
    
    # Nodes for parallel execution
    workflow.add_node("fetch_topology", fetch_topology_data)
    workflow.add_node("fetch_telemetry", fetch_telemetry_data)
    workflow.add_node("fetch_config", fetch_config_data)
    workflow.add_node("synthesize", synthesize_results)
    
    # Entry point
    workflow.set_entry_point("fetch_topology")
    
    # Parallel branches
    workflow.add_edge("fetch_topology", "synthesize")
    workflow.add_edge("fetch_telemetry", "synthesize")
    workflow.add_edge("fetch_config", "synthesize")
    
    # Note: To actually execute in parallel, use Send() API:
    # workflow.add_conditional_edges(
    #     START,
    #     lambda _: [
    #         Send("fetch_topology", ...),
    #         Send("fetch_telemetry", ...),
    #         Send("fetch_config", ...)
    #     ]
    # )
    
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()


async def fetch_topology_data(state: NautobotAgentState) -> NautobotAgentState:
    """Fetch topology data (runs in parallel)."""
    client, tools = await get_or_create_mcp_client()
    
    # Find and call topology tool
    result = await call_mcp_tool(client, "topology", {...})
    state["tool_results"]["topology"] = result
    
    return state


async def synthesize_results(state: NautobotAgentState) -> NautobotAgentState:
    """Synthesize results from all parallel branches."""
    llm = await get_llm_model_async()
    
    synthesis_prompt = f"""
    Synthesize insights from these data sources:
    
    Topology: {state["tool_results"].get("topology", "N/A")}
    Telemetry: {state["tool_results"].get("telemetry", "N/A")}
    Config: {state["tool_results"].get("config", "N/A")}
    
    Provide a comprehensive analysis.
    """
    
    response = await llm.ainvoke(synthesis_prompt)
    state["messages"].append(AIMessage(content=response.content))
    
    return state
```

---

## 5. Migration Plan

### Phase 1: Foundation (Week 1-2) - Quick Wins

**Goal:** Improve existing code without breaking changes

#### Tasks:
1. **Add Typed State Models**
   - [ ] Create `NautobotAgentState` Pydantic model
   - [ ] Update `build_agent()` to accept typed state
   - [ ] Maintain backward compatibility with dict-based state

2. **Enhance Error Handling**
   - [ ] Create `ErrorHandlingMiddleware`
   - [ ] Add structured logging for all agent invocations
   - [ ] Implement correlation ID tracing end-to-end

3. **Improve Tool Wrappers**
   - [ ] Create `@tool` wrappers for top 5 MCP tools
   - [ ] Add input validation with Pydantic schemas
   - [ ] Centralize tool error handling

4. **Documentation**
   - [ ] Document current architecture (this file)
   - [ ] Create developer guide for adding new workflows
   - [ ] Add inline comments to complex orchestration logic

**Expected Impact:**
- Better error messages for users
- Easier debugging for developers
- Foundation for Phase 2 work

### Phase 2: Intermediate (Week 3-5) - LangGraph Workflows

**Goal:** Introduce explicit workflows for complex operations

#### Tasks:
1. **Create First LangGraph Workflow**
   - [ ] Identify top use case for multi-step workflow (e.g., "Config Compliance Check")
   - [ ] Implement using `StateGraph` with typed state
   - [ ] Add unit tests for each node
   - [ ] Deploy behind feature flag

2. **Refactor build_agent() to build_agent_v2()**
   - [ ] Create new `build_agent_v2()` with explicit graph
   - [ ] Add conditional routing for error handling
   - [ ] Parallel execution for independent middleware
   - [ ] Keep `build_agent()` as fallback for compatibility

3. **Implement Human-in-the-Loop Pattern**
   - [ ] Create approval workflow template
   - [ ] Add database model for approval requests
   - [ ] Build UI components for approval interface
   - [ ] Add API endpoints for approval actions

4. **Testing & Validation**
   - [ ] Unit tests for all workflow nodes
   - [ ] Integration tests for end-to-end workflows
   - [ ] Load testing with complex workflows
   - [ ] User acceptance testing

**Expected Impact:**
- Support for complex multi-step workflows
- Human approval gates for sensitive operations
- Better visibility into agent decision-making

### Phase 3: Advanced (Week 6-8) - Multi-Agent & Optimization

**Goal:** Implement specialist agents and advanced patterns

#### Tasks:
1. **Implement Planner/Executor Pattern**
   - [ ] Create planner agent (GPT-4 for complex reasoning)
   - [ ] Create executor agent (faster model + tools)
   - [ ] Add replanning logic for failed executions
   - [ ] Benchmark against single-agent baseline

2. **Build Specialist Agents**
   - [ ] Define agent roles (Topology, Telemetry, Config, Remediation)
   - [ ] Create routing logic (query classifier)
   - [ ] Implement specialist-specific prompts
   - [ ] Add specialist selection UI (for admins)

3. **Advanced Observability**
   - [ ] Integrate LangSmith for production tracing
   - [ ] Add token usage tracking and cost analytics
   - [ ] Create dashboard for agent performance metrics
   - [ ] Set up alerting for agent failures

4. **Optimization**
   - [ ] Benchmark workflow execution times
   - [ ] Optimize MCP client caching strategy
   - [ ] Implement parallel tool execution
   - [ ] Add request queuing for rate limiting

**Expected Impact:**
- 30-50% faster response times (via specialists)
- Better handling of complex queries
- Full observability into agent behavior
- Cost optimization through intelligent routing

### Phase 4: Production Hardening (Week 9-10)

**Goal:** Ensure production readiness

#### Tasks:
1. **Persistent State Management**
   - [ ] Migrate from MemorySaver to PostgreSQL checkpointer
   - [ ] Implement checkpoint cleanup policies
   - [ ] Add state backup/restore for disaster recovery

2. **Security Enhancements**
   - [ ] Implement prompt injection detection
   - [ ] Add tool usage rate limiting per user
   - [ ] Audit logging for all sensitive operations
   - [ ] Security review of all workflows

3. **Documentation & Training**
   - [ ] Complete developer documentation
   - [ ] Create user guide for new workflows
   - [ ] Record training videos
   - [ ] Conduct team training sessions

4. **Monitoring & Alerting**
   - [ ] Production health checks for all workflows
   - [ ] SLO definition and monitoring
   - [ ] Incident response playbook
   - [ ] On-call rotation setup

**Expected Impact:**
- Production-ready system
- Full team enablement
- Comprehensive monitoring

---

## 6. Success Metrics

### Developer Experience
- **Code maintainability:** -30% lines of code in orchestration logic
- **Test coverage:** 90%+ for workflow nodes
- **Development velocity:** 50% faster to add new workflows

### User Experience
- **Response time:** <5s for simple queries, <30s for complex workflows
- **Error rate:** <1% of requests result in unhandled errors
- **Success rate:** >95% of queries result in useful responses

### Operational Excellence
- **Observability:** 100% of agent invocations traced
- **Cost efficiency:** 20% reduction in token usage via intelligent routing
- **Reliability:** 99.9% uptime for agent service

---

## 7. Risks & Mitigation

### Risk 1: Breaking Changes
**Mitigation:**
- Maintain backward compatibility throughout migration
- Use feature flags for new workflows
- Comprehensive testing before cutover

### Risk 2: Performance Degradation
**Mitigation:**
- Benchmark all changes against baseline
- Use parallel execution where possible
- Optimize hot paths (MCP client, middleware)

### Risk 3: Increased Complexity
**Mitigation:**
- Thorough documentation of all workflows
- Developer training sessions
- Code review guidelines for workflows

### Risk 4: LangGraph/LangChain API Changes
**Mitigation:**
- Pin dependency versions in production
- Monitor upstream changelogs
- Maintain compatibility layer for major changes

---

## 8. Appendix

### A. LangGraph vs Current Approach Comparison

| Aspect | Current (create_agent) | Proposed (StateGraph) |
|--------|------------------------|----------------------|
| **State** | Implicit dict | Typed Pydantic model |
| **Flow** | Linear (LLM→Tools→LLM) | Explicit graph with branches |
| **Conditional Logic** | In LLM's reasoning | Graph edges |
| **Parallelization** | No | Yes (via Send API) |
| **Human-in-Loop** | Manual implementation | Built-in (Interrupt pattern) |
| **Observability** | Callbacks only | Full state snapshots |
| **Checkpointing** | Messages only | Full state persistence |

### B. Recommended Reading

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph How-to Guides](https://langchain-ai.github.io/langgraph/how-tos/)
- [Multi-Agent Patterns in LangGraph](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/)
- [Human-in-the-Loop Pattern](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)
- [LangSmith Tracing](https://docs.smith.langchain.com/)

### C. Related Work

- **AutoGPT:** Autonomous agent with goal-driven planning
- **BabyAGI:** Task-driven autonomous agent
- **MetaGPT:** Multi-agent collaboration framework
- **CrewAI:** Role-based multi-agent framework

---

**Document Status:** ✅ Ready for Review  
**Next Steps:** Team review → Phase 1 implementation → Iterative deployment

