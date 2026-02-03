"""Example LangGraph workflow demonstrating planner/executor pattern.

This module shows how to implement a planner/executor multi-agent workflow
using typed state and explicit graph structure.
"""

import json
import logging
from typing import Any

from asgiref.sync import sync_to_async
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from ai_ops.agents.multi_mcp_agent import get_or_create_mcp_client
from ai_ops.agents.state_models import PlanExecuteState, WorkflowStatus
from ai_ops.helpers.get_llm_model import get_llm_model_async

logger = logging.getLogger(__name__)


# ============================================================================
# Workflow Builder
# ============================================================================


def create_planner_executor_workflow(checkpointer=None):
    """Create a planner/executor workflow using LangGraph.

    This workflow separates planning from execution:
    1. Planner agent creates a detailed execution plan
    2. Executor agent executes each step with tools
    3. Replanner agent adjusts the plan if steps fail
    4. Responder generates final user-facing response

    Args:
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(PlanExecuteState)

    # Define nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("replanner", replanner_node)
    workflow.add_node("responder", responder_node)

    # Define workflow edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "executor")

    # Conditional routing based on execution status
    workflow.add_conditional_edges(
        "executor",
        should_continue_or_replan,
        {
            "continue": "executor",  # Continue to next step
            "replan": "replanner",  # Replanning needed
            "complete": "responder",  # All steps complete
        },
    )

    workflow.add_edge("replanner", "executor")
    workflow.add_edge("responder", END)

    return workflow.compile(checkpointer=checkpointer)


# ============================================================================
# Node Implementations
# ============================================================================


async def planner_node(state: PlanExecuteState) -> PlanExecuteState:
    """Generate an execution plan using a planning-specialized LLM."""
    logger.info("[Planner] Generating execution plan...")
    state["workflow_status"] = WorkflowStatus.PLANNING

    try:
        planner_llm = await get_llm_model_async(temperature=0.0)
        user_message = state["messages"][-1].content

        _, tools = await get_or_create_mcp_client()
        tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in tools[:10]])

        planning_prompt = f"""You are a planning specialist for network operations.
Create a step-by-step plan for: {user_message}

Available tools: {tool_descriptions}

Return JSON array: [{{"step_number": 1, "action": "...", "tools_needed": [...], "expected_output": "...", "success_criteria": "..."}}]"""

        response = await planner_llm.ainvoke([SystemMessage(content=planning_prompt)])

        content = response.content.strip()
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()

        plan = json.loads(content)
        state["plan"] = plan
        state["current_step_index"] = 0
        state["execution_results"] = []

        plan_summary = "\n".join([f"{i + 1}. {step.get('action', 'N/A')}" for i, step in enumerate(plan)])
        state["messages"].append(AIMessage(content=f"Plan:\n{plan_summary}\n\nExecuting..."))

    except Exception as e:
        logger.error(f"[Planner] Error: {e}", exc_info=True)
        state["error_count"] += 1
        state["messages"].append(AIMessage(content=f"Planning failed: {str(e)}"))

    return state


async def executor_node(state: PlanExecuteState) -> PlanExecuteState:
    """Execute the current step in the plan."""
    logger.info(f"[Executor] Step {state['current_step_index'] + 1}/{len(state['plan'])}")
    state["workflow_status"] = WorkflowStatus.EXECUTING

    try:
        current_step = state["plan"][state["current_step_index"]]
        executor_llm = await get_llm_model_async()
        _, tools = await get_or_create_mcp_client()

        executor_agent = create_agent(
            model=executor_llm,
            tools=tools,
            system_prompt="Execute this step precisely.",
        )

        step_prompt = f"Execute: {current_step['action']}"
        result = await executor_agent.ainvoke({"messages": [HumanMessage(content=step_prompt)]})

        state["execution_results"].append({"step": current_step, "result": result["messages"][-1].content, "success": True})
        state["current_step_index"] += 1

    except Exception as e:
        logger.error(f"[Executor] Error: {e}", exc_info=True)
        state["error_count"] += 1
        state["execution_results"].append({"step": current_step, "result": None, "success": False, "error": str(e)})

    return state


async def replanner_node(state: PlanExecuteState) -> PlanExecuteState:
    """Adjust plan based on failures."""
    logger.info("[Replanner] Adjusting plan...")
    state["replanning_count"] += 1
    # Implementation omitted for brevity
    return state


async def responder_node(state: PlanExecuteState) -> PlanExecuteState:
    """Generate final response."""
    logger.info("[Responder] Generating response...")
    state["workflow_status"] = WorkflowStatus.COMPLETED
    state["messages"].append(AIMessage(content="Task completed."))
    return state


def should_continue_or_replan(state: PlanExecuteState) -> str:
    """Route decision."""
    if state["current_step_index"] >= len(state["plan"]):
        return "complete"
    if state["execution_results"] and not state["execution_results"][-1]["success"]:
        if state["replanning_count"] < 2:
            return "replan"
        return "complete"
    return "continue"
