from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest_asyncio.fixture
async def test_app(tmp_path: Path):
    app = create_app(
        checkpoints_db_path=tmp_path / "checkpoints.db",
        events_db_path=tmp_path / "events.db",
    )
    async with app.router.lifespan_context(app):
        yield app


@pytest_asyncio.fixture
async def api_client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
