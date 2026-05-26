"""Workflow orchestration layer.

A thin ``WorkflowEngine`` interface fronts the multi-step scenarios so the engine is pluggable
(a LangGraph-backed engine is introduced once flows gain branching/state, in the change-request
milestone). The current engine runs the steps procedurally.
"""

from engram.orchestration.engine import WorkflowEngine, get_workflow_engine

__all__ = ["WorkflowEngine", "get_workflow_engine"]
