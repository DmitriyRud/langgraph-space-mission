import asyncio

import pytest


async def _wait_for_mission_status(client, mission_id: str, targets: set[str], timeout: float = 10.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/missions/{mission_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["mission"]["status"] in targets:
            return data
        await asyncio.sleep(0.1)
    raise AssertionError(f"Mission {mission_id} did not reach {targets} within {timeout}s")


@pytest.mark.asyncio
async def test_health_scenarios_and_graph_endpoints(api_client):
    health = await api_client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["spacecraft"] == "AURORA-7"

    scenarios = await api_client.get("/api/scenarios")
    assert scenarios.status_code == 200
    assert len(scenarios.json()["scenarios"]) == 5

    graph = await api_client.get("/api/graph")
    assert graph.status_code == 200
    gdata = graph.json()
    node_ids = {n["id"] for n in gdata["nodes"]}
    assert {"commander", "engineer", "scientist", "medical_officer", "safety_officer", "human_approval", "executor", "mission_evaluator"}.issubset(node_ids)
    assert len(gdata["learning_catalog"]) >= 6


@pytest.mark.asyncio
async def test_end_to_end_mission_api_events_checkpoints_and_fork(api_client):
    # 1. Create mission
    create_resp = await api_client.post(
        "/api/missions",
        json={"scenario_id": "engine_failure", "mode": "demo", "max_iterations": 5},
    )
    assert create_resp.status_code == 201
    mission_id = create_resp.json()["mission"]["mission_id"]

    # 2. Start mission
    start_resp = await api_client.post(f"/api/missions/{mission_id}/start")
    assert start_resp.status_code == 200

    # 3. Wait until paused at Human Approval interrupt
    paused = await _wait_for_mission_status(api_client, mission_id, {"awaiting_approval"})
    assert paused["snapshot"]["interrupts"]

    # 4. Approve iteration 1 -> reaches iteration 2 interrupt
    res1 = await api_client.post(
        f"/api/missions/{mission_id}/resume",
        json={"decision": "approve", "feedback": "Proceed with EVA repair"},
    )
    assert res1.status_code == 200
    paused2 = await _wait_for_mission_status(api_client, mission_id, {"awaiting_approval"})
    assert paused2["snapshot"]["values"]["iteration"] == 2

    # 5. Approve iteration 2 -> completes successfully
    res2 = await api_client.post(
        f"/api/missions/{mission_id}/resume",
        json={"decision": "approve", "feedback": "Finalize reactor rebalance"},
    )
    assert res2.status_code == 200
    done = await _wait_for_mission_status(api_client, mission_id, {"completed"})
    assert done["snapshot"]["values"]["mission_result"]["outcome"] == "success"

    # 6. Verify recorded execution events match actual LangGraph execution
    export_resp = await api_client.get(f"/api/missions/{mission_id}/export")
    assert export_resp.status_code == 200
    exported = export_resp.json()
    event_types = {e["event_type"] for e in exported["events"]}
    assert "mission_started" in event_types
    assert "node_started" in event_types
    assert "node_completed" in event_types
    assert "parallel_branch_started" in event_types
    assert "plan_rejected" in event_types
    assert "human_approval_requested" in event_types
    assert "execution_resumed" in event_types
    assert "checkpoint_created" in event_types
    assert "mission_completed" in event_types

    # 7. Verify checkpoints endpoint and Time Travel Fork
    ckpts_resp = await api_client.get(f"/api/missions/{mission_id}/checkpoints")
    assert ckpts_resp.status_code == 200
    checkpoints = ckpts_resp.json()["checkpoints"]
    assert len(checkpoints) >= 6

    # Pick an earlier checkpoint (e.g., after incident_init or commander) to fork from
    target_ckpt = next(
        (c for c in checkpoints if c.get("writes") and "incident_init" in c["writes"]),
        checkpoints[-2],
    )
    fork_resp = await api_client.post(
        f"/api/missions/{mission_id}/fork",
        json={"checkpoint_id": target_ckpt["checkpoint_id"], "mode": "demo", "auto_start": True},
    )
    assert fork_resp.status_code == 201
    forked_mission = fork_resp.json()["mission"]
    assert forked_mission["parent_mission_id"] == mission_id
    assert forked_mission["parent_checkpoint_id"] == target_ckpt["checkpoint_id"]

    fork_paused = await _wait_for_mission_status(
        api_client, forked_mission["mission_id"], {"awaiting_approval", "completed"}
    )
    assert fork_paused["mission"]["mission_id"] != mission_id


@pytest.mark.asyncio
async def test_live_mode_surfaces_ollama_error_without_silent_demo_fallback(api_client, monkeypatch):
    from app.llm.provider import LLMUnavailableError, get_llm_provider

    async def fake_unavailable(*args, **kwargs):
        raise LLMUnavailableError("Ollama offline at http://localhost:11434")

    monkeypatch.setattr(get_llm_provider(), "invoke_structured", fake_unavailable)

    create_resp = await api_client.post(
        "/api/missions",
        json={"scenario_id": "engine_failure", "mode": "live", "max_iterations": 3},
    )
    assert create_resp.status_code == 201
    mission_id = create_resp.json()["mission"]["mission_id"]

    await api_client.post(f"/api/missions/{mission_id}/start")
    errored = await _wait_for_mission_status(api_client, mission_id, {"error"})
    assert errored["mission"]["status"] == "error"

    exported = (await api_client.get(f"/api/missions/{mission_id}/export")).json()
    error_events = [e for e in exported["events"] if e["event_type"] == "error"]
    assert error_events
    assert error_events[-1]["payload"]["can_switch_to_demo"] is True


@pytest.mark.asyncio
async def test_i18n_scenarios_and_graph_endpoints_default_en_and_ru(api_client):
    sc_default = (await api_client.get("/api/scenarios")).json()
    sc_ru = (await api_client.get("/api/scenarios?lang=ru")).json()
    assert sc_default["language"] == "en"
    assert sc_ru["language"] == "ru"

    eng_en = next(s for s in sc_default["scenarios"] if s["id"] == "engine_failure")
    eng_ru = next(s for s in sc_ru["scenarios"] if s["id"] == "engine_failure")
    assert eng_en["title"] == "Engine Failure"
    assert eng_ru["title"] == "Отказ двигателя"

    g_en = (await api_client.get("/api/graph?lang=en")).json()
    g_ru = (await api_client.get("/api/graph?lang=ru")).json()
    cmd_en = next(n for n in g_en["nodes"] if n["id"] == "commander")
    cmd_ru = next(n for n in g_ru["nodes"] if n["id"] == "commander")
    assert cmd_en["label"] == "Commander"
    assert cmd_ru["label"] == "Командир"
