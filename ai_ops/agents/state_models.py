"""Typed state models for LangGraph workflows.

This module provides Pydantic-based state models for agent workflows,
enabling type safety, validation, and better IDE support.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    INITIALIZED = "initialized"
    PLANNING = "planning"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    """Status of approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class NautobotAgentState(MessagesState):
    """Base typed state for Nautobot AI agent workflows.

    Extends LangGraph's MessagesState with custom fields for Nautobot-specific context.
    This enables type-safe state management and better observability.

    Attributes:
        messages: Inherited from MessagesState - conversation history
        nautobot_context: Nautobot-specific context (device IDs, locations, etc.)
        tool_results: Cache of tool execution results for reuse
        current_task: Description of current task being executed
        workflow_status: Current status of the workflow
        error_count: Number of errors encountered in this workflow
        requires_approval: Flag indicating human approval is needed
        metadata: Additional metadata for logging/tracing
    """

    # Inherited from MessagesState:
    # messages: Annotated[list, "Conversation messages"]

    # Custom fields for Nautobot workflows
    nautobot_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Nautobot-specific context: device IDs, locations, IP ranges, etc.",
    )

    tool_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Cache of tool execution results (key=tool_name, value=result)",
    )

    current_task: Optional[str] = Field(
        default=None,
        description="Description of the current task being executed",
    )

    workflow_status: WorkflowStatus = Field(
        default=WorkflowStatus.INITIALIZED,
        description="Current status of the workflow execution",
    )

    error_count: int = Field(
        default=0,
        ge=0,
        description="Number of errors encountered during workflow execution",
    )

    requires_approval: bool = Field(
        default=False,
        description="Flag indicating whether human approval is required",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for logging, tracing, and analytics",
    )


class PlanExecuteState(NautobotAgentState):
    """State for planner/executor multi-agent pattern.

    Used when separating planning from execution - one agent creates a plan,
    another agent executes it step-by-step.

    Attributes:
        plan: List of planned steps (each step is a dict with action, tools, etc.)
        current_step_index: Index of the current step being executed
        execution_results: Results from each executed step
        replanning_count: Number of times the plan has been regenerated
    """

    plan: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Execution plan - list of steps with actions, tools, and expected outputs",
    )

    current_step_index: int = Field(
        default=0,
        ge=0,
        description="Index of the current step being executed (0-based)",
    )

    execution_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Results from each executed step",
    )

    replanning_count: int = Field(
        default=0,
        ge=0,
        description="Number of times the plan has been regenerated due to failures",
    )


class ApprovalWorkflowState(NautobotAgentState):
    """State for workflows requiring human approval.

    Used when sensitive operations need human confirmation before execution.

    Attributes:
        proposed_action: Details of the action proposed for approval
        approval_status: Current approval status (pending/approved/rejected)
        approver: Username of the person who approved/rejected
        approval_timestamp: When the approval decision was made
        approver_comment: Optional comment from the approver
    """

    proposed_action: dict[str, Any] = Field(
        default_factory=dict,
        description="Details of the proposed action: description, changes, risks, rollback",
    )

    approval_status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Current approval status",
    )

    approver: Optional[str] = Field(
        default=None,
        description="Username of the person who approved/rejected",
    )

    approval_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the approval decision was made",
    )

    approver_comment: Optional[str] = Field(
        default=None,
        description="Optional comment from the approver explaining their decision",
    )


class SpecialistRoutingState(NautobotAgentState):
    """State for specialist agent routing pattern.

    Used when routing queries to specialist agents based on domain expertise.

    Attributes:
        query_classification: Classification of the user query (topology/telemetry/config/etc.)
        assigned_specialist: Name of the specialist agent assigned to this query
        specialist_confidence: Confidence score for the specialist assignment (0-1)
        fallback_to_generalist: Flag indicating fallback to generalist agent
    """

    query_classification: Optional[str] = Field(
        default=None,
        description="Classification of user query (e.g., 'topology', 'telemetry', 'config')",
    )

    assigned_specialist: Optional[str] = Field(
        default=None,
        description="Name of the specialist agent assigned to handle this query",
    )

    specialist_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for specialist assignment (0.0-1.0)",
    )

    fallback_to_generalist: bool = Field(
        default=False,
        description="Whether to fallback to generalist agent if specialist fails",
    )


class ParallelExecutionState(NautobotAgentState):
    """State for parallel tool execution workflows.

    Used when multiple independent tasks can be executed concurrently.

    Attributes:
        parallel_tasks: List of tasks to execute in parallel
        completed_tasks: List of tasks that have completed
        failed_tasks: List of tasks that failed
        task_results: Results keyed by task name
    """

    parallel_tasks: list[str] = Field(
        default_factory=list,
        description="List of task names to execute in parallel",
    )

    completed_tasks: list[str] = Field(
        default_factory=list,
        description="List of task names that have completed successfully",
    )

    failed_tasks: list[str] = Field(
        default_factory=list,
        description="List of task names that failed during execution",
    )

    task_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Results from each parallel task (key=task_name, value=result)",
    )


# Type aliases for common state patterns
SimpleAgentState = NautobotAgentState
MultiStepWorkflowState = PlanExecuteState
HumanInLoopState = ApprovalWorkflowState
