from dataclasses import dataclass
from typing import Any

from app.i18n import DEFAULT_LANGUAGE, t
from app.scenarios.catalog import ScenarioDefinition, get_scenario
from app.state.mission_state import ShipState

NUMERIC_TELEMETRY_FIELDS = (
    "energy",
    "oxygen",
    "hull_integrity",
    "engine_condition",
    "communication",
    "navigation",
    "crew_health",
    "crew_morale",
    "reserve_fuel",
)


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    invalid_actions: list[str]
    insufficient_resources: list[str]
    unsafe_actions: list[str]
    projected_effects: dict[str, int]


@dataclass(frozen=True)
class ExecutionBatchResult:
    updated_ship_state: ShipState
    telemetry_before: ShipState
    telemetry_deltas: dict[str, int]
    action_records: list[dict[str, Any]]
    skipped_duplicate_ids: list[str]
    rejected_actions: list[dict[str, Any]]


@dataclass(frozen=True)
class EvaluationResult:
    outcome: str  # "success" | "failure" | "continue" | "max_iterations_reached"
    reason: str
    mission_status: str
    met_thresholds: dict[str, bool]
    resolved_flags: list[str]
    missing_flags: list[str]
    critical_breaches: list[str]


def validate_plan_actions(
    scenario_id: str,
    ship_state: ShipState,
    action_ids: list[str],
) -> ValidationResult:
    """Validate proposed actions against scenario rules and current resources."""
    scenario: ScenarioDefinition = get_scenario(scenario_id)
    invalid_actions: list[str] = []
    insufficient_resources: list[str] = []
    unsafe_actions: list[str] = []
    projected_effects: dict[str, int] = {}

    sim_resources: dict[str, int] = {
        field: int(ship_state[field])  # type: ignore[literal-required]
        for field in NUMERIC_TELEMETRY_FIELDS
    }

    for action_id in action_ids:
        spec = scenario.allowed_actions.get(action_id)
        if spec is None:
            invalid_actions.append(action_id)
            continue

        if spec.risk_level == "critical":
            unsafe_actions.append(action_id)

        for res_key, required_amount in spec.resource_requirements.items():
            if sim_resources.get(res_key, 0) < required_amount:
                insufficient_resources.append(
                    f"{action_id} requires {res_key} >= {required_amount} (current: {sim_resources.get(res_key, 0)})"
                )

        for field_name, delta in spec.telemetry_effects.items():
            projected_effects[field_name] = projected_effects.get(field_name, 0) + delta
            if field_name in sim_resources:
                sim_resources[field_name] = _clamp(sim_resources[field_name] + delta)

    valid = not invalid_actions and not insufficient_resources
    return ValidationResult(
        valid=valid,
        invalid_actions=invalid_actions,
        insufficient_resources=insufficient_resources,
        unsafe_actions=unsafe_actions,
        projected_effects=projected_effects,
    )


def execute_plan_actions(
    scenario_id: str,
    ship_state: ShipState,
    action_ids: list[str],
    iteration: int,
    plan_id: str,
    already_executed: list[dict[str, Any]],
    lang: str = DEFAULT_LANGUAGE,
) -> ExecutionBatchResult:
    """Deterministically execute validated actions with strict idempotency."""
    scenario = get_scenario(scenario_id)
    telemetry_before: ShipState = dict(ship_state)  # type: ignore[assignment]
    updated: dict[str, Any] = dict(ship_state)

    existing_keys = {
        (rec.get("plan_id"), rec.get("action_id"), rec.get("iteration"))
        for rec in already_executed
        if rec.get("status") == "executed"
    }

    action_records: list[dict[str, Any]] = []
    skipped_duplicate_ids: list[str] = []
    rejected_actions: list[dict[str, Any]] = []

    for action_id in action_ids:
        idempotency_key = (plan_id, action_id, iteration)
        if idempotency_key in existing_keys:
            skipped_duplicate_ids.append(action_id)
            continue

        spec = scenario.allowed_actions.get(action_id)
        if spec is None:
            rejected_actions.append({"action_id": action_id, "reason": "Action not allowed in scenario"})
            continue

        missing_res = [
            f"{k} < {v}"
            for k, v in spec.resource_requirements.items()
            if int(updated.get(k, 0)) < v
        ]
        if missing_res:
            rejected_actions.append(
                {
                    "action_id": action_id,
                    "reason": f"Insufficient resources: {', '.join(missing_res)}",
                }
            )
            continue

        applied_deltas: dict[str, int] = {}
        for field_name, delta in spec.telemetry_effects.items():
            if field_name in NUMERIC_TELEMETRY_FIELDS:
                before_val = int(updated[field_name])
                after_val = _clamp(before_val + delta)
                updated[field_name] = after_val
                applied_deltas[field_name] = after_val - before_val

        record = {
            "plan_id": plan_id,
            "action_id": action_id,
            "label": spec.localized_label(scenario_id, lang),
            "iteration": iteration,
            "status": "executed",
            "applied_deltas": applied_deltas,
            "resolved_flags": list(spec.resolves_flags),
        }
        action_records.append(record)
        existing_keys.add(idempotency_key)

    # Apply passive scenario decay once per execution batch if any action actually ran
    if action_records and scenario.passive_decay:
        for field_name, decay in scenario.passive_decay.items():
            if field_name in NUMERIC_TELEMETRY_FIELDS:
                updated[field_name] = _clamp(int(updated[field_name]) + decay)

    telemetry_deltas: dict[str, int] = {}
    for field_name in NUMERIC_TELEMETRY_FIELDS:
        diff = int(updated[field_name]) - int(telemetry_before[field_name])  # type: ignore[literal-required]
        if diff != 0:
            telemetry_deltas[field_name] = diff

    return ExecutionBatchResult(
        updated_ship_state=ShipState(**updated),
        telemetry_before=telemetry_before,
        telemetry_deltas=telemetry_deltas,
        action_records=action_records,
        skipped_duplicate_ids=skipped_duplicate_ids,
        rejected_actions=rejected_actions,
    )


