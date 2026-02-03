# Migration Guide: From Manual Orchestration to LangGraph

This guide provides step-by-step instructions for migrating from the current manual orchestration patterns to LangGraph-based workflows.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Foundation](#phase-1-foundation)
3. [Phase 2: First Workflow](#phase-2-first-workflow)
4. [Phase 3: Advanced Patterns](#phase-3-advanced-patterns)
5. [Testing Strategy](#testing-strategy)
6. [Rollback Plan](#rollback-plan)

---

## Prerequisites

### Dependencies

Ensure these packages are installed (already in `pyproject.toml`):

```toml
[tool.poetry.dependencies]
langgraph = ">=0.2.0"
langchain = ">=0.3.0"
langchain-core = ">=0.3.0"
pydantic = ">=2.0.0"
```

### Knowledge Requirements

Team members should be familiar with:
- LangGraph basics (nodes, edges, state)
- Pydantic models
- Async/await patterns in Python
- LangChain concepts (tools, agents, callbacks)

**Recommended Reading:**
- [LangGraph Quick Start](https://langchain-ai.github.io/langgraph/tutorials/quickstart/)
- [LangGraph How-To Guides](https://langchain-ai.github.io/langgraph/how-tos/)

---

## Phase 1: Foundation

### Step 1.1: Add Typed State Models (Week 1)

**File:** `ai_ops/agents/state_models.py` (already created)

**What to do:**
1. Review the typed state models in `state_models.py`
2. Understand the base `NautobotAgentState` structure
3. Familiarize yourself with specialized states (`PlanExecuteState`, `ApprovalWorkflowState`, etc.)

**Testing:**
```python
# Test state model instantiation
from ai_ops.agents.state_models import NautobotAgentState
from langchain_core.messages import HumanMessage

state = NautobotAgentState(
    messages=[HumanMessage(content="Test message")],
    nautobot_context={"device_id": "12345"},
    current_task="Test task"
)

assert state.workflow_status == WorkflowStatus.INITIALIZED
assert state.error_count == 0
```

### Step 1.2: Create Compatibility Layer (Week 1)

**Goal:** Allow gradual migration without breaking existing code

**File:** `ai_ops/agents/compat.py`

```python
"""Compatibility layer for gradual migration from v1 to v2 agent architecture.

This module provides a compatibility wrapper to enable incremental migration
from the current agent architecture (v1) to the improved v2 architecture
with explicit LangGraph StateGraphs, typed state models, and advanced patterns.

Note: Both v1 and v2 use LangGraph's create_agent() function, but v2 adds:
- Typed Pydantic state models
- Explicit StateGraph workflows for complex operations
- Conditional routing and multi-agent patterns
"""

from typing import Any, Optional
from ai_ops.agents.multi_mcp_agent import build_agent as build_agent_v1
from ai_ops.agents.state_models import NautobotAgentState


async def build_agent_compat(
    llm_model=None,
    checkpointer=None,
    provider: Optional[str] = None,
    use_v2: bool = False
) -> Any:
    """Build agent with backward compatibility between v1 and v2 architectures.
    
    Args:
        llm_model: LLMModel instance
        checkpointer: Checkpointer for conversation persistence
        provider: Optional provider override
        use_v2: If True, use v2 agent architecture with explicit StateGraphs
                If False, use v1 agent architecture (default)
    
    Returns:
        Compiled agent graph (compatible interface for both v1 and v2)
    """
    if use_v2:
        # Import v2 when ready
        from ai_ops.agents.multi_mcp_agent_v2 import build_agent_v2
        return await build_agent_v2(llm_model, checkpointer, provider)
    else:
        # Use existing v1 implementation
        return await build_agent_v1(llm_model, checkpointer, provider)
```

**Usage in views.py:**
```python
# In process_message():
from ai_ops.agents.compat import build_agent_compat

# Check feature flag (e.g., from Constance)
use_v2_agent = await sync_to_async(get_app_settings_or_config)("ai_ops", "use_langgraph_v2")

graph = await build_agent_compat(
    checkpointer=checkpointer,
    provider=provider,
    use_v2=use_v2_agent  # Defaults to False (v1)
)
```

### Step 1.3: Add Configuration (Week 1)

**File:** Update `ai_ops/app-config-schema.json`

```json
{
  "use_langgraph_v2": {
    "default": false,
    "help_text": "Enable LangGraph v2 agent architecture (experimental)",
    "field_type": "boolean"
  },
  "enable_planner_executor": {
    "default": false,
    "help_text": "Enable planner/executor workflow for complex queries",
    "field_type": "boolean"
  }
}
```

**Testing:**
```bash
# In Nautobot admin interface, verify new settings appear
# Navigate to: Plugins > AI Ops > Configuration
```

---

## Phase 2: First Workflow

### Step 2.1: Implement Planner/Executor Workflow (Week 2-3)

**File:** `ai_ops/agents/workflows/planner_executor.py` (already created)

**What to do:**
1. Review the planner/executor implementation
2. Test with simple queries first
3. Monitor performance vs. existing single-agent approach

**Testing Script:** `test_planner_executor.py`

```python
"""Test script for planner/executor workflow."""

import asyncio
from langchain_core.messages import HumanMessage
from ai_ops.agents.workflows.planner_executor import create_planner_executor_workflow
from ai_ops.checkpointer import get_checkpointer


async def test_simple_query():
    """Test planner/executor with a simple query."""
    async with get_checkpointer() as checkpointer:
        workflow = create_planner_executor_workflow(checkpointer)
        
        result = await workflow.ainvoke(
            {
                "messages": [HumanMessage(content="List all devices in datacenter-1")],
            },
            config={"configurable": {"thread_id": "test-123"}}
        )
        
        print(f"Status: {result['workflow_status']}")
        print(f"Steps executed: {len(result['execution_results'])}")
        print(f"Response: {result['messages'][-1].content}")


async def test_complex_query():
    """Test with a multi-step query."""
    async with get_checkpointer() as checkpointer:
        workflow = create_planner_executor_workflow(checkpointer)
        
        result = await workflow.ainvoke(
            {
                "messages": [HumanMessage(
                    content="Analyze topology for datacenter-1, identify devices with >80% CPU, and recommend remediation"
                )],
            },
            config={"configurable": {"thread_id": "test-456"}}
        )
        
        print(f"Plan had {len(result['plan'])} steps")
        print(f"Replanning attempts: {result['replanning_count']}")
        assert result['workflow_status'] == 'completed'


if __name__ == "__main__":
    asyncio.run(test_simple_query())
    asyncio.run(test_complex_query())
```

**Run Tests:**
```bash
cd /home/runner/work/nautobot-ai-ops/nautobot-ai-ops
invoke cli -- python test_planner_executor.py
```

### Step 2.2: Add Workflow Router (Week 3)

**Goal:** Automatically route queries to appropriate workflow

**File:** `ai_ops/agents/router.py`

```python
"""Intelligent routing to appropriate workflows."""

import logging
from typing import Literal
from ai_ops.helpers.get_llm_model import get_llm_model_async
from langchain_core.messages import SystemMessage

logger = logging.getLogger(__name__)

WorkflowType = Literal["simple", "planner_executor", "approval_required"]


async def route_to_workflow(user_message: str) -> WorkflowType:
    """Route user message to appropriate workflow.
    
    Args:
        user_message: The user's input message
        
    Returns:
        Workflow type to use
    """
    # Use fast, cheap model for routing
    router_llm = await get_llm_model_async(temperature=0.0)
    
    routing_prompt = f"""Classify this user request into ONE category:

1. simple - Single-step queries (list devices, show status, simple lookups)
2. planner_executor - Multi-step analysis or complex workflows  
3. approval_required - Changes that need human approval (config changes, reboots)

User request: {user_message}

Return ONLY the category name (one word).
"""
    
    response = await router_llm.ainvoke([SystemMessage(content=routing_prompt)])
    workflow_type = response.content.strip().lower()
    
    if workflow_type not in ["simple", "planner_executor", "approval_required"]:
        logger.warning(f"Unknown workflow type '{workflow_type}', defaulting to simple")
        workflow_type = "simple"
    
    logger.info(f"[Router] Classified as: {workflow_type}")
    return workflow_type


async def build_agent_with_routing(
    user_message: str,
    llm_model=None,
    checkpointer=None,
    provider=None
):
    """Build agent with intelligent workflow routing.
    
    Args:
        user_message: User's input message
        llm_model: LLMModel instance
        checkpointer: Checkpointer for state
        provider: Optional provider override
        
    Returns:
        Compiled workflow appropriate for the query
    """
    workflow_type = await route_to_workflow(user_message)
    
    if workflow_type == "planner_executor":
        from ai_ops.agents.workflows.planner_executor import create_planner_executor_workflow
        return create_planner_executor_workflow(checkpointer)
    
    elif workflow_type == "approval_required":
        # TODO: Implement approval workflow
        logger.info("Approval workflow not yet implemented, using simple")
        from ai_ops.agents.multi_mcp_agent import build_agent
        return await build_agent(llm_model, checkpointer, provider)
    
    else:  # simple
        from ai_ops.agents.multi_mcp_agent import build_agent
        return await build_agent(llm_model, checkpointer, provider)
```

**Update views.py:**
```python
# In ChatMessageView.post():
if use_v2_agent:
    from ai_ops.agents.router import build_agent_with_routing
    graph = await build_agent_with_routing(
        user_message=user_message,
        checkpointer=checkpointer,
        provider=provider_override
    )
else:
    graph = await build_agent(checkpointer=checkpointer, provider=provider_override)
```

### Step 2.3: Add Observability (Week 3)

**File:** `ai_ops/helpers/workflow_metrics.py`

```python
"""Metrics collection for workflow execution."""

import time
import logging
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class WorkflowMetrics:
    """Collect metrics for workflow execution."""
    
    def __init__(self, workflow_type: str, thread_id: str):
        self.workflow_type = workflow_type
        self.thread_id = thread_id
        self.start_time = time.time()
        self.node_times = {}
        self.tool_calls = 0
        self.error_count = 0
    
    def record_node_execution(self, node_name: str, duration: float):
        """Record execution time for a node."""
        self.node_times[node_name] = duration
        logger.info(f"[Metrics] {node_name} took {duration:.2f}s")
    
    def record_tool_call(self):
        """Increment tool call counter."""
        self.tool_calls += 1
    
    def record_error(self):
        """Increment error counter."""
        self.error_count += 1
    
    def get_summary(self) -> dict:
        """Get metrics summary."""
        total_time = time.time() - self.start_time
        return {
            "workflow_type": self.workflow_type,
            "thread_id": self.thread_id,
            "total_time": total_time,
            "node_times": self.node_times,
            "tool_calls": self.tool_calls,
            "error_count": self.error_count,
        }


@asynccontextmanager
async def track_workflow_metrics(workflow_type: str, thread_id: str):
    """Context manager for tracking workflow metrics."""
    metrics = WorkflowMetrics(workflow_type, thread_id)
    try:
        yield metrics
    finally:
        summary = metrics.get_summary()
        logger.info(f"[Metrics] Workflow completed: {summary}")
        # TODO: Store in database for analytics
```

**Usage:**
```python
from ai_ops.helpers.workflow_metrics import track_workflow_metrics

async with track_workflow_metrics("planner_executor", thread_id) as metrics:
    result = await workflow.ainvoke(state, config)
    
    # Metrics are automatically logged on exit
```

---

## Phase 3: Advanced Patterns

### Step 3.1: Human-in-the-Loop Approval (Week 4)

**File:** `ai_ops/agents/workflows/approval_workflow.py`

See full implementation in main analysis document, Section 4, Example 2.

**Key Features:**
- Workflow pauses at approval gate
- Frontend polls for approval status
- Admin can approve/reject via API
- Approved actions execute automatically

**Testing:**
```python
async def test_approval_workflow():
    """Test approval workflow."""
    workflow = create_approval_workflow()
    
    # Start workflow
    result = await workflow.ainvoke({
        "messages": [HumanMessage(content="Reboot device core-sw-01")]
    }, config={"configurable": {"thread_id": "approval-test"}})
    
    # Should be waiting for approval
    assert result["approval_status"] == "pending"
    assert result["proposed_action"] is not None
    
    # Simulate approval
    workflow.update_state(
        config={"configurable": {"thread_id": "approval-test"}},
        values={"approval_status": "approved"}
    )
    
    # Continue execution
    result = await workflow.ainvoke(
        None,
        config={"configurable": {"thread_id": "approval-test"}}
    )
    
    assert result["workflow_status"] == "completed"
```

### Step 3.2: Specialist Agent Routing (Week 5)

**File:** `ai_ops/agents/specialists.py`

```python
"""Specialist agent definitions and routing."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class AgentRole(str, Enum):
    """Specialist agent roles."""
    TOPOLOGY_EXPERT = "topology_expert"
    TELEMETRY_ANALYZER = "telemetry_analyzer"
    CONFIG_SPECIALIST = "config_specialist"
    REMEDIATION_PLANNER = "remediation_planner"


class SpecialistConfig(BaseModel):
    """Configuration for a specialist agent."""
    role: AgentRole
    system_prompt: str
    tools: list[str]
    model_name: Optional[str] = None


SPECIALISTS = {
    AgentRole.TOPOLOGY_EXPERT: SpecialistConfig(
        role=AgentRole.TOPOLOGY_EXPERT,
        system_prompt="""You are a network topology expert.
        Specialize in: device connectivity, path analysis, network graphs.
        Always verify topology data before making recommendations.""",
        tools=["query_topology", "find_path", "identify_loops"],
        model_name="gpt-4"  # Use better model for complex analysis
    ),
    
    AgentRole.TELEMETRY_ANALYZER: SpecialistConfig(
        role=AgentRole.TELEMETRY_ANALYZER,
        system_prompt="""You are a telemetry and monitoring expert.
        Specialize in: metrics analysis, anomaly detection, trends.
        Use time-series data to support your conclusions.""",
        tools=["query_metrics", "detect_anomalies", "compare_baselines"]
    ),
}


async def route_to_specialist(query: str) -> AgentRole:
    """Route query to appropriate specialist."""
    from ai_ops.helpers.get_llm_model import get_llm_model_async
    from langchain_core.messages import SystemMessage
    
    router = await get_llm_model_async(temperature=0.0)
    
    prompt = f"""Classify into ONE category:
    - topology_expert: Network topology, connectivity, paths
    - telemetry_analyzer: Metrics, performance, monitoring
    - config_specialist: Configuration, compliance
    - remediation_planner: Issue fixing, change planning
    
    Query: {query}
    
    Return ONLY the category name."""
    
    response = await router.ainvoke([SystemMessage(content=prompt)])
    role = response.content.strip().lower()
    
    try:
        return AgentRole(role)
    except ValueError:
        return AgentRole.TOPOLOGY_EXPERT  # Default
```

### Step 3.3: Parallel Execution (Week 6)

**Goal:** Execute independent tasks concurrently

**Example:** Gather topology, telemetry, and config data in parallel

See full implementation in main analysis document, Section 4, Example 3.

---

## Testing Strategy

### Unit Tests

**File:** `ai_ops/tests/test_workflows.py`

```python
"""Unit tests for LangGraph workflows."""

import pytest
from langchain_core.messages import HumanMessage
from ai_ops.agents.state_models import PlanExecuteState, WorkflowStatus
from ai_ops.agents.workflows.planner_executor import (
    planner_node,
    executor_node,
    should_continue_or_replan
)


@pytest.mark.asyncio
async def test_planner_node():
    """Test planner node generates a valid plan."""
    state = PlanExecuteState(
        messages=[HumanMessage(content="List all devices")]
    )
    
    result = await planner_node(state)
    
    assert "plan" in result
    assert isinstance(result["plan"], list)
    assert len(result["plan"]) > 0
    assert result["workflow_status"] == WorkflowStatus.PLANNING


@pytest.mark.asyncio
async def test_executor_node():
    """Test executor node executes a plan step."""
    state = PlanExecuteState(
        messages=[HumanMessage(content="Test")],
        plan=[{
            "step_number": 1,
            "action": "List devices",
            "tools_needed": [],
            "expected_output": "Device list",
            "success_criteria": "Response received"
        }],
        current_step_index=0
    )
    
    result = await executor_node(state)
    
    assert len(result["execution_results"]) == 1
    assert result["current_step_index"] == 1


def test_routing_logic():
    """Test routing decisions."""
    # All steps complete
    state = PlanExecuteState(
        plan=[{"step": 1}],
        current_step_index=1,
        execution_results=[{"success": True}]
    )
    assert should_continue_or_replan(state) == "complete"
    
    # Step failed, replan needed
    state = PlanExecuteState(
        plan=[{"step": 1}, {"step": 2}],
        current_step_index=1,
        execution_results=[{"success": False}],
        replanning_count=0
    )
    assert should_continue_or_replan(state) == "replan"
```

### Integration Tests

```python
"""Integration tests for end-to-end workflows."""

import pytest
from ai_ops.agents.router import build_agent_with_routing
from ai_ops.checkpointer import get_checkpointer


@pytest.mark.asyncio
async def test_simple_query_routing():
    """Test that simple queries use simple workflow."""
    async with get_checkpointer() as checkpointer:
        workflow = await build_agent_with_routing(
            user_message="Show status of device core-sw-01",
            checkpointer=checkpointer
        )
        
        result = await workflow.ainvoke(
            {"messages": [HumanMessage(content="Show status")]},
            config={"configurable": {"thread_id": "test-routing-1"}}
        )
        
        assert result["messages"][-1].content is not None


@pytest.mark.asyncio
async def test_complex_query_routing():
    """Test that complex queries use planner/executor."""
    async with get_checkpointer() as checkpointer:
        workflow = await build_agent_with_routing(
            user_message="Analyze topology and identify high CPU devices",
            checkpointer=checkpointer
        )
        
        result = await workflow.ainvoke(
            {"messages": [HumanMessage(content="Analyze topology")]},
            config={"configurable": {"thread_id": "test-routing-2"}}
        )
        
        # Should have a plan
        assert "plan" in result
        assert len(result["plan"]) > 1
```

### Performance Tests

```bash
# Benchmark single-agent vs planner/executor
invoke cli -- python -m pytest ai_ops/tests/test_performance.py --benchmark
```

---

## Rollback Plan

### If Issues Arise

1. **Disable Feature Flag**
   ```python
   # In Nautobot admin
   use_langgraph_v2 = False
   ```

2. **Revert to v1**
   ```python
   # views.py automatically falls back to build_agent()
   graph = await build_agent(checkpointer=checkpointer, provider=provider)
   ```

3. **Monitor Logs**
   ```bash
   # Check for errors
   tail -f /var/log/nautobot/nautobot.log | grep -i "workflow\|langgraph"
   ```

4. **Database Rollback** (if schema changes)
   ```bash
   nautobot-server migrate ai_ops <previous_migration>
   ```

### Gradual Rollout

**Week 1-2:** Internal testing only (dev environment)
**Week 3:** Beta testing with 10% of users (via feature flag)
**Week 4:** 50% rollout
**Week 5:** Full rollout if metrics look good

### Success Criteria

- ✅ Response time <= current baseline
- ✅ Error rate < 1%
- ✅ User satisfaction score >= current
- ✅ 90%+ test coverage
- ✅ Zero production incidents

---

## Next Steps

1. Review this migration guide with the team
2. Schedule kickoff meeting (Week 1)
3. Assign Phase 1 tasks
4. Set up monitoring dashboards
5. Begin implementation!

**Questions?** Open an issue or discuss in #nautobot-ai-ops Slack channel.
