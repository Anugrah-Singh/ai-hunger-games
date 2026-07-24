import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from ai_hunger_games.api import create_app
from ai_hunger_games.settings import Settings


@pytest_asyncio.fixture
async def background_api_client(
    tmp_path: Path,
) -> AsyncIterator[httpx.AsyncClient]:
    database_path = tmp_path / "background-runs.db"
    app = create_app(
        database_url=f"sqlite+aiosqlite:///{database_path}",
        settings=Settings(
            use_real_llm=False,
            groq_api_key=None,
            groq_model="openai/gpt-oss-20b",
        ),
    )
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client


async def wait_for_terminal_run(
    client: httpx.AsyncClient,
    run_id: int,
) -> dict[str, object]:
    for _ in range(200):
        response = await client.get(f"/runs/{run_id}")
        assert response.status_code == 200
        payload = response.json()

        if payload["status"] in {"completed", "failed"}:
            return payload

        await asyncio.sleep(0.02)

    pytest.fail("Background generation did not reach a terminal state.")


@pytest.mark.asyncio
async def test_background_generation_completes_and_persists(
    background_api_client: httpx.AsyncClient,
) -> None:
    created = await background_api_client.post(
        "/experiments",
        json={"name": "Background completion"},
    )
    assert created.status_code == 201
    experiment_id = created.json()["id"]

    started = await background_api_client.post(
        f"/experiments/{experiment_id}/runs",
        json={"generation_count": 1},
    )
    assert started.status_code == 202

    terminal = await wait_for_terminal_run(
        background_api_client,
        started.json()["id"],
    )
    assert terminal["status"] == "completed"
    assert terminal["game_id"] is not None

    generations = await background_api_client.get(
        f"/experiments/{experiment_id}/generations"
    )
    assert generations.status_code == 200
    assert len(generations.json()) == 1

    active = await background_api_client.get(
        f"/experiments/{experiment_id}/runs/active"
    )
    assert active.status_code == 200
    assert active.json() is None


@pytest.mark.asyncio
async def test_background_generation_rejects_a_duplicate_active_run(
    background_api_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await background_api_client.post(
        "/experiments",
        json={"name": "Duplicate run protection"},
    )
    experiment_id = created.json()["id"]
    release = asyncio.Event()

    async def blocked_run_generations(
        *_: object,
        **__: object,
    ) -> list[object]:
        await release.wait()
        raise RuntimeError("test release")

    monkeypatch.setattr(
        "ai_hunger_games.api.run_generations",
        blocked_run_generations,
    )

    first = await background_api_client.post(
        f"/experiments/{experiment_id}/runs",
        json={"generation_count": 1},
    )
    assert first.status_code == 202

    second = await background_api_client.post(
        f"/experiments/{experiment_id}/runs",
        json={"generation_count": 1},
    )
    assert second.status_code == 409
    assert "already has a generation" in second.json()["detail"]

    release.set()
    terminal = await wait_for_terminal_run(
        background_api_client,
        first.json()["id"],
    )
    assert terminal["status"] == "failed"
