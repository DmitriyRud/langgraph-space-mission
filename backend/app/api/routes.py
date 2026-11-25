import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import CreateMissionRequest, ForkMissionRequest, ResumeMissionRequest
from app.config import get_settings
from app.graph.workflow import get_graph_topology
from app.i18n import DEFAULT_LANGUAGE, normalize_lang
from app.llm.provider import get_llm_provider
from app.scenarios.catalog import get_random_scenario, get_scenario, list_scenarios
from app.streaming.manager import MissionAlreadyRunningError, MissionRuntimeManager
from app.system_info import get_system_info

router = APIRouter(prefix="/api", tags=["mission-control"])


def _get_runtime(request: Request) -> MissionRuntimeManager:
    return request.app.state.runtime


@router.get("/health")
async def health_check(request: Request) -> dict[str, Any]:
    settings = get_settings()
    llm_health = await get_llm_provider().check_health()
    return {
        "status": "ok",
        "spacecraft": "AURORA-7",
        "llm": llm_health,
        "system": get_system_info(),
        "default_max_iterations": settings.default_max_iterations,
    }


@router.get("/models")
async def list_models() -> dict[str, Any]:
    settings = get_settings()
    llm_health = await get_llm_provider().check_health()
    sys_info = get_system_info()
    return {
        "provider": settings.llm_provider,
        "active_model": get_llm_provider().active_model_name,
        "temperature": settings.llm_temperature,
        "max_concurrency": settings.llm_max_concurrency,
        "recommended_local_models": sys_info["recommended_models"],
        "system": sys_info,
        **llm_health,
    }


@router.get("/scenarios")
async def get_scenarios(lang: str = Query(default=DEFAULT_LANGUAGE)) -> dict[str, Any]:
    normalized = normalize_lang(lang)
    return {
        "language": normalized,
        "scenarios": [s.to_summary_dict(normalized) for s in list_scenarios()],
    }


@router.get("/graph")
async def get_graph(
    request: Request,
    lang: str = Query(default=DEFAULT_LANGUAGE),
) -> dict[str, Any]:
    runtime = _get_runtime(request)
    return get_graph_topology(runtime.checkpointer_mgr.graph, lang=normalize_lang(lang))


@router.post("/missions", status_code=201)
async def create_mission(body: CreateMissionRequest, request: Request) -> dict[str, Any]:
    runtime = _get_runtime(request)
    scenario_id = body.scenario_id
    if scenario_id == "random":
        scenario_id = get_random_scenario().id
    else:
        try:
            get_scenario(scenario_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    mission = await runtime.create_mission(
        scenario_id=scenario_id,
        mode=body.mode,
        language=normalize_lang(body.language),
        max_iterations=body.max_iterations,
    )
    return {"mission": mission}


@router.get("/missions")
async def list_missions(request: Request, limit: int = Query(default=30, ge=1, le=100)) -> dict[str, Any]:
    runtime = _get_runtime(request)
    missions = await runtime.event_store.list_missions(limit=limit)
    return {"missions": missions}


@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str, request: Request) -> dict[str, Any]:
    runtime = _get_runtime(request)
    mission = await runtime.event_store.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")

    snapshot = await runtime.checkpointer_mgr.get_state_snapshot(mission["thread_id"])
    events = await runtime.event_store.list_events(mission_id)
    return {
        "mission": mission,
        "running": runtime.is_running(mission_id),
        "snapshot": snapshot,
        "event_count": len(events),
    }


@router.post("/missions/{mission_id}/start")
async def start_mission(mission_id: str, request: Request) -> dict[str, Any]:
    runtime = _get_runtime(request)
    try:
        mission = await runtime.start_mission(mission_id)
        return {"mission": mission, "started": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissionAlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/missions/{mission_id}/events")
async def stream_mission_events(
    mission_id: str,
    request: Request,
    last_event_id: str | None = Query(default=None),
    header_last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> EventSourceResponse:
    runtime = _get_runtime(request)
    mission = await runtime.event_store.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")

    after_id = last_event_id or header_last_event_id

    async def event_generator():
        async for evt in runtime.subscribe(mission_id, after_event_id=after_id):
            if await request.is_disconnected():
                break
            yield {
                "id": evt["event_id"],
                "event": evt["event_type"],
                "data": json.dumps(evt, default=str),
            }

    return EventSourceResponse(event_generator())


@router.post("/missions/{mission_id}/resume")
async def resume_mission(
    mission_id: str,
    body: ResumeMissionRequest,
    request: Request,
) -> dict[str, Any]:
    runtime = _get_runtime(request)
    try:
        mission = await runtime.resume_mission(
            mission_id,
            decision=body.decision,
            feedback=body.feedback,
            switch_to_demo=body.switch_to_demo,
        )
        return {"mission": mission, "resumed": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissionAlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/missions/{mission_id}/state")
async def get_mission_state(
    mission_id: str,
    request: Request,
    checkpoint_id: str | None = Query(default=None),
) -> dict[str, Any]:
    runtime = _get_runtime(request)
    mission = await runtime.event_store.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")

    snapshot = await runtime.checkpointer_mgr.get_state_snapshot(
        mission["thread_id"], checkpoint_id=checkpoint_id
    )
    return {
        "mission_id": mission_id,
        "thread_id": mission["thread_id"],
        "snapshot": snapshot,
    }


@router.get("/missions/{mission_id}/checkpoints")
async def get_mission_checkpoints(
    mission_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    runtime = _get_runtime(request)
    mission = await runtime.event_store.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")

    checkpoints = await runtime.checkpointer_mgr.list_checkpoints(
        mission["thread_id"], limit=limit
    )
    return {
        "mission_id": mission_id,
        "thread_id": mission["thread_id"],
        "checkpoints": checkpoints,
    }


@router.post("/missions/{mission_id}/fork", status_code=201)
async def fork_mission(
    mission_id: str,
    body: ForkMissionRequest,
    request: Request,
) -> dict[str, Any]:
    runtime = _get_runtime(request)
    try:
        forked = await runtime.fork_mission(
            mission_id,
            checkpoint_id=body.checkpoint_id,
            mode=body.mode,
            state_overrides=body.state_overrides,
            auto_start=body.auto_start,
        )
        return {
            "mission": forked,
            "warning": (
                "Forked execution creates an independent LangGraph thread from the selected checkpoint. "
                "In Live Mode, re-running LLM nodes may produce different responses."
            ),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/missions/{mission_id}/export")
async def export_mission(mission_id: str, request: Request) -> dict[str, Any]:
    runtime = _get_runtime(request)
    mission = await runtime.event_store.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")

    events = await runtime.event_store.list_events(mission_id)
    checkpoints = await runtime.checkpointer_mgr.list_checkpoints(mission["thread_id"], limit=100)
    current_state = await runtime.checkpointer_mgr.get_state_snapshot(mission["thread_id"])

    return {
        "exported_for": "AI Space Mission — AURORA-7 LangGraph Simulator",
        "mission": mission,
        "current_state": current_state,
        "checkpoints": checkpoints,
        "events": events,
    }
