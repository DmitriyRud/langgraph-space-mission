from pathlib import Path

import pytest
from langgraph.types import Command

from app.persistence.checkpointer import CheckpointerManager
from app.state.mission_state import create_baseline_ship_state


def _make_initial_state(mission_id: str, scenario_id: str = "engine_failure", max_iterations: int = 5):
    baseline = create_baseline_ship_state()
    return {
        "mission_id": mission_id,
        "scenario_id": scenario_id,
        "mode": "demo",
        "mission_status": "Operational",
        "incident": {},
        "ship_state": baseline,
        "initial_ship_state": baseline,
        "selected_specialists": [],
        "specialist_reports": [],
        "current_plan": None,
        "previous_plans": [],
        "executed_actions": [],
        "safety_assessment": None,
        "risk_level": "high",
        "iteration": 1,
        "max_iterations": max_iterations,
        "user_feedback": None,
        "approval_status": "pending",
        "mission_result": None,
        "event_history": [],
        "errors": [],
        "plan_revision_count": 0,
    }


@pytest.mark.asyncio
async def test_full_demo_workflow_parallel_rejection_hitl_and_success(tmp_path: Path):
    mgr = CheckpointerManager(tmp_path / "ckpt.db")
    await mgr.startup()
    try:
        config = mgr.make_config("thread-demo-1")

        # Run Phase 1: should run incident_init -> commander -> parallel specialists ->
        # plan_aggregator (unsafe draft) -> safety_officer (REJECT) -> commander ->
        # parallel specialists -> plan_aggregator (safe) -> safety_officer (APPROVE) ->
        # human_approval (INTERRUPT!)
        visited_nodes: list[str] = []
        async for chunk in mgr.graph.astream(
            _make_initial_state("msn-1", "engine_failure"),
            config,
            stream_mode="updates",
        ):
            visited_nodes.extend(k for k in chunk.keys() if k != "__interrupt__")

        # Verify parallel specialists ran and safety rejected draft 1 before approving draft 2
        assert "engineer" in visited_nodes
        assert "medical_officer" in visited_nodes
        assert visited_nodes.count("safety_officer") == 2
        assert visited_nodes.count("commander") == 2

        snap1 = await mgr.get_state_snapshot("thread-demo-1")
        assert snap1 is not None
        assert len(snap1["interrupts"]) == 1
        assert snap1["values"]["safety_assessment"]["approved"] is True
        assert snap1["values"]["plan_revision_count"] >= 1

        # Test Captain requesting revision before approving
        async for _ in mgr.graph.astream(
            Command(resume={"decision": "request_revision", "feedback": "Prioritize reactor safety"}),
            config,
            stream_mode="updates",
        ):
            pass

        snap_rev = await mgr.get_state_snapshot("thread-demo-1")
        assert snap_rev is not None
        assert len(snap_rev["interrupts"]) == 1
        assert snap_rev["values"]["user_feedback"] == "Prioritize reactor safety"

        # Now Captain approves Iteration 1 -> Executor runs -> Evaluator loops to Iteration 2 -> Interrupts again
        async for _ in mgr.graph.astream(
            Command(resume={"decision": "approve", "feedback": "Execute repair"}),
            config,
            stream_mode="updates",
        ):
            pass

        snap2 = await mgr.get_state_snapshot("thread-demo-1")
        assert snap2 is not None
        assert snap2["values"]["iteration"] == 2
        assert len(snap2["values"]["executed_actions"]) >= 1
        assert len(snap2["interrupts"]) == 1

        # Captain approves Iteration 2 -> Mission stabilizes and finishes
        async for _ in mgr.graph.astream(
            Command(resume={"decision": "approve", "feedback": "Complete stabilization"}),
            config,
            stream_mode="updates",
        ):
            pass

        final_snap = await mgr.get_state_snapshot("thread-demo-1")
        assert final_snap is not None
        assert not final_snap["interrupts"]
        assert final_snap["values"]["mission_result"]["outcome"] == "success"
        assert final_snap["values"]["mission_status"] == "Stabilized"

        # Verify checkpoints persisted in SQLite
        history = await mgr.list_checkpoints("thread-demo-1")
        assert len(history) >= 8
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_checkpoint_recovery_across_restart_and_iteration_cap(tmp_path: Path):
    db_file = tmp_path / "persistent.db"

    # Instance 1: start mission and pause at interrupt
    mgr1 = CheckpointerManager(db_file)
    await mgr1.startup()
    config = mgr1.make_config("thread-persist")
    async for _ in mgr1.graph.astream(
        _make_initial_state("msn-persist", "critical_cascade", max_iterations=1),
        config,
        stream_mode="updates",
    ):
        pass
    await mgr1.shutdown()

    # Instance 2 (simulates backend restart): recover paused mission and resume
    mgr2 = CheckpointerManager(db_file)
    await mgr2.startup()
    try:
        recovered = await mgr2.get_state_snapshot("thread-persist")
        assert recovered is not None
        assert len(recovered["interrupts"]) == 1

        async for _ in mgr2.graph.astream(
            Command(resume={"decision": "approve"}),
            config,
            stream_mode="updates",
        ):
            pass

        final_snap = await mgr2.get_state_snapshot("thread-persist")
        assert final_snap is not None
        # critical_cascade needs 2 iterations, so max_iterations=1 triggers cap cleanly
        assert final_snap["values"]["mission_result"]["outcome"] == "max_iterations_reached"
    finally:
        await mgr2.shutdown()
