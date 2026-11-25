import asyncio
from typing import Any

from app.i18n import DEFAULT_LANGUAGE, get_localized, t
from app.llm.schemas import (
    CommanderOutput,
    PlanAggregationOutput,
    SafetyAssessmentOutput,
    SpecialistReportOutput,
)
from app.scenarios.catalog import get_scenario
from app.simulation.engine import validate_plan_actions

DEMO_SCENARIO_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "engine_failure": {
        "specialists_by_iter": {
            1: ["engineer", "medical_officer"],
            2: ["engineer", "medical_officer"],
        },
        "unsafe_first_draft": ["overdrive_damaged_core"],
        "safe_actions_by_iter": {
            1: ["eva_thruster_repair"],
            2: ["rebalance_reactor_bus", "medical_eva_prep"],
        },
    },
    "oxygen_leak": {
        "specialists_by_iter": {
            1: ["engineer", "medical_officer"],
            2: ["engineer", "medical_officer"],
        },
        "unsafe_first_draft": ["vent_all_nonessential_bays"],
        "safe_actions_by_iter": {
            1: ["isolate_habitat_b", "activate_reserve_o2_scrubbers"],
            2: ["deploy_nanoseal_patch", "crew_hypoxia_protocol"],
        },
    },
    "unknown_signal": {
        "specialists_by_iter": {
            1: ["scientist", "engineer", "medical_officer"],
            2: ["scientist", "engineer"],
        },
        "unsafe_first_draft": ["broadcast_unfiltered_reply"],
        "safe_actions_by_iter": {
            1: ["passive_spectral_analysis", "recalibrate_nav_array"],
            2: ["crew_psych_briefing"],
        },
    },
    "solar_storm": {
        "specialists_by_iter": {
            1: ["engineer", "scientist", "medical_officer"],
            2: ["engineer", "medical_officer"],
        },
        "unsafe_first_draft": ["ignore_storm_full_burn"],
        "safe_actions_by_iter": {
            1: ["shed_noncritical_loads", "boost_magnetic_deflector"],
            2: ["model_cme_wavefront", "storm_shelter_protocol"],
        },
    },
    "critical_cascade": {
        "specialists_by_iter": {
            1: ["engineer", "scientist", "medical_officer"],
            2: ["engineer", "scientist", "medical_officer"],
        },
        "unsafe_first_draft": ["hard_reboot_all_systems"],
        "safe_actions_by_iter": {
            1: ["emergency_bus_recovery", "stabilize_thruster_manifold"],
            2: ["restore_comms_transponder", "life_support_stabilization"],
        },
    },
}


async def generate_demo_commander(state: dict[str, Any]) -> CommanderOutput:
    await asyncio.sleep(0.18)
    lang = state.get("language", DEFAULT_LANGUAGE)
    scenario_id = state["scenario_id"]
    scenario = get_scenario(scenario_id)
    title = scenario.localized_title(lang)
    objectives = scenario.localized_objectives(lang)
    iteration = int(state.get("iteration", 1))
    revision_count = int(state.get("plan_revision_count", 0))
    feedback = state.get("user_feedback")
    safety = state.get("safety_assessment")

    blueprint = DEMO_SCENARIO_BLUEPRINTS[scenario_id]
    specialists = list(
        blueprint["specialists_by_iter"].get(
            iteration,
            list(scenario.recommended_specialists),
        )
    )
    spec_names = ", ".join(t(f"specialists.{s}", lang) for s in specialists)

    if feedback:
        summary = t(
            "demo.commander_feedback_summary",
            lang,
            iteration=iteration,
            feedback=feedback,
            title=title,
        )
        rationale = t("demo.commander_feedback_rationale", lang)
    elif safety and not safety.get("approved", True):
        summary = t(
            "demo.commander_safety_summary",
            lang,
            iteration=iteration,
            revision_count=revision_count,
        )
        rationale = t("demo.commander_safety_rationale", lang)
    else:
        summary = t(
            "demo.commander_default_summary",
            lang,
            iteration=iteration,
            title=title,
            energy=state["ship_state"]["energy"],
            oxygen=state["ship_state"]["oxygen"],
            engine=state["ship_state"]["engine_condition"],
        )
        rationale = t("demo.commander_default_rationale", lang, specialists=spec_names)

    directives = {
        spec: t(
            "demo.commander_directive",
            lang,
            title=title,
            specialist=t(f"specialists.{spec}", lang),
        )
        for spec in specialists
    }

    return CommanderOutput(
        situation_summary=summary,
        priority_focus=objectives[min(iteration - 1, len(objectives) - 1)],
        selected_specialists=specialists,  # type: ignore[arg-type]
        directives=directives,
        rationale=rationale,
    )


