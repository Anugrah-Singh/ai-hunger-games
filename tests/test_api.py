import asyncio
import re
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from ai_hunger_games.api import create_app
from ai_hunger_games.repositories import ExperimentRepository
from ai_hunger_games.settings import Settings


@pytest_asyncio.fixture
async def api_client(
    tmp_path: Path,
) -> AsyncIterator[httpx.AsyncClient]:
    database_path = tmp_path / "api.db"

    app = create_app(
        database_url=f"sqlite+aiosqlite:///{database_path}",
        settings=Settings(
            use_real_llm=False,
            groq_api_key=None,
            groq_model="openai/gpt-oss-20b",
        ),
    )

    transport = httpx.ASGITransport(app=app)

    # ASGITransport does not manage application lifespan events.
    # Entering the application's lifespan explicitly initializes the
    # temporary database before requests are issued.
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client


@pytest.mark.asyncio
async def test_api_runs_and_exposes_a_simulated_generation(
    api_client: httpx.AsyncClient,
) -> None:
    health = await api_client.get("/health")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    created = await api_client.post(
        "/experiments",
        json={"name": "API test experiment"},
    )

    assert created.status_code == 201

    experiment = created.json()

    assert experiment["provider_name"] == "Simulated providers"

    experiment_id = experiment["id"]

    before_run = await api_client.get(f"/experiments/{experiment_id}")

    assert before_run.status_code == 200

    before_run_payload = before_run.json()

    assert before_run_payload["generation_count"] == 0
    assert len(before_run_payload["current_population"]) == 4
    assert before_run_payload["can_run"] is True
    assert before_run_payload["run_block_reason"] is None

    duplicate = await api_client.post(
        "/experiments",
        json={"name": "API test experiment"},
    )

    assert duplicate.status_code == 409

    run = await api_client.post(
        f"/experiments/{experiment_id}/generations",
        json={"generation_count": 1},
    )

    assert run.status_code == 200

    generations = run.json()

    assert len(generations) == 1
    assert generations[0]["generation_number"] == 1
    assert generations[0]["round_count"] == 3
    assert set(generations[0]["seeds"]) == {
        "candidate_order_seed",
        "voting_seed",
        "elimination_seed",
        "replacement_seed",
    }

    experiment_detail = await api_client.get(f"/experiments/{experiment_id}")

    assert experiment_detail.status_code == 200

    experiment_detail_payload = experiment_detail.json()

    assert experiment_detail_payload["generation_count"] == 1
    assert len(experiment_detail_payload["current_population"]) == 4

    game_id = generations[0]["game_id"]

    generation_detail = await api_client.get(f"/generations/{game_id}")

    assert generation_detail.status_code == 200

    generation_payload = generation_detail.json()
    rounds = generation_payload["rounds"]

    assert len(generation_payload["starting_agents"]) == 4
    assert len(generation_payload["final_agents"]) == 4
    assert len(rounds) == 3

    # The browser receives anonymous candidate IDs only. Internal author and
    # target IDs remain in persistence for scoring and analysis, not HTTP.
    first_answer = rounds[0]["answers"][0]

    assert set(first_answer) == {
        "candidate_id",
        "content",
        "attempt_count",
    }
    assert "agent_id" not in first_answer

    first_vote = rounds[0]["votes"][0]

    assert set(first_vote) == {
        "voter_agent_id",
        "selected_candidate_id",
    }
    assert "selected_agent_id" not in first_vote

    first_score = rounds[0]["scores"][0]

    assert set(first_score) == {
        "candidate_id",
        "score",
    }
    assert "agent_id" not in first_score

    votes = await api_client.get(f"/generations/{game_id}/votes")

    assert votes.status_code == 200
    assert len(votes.json()) == 12
    assert all(
        set(vote)
        == {
            "voter_agent_id",
            "selected_candidate_id",
        }
        for vote in votes.json()
    )

    analysis = await api_client.get(f"/experiments/{experiment_id}/analysis")

    assert analysis.status_code == 200

    analysis_payload = analysis.json()

    assert analysis_payload["generation_count"] == 1
    assert "cautions" in analysis_payload
    assert {
        "personality",
        "generation_scores",
        "total_points",
    } <= set(analysis_payload["agent_performance"][0])
    assert {
        "periods",
        "eligible_voting_opportunities",
        "random_baseline_rate",
    } <= set(analysis_payload["vote_relationships"][0])


