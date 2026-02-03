"""Unit tests for typed state models and workflows."""

import pytest
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

from ai_ops.agents.state_models import (
    NautobotAgentState,
    PlanExecuteState,
    ApprovalWorkflowState,
    WorkflowStatus,
    ApprovalStatus,
)


class TestNautobotAgentState:
    """Test cases for base agent state model."""

    def test_state_initialization(self):
        """Test state initializes with correct defaults."""
        state = NautobotAgentState(
            messages=[HumanMessage(content="Test message")]
        )

        assert len(state["messages"]) == 1
        assert state["nautobot_context"] == {}
        assert state["tool_results"] == {}
        assert state["current_task"] is None
        assert state["workflow_status"] == WorkflowStatus.INITIALIZED
        assert state["error_count"] == 0
        assert state["requires_approval"] is False
        assert state["metadata"] == {}

    def test_state_with_context(self):
        """Test state with Nautobot context."""
        state = NautobotAgentState(
            messages=[HumanMessage(content="Test")],
            nautobot_context={
                "device_id": "12345",
                "location": "datacenter-1",
                "tenant": "customer-a"
            }
        )

        assert state["nautobot_context"]["device_id"] == "12345"
        assert state["nautobot_context"]["location"] == "datacenter-1"

    def test_state_error_tracking(self):
        """Test error count tracking."""
        state = NautobotAgentState(messages=[HumanMessage(content="Test")])

        state["error_count"] = 3
        assert state["error_count"] == 3

        # Error count should be non-negative (enforced by Pydantic)
        with pytest.raises(Exception):
            state = NautobotAgentState(
                messages=[HumanMessage(content="Test")],
                error_count=-1
            )

    def test_state_metadata(self):
        """Test metadata field for tracing."""
        state = NautobotAgentState(
            messages=[HumanMessage(content="Test")],
            metadata={
                "correlation_id": "abc-123",
                "user": "admin",
                "request_time": datetime.now().isoformat()
            }
        )

        assert "correlation_id" in state["metadata"]
        assert state["metadata"]["user"] == "admin"


class TestPlanExecuteState:
    """Test cases for planner/executor state."""

    def test_plan_initialization(self):
        """Test plan state initializes correctly."""
        state = PlanExecuteState(
            messages=[HumanMessage(content="Test")]
        )

        assert state["plan"] == []
        assert state["current_step_index"] == 0
        assert state["execution_results"] == []
        assert state["replanning_count"] == 0

    def test_plan_execution_tracking(self):
        """Test plan execution progress tracking."""
        plan = [
            {"step_number": 1, "action": "Fetch topology"},
            {"step_number": 2, "action": "Analyze data"},
            {"step_number": 3, "action": "Generate report"},
        ]

        state = PlanExecuteState(
            messages=[HumanMessage(content="Test")],
            plan=plan,
            current_step_index=0
        )

        # Simulate step execution
        state["execution_results"].append({
            "step": plan[0],
            "result": "Topology fetched successfully",
            "success": True
        })
        state["current_step_index"] += 1

        assert len(state["execution_results"]) == 1
        assert state["current_step_index"] == 1
        assert state["execution_results"][0]["success"] is True

    def test_replanning_logic(self):
        """Test replanning counter."""
        state = PlanExecuteState(
            messages=[HumanMessage(content="Test")],
            replanning_count=0
        )

        # Simulate replanning
        state["replanning_count"] += 1
        assert state["replanning_count"] == 1

        # Max replanning check
        state["replanning_count"] = 2
        max_replans = 2
        assert state["replanning_count"] >= max_replans


