from typing import Any

from app.i18n import DEFAULT_LANGUAGE, t

NODE_LAYOUT: dict[str, dict[str, Any]] = {
    "__start__": {"category": "boundary", "position": {"x": 40, "y": 210}},
    "incident_init": {"category": "system", "position": {"x": 190, "y": 210}},
    "commander": {"category": "agent", "position": {"x": 380, "y": 210}},
    "engineer": {"category": "specialist", "position": {"x": 620, "y": 50}},
    "scientist": {"category": "specialist", "position": {"x": 620, "y": 210}},
    "medical_officer": {"category": "specialist", "position": {"x": 620, "y": 370}},
    "plan_aggregator": {"category": "agent", "position": {"x": 860, "y": 210}},
    "safety_officer": {"category": "agent", "position": {"x": 1070, "y": 210}},
    "human_approval": {"category": "hitl", "position": {"x": 1280, "y": 210}},
    "executor": {"category": "system", "position": {"x": 1490, "y": 210}},
    "mission_evaluator": {"category": "system", "position": {"x": 1690, "y": 210}},
    "__end__": {"category": "boundary", "position": {"x": 1890, "y": 210}},
}

LEARNING_SPECS: list[dict[str, Any]] = [
    {
        "id": "state_graph",
        "nodes": ["incident_init", "commander", "plan_aggregator"],
        "snippet": (
            "class MissionState(TypedDict):\n"
            "    ship_state: ShipState\n"
            "    specialist_reports: Annotated[list[dict], merge_specialist_reports]\n"
            "    current_plan: dict | None\n\n"
            "builder = StateGraph(MissionState)"
        ),
        "doc_url": "https://langchain-ai.github.io/langgraph/concepts/low_level/#stategraph",
    },
    {
        "id": "send_fan_out",
        "nodes": ["commander", "engineer", "scientist", "medical_officer", "plan_aggregator"],
        "snippet": (
            "def route_to_specialists(state: MissionState) -> list[Send]:\n"
            "    selected = state.get('selected_specialists', ['engineer'])\n"
            "    return [Send(specialist, state) for specialist in selected]"
        ),
        "doc_url": "https://langchain-ai.github.io/langgraph/concepts/low_level/#send",
    },
    {
        "id": "reducers",
        "nodes": ["commander", "engineer", "scientist", "medical_officer"],
        "snippet": (
            "def merge_specialist_reports(existing, update):\n"
            "    if isinstance(update, dict) and update.get('__reset__'):\n"
            "        return []\n"
            "    # Deduplicate by (agent, iteration) across parallel superstep"
        ),
        "doc_url": "https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers",
    },
    {
        "id": "conditional_cycles",
        "nodes": ["safety_officer", "mission_evaluator", "commander"],
        "snippet": (
            "builder.add_conditional_edges(\n"
            "    'safety_officer',\n"
            "    route_after_safety,\n"
            "    {'human_approval': 'human_approval', 'commander': 'commander'},\n"
            ")"
        ),
        "doc_url": "https://langchain-ai.github.io/langgraph/concepts/low_level/#conditional-edges",
    },
    {
        "id": "hitl_interrupt",
        "nodes": ["human_approval", "executor", "commander"],
        "snippet": (
            "decision_payload = interrupt(interrupt_payload)\n"
            "if decision == 'approve':\n"
            "    return Command(update={'approval_status': 'approved'}, goto='executor')\n"
            "return Command(update={'approval_status': 'rejected'}, goto='commander')"
        ),
        "doc_url": "https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/",
    },
    {
        "id": "checkpointing_time_travel",
        "nodes": ["human_approval", "mission_evaluator"],
        "snippet": (
            "history = [snap async for snap in graph.aget_state_history(config)]\n"
            "# Fork timeline by branching state into a new thread_id\n"
            "await graph.aupdate_state(fork_config, values=target_snapshot.values)"
        ),
        "doc_url": "https://langchain-ai.github.io/langgraph/concepts/time-travel/",
    },
    {
        "id": "retry_policy",
        "nodes": ["commander", "engineer", "scientist", "medical_officer", "plan_aggregator", "safety_officer"],
        "snippet": (
            "LLM_RETRY_POLICY = RetryPolicy(\n"
            "    max_attempts=3,\n"
            "    initial_interval=0.5,\n"
            "    backoff_factor=2.0,\n"
            "    retry_on=_should_retry_llm_error,\n"
            ")"
        ),
        "doc_url": "https://langchain-ai.github.io/langgraph/concepts/low_level/#retries",
    },
    {
        "id": "streaming",
        "nodes": ["commander", "executor", "mission_evaluator"],
        "snippet": (
            "async for mode, chunk in graph.astream(\n"
            "    graph_input, config,\n"
            "    stream_mode=['updates', 'values', 'custom', 'debug'],\n"
            "):\n"
            "    await self._handle_stream_chunk(mission_id, thread_id, mode, chunk)"
        ),
        "doc_url": "https://langchain-ai.github.io/langgraph/concepts/streaming/",
    },
]


def get_node_metadata(node_id: str, lang: str = DEFAULT_LANGUAGE) -> dict[str, Any]:
    layout = NODE_LAYOUT.get(node_id, {"category": "system", "position": {"x": 0, "y": 0}})
    label = t(f"nodes.{node_id}.label", lang)
    role = t(f"nodes.{node_id}.role", lang)
    description = t(f"nodes.{node_id}.description", lang)
    mechanism = t(f"nodes.{node_id}.langgraph_mechanism", lang)
    return {
        "label": node_id if label.startswith("nodes.") else label,
        "role": "System" if role.startswith("nodes.") else role,
        "category": layout["category"],
        "description": "" if description.startswith("nodes.") else description,
        "langgraph_mechanism": "Graph Node" if mechanism.startswith("nodes.") else mechanism,
        "position": layout["position"],
    }


def get_learning_catalog(lang: str = DEFAULT_LANGUAGE) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for spec in LEARNING_SPECS:
        item_id = spec["id"]
        items.append(
            {
                "id": item_id,
                "name": t(f"learning.{item_id}.name", lang),
                "summary": t(f"learning.{item_id}.summary", lang),
                "where_used": t(f"learning.{item_id}.where_used", lang),
                "nodes": list(spec["nodes"]),
                "snippet": spec["snippet"],
                "doc_url": spec["doc_url"],
            }
        )
    return items