@pytest.mark.asyncio
async def test_api_accepts_one_generation_per_run_request(
    api_client: httpx.AsyncClient,
) -> None:
    created = await api_client.post(
        "/experiments",
        json={"name": "Single-generation API experiment"},
    )

    assert created.status_code == 201

    response = await api_client.post(
        f"/experiments/{created.json()['id']}/generations",
        json={"generation_count": 2},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_hides_unexpected_generation_failure(
    api_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    created = await api_client.post(
        "/experiments",
        json={"name": "Failure privacy API experiment"},
    )

    assert created.status_code == 201

    async def fail_run_generations(
        *_: object,
        **__: object,
    ) -> object:
        raise RuntimeError("provider response contained secret diagnostic data")

    monkeypatch.setattr(
        "ai_hunger_games.api.run_generations",
        fail_run_generations,
    )

    with caplog.at_level(
        "ERROR",
        logger="ai_hunger_games.api",
    ):
        response = await api_client.post(
            f"/experiments/{created.json()['id']}/generations",
            json={"generation_count": 1},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Generation did not complete; no generation was saved."
    )
    assert "secret diagnostic data" not in response.text
    assert "secret diagnostic data" in caplog.text


@pytest.mark.asyncio
async def test_api_marks_legacy_experiments_as_read_only(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy-api.db"

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
        async with app.state.session_factory() as session:
            legacy_experiment = await ExperimentRepository(session).create_experiment(
                "Imported history"
            )

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            detail = await client.get(f"/experiments/{legacy_experiment.id}")

            assert detail.status_code == 200
            assert detail.json()["can_run"] is False
            assert "no saved provider" in detail.json()["run_block_reason"]
            assert detail.json()["current_population"] == []

            run = await client.post(
                (f"/experiments/{legacy_experiment.id}/generations"),
                json={"generation_count": 1},
            )

            assert run.status_code == 409


@pytest.mark.asyncio
async def test_dashboard_and_static_asset_are_served(
    api_client: httpx.AsyncClient,
) -> None:
    dashboard = await api_client.get("/")

    assert dashboard.status_code == 200
    assert "AI Hunger Games" in dashboard.text
    assert 'id="root"' in dashboard.text

    script_match = re.search(
        r'src="(?P<path>/static/assets/index-[^"]+\.js)"',
        dashboard.text,
    )

    assert script_match is not None

    asset = await api_client.get("/static/arena-mark.png")

    assert asset.status_code == 200
    assert asset.headers["content-type"] == "image/png"
    assert len(asset.content) > 1000

    script = await api_client.get(script_match.group("path"))

    assert script.status_code == 200
    assert "AI Hunger Games" in script.text


@pytest.mark.asyncio
async def test_api_rejects_unknown_experiments(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get("/experiments/999")

    assert response.status_code == 404

    invalid_identifier = await api_client.get("/experiments/0")

    assert invalid_identifier.status_code == 422


@pytest.mark.asyncio
async def test_api_creates_quick_demo_by_default(
    api_client: httpx.AsyncClient,
) -> None:
    created = await api_client.post(
        "/experiments",
        json={"name": "Recruiter quick demo"},
    )

    assert created.status_code == 201

    experiment_id = created.json()["id"]

    detail_response = await api_client.get(f"/experiments/{experiment_id}")

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert len(detail["current_population"]) == 4
    assert detail["generation_count"] == 0
    assert detail["can_run"] is True

    run_response = await api_client.post(
        f"/experiments/{experiment_id}/generations",
        json={"generation_count": 1},
    )

    assert run_response.status_code == 200

    generations = run_response.json()

    assert len(generations) == 1
    assert generations[0]["round_count"] == 3

    saved_detail = await api_client.get(f"/experiments/{experiment_id}")

    assert saved_detail.status_code == 200
    assert len(saved_detail.json()["current_population"]) == 4


@pytest.mark.asyncio
async def test_api_creates_full_tournament_when_requested(
    api_client: httpx.AsyncClient,
) -> None:
    created = await api_client.post(
        "/experiments",
        json={
            "name": "Full tournament",
            "preset": "full_tournament",
        },
    )

    assert created.status_code == 201

    experiment_id = created.json()["id"]

    detail_response = await api_client.get(f"/experiments/{experiment_id}")

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert len(detail["current_population"]) == 8
    assert detail["generation_count"] == 0
    assert detail["can_run"] is True

    run_response = await api_client.post(
        f"/experiments/{experiment_id}/generations",
        json={"generation_count": 1},
    )

    assert run_response.status_code == 200

    generations = run_response.json()

    assert len(generations) == 1
    assert generations[0]["round_count"] == 8

    saved_detail = await api_client.get(f"/experiments/{experiment_id}")

    assert saved_detail.status_code == 200
    assert len(saved_detail.json()["current_population"]) == 8


@pytest.mark.asyncio
async def test_api_rejects_unknown_experiment_preset(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.post(
        "/experiments",
        json={
            "name": "Invalid preset",
            "preset": "instant_chaos",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_starts_background_generation_run(
    api_client: httpx.AsyncClient,
) -> None:
    created = await api_client.post(
        "/experiments",
        json={"name": "Background run"},
    )

    assert created.status_code == 201

    experiment_id = created.json()["id"]

    started = await api_client.post(
        f"/experiments/{experiment_id}/runs",
        json={"generation_count": 1},
    )

    assert started.status_code == 202

    started_payload = started.json()

    assert started_payload["experiment_id"] == (experiment_id)
    assert started_payload["generation_number"] == 1
    assert started_payload["status"] in {
        "queued",
        "running",
        "completed",
    }

    run_id = started_payload["id"]

    for _ in range(50):
        current = await api_client.get(f"/runs/{run_id}")

        assert current.status_code == 200

        current_payload = current.json()

        if current_payload["status"] in {
            "completed",
            "failed",
        }:
            break

        await asyncio.sleep(0.02)
    else:
        pytest.fail("Background generation did not finish.")

    assert current_payload["status"] == "completed"
    assert current_payload["game_id"] is not None

    generations = await api_client.get(f"/experiments/{experiment_id}/generations")

    assert generations.status_code == 200
    assert len(generations.json()) == 1


@pytest.mark.asyncio
async def test_api_rejects_second_active_background_run(
    api_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await api_client.post(
        "/experiments",
        json={"name": "One active run"},
    )

    experiment_id = created.json()["id"]

    release = asyncio.Event()

    async def blocked_run_generations(
        *_: object,
        **__: object,
    ) -> list[object]:
        await release.wait()
        return []

    monkeypatch.setattr(
        "ai_hunger_games.api.run_generations",
        blocked_run_generations,
    )

    first = await api_client.post(
        f"/experiments/{experiment_id}/runs",
        json={"generation_count": 1},
    )

    assert first.status_code == 202

    second = await api_client.post(
        f"/experiments/{experiment_id}/runs",
        json={"generation_count": 1},
    )

    assert second.status_code == 409

    release.set()
