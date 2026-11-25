import json
from datetime import datetime, timezone
from typing import Any, Literal

from langgraph.config import get_stream_writer
from langgraph.types import Command, interrupt

from app.agents.base import run_structured_agent
from app.agents.demo_responses import (
    generate_demo_commander,
    generate_demo_plan,
    generate_demo_safety,
    generate_demo_specialist,
)
from app.i18n import DEFAULT_LANGUAGE, t
from app.llm.schemas import (
    CommanderOutput,
    PlanAggregationOutput,
    SafetyAssessmentOutput,
    SpecialistReportOutput,
)
from app.scenarios.catalog import get_scenario
from app.simulation.engine import evaluate_mission_state, execute_plan_actions, validate_plan_actions
from app.state.mission_state import MissionState
from app.state.reducers import RESET_SENTINEL


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit_custom(event_type: str, node_id: str, iteration: int, payload: dict[str, Any]) -> None:
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


def _format_allowed_actions(scenario_id: str, lang: str) -> str:
    scenario = get_scenario(scenario_id)
    lines = []
    for aid, spec in scenario.allowed_actions.items():
        lines.append(
            f"- {aid} ({spec.localized_label(scenario_id, lang)}) | owner={spec.specialist_owner} | risk={spec.risk_level} | "
            f"requires={spec.resource_requirements} | effects={spec.telemetry_effects}"
        )
    return "\n".join(lines)


async def incident_init_node(state: MissionState) -> dict[str, Any]:
    """Initialize scenario incident details and baseline ship state."""
    lang = state.get("language", DEFAULT_LANGUAGE)
    scenario = get_scenario(state["scenario_id"])
    initial_ship = dict(scenario.initial_ship_state)
    title = scenario.localized_title(lang)
    incident = {
        "scenario_id": scenario.id,
        "title": title,
        "subtitle": scenario.localized_subtitle(lang),
        "severity": scenario.severity,
        "description": scenario.localized_description(lang),
        "objectives": scenario.localized_objectives(lang),
    }

    return {
        "incident": incident,
        "ship_state": initial_ship,
        "initial_ship_state": dict(initial_ship),
        "mission_status": initial_ship["mission_status"],
        "iteration": 1,
        "plan_revision_count": 0,
        "approval_status": "pending",
        "risk_level": scenario.severity,
        "event_history": [
            {
                "timestamp": _utc_now(),
                "node": "incident_init",
                "iteration": 1,
                "summary": t("events.incident_init", lang, title=title, severity=scenario.severity.upper()),
            }
        ],
    }


async def commander_node(state: MissionState) -> dict[str, Any]:
    """Commander analyzes ship state & feedback, resets iteration reports, and picks specialists."""
    lang = state.get("language", DEFAULT_LANGUAGE)
    scenario = get_scenario(state["scenario_id"])
    iteration = int(state.get("iteration", 1))
    user_prompt = (
        f"Scenario: {scenario.localized_title(lang)} — {scenario.localized_description(lang)}\n"
        f"Objectives: {json.dumps(scenario.localized_objectives(lang), ensure_ascii=False)}\n"
        f"Current Iteration: {iteration}/{state.get('max_iterations', 5)}\n"
        f"Ship Telemetry: {json.dumps(state['ship_state'])}\n"
        f"Executed Actions So Far: {json.dumps([a['action_id'] for a in state.get('executed_actions', [])])}\n"
        f"Previous Safety Assessment: {json.dumps(state.get('safety_assessment'), ensure_ascii=False)}\n"
        f"Captain Feedback: {state.get('user_feedback') or 'None'}\n"
        f"Select 1 to 3 specialists from ['engineer', 'scientist', 'medical_officer']."
    )

    meta = await run_structured_agent(
        agent_name="commander",
        node_id="commander",
        state=state,
        schema=CommanderOutput,
        user_prompt=user_prompt,
        demo_fn=generate_demo_commander,
    )
    output: CommanderOutput = meta.parsed  # type: ignore[assignment]

    return {
        "selected_specialists": list(output.selected_specialists),
        "specialist_reports": {RESET_SENTINEL: True},  # type: ignore[dict-item]
        "approval_status": "pending",
        "event_history": [
            {
                "timestamp": _utc_now(),
                "node": "commander",
                "iteration": iteration,
                "summary": t(
                    "events.commander_dispatch",
                    lang,
                    specialists=", ".join(output.selected_specialists),
                    priority=output.priority_focus,
                ),
                "details": output.model_dump(),
            }
        ],
    }