async def generate_demo_specialist(agent: str, state: dict[str, Any]) -> SpecialistReportOutput:
    stagger = {"engineer": 0.22, "scientist": 0.28, "medical_officer": 0.25}.get(agent, 0.2)
    await asyncio.sleep(stagger)

    lang = state.get("language", DEFAULT_LANGUAGE)
    scenario_id = state["scenario_id"]
    scenario = get_scenario(scenario_id)
    title = scenario.localized_title(lang)
    iteration = int(state.get("iteration", 1))
    revision_count = int(state.get("plan_revision_count", 0))
    blueprint = DEMO_SCENARIO_BLUEPRINTS[scenario_id]

    safe_actions = blueprint["safe_actions_by_iter"].get(
        iteration,
        blueprint["safe_actions_by_iter"][1],
    )

    domain_actions = [
        aid for aid, spec in scenario.allowed_actions.items()
        if spec.specialist_owner == agent and spec.risk_level != "critical"
    ]
    chosen = [a for a in safe_actions if a in scenario.allowed_actions and scenario.allowed_actions[a].specialist_owner == agent]
    if not chosen:
        chosen = domain_actions[:1] or safe_actions[:1]

    if iteration == 1 and revision_count == 0 and agent == scenario.allowed_actions[blueprint["unsafe_first_draft"][0]].specialist_owner:
        unsafe_id = blueprint["unsafe_first_draft"][0]
        unsafe_label = scenario.allowed_actions[unsafe_id].localized_label(scenario_id, lang)
        return SpecialistReportOutput(
            agent=agent,  # type: ignore[arg-type]
            diagnosis=t("demo.specialist_unsafe_diagnosis", lang, title=title),
            recommended_actions=[unsafe_id],
            resource_estimate=t("demo.specialist_unsafe_resources", lang),
            projected_consequences=t("demo.specialist_unsafe_consequences", lang, action_label=unsafe_label),
            risk_level="high",
        )

    action_labels = ", ".join(
        scenario.allowed_actions[a].localized_label(scenario_id, lang)
        for a in chosen
        if a in scenario.allowed_actions
    )
    ship = state["ship_state"]
    agent_label = t(f"specialists.{agent}", lang).upper()
    return SpecialistReportOutput(
        agent=agent,  # type: ignore[arg-type]
        diagnosis=t(
            "demo.specialist_safe_diagnosis",
            lang,
            agent_label=agent_label,
            energy=ship["energy"],
            oxygen=ship["oxygen"],
            hull=ship["hull_integrity"],
            engine=ship["engine_condition"],
        ),
        recommended_actions=chosen[:2],
        resource_estimate=t("demo.specialist_safe_resources", lang),
        projected_consequences=t("demo.specialist_safe_consequences", lang, action_labels=action_labels),
        risk_level="low",
    )


