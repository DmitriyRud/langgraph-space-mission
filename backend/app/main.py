from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import Settings, get_settings
from app.persistence.checkpointer import CheckpointerManager
from app.persistence.event_store import EventStore
from app.streaming.manager import MissionRuntimeManager


def create_app(
    *,
    checkpoints_db_path: Path | None = None,
    events_db_path: Path | None = None,
) -> FastAPI:
    settings: Settings = get_settings()
    ckpt_path = checkpoints_db_path or settings.checkpoints_db_path
    evts_path = events_db_path or settings.events_db_path

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        checkpointer_mgr = CheckpointerManager(ckpt_path)
        event_store = EventStore(evts_path)
        await checkpointer_mgr.startup()
        await event_store.startup()
        runtime = MissionRuntimeManager(checkpointer_mgr, event_store)

        app.state.checkpointer_mgr = checkpointer_mgr
        app.state.event_store = event_store
        app.state.runtime = runtime
        try:
            yield
        finally:
            await runtime.shutdown()
            await event_store.shutdown()
            await checkpointer_mgr.shutdown()

    app = FastAPI(
        title="AI Space Mission — AURORA-7 LangGraph Simulator",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
