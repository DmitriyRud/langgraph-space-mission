from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.graph.workflow import build_mission_graph


class CheckpointerManager:
    """Manages AsyncSqliteSaver lifecycle, compiled LangGraph, and time-travel helpers."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._stack: AsyncExitStack | None = None
        self.checkpointer: AsyncSqliteSaver | None = None
        self.graph: Any = None

    async def startup(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._stack = AsyncExitStack()
        self.checkpointer = await self._stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(str(self.db_path))
        )
        await self.checkpointer.setup()
        self.graph = build_mission_graph(checkpointer=self.checkpointer)

    async def shutdown(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self.checkpointer = None
            self.graph = None

    def make_config(self, thread_id: str, checkpoint_id: str | None = None) -> dict[str, Any]:
        configurable: dict[str, Any] = {"thread_id": thread_id}
        if checkpoint_id:
            configurable["checkpoint_id"] = checkpoint_id
        return {"configurable": configurable}

    async def get_state_snapshot(self, thread_id: str, checkpoint_id: str | None = None) -> dict[str, Any] | None:
        assert self.graph is not None
        snapshot = await self.graph.aget_state(self.make_config(thread_id, checkpoint_id))
        if snapshot is None or not snapshot.values:
            return None
        return self._serialize_snapshot(snapshot)

    async def list_checkpoints(self, thread_id: str, limit: int = 50) -> list[dict[str, Any]]:
        assert self.graph is not None
        snapshots: list[dict[str, Any]] = []
        async for snap in self.graph.aget_state_history(self.make_config(thread_id), limit=limit):
            snapshots.append(self._serialize_snapshot(snap))
        return snapshots

    def _serialize_snapshot(self, snap: Any) -> dict[str, Any]:
        cfg = snap.config.get("configurable", {}) if snap.config else {}
        parent_cfg = snap.parent_config.get("configurable", {}) if snap.parent_config else {}

        interrupts: list[dict[str, Any]] = []
        for task in getattr(snap, "tasks", ()) or ():
            for intr in getattr(task, "interrupts", ()) or ():
                interrupts.append(
                    {
                        "id": getattr(intr, "id", None),
                        "value": getattr(intr, "value", None),
                    }
                )

        metadata = snap.metadata if isinstance(snap.metadata, dict) else {}
        return {
            "checkpoint_id": cfg.get("checkpoint_id"),
            "thread_id": cfg.get("thread_id"),
            "parent_checkpoint_id": parent_cfg.get("checkpoint_id"),
            "created_at": snap.created_at,
            "next": list(snap.next) if snap.next else [],
            "step": metadata.get("step"),
            "source": metadata.get("source"),
            "writes": metadata.get("writes"),
            "values": dict(snap.values) if isinstance(snap.values, dict) else {},
            "interrupts": interrupts,
        }