class TestApprovalWorkflowState:
    """Test cases for approval workflow state."""

    def test_approval_initialization(self):
        """Test approval state initializes with pending status."""
        state = ApprovalWorkflowState(
            messages=[HumanMessage(content="Reboot device")]
        )

        assert state["approval_status"] == ApprovalStatus.PENDING
        assert state["proposed_action"] == {}
        assert state["approver"] is None
        assert state["approval_timestamp"] is None
        assert state["approver_comment"] is None

    def test_approval_workflow(self):
        """Test approval workflow transitions."""
        state = ApprovalWorkflowState(
            messages=[HumanMessage(content="Reboot device")],
            proposed_action={
                "description": "Reboot core-sw-01",
                "impact": "Brief network interruption",
                "rollback": "Power cycle if needed"
            }
        )

        # Simulate approval
        state["approval_status"] = ApprovalStatus.APPROVED
        state["approver"] = "admin_user"
        state["approval_timestamp"] = datetime.now()
        state["approver_comment"] = "Approved for maintenance window"

        assert state["approval_status"] == ApprovalStatus.APPROVED
        assert state["approver"] == "admin_user"
        assert state["approver_comment"] is not None

    def test_rejection_workflow(self):
        """Test rejection workflow."""
        state = ApprovalWorkflowState(
            messages=[HumanMessage(content="Reboot device")],
            approval_status=ApprovalStatus.PENDING
        )

        # Simulate rejection
        state["approval_status"] = ApprovalStatus.REJECTED
        state["approver"] = "admin_user"
        state["approver_comment"] = "Not during business hours"

        assert state["approval_status"] == ApprovalStatus.REJECTED


class TestWorkflowStatus:
    """Test workflow status transitions."""

    def test_status_enum_values(self):
        """Test all status enum values are valid."""
        assert WorkflowStatus.INITIALIZED == "initialized"
        assert WorkflowStatus.PLANNING == "planning"
        assert WorkflowStatus.EXECUTING == "executing"
        assert WorkflowStatus.AWAITING_APPROVAL == "awaiting_approval"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.FAILED == "failed"
        assert WorkflowStatus.CANCELLED == "cancelled"

    def test_status_transitions(self):
        """Test valid status transitions."""
        state = NautobotAgentState(
            messages=[HumanMessage(content="Test")]
        )

        # Valid transition: INITIALIZED -> PLANNING -> EXECUTING -> COMPLETED
        assert state["workflow_status"] == WorkflowStatus.INITIALIZED

        state["workflow_status"] = WorkflowStatus.PLANNING
        assert state["workflow_status"] == WorkflowStatus.PLANNING

        state["workflow_status"] = WorkflowStatus.EXECUTING
        assert state["workflow_status"] == WorkflowStatus.EXECUTING

        state["workflow_status"] = WorkflowStatus.COMPLETED
        assert state["workflow_status"] == WorkflowStatus.COMPLETED

    def test_failure_status(self):
        """Test failure status handling."""
        state = NautobotAgentState(
            messages=[HumanMessage(content="Test")],
            workflow_status=WorkflowStatus.EXECUTING
        )

        # Simulate failure
        state["workflow_status"] = WorkflowStatus.FAILED
        state["error_count"] = 1

        assert state["workflow_status"] == WorkflowStatus.FAILED
        assert state["error_count"] > 0


class TestStateValidation:
    """Test Pydantic validation rules."""

    def test_negative_error_count_rejected(self):
        """Test that negative error counts are rejected."""
        with pytest.raises(Exception):
            NautobotAgentState(
                messages=[HumanMessage(content="Test")],
                error_count=-1
            )

    def test_negative_step_index_rejected(self):
        """Test that negative step indices are rejected."""
        with pytest.raises(Exception):
            PlanExecuteState(
                messages=[HumanMessage(content="Test")],
                current_step_index=-1
            )

    def test_messages_field_inheritance(self):
        """Test that messages field is inherited from MessagesState."""
        state = NautobotAgentState(
            messages=[
                HumanMessage(content="User message"),
                AIMessage(content="AI response")
            ]
        )

        assert len(state["messages"]) == 2
        assert isinstance(state["messages"][0], HumanMessage)
        assert isinstance(state["messages"][1], AIMessage)


class TestStateSerializ:
    """Test state serialization for checkpointing."""

    def test_state_dict_conversion(self):
        """Test state can be converted to dict."""
        state = NautobotAgentState(
            messages=[HumanMessage(content="Test")],
            nautobot_context={"device_id": "123"},
            current_task="Test task"
        )

        # State should be dict-like (MessagesState is TypedDict-based)
        assert isinstance(state, dict)
        assert "messages" in state
        assert "nautobot_context" in state

    def test_state_metadata_json_serializable(self):
        """Test that metadata can be JSON serialized."""
        import json

        state = NautobotAgentState(
            messages=[HumanMessage(content="Test")],
            metadata={
                "correlation_id": "abc-123",
                "timestamp": "2025-01-01T00:00:00",
                "user": "admin"
            }
        )

        # Metadata should be JSON serializable
        json_str = json.dumps(state["metadata"])
        assert json_str is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
