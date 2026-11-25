import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from langgraph.types import Command

from app.llm.provider import LLMUnavailableError
from app.persistence.checkpointer import CheckpointerManager
from app.persistence.event_store import EventStore
from app.scenarios.catalog import get_scenario
from app.state.mission_state import create_baseline_ship_state


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


class MissionAlreadyRunningError(Exception):
    """Raised when attempting to start or resume a mission that is already executing."""


class MissionRuntimeManager:
    """Orchestrates real LangGraph execution, multi-mode streaming, SSE fan-out, and time travel."""

    def __init__(
        self,
        checkpointer_mgr: CheckpointerManager,
        event_store: EventStore,
    ) -> None:
        self.checkpointer_mgr = checkpointer_mgr
        self.event_store = event_store
        self._running_tasks: dict[str, asyncio.Task[Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._task_start_times: dict[str, float] = {}
        self._task_attempts: dict[tuple[str, str], int] = {}

    def _get_lock(self, mission_id: str) -> asyncio.Lock:
        if mission_id not in self._locks:
            self._locks[mission_id] = asyncio.Lock()
        return self._locks[mission_id]

    def is_running(self, mission_id: str) -> bool:
        task = self._running_tasks.get(mission_id)
        return task is not None and not task.done()

    async def shutdown(self) -> None:
        for task in list(self._running_tasks.values()):
            if not task.done():
                task.cancel()
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        self._running_tasks.clear()

    async def _publish_event(
        self,
        *,
        mission_id: str,
        thread_id: str,
        event_type: str,
        payload: dict[str, Any],
        node_id: str | None = None,
        task_id: str | None = None,
        iteration: int | None = None,
        checkpoint_id: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": _new_event_id(),
            "event_type": event_type,
            "timestamp": _utc_now(),
            "mission_id": mission_id,
            "thread_id": thread_id,
            "node_id": node_id,
            "task_id": task_id,
            "iteration": iteration,
            "checkpoint_id": checkpoint_id,
            "payload": payload,
        }
        stored = await self.event_store.append_event(event)
        for queue in list(self._subscribers.get(mission_id, set())):
            try:
                queue.put_nowait(stored)
            except asyncio.QueueFull:
                pass
        return stored

    async def subscribe(
        self,
        mission_id: str,
        after_event_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield missed persisted events followed by live events for SSE clients."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=500)
        subs = self._subscribers.setdefault(mission_id, set())
        subs.add(queue)
        seen_ids: set[str] = set()

        try:
            missed = await self.event_store.list_events(mission_id, after_event_id=after_event_id)
            for evt in missed:
                seen_ids.add(evt["event_id"])
                yield evt

            while True:
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=15.0)
                    if evt["event_id"] not in seen_ids:
                        seen_ids.add(evt["event_id"])
                        yield evt
                except asyncio.TimeoutError:
                    yield {
                        "event_id": "keepalive",
                        "event_type": "ping",
                        "timestamp": _utc_now(),
                        "mission_id": mission_id,
                        "thread_id": "",
                        "payload": {},
                    }
        finally:
            subs.discard(queue)
            if not subs:
                self._subscribers.pop(mission_id, None)

    async def create_mission(
        self,
        *,
        scenario_id: str,
        mode: str = "demo",
        max_iterations: int = 5,
        language: str = "en",
        parent_mission_id: str | None = None,
        parent_checkpoint_id: str | None = None,
    ) -> dict[str, Any]:
        get_scenario(scenario_id)
        mission_id = f"msn_{uuid.uuid4().hex[:10]}"
        thread_id = f"thr_{uuid.uuid4().hex[:10]}"
        return await self.event_store.create_mission(
            mission_id=mission_id,
            thread_id=thread_id,
            scenario_id=scenario_id,
            mode=mode,
            language=language,
            max_iterations=max_iterations,
            status="created",
            parent_mission_id=parent_mission_id,
            parent_checkpoint_id=parent_checkpoint_id,
        )

    async def start_mission(self, mission_id: str) -> dict[str, Any]:
        lock = self._get_lock(mission_id)
        async with lock:
            if self.is_running(mission_id):
                raise MissionAlreadyRunningError(f"Mission {mission_id} is already running.")

            mission = await self.event_store.get_mission(mission_id)
            if mission is None:
                raise KeyError(f"Mission not found: {mission_id}")

            scenario = get_scenario(mission["scenario_id"])
            baseline = create_baseline_ship_state()
            initial_input: dict[str, Any] = {
                "mission_id": mission_id,
                "scenario_id": scenario.id,
                "mode": mission["mode"],
                "language": mission.get("language", "en"),
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
                "risk_level": scenario.severity,
                "iteration": 1,
                "max_iterations": int(mission["max_iterations"]),
                "user_feedback": None,
                "approval_status": "pending",
                "mission_result": None,
                "event_history": [],
                "errors": [],
                "plan_revision_count": 0,
            }

            await self.event_store.update_mission_status(mission_id, "running")
            await self._publish_event(
                mission_id=mission_id,
                thread_id=mission["thread_id"],
                event_type="mission_started",
                iteration=1,
                payload={
                    "scenario_id": scenario.id,
                    "scenario_title": scenario.title,
                    "mode": mission["mode"],
                    "max_iterations": mission["max_iterations"],
                },
            )

            task = asyncio.create_task(
                self._execute_graph_stream(
                    mission_id=mission_id,
                    thread_id=mission["thread_id"],
                    graph_input=initial_input,
                )
            )
            self._running_tasks[mission_id] = task
            return await self.event_store.get_mission(mission_id)  # type: ignore[return-value]

    async def resume_mission(
        self,
        mission_id: str,
        *,
        decision: str,
        feedback: str = "",
        switch_to_demo: bool = False,
    ) -> dict[str, Any]:
        lock = self._get_lock(mission_id)
        async with lock:
            if self.is_running(mission_id):
                raise MissionAlreadyRunningError(f"Mission {mission_id} is already running.")

            mission = await self.event_store.get_mission(mission_id)
            if mission is None:
                raise KeyError(f"Mission not found: {mission_id}")

            thread_id = mission["thread_id"]
            config = self.checkpointer_mgr.make_config(thread_id)

            if switch_to_demo and mission["mode"] != "demo":
                await self.event_store.update_mission_mode(mission_id, "demo")
                await self.checkpointer_mgr.graph.aupdate_state(config, {"mode": "demo"})

            snapshot = await self.checkpointer_mgr.get_state_snapshot(thread_id)
            if snapshot is None:
                raise ValueError("Cannot resume mission: no persisted checkpoint state found.")

            iteration = int(snapshot["values"].get("iteration", 1))
            has_interrupt = bool(snapshot.get("interrupts"))

            await self.event_store.update_mission_status(mission_id, "running")
            await self._publish_event(
                mission_id=mission_id,
                thread_id=thread_id,
                event_type="execution_resumed",
                node_id="human_approval" if has_interrupt else None,
                iteration=iteration,
                checkpoint_id=snapshot.get("checkpoint_id"),
                payload={
                    "decision": decision,
                    "feedback": feedback,
                    "switch_to_demo": switch_to_demo,
                    "resumed_from_interrupt": has_interrupt,
                },
            )

            graph_input: Any = (
                Command(resume={"decision": decision, "feedback": feedback})
                if has_interrupt
                else None
            )

            task = asyncio.create_task(
                self._execute_graph_stream(
                    mission_id=mission_id,
                    thread_id=thread_id,
                    graph_input=graph_input,
                )
            )
            self._running_tasks[mission_id] = task
            return await self.event_store.get_mission(mission_id)  # type: ignore[return-value]

    async def fork_mission(
        self,
        source_mission_id: str,
        *,
        checkpoint_id: str,
        mode: str | None = None,
        state_overrides: dict[str, Any] | None = None,
        auto_start: bool = True,
    ) -> dict[str, Any]:
        """LangGraph Time Travel: branch a new mission thread from an existing checkpoint."""
        source = await self.event_store.get_mission(source_mission_id)
        if source is None:
            raise KeyError(f"Source mission not found: {source_mission_id}")

        source_snap = await self.checkpointer_mgr.get_state_snapshot(
            source["thread_id"], checkpoint_id=checkpoint_id
        )
        if source_snap is None:
            raise ValueError(f"Checkpoint '{checkpoint_id}' not found for mission '{source_mission_id}'.")

        fork_mode = mode or source["mode"]
        forked = await self.create_mission(
            scenario_id=source["scenario_id"],
            mode=fork_mode,
            max_iterations=int(source["max_iterations"]),
            language=source.get("language", "en"),
            parent_mission_id=source_mission_id,
            parent_checkpoint_id=checkpoint_id,
        )

        new_mission_id = forked["mission_id"]
        new_thread_id = forked["thread_id"]
        new_config = self.checkpointer_mgr.make_config(new_thread_id)

        # Build clean state from the historical checkpoint values
        fork_values = dict(source_snap["values"])
        fork_values["mission_id"] = new_mission_id
        fork_values["mode"] = fork_mode
        if state_overrides:
            for key, val in state_overrides.items():
                if key in fork_values:
                    fork_values[key] = val

        # Determine which node wrote this checkpoint so LangGraph resumes from the exact next step
        writes = source_snap.get("writes")
        as_node: str | None = None
        if isinstance(writes, dict) and writes:
            candidate = next(iter(writes.keys()))
            if candidate not in ("__start__", "__interrupt__"):
                as_node = candidate
        if as_node is None:
            as_node = "incident_init"

        await self.checkpointer_mgr.graph.aupdate_state(
            new_config,
            values=fork_values,
            as_node=as_node,
        )

        await self._publish_event(
            mission_id=new_mission_id,
            thread_id=new_thread_id,
            event_type="mission_started",
            iteration=int(fork_values.get("iteration", 1)),
            checkpoint_id=checkpoint_id,
            payload={
                "forked_from_mission_id": source_mission_id,
                "forked_from_checkpoint_id": checkpoint_id,
                "as_node": as_node,
                "mode": fork_mode,
                "scenario_id": source["scenario_id"],
                "time_travel": True,
            },
        )

        if auto_start:
            await self.event_store.update_mission_status(new_mission_id, "running")
            task = asyncio.create_task(
                self._execute_graph_stream(
                    mission_id=new_mission_id,
                    thread_id=new_thread_id,
                    graph_input=None,
                )
            )
            self._running_tasks[new_mission_id] = task

        return await self.event_store.get_mission(new_mission_id)  # type: ignore[return-value]

    async def _execute_graph_stream(
        self,
        *,
        mission_id: str,
        thread_id: str,
        graph_input: Any,
    ) -> None:
        config = self.checkpointer_mgr.make_config(thread_id)
        current_iteration = 1
        latest_checkpoint_id: str | None = None

        try:
            async for stream_mode, chunk in self.checkpointer_mgr.graph.astream(
                graph_input,
                config,
                stream_mode=["updates", "values", "custom", "debug"],
            ):
                if stream_mode == "values" and isinstance(chunk, dict):
                    current_iteration = int(chunk.get("iteration", current_iteration))
                    await self._publish_event(
                        mission_id=mission_id,
                        thread_id=thread_id,
                        event_type="state_snapshot",
                        iteration=current_iteration,
                        checkpoint_id=latest_checkpoint_id,
                        payload={"state": chunk},
                    )

                elif stream_mode == "debug" and isinstance(chunk, dict):
                    debug_type = chunk.get("type")
                    payload = chunk.get("payload") or {}
                    if debug_type == "checkpoint" and isinstance(payload, dict):
                        cfg = payload.get("config", {}).get("configurable", {})
                        latest_checkpoint_id = cfg.get("checkpoint_id")
                        meta = payload.get("metadata") or {}
                        await self._publish_event(
                            mission_id=mission_id,
                            thread_id=thread_id,
                            event_type="checkpoint_created",
                            iteration=current_iteration,
                            checkpoint_id=latest_checkpoint_id,
                            payload={
                                "checkpoint_id": latest_checkpoint_id,
                                "step": chunk.get("step", meta.get("step")),
                                "source": meta.get("source"),
                                "next": list(payload.get("next", [])),
                            },
                        )
                    elif debug_type == "task" and isinstance(payload, dict):
                        task_id = str(payload.get("id", ""))
                        node_name = str(payload.get("name", ""))
                        attempt_key = (mission_id, task_id)
                        attempt = self._task_attempts.get(attempt_key, 0) + 1
                        self._task_attempts[attempt_key] = attempt
                        self._task_start_times[task_id] = time.perf_counter()

                        if attempt > 1:
                            await self._publish_event(
                                mission_id=mission_id,
                                thread_id=thread_id,
                                event_type="retry",
                                node_id=node_name,
                                task_id=task_id,
                                iteration=current_iteration,
                                checkpoint_id=latest_checkpoint_id,
                                payload={"attempt": attempt, "node": node_name},
                            )

                        await self._publish_event(
                            mission_id=mission_id,
                            thread_id=thread_id,
                            event_type="node_started",
                            node_id=node_name,
                            task_id=task_id,
                            iteration=current_iteration,
                            checkpoint_id=latest_checkpoint_id,
                            payload={
                                "attempt": attempt,
                                "triggers": list(payload.get("triggers", [])),
                                "input_state": payload.get("input") if isinstance(payload.get("input"), dict) else None,
                            },
                        )
                    elif debug_type == "task_result" and isinstance(payload, dict):
                        task_id = str(payload.get("id", ""))
                        node_name = str(payload.get("name", ""))
                        started = self._task_start_times.pop(task_id, None)
                        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
                        interrupts = payload.get("interrupts") or []
                        error = payload.get("error")

                        if interrupts:
                            first_intr = interrupts[0]
                            intr_val = first_intr.get("value") if isinstance(first_intr, dict) else getattr(first_intr, "value", first_intr)
                            await self._publish_event(
                                mission_id=mission_id,
                                thread_id=thread_id,
                                event_type="human_approval_requested",
                                node_id=node_name,
                                task_id=task_id,
                                iteration=current_iteration,
                                checkpoint_id=latest_checkpoint_id,
                                payload={
                                    "interrupt": intr_val,
                                    "duration_ms": duration_ms,
                                },
                            )
                        elif error:
                            await self._publish_event(
                                mission_id=mission_id,
                                thread_id=thread_id,
                                event_type="error",
                                node_id=node_name,
                                task_id=task_id,
                                iteration=current_iteration,
                                checkpoint_id=latest_checkpoint_id,
                                payload={
                                    "error": str(error),
                                    "duration_ms": duration_ms,
                                },
                            )
                        else:
                            await self._publish_event(
                                mission_id=mission_id,
                                thread_id=thread_id,
                                event_type="node_completed",
                                node_id=node_name,
                                task_id=task_id,
                                iteration=current_iteration,
                                checkpoint_id=latest_checkpoint_id,
                                payload={
                                    "duration_ms": duration_ms,
                                    "result": payload.get("result"),
                                },
                            )

                elif stream_mode == "updates" and isinstance(chunk, dict):
                    for node_name, partial in chunk.items():
                        if node_name == "__interrupt__":
                            continue
                        await self._publish_event(
                            mission_id=mission_id,
                            thread_id=thread_id,
                            event_type="state_updated",
                            node_id=node_name,
                            iteration=current_iteration,
                            checkpoint_id=latest_checkpoint_id,
                            payload={
                                "partial_update": partial if isinstance(partial, dict) else {"value": partial},
                            },
                        )

                elif stream_mode == "custom" and isinstance(chunk, dict):
                    await self._publish_event(
                        mission_id=mission_id,
                        thread_id=thread_id,
                        event_type=str(chunk.get("event_type", "custom")),
                        node_id=chunk.get("node_id"),
                        iteration=chunk.get("iteration", current_iteration),
                        checkpoint_id=latest_checkpoint_id,
                        payload=chunk.get("payload", {}),
                    )

            # Inspect final snapshot to determine if paused at interrupt or completed
            final_snap = await self.checkpointer_mgr.get_state_snapshot(thread_id)
            if final_snap and final_snap.get("interrupts"):
                await self.event_store.update_mission_status(mission_id, "awaiting_approval")
            else:
                result = (final_snap or {}).get("values", {}).get("mission_result") or {}
                outcome = result.get("outcome", "completed")
                final_status = "completed" if outcome == "success" else ("failed" if outcome == "failure" else "completed")
                await self.event_store.update_mission_status(mission_id, final_status)
                await self._publish_event(
                    mission_id=mission_id,
                    thread_id=thread_id,
                    event_type="mission_completed",
                    iteration=current_iteration,
                    checkpoint_id=(final_snap or {}).get("checkpoint_id"),
                    payload={
                        "outcome": outcome,
                        "mission_result": result,
                        "ship_state": (final_snap or {}).get("values", {}).get("ship_state"),
                    },
                )

        except LLMUnavailableError as exc:
            await self.event_store.update_mission_status(mission_id, "error")
            await self._publish_event(
                mission_id=mission_id,
                thread_id=thread_id,
                event_type="error",
                iteration=current_iteration,
                checkpoint_id=latest_checkpoint_id,
                payload={
                    "error_type": "LLMUnavailableError",
                    "message": str(exc),
                    "can_switch_to_demo": True,
                },
            )
        except asyncio.CancelledError:
            await self.event_store.update_mission_status(mission_id, "cancelled")
            raise
        except Exception as exc:
            await self.event_store.update_mission_status(mission_id, "error")
            await self._publish_event(
                mission_id=mission_id,
                thread_id=thread_id,
                event_type="error",
                iteration=current_iteration,
                checkpoint_id=latest_checkpoint_id,
                payload={
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "can_switch_to_demo": False,
                },
            )