def evaluate_mission_state(
    scenario_id: str,
    ship_state: ShipState,
    executed_actions: list[dict[str, Any]],
    iteration: int,
    max_iterations: int,
    lang: str = DEFAULT_LANGUAGE,
) -> EvaluationResult:
    """Deterministically evaluate whether the mission succeeded, failed, or needs another iteration."""
    scenario = get_scenario(scenario_id)

    critical_breaches: list[str] = []
    for metric, min_allowed in scenario.failure_thresholds.items():
        current_val = int(ship_state[metric])  # type: ignore[literal-required]
        if current_val <= min_allowed:
            critical_breaches.append(f"{metric}={current_val}% (critical limit <= {min_allowed}%)")

    resolved_flags_set: set[str] = set()
    for rec in executed_actions:
        if rec.get("status") == "executed":
            for flag in rec.get("resolved_flags", []):
                resolved_flags_set.add(flag)

    resolved_flags = sorted(resolved_flags_set)
    missing_flags = [f for f in scenario.required_flags if f not in resolved_flags_set]

    met_thresholds: dict[str, bool] = {}
    for metric, target in scenario.success_thresholds.items():
        current_val = int(ship_state[metric])  # type: ignore[literal-required]
        met_thresholds[metric] = current_val >= target

    none_word = t("eval.none", lang)

    if critical_breaches:
        return EvaluationResult(
            outcome="failure",
            reason=t("eval.failure", lang, breaches="; ".join(critical_breaches)),
            mission_status="Failed",
            met_thresholds=met_thresholds,
            resolved_flags=resolved_flags,
            missing_flags=missing_flags,
            critical_breaches=critical_breaches,
        )

    if all(met_thresholds.values()) and not missing_flags:
        return EvaluationResult(
            outcome="success",
            reason=t("eval.success", lang),
            mission_status="Stabilized",
            met_thresholds=met_thresholds,
            resolved_flags=resolved_flags,
            missing_flags=[],
            critical_breaches=[],
        )

    if iteration >= max_iterations:
        return EvaluationResult(
            outcome="max_iterations_reached",
            reason=t(
                "eval.max_iterations",
                lang,
                max_iterations=max_iterations,
                missing_flags=", ".join(missing_flags) if missing_flags else none_word,
            ),
            mission_status="Alert",
            met_thresholds=met_thresholds,
            resolved_flags=resolved_flags,
            missing_flags=missing_flags,
            critical_breaches=[],
        )

    unmet = [k for k, ok in met_thresholds.items() if not ok]
    return EvaluationResult(
        outcome="continue",
        reason=t(
            "eval.continue",
            lang,
            iteration=iteration,
            unmet=", ".join(unmet) if unmet else none_word,
            missing_flags=", ".join(missing_flags) if missing_flags else none_word,
        ),
        mission_status="Alert",
        met_thresholds=met_thresholds,
        resolved_flags=resolved_flags,
        missing_flags=missing_flags,
        critical_breaches=[],
    )
