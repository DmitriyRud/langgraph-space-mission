from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.graph.learning_catalog import get_learning_catalog, get_node_metadata
from app.i18n import DEFAULT_LANGUAGE, t
from app.graph.nodes import (
    commander_node,
    engineer_node,
    executor_node,
    human_approval_node,
    incident_init_node,
    medical_officer_node,
    mission_evaluator_node,
    plan_aggregator_node,
    safety_officer_node,
    scientist_node,
)
from app.graph.routing import (
    route_after_evaluation,
    route_after_safety,
    route_to_specialists,
)
from app.llm.provider import LLMProviderError, LLMUnavailableError
from app.prompts.system_prompts import AGENT_SYSTEM_PROMPTS, get_system_prompt
from app.state.mission_state import MissionState


def _should_retry_llm_error(exc: Exception) -> bool:
    """Retry transient parsing/provider errors, but fail fast if Ollama server is down."""
    return isinstance(exc, LLMProviderError) and not isinstance(exc, LLMUnavailableError)


LLM_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    initial_interval=0.5,
    backoff_factor=2.0,
    retry_on=_should_retry_llm_error,
)


def build_mission_graph(checkpointer: Any = None) -> Any:
    """Build and compile the real LangGraph StateGraph for AURORA-7."""
    builder = StateGraph(MissionState)

    builder.add_node("incident_init", incident_init_node)
    builder.add_node("commander", commander_node, retry=LLM_RETRY_POLICY)
    builder.add_node("engineer", engineer_node, retry=LLM_RETRY_POLICY)
    builder.add_node("scientist", scientist_node, retry=LLM_RETRY_POLICY)
    builder.add_node("medical_officer", medical_officer_node, retry=LLM_RETRY_POLICY)
    builder.add_node("plan_aggregator", plan_aggregator_node, retry=LLM_RETRY_POLICY)
    builder.add_node("safety_officer", safety_officer_node, retry=LLM_RETRY_POLICY)
    builder.add_node(
        "human_approval",
        human_approval_node,
        destinations=("executor", "commander"),
    )
    builder.add_node("executor", executor_node)
    builder.add_node("mission_evaluator", mission_evaluator_node)

    # Entry edge
    builder.add_edge(START, "incident_init")
    builder.add_edge("incident_init", "commander")

    # Dynamic fan-out via Send() to parallel specialists
    builder.add_conditional_edges(
        "commander",
        route_to_specialists,
        ["engineer", "scientist", "medical_officer"],
    )

    # Fan-in from all parallel specialists into plan_aggregator
    builder.add_edge("engineer", "plan_aggregator")
    builder.add_edge("scientist", "plan_aggregator")
    builder.add_edge("medical_officer", "plan_aggregator")

    # Safety review & conditional feedback loop
    builder.add_edge("plan_aggregator", "safety_officer")
    builder.add_conditional_edges(
        "safety_officer",
        route_after_safety,
        {
            "human_approval": "human_approval",
            "commander": "commander",
        },
    )

    # Note: human_approval routes dynamically via Command(goto="executor" | "commander")
    builder.add_edge("executor", "mission_evaluator")
    builder.add_conditional_edges(
        "mission_evaluator",
        route_after_evaluation,
        {
            "commander": "commander",
            END: END,
        },
    )

    return builder.compile(checkpointer=checkpointer)


def get_graph_topology(compiled_graph: Any, lang: str = DEFAULT_LANGUAGE) -> dict[str, Any]:
    """Extract live graph topology directly from the compiled LangGraph representation."""
    drawable = compiled_graph.get_graph()

    nodes: list[dict[str, Any]] = []
    for node_id in drawable.nodes:
        meta = get_node_metadata(node_id, lang)
        nodes.append(
            {
                "id": node_id,
                "label": meta["label"],
                "role": meta["role"],
                "category": meta["category"],
                "description": meta["description"],
                "langgraph_mechanism": meta["langgraph_mechanism"],
                "system_prompt": get_system_prompt(node_id, lang) if node_id in AGENT_SYSTEM_PROMPTS else None,
                "position": meta["position"],
            }
        )

    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()
    for edge in drawable.edges:
        source = edge.source
        target = edge.target
        if (source, target) in seen_edges:
            continue
        seen_edges.add((source, target))

        is_dynamic = source == "commander" and target in ("engineer", "scientist", "medical_officer")
        is_cyclic = (
            (source == "safety_officer" and target == "commander")
            or (source == "human_approval" and target == "commander")
            or (source == "mission_evaluator" and target == "commander")
        )
        is_conditional = bool(edge.conditional) or is_dynamic or source == "human_approval"

        label = ""
        if is_dynamic:
            label = t("edges.send", lang)
        elif source == "safety_officer" and target == "commander":
            label = t("edges.safety_reject", lang)
        elif source == "safety_officer" and target == "human_approval":
            label = t("edges.safety_approve", lang)
        elif source == "human_approval" and target == "commander":
            label = t("edges.hitl_revise", lang)
        elif source == "human_approval" and target == "executor":
            label = t("edges.hitl_approve", lang)
        elif source == "mission_evaluator" and target == "commander":
            label = t("edges.eval_continue", lang)
        elif source == "mission_evaluator" and target == "__end__":
            label = t("edges.eval_complete", lang)

        edges.append(
            {
                "id": f"{source}->{target}",
                "source": source,
                "target": target,
                "conditional": is_conditional,
                "dynamic": is_dynamic,
                "cyclic": is_cyclic,
                "label": label,
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "learning_catalog": get_learning_catalog(lang),
    }
