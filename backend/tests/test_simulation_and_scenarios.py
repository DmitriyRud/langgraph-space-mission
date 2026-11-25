import pytest

from app.scenarios.catalog import get_random_scenario, get_scenario, list_scenarios
from app.simulation.engine import (
    evaluate_mission_state,
    execute_plan_actions,
    validate_plan_actions,
)
from app.state.reducers import RESET_SENTINEL, append_list, merge_specialist_reports


def test_all_five_scenarios_loaded():
    scenarios = list_scenarios()
    ids = {s.id for s in scenarios}
    assert ids == {
        "engine_failure",
        "oxygen_leak",
        "unknown_signal",
        "solar_storm",
        "critical_cascade",
    }
    assert get_random_scenario().id in ids


def test_unknown_scenario_raises():
    with pytest.raises(ValueError):
        get_scenario("nonexistent_scenario")


def test_specialist_reports_reducer_parallel_merge_and_reset():
    existing = [{"agent": "engineer", "iteration": 1, "diagnosis": "old"}]
    merged = merge_specialist_reports(
        existing,
        [{"agent": "medical_officer", "iteration": 1, "diagnosis": "crew ok"}],
    )
    assert len(merged) == 2
    assert {r["agent"] for r in merged} == {"engineer", "medical_officer"}

    # Reset clears stale reports on new iteration
    reset = merge_specialist_reports(merged, {RESET_SENTINEL: True})
    assert reset == []

    # Append list does not mutate input
    base = [1]
    res = append_list(base, [2, 3])
    assert base == [1]
    assert res == [1, 2, 3]


def test_simulation_engine_validation_and_idempotency():
    scenario = get_scenario("engine_failure")
    ship = dict(scenario.initial_ship_state)

    # Unsafe action flagged
    val = validate_plan_actions("engine_failure", ship, ["overdrive_damaged_core"])
    assert val.unsafe_actions == ["overdrive_damaged_core"]

    # Invalid action rejected
    val_bad = validate_plan_actions("engine_failure", ship, ["teleport_ship"])
    assert not val_bad.valid
    assert val_bad.invalid_actions == ["teleport_ship"]

    # First execution modifies ship state
    batch1 = execute_plan_actions(
        scenario_id="engine_failure",
        ship_state=ship,
        action_ids=["eva_thruster_repair"],
        iteration=1,
        plan_id="plan-1",
        already_executed=[],
    )
    assert batch1.updated_ship_state["engine_condition"] == 75
    assert len(batch1.action_records) == 1

    # Re-running same plan_id + action_id + iteration is idempotent
    batch2 = execute_plan_actions(
        scenario_id="engine_failure",
        ship_state=batch1.updated_ship_state,
        action_ids=["eva_thruster_repair"],
        iteration=1,
        plan_id="plan-1",
        already_executed=batch1.action_records,
    )
    assert batch2.skipped_duplicate_ids == ["eva_thruster_repair"]
    assert batch2.action_records == []
    assert batch2.updated_ship_state == batch1.updated_ship_state


def test_evaluation_success_failure_and_iteration_limit():
    scenario = get_scenario("oxygen_leak")
    ship = dict(scenario.initial_ship_state)

    # Failure breach
    critical_ship = dict(ship)
    critical_ship["oxygen"] = 10
    res_fail = evaluate_mission_state("oxygen_leak", critical_ship, [], 1, 5)
    assert res_fail.outcome == "failure"
    assert res_fail.mission_status == "Failed"

    # Max iterations reached
    res_limit = evaluate_mission_state("oxygen_leak", ship, [], 5, 5)
    assert res_limit.outcome == "max_iterations_reached"

    # Success when thresholds + required flags met
    good_ship = dict(ship)
    good_ship["oxygen"] = 85
    good_ship["hull_integrity"] = 80
    good_ship["crew_health"] = 88
    res_ok = evaluate_mission_state(
        "oxygen_leak",
        good_ship,
        [{"status": "executed", "resolved_flags": ["leak_contained"]}],
        2,
        5,
    )
    assert res_ok.outcome == "success"
    assert res_ok.mission_status == "Stabilized"