async def generate_demo_plan(state: dict[str, Any]) -> PlanAggregationOutput:
    await asyncio.sleep(0.16)
    lang = state.get("language", DEFAULT_LANGUAGE)
    scenario_id = state["scenario_id"]
    scenario = get_scenario(scenario_id)
    title = scenario.localized_title(lang)
    iteration = int(state.get("iteration", 1))
    revision_count = int(state.get("plan_revision_count", 0))
    feedback = state.get("user_feedback")
    blueprint = DEMO_SCENARIO_BLUEPRINTS[scenario_id]

    if iteration == 1 and revision_count == 0:
        action_ids = list(blueprint["unsafe_first_draft"])
        action_spec = scenario.allowed_actions[action_ids[0]]
        action_label = action_spec.localized_label(scenario_id, lang)
        return PlanAggregationOutput(
            plan_title=t("demo.plan_unsafe_title", lang, iteration=iteration, draft_num=revision_count + 1),
            summary=t("demo.plan_unsafe_summary", lang, action_label=action_label, title=title),
            action_ids=action_ids,
            expected_outcomes=t("demo.plan_unsafe_outcomes", lang),
            resource_summary=t("demo.plan_unsafe_resources", lang, requirements=action_spec.resource_requirements),
            risk_level="critical",
        )

    safe_ids = list(
        blueprint["safe_actions_by_iter"].get(
            iteration,
            blueprint["safe_actions_by_iter"].get(2, blueprint["safe_actions_by_iter"][1]),
        )
    )

    already = {rec.get("action_id") for rec in state.get("executed_actions", [])}
    remaining = [a for a in safe_ids if a not in already]
    if not remaining:
        remaining = [
            aid for aid, spec in scenario.allowed_actions.items()
            if spec.risk_level != "critical" and aid not in already
        ][:2] or safe_ids

    labels = [
        scenario.allowed_actions[a].localized_label(scenario_id, lang)
        for a in remaining
        if a in scenario.allowed_actions
    ]
    fb_note = t("demo.plan_safe_fb_note", lang, feedback=feedback) if feedback else ""

    return PlanAggregationOutput(
        plan_title=t("demo.plan_safe_title", lang, iteration=iteration, revision_count=revision_count),
        summary=t("demo.plan_safe_summary", lang, labels=", ".join(labels), fb_note=fb_note),
        action_ids=remaining,
        expected_outcomes=t("demo.plan_safe_outcomes", lang),
        resource_summary=t("demo.plan_safe_resources", lang),
        risk_level="low",
    )


async def generate_demo_safety(state: dict[str, Any]) -> SafetyAssessmentOutput:
    await asyncio.sleep(0.16)
    lang = state.get("language", DEFAULT_LANGUAGE)
    scenario_id = state["scenario_id"]
    plan = state.get("current_plan") or {}
    action_ids = plan.get("action_ids", [])
    validation = validate_plan_actions(scenario_id, state["ship_state"], action_ids)

    if validation.invalid_actions or validation.insufficient_resources or validation.unsafe_actions:
        findings: list[str] = []
        if validation.unsafe_actions:
            findings.append(
                t("demo.safety_unsafe_finding", lang, actions=", ".join(validation.unsafe_actions))
            )
        if validation.insufficient_resources:
            findings.extend(validation.insufficient_resources)
        if validation.invalid_actions:
            findings.append(
                t("demo.safety_invalid_finding", lang, actions=", ".join(validation.invalid_actions))
            )

        return SafetyAssessmentOutput(
            approved=False,
            risk_level="critical" if validation.unsafe_actions else "high",
            resource_check_passed=not validation.insufficient_resources,
            findings=findings,
            required_revisions=t("demo.safety_required_revisions", lang),
            summary=t("demo.safety_rejected_summary", lang),
        )

    approved_findings = get_localized("demo.safety_approved_findings", lang)
    return SafetyAssessmentOutput(
        approved=True,
        risk_level="low",
        resource_check_passed=True,
        findings=list(approved_findings) if isinstance(approved_findings, list) else [],
        required_revisions="",
        summary=t("demo.safety_approved_summary", lang),
    )