async def _run_specialist_node(agent_name: str, state: MissionState) -> dict[str, Any]:
    lang = state.get("language", DEFAULT_LANGUAGE)
    scenario = get_scenario(state["scenario_id"])
    iteration = int(state.get("iteration", 1))
    user_prompt = (
        f"Scenario: {scenario.localized_title(lang)} — {scenario.localized_description(lang)}\n"
        f"Iteration: {iteration}\n"
        f"Ship Telemetry: {json.dumps(state['ship_state'])}\n"
        f"Captain Feedback: {state.get('user_feedback') or 'None'}\n"
        f"Previous Safety Notes: {json.dumps(state.get('safety_assessment'), ensure_ascii=False)}\n"
        f"Allowed Actions:\n{_format_allowed_actions(state['scenario_id'], lang)}\n"
        f"Provide your domain report as '{agent_name}'."
    )

    meta = await run_structured_agent(
        agent_name=agent_name,
        node_id=agent_name,
        state=state,
        schema=SpecialistReportOutput,
        user_prompt=user_prompt,
        demo_fn=lambda s: generate_demo_specialist(agent_name, s),
    )
    output: SpecialistReportOutput = meta.parsed  # type: ignore[assignment]

    valid_actions = [a for a in output.recommended_actions if a in scenario.allowed_actions]
    if not valid_actions:
        valid_actions = [
            aid for aid, spec in scenario.allowed_actions.items()
            if spec.risk_level != "critical"
        ][:1]

    report = {
        "agent": agent_name,
        "iteration": iteration,
        "diagnosis": output.diagnosis,
        "recommended_actions": valid_actions,
        "resource_estimate": output.resource_estimate,
        "projected_consequences": output.projected_consequences,
        "risk_level": output.risk_level,
    }

    return {
        "specialist_reports": [report],
        "event_history": [
            {
                "timestamp": _utc_now(),
                "node": agent_name,
                "iteration": iteration,
                "summary": t(
                    "events.specialist_recommend",
                    lang,
                    agent=t(f"specialists.{agent_name}", lang),
                    actions=", ".join(valid_actions),
                ),
                "details": report,
            }
        ],
    }


async def engineer_node(state: MissionState) -> dict[str, Any]:
    return await _run_specialist_node("engineer", state)


async def scientist_node(state: MissionState) -> dict[str, Any]:
    return await _run_specialist_node("scientist", state)


async def medical_officer_node(state: MissionState) -> dict[str, Any]:
    return await _run_specialist_node("medical_officer", state)


async def plan_aggregator_node(state: MissionState) -> dict[str, Any]:
    """Fan-in node: synthesizes parallel specialist reports into a concrete action plan."""
    lang = state.get("language", DEFAULT_LANGUAGE)
    scenario = get_scenario(state["scenario_id"])
    iteration = int(state.get("iteration", 1))
    revision_count = int(state.get("plan_revision_count", 0))
    reports = state.get("specialist_reports", [])

    user_prompt = (
        f"Scenario: {scenario.localized_title(lang)}\n"
        f"Iteration: {iteration}, Revision: {revision_count}\n"
        f"Ship Telemetry: {json.dumps(state['ship_state'])}\n"
        f"Specialist Reports (Fan-in): {json.dumps(reports, ensure_ascii=False)}\n"
        f"Previous Safety Rejection: {json.dumps(state.get('safety_assessment'), ensure_ascii=False)}\n"
        f"Captain Feedback: {state.get('user_feedback') or 'None'}\n"
        f"Allowed Actions:\n{_format_allowed_actions(state['scenario_id'], lang)}\n"
        "Produce a concise, actionable plan using 1 to 2 valid action_ids."
    )

    meta = await run_structured_agent(
        agent_name="plan_aggregator",
        node_id="plan_aggregator",
        state=state,
        schema=PlanAggregationOutput,
        user_prompt=user_prompt,
        demo_fn=generate_demo_plan,
    )
    output: PlanAggregationOutput = meta.parsed  # type: ignore[assignment]

    valid_ids = [aid for aid in output.action_ids if aid in scenario.allowed_actions]
    if not valid_ids:
        for rep in reports:
            for aid in rep.get("recommended_actions", []):
                if aid in scenario.allowed_actions and aid not in valid_ids:
                    valid_ids.append(aid)
        valid_ids = valid_ids[:2] or [
            aid for aid, spec in scenario.allowed_actions.items() if spec.risk_level != "critical"
        ][:1]

    validation = validate_plan_actions(state["scenario_id"], state["ship_state"], valid_ids)
    plan_id = f"plan-iter{iteration}-rev{revision_count}"
    plan = {
        "plan_id": plan_id,
        "iteration": iteration,
        "revision": revision_count,
        "title": output.plan_title,
        "summary": output.summary,
        "action_ids": valid_ids,
        "actions_detail": [scenario.allowed_actions[a].to_dict(state["scenario_id"], lang) for a in valid_ids],
        "expected_outcomes": output.expected_outcomes,
        "resource_summary": output.resource_summary,
        "projected_effects": validation.projected_effects,
        "risk_level": output.risk_level,
    }

    previous_update = [state["current_plan"]] if state.get("current_plan") else []

    return {
        "current_plan": plan,
        "previous_plans": previous_update,
        "risk_level": output.risk_level,
        "event_history": [
            {
                "timestamp": _utc_now(),
                "node": "plan_aggregator",
                "iteration": iteration,
                "summary": t("events.plan_assembled", lang, title=plan["title"], actions=", ".join(valid_ids)),
                "details": plan,
            }
        ],
    }


