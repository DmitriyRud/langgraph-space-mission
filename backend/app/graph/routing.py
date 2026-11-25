from typing import Any

from langgraph.config import get_stream_writer
from langgraph.graph import END
from langgraph.types import Send

from app.state.mission_state import MissionState

VALID_SPECIALIST_NODES = ("engineer", "scientist", "medical_officer")


def _emit_routing_event(event_type: str, node_id: str, iteration: int, payload: dict[str, Any]) -> None:
    try:
        writer = get_stream_writer()
        writer(
            {
                "event_type": event_type,
                "node_id": node_id,
                "iteration": iteration,
                "payload": payload,
            }
        )
    except Exception:
        pass


def route_to_specialists(state: MissionState) -> list[Send]:
    """Dynamic fan-out using LangGraph Send() to run selected specialists in parallel."""
    selected = [
        name for name in state.get("selected_specialists", [])
        if name in VALID_SPECIALIST_NODES
    ]
    if not selected:
        selected = ["engineer"]

    iteration = int(state.get("iteration", 1))
    _emit_routing_event(
        "parallel_branch_started",
        "commander",
        iteration,
        {
            "targets": selected,
            "branch_count": len(selected),
            "mechanism": "LangGraph Send() fan-out",
        },
    )
    return [Send(specialist, state) for specialist in selected]


def route_after_safety(state: MissionState) -> str:
    """Conditional edge after Safety Officer: approve -> human_approval, reject -> commander."""
    safety = state.get("safety_assessment") or {}
    approved = bool(safety.get("approved", False))
    iteration = int(state.get("iteration", 1))
    revision_count = int(state.get("plan_revision_count", 0))

    # Guardrail against endless safety rejection loops
    if not approved and revision_count >= 3:
        _emit_routing_event(
            "conditional_edge_selected",
            "safety_officer",
            iteration,
            {
                "from": "safety_officer",
                "to": "human_approval",
                "reason": "Safety revision cap reached; escalating to Captain for final decision.",
            },
        )
        return "human_approval"

    target = "human_approval" if approved else "commander"
    _emit_routing_event(
        "conditional_edge_selected",
        "safety_officer",
        iteration,
        {
            "from": "safety_officer",
            "to": target,
            "approved": approved,
            "reason": safety.get("summary", ""),
        },
    )
    return target


def route_after_evaluation(state: MissionState) -> str:
    """Conditional edge after Mission Evaluator: continue -> commander, otherwise END."""
    result = state.get("mission_result") or {}
    outcome = result.get("outcome", "continue")
    iteration = int(state.get("iteration", 1))

    target = "commander" if outcome == "continue" else END
    _emit_routing_event(
        "conditional_edge_selected",
        "mission_evaluator",
        iteration,
        {
            "from": "mission_evaluator",
            "to": "__end__" if target == END else target,
            "outcome": outcome,
            "reason": result.get("reason", ""),
        },
    )
    return target