async def safety_officer_node(state: MissionState) -> dict[str, Any]:
    """Independent safety critic verifying feasibility, hazards, and resource constraints."""
    lang = state.get("language", DEFAULT_LANGUAGE)
    scenario = get_scenario(state["scenario_id"])
    iteration = int(state.get("iteration", 1))
    plan = state.get("current_plan") or {}
    action_ids = plan.get("action_ids", [])
    validation = validate_plan_actions(state["scenario_id"], state["ship_state"], action_ids)

    user_prompt = (
        f"Scenario: {scenario.localized_title(lang)}\n"
        f"Ship Telemetry: {json.dumps(state['ship_state'])}\n"
        f"Proposed Plan: {json.dumps(plan, ensure_ascii=False)}\n"
        f"Deterministic Pre-Check: valid={validation.valid}, "
        f"unsafe_actions={validation.unsafe_actions}, "
        f"insufficient_resources={validation.insufficient_resources}, "
        f"invalid_actions={validation.invalid_actions}\n"
        "Audit this plan strictly. Reject if unsafe_actions or insufficient_resources is non-empty."
    )

    meta = await run_structured_agent(
        agent_name="safety_officer",
        node_id="safety_officer",
        state=state,
        schema=SafetyAssessmentOutput,
        user_prompt=user_prompt,
        demo_fn=generate_demo_safety,
    )
    output: SafetyAssessmentOutput = meta.parsed  # type: ignore[assignment]

    approved = output.approved and validation.valid and not validation.unsafe_actions
    findings = list(output.findings)
    if validation.unsafe_actions and output.approved:
        findings.append(
            t("demo.safety_unsafe_finding", lang, actions=", ".join(validation.unsafe_actions))
        )
    if validation.insufficient_resources and output.approved:
        findings.extend(validation.insufficient_resources)

    assessment = {
        "approved": approved,
        "risk_level": "critical" if validation.unsafe_actions else output.risk_level,
        "resource_check_passed": validation.valid,
        "findings": findings,
        "required_revisions": output.required_revisions if not approved else "",
        "summary": output.summary if approved else (output.summary or t("demo.safety_rejected_summary", lang)),
    }

    revision_count = int(state.get("plan_revision_count", 0))
    if not approved:
        revision_count += 1
        _emit_custom(
            "plan_rejected",
            "safety_officer",
            iteration,
            {
                "rejected_by": "safety_officer",
                "plan_id": plan.get("plan_id"),
                "findings": findings,
                "revision_count": revision_count,
            },
        )

    verdict = t("events.safety_approved" if approved else "events.safety_rejected", lang)
    return {
        "safety_assessment": assessment,
        "risk_level": assessment["risk_level"],
        "plan_revision_count": revision_count,
        "event_history": [
            {
                "timestamp": _utc_now(),
                "node": "safety_officer",
                "iteration": iteration,
                "summary": t("events.safety_verdict", lang, verdict=verdict, summary=assessment["summary"]),
                "details": assessment,
            }
        ],
    }


async def human_approval_node(
    state: MissionState,
) -> Command[Literal["executor", "commander"]]:
    """Human-in-the-loop node using real LangGraph interrupt() and Command routing."""
    lang = state.get("language", DEFAULT_LANGUAGE)
    iteration = int(state.get("iteration", 1))
    plan = state.get("current_plan") or {}
    safety = state.get("safety_assessment") or {}

    interrupt_payload = {
        "type": "human_approval_required",
        "mission_id": state["mission_id"],
        "iteration": iteration,
        "plan": plan,
        "safety_assessment": safety,
        "ship_state": state["ship_state"],
        "available_decisions": ["approve", "reject", "request_revision"],
    }

    decision_payload = interrupt(interrupt_payload)

    decision = "approve"
    feedback = ""
    if isinstance(decision_payload, dict):
        decision = str(decision_payload.get("decision", "approve")).lower()
        feedback = str(decision_payload.get("feedback", "")).strip()
    elif isinstance(decision_payload, str):
        decision = decision_payload.lower()

    if decision == "approve":
        return Command(
            update={
                "approval_status": "approved",
                "user_feedback": feedback or None,
                "event_history": [
                    {
                        "timestamp": _utc_now(),
                        "node": "human_approval",
                        "iteration": iteration,
                        "summary": t("events.captain_approved", lang),
                    }
                ],
            },
            goto="executor",
        )

    status_value = "revision_requested" if decision == "request_revision" else "rejected"
    revision_count = int(state.get("plan_revision_count", 0)) + 1
    _emit_custom(
        "plan_rejected",
        "human_approval",
        iteration,
        {
            "rejected_by": "captain",
            "decision": status_value,
            "feedback": feedback,
            "plan_id": plan.get("plan_id"),
        },
    )

    return Command(
        update={
            "approval_status": status_value,
            "user_feedback": feedback or t("events.captain_rejected_default", lang),
            "plan_revision_count": revision_count,
            "event_history": [
                {
                    "timestamp": _utc_now(),
                    "node": "human_approval",
                    "iteration": iteration,
                    "summary": t(
                        "events.captain_rejected",
                        lang,
                        status=status_value.upper(),
                        feedback=feedback or t("eval.none", lang),
                    ),
                }
            ],
        },
        goto="commander",
    )


async def executor_node(state: MissionState) -> dict[str, Any]:
    """Deterministic, idempotent simulation node — never calls an LLM."""
    lang = state.get("language", DEFAULT_LANGUAGE)
    iteration = int(state.get("iteration", 1))
    plan = state.get("current_plan") or {}
    action_ids = plan.get("action_ids", [])
    plan_id = str(plan.get("plan_id", f"plan-iter{iteration}"))

    batch = execute_plan_actions(
        scenario_id=state["scenario_id"],
        ship_state=state["ship_state"],
        action_ids=action_ids,
        iteration=iteration,
        plan_id=plan_id,
        already_executed=state.get("executed_actions", []),
        lang=lang,
    )

    errors_update = [
        {
            "timestamp": _utc_now(),
            "node": "executor",
            "iteration": iteration,
            "message": f"Action '{rej['action_id']}' skipped: {rej['reason']}",
        }
        for rej in batch.rejected_actions
    ]

    summary_parts = [f"{r['label']}" for r in batch.action_records]
    summary = (
        t("events.executor_ran", lang, actions=", ".join(summary_parts), deltas=batch.telemetry_deltas)
        if summary_parts
        else t("events.executor_noop", lang)
    )

    return {
        "ship_state": batch.updated_ship_state,
        "executed_actions": batch.action_records,
        "errors": errors_update,
        "event_history": [
            {
                "timestamp": _utc_now(),
                "node": "executor",
                "iteration": iteration,
                "summary": summary,
                "details": {
                    "telemetry_deltas": batch.telemetry_deltas,
                    "skipped_duplicates": batch.skipped_duplicate_ids,
                    "rejected_actions": batch.rejected_actions,
                },
            }
        ],
    }


async def mission_evaluator_node(state: MissionState) -> dict[str, Any]:
    """Deterministic mission evaluator deciding success, failure, limit, or next iteration."""
    lang = state.get("language", DEFAULT_LANGUAGE)
    iteration = int(state.get("iteration", 1))
    max_iterations = int(state.get("max_iterations", 5))

    evaluation = evaluate_mission_state(
        scenario_id=state["scenario_id"],
        ship_state=state["ship_state"],
        executed_actions=state.get("executed_actions", []),
        iteration=iteration,
        max_iterations=max_iterations,
        lang=lang,
    )

    updated_ship = dict(state["ship_state"])
    updated_ship["mission_status"] = evaluation.mission_status

    next_iteration = iteration + 1 if evaluation.outcome == "continue" else iteration
    result_dict = {
        "outcome": evaluation.outcome,
        "reason": evaluation.reason,
        "met_thresholds": evaluation.met_thresholds,
        "resolved_flags": evaluation.resolved_flags,
        "missing_flags": evaluation.missing_flags,
        "critical_breaches": evaluation.critical_breaches,
        "completed_at_iteration": iteration,
    }

    return {
        "ship_state": updated_ship,
        "mission_status": evaluation.mission_status,
        "mission_result": result_dict,
        "iteration": next_iteration,
        "user_feedback": None if evaluation.outcome == "continue" else state.get("user_feedback"),
        "event_history": [
            {
                "timestamp": _utc_now(),
                "node": "mission_evaluator",
                "iteration": iteration,
                "summary": t("events.eval_summary", lang, outcome=evaluation.outcome.upper(), reason=evaluation.reason),
                "details": result_dict,
            }
        ],
    }
