"""spec_21 — third small-wins batch (backend slice)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import live_store
    from app.main import app

    monkeypatch.setattr(live_store, "SESSIONS_DIR", tmp_path)
    live_store.HUB.stop_session()
    return TestClient(app)


def test_config_exposes_the_caps(client: TestClient) -> None:
    cfg = client.get("/api/live/config").json()
    assert cfg["maxSessionEvents"] == 100_000
    assert cfg["defaultSmCount"] == 24
    assert cfg["maxSmid"] == 1024 and cfg["maxSpans"] == 2048


def test_batch_ingest(client: TestClient) -> None:
    sid = client.post("/api/live/session", json={"name": "batch"}).json()["id"]
    r = client.post(
        "/api/live/ingest/batch",
        json=[
            {"type": "gpu_sample", "utilPct": 1},
            {"type": "gpu_sample", "utilPct": 2},
            {"type": "gpu_sample", "utilPct": 3},
        ],
    )
    assert r.status_code == 200
    assert r.json()["utilPct"] == 3  # the last state comes back
    t = client.get(f"/api/live/sessions/{sid}/trace").json()
    assert len(t["trace"]) == 3
    assert client.post("/api/live/ingest/batch", json=[]).status_code == 422
    # A bad event mid-batch stops with its error; prior events are recorded.
    r = client.post(
        "/api/live/ingest/batch",
        json=[{"type": "gpu_sample", "utilPct": 4}, {"type": "nonsense"}],
    )
    assert r.status_code == 422


def test_trace_pagination(client: TestClient) -> None:
    sid = client.post("/api/live/session", json={"name": "page"}).json()["id"]
    for i in range(10):
        client.post("/api/live/ingest", json={"type": "gpu_sample", "utilPct": i})
    full = client.get(f"/api/live/sessions/{sid}/trace").json()
    assert full["total"] == 10 and len(full["trace"]) == 10
    page = client.get(f"/api/live/sessions/{sid}/trace?from=4&limit=3").json()
    assert page["total"] == 10
    assert [s["utilPct"] for s in page["trace"]] == [4, 5, 6]


def test_health_reports_tours(client: TestClient) -> None:
    assert client.get("/api/health").json()["toursAvailable"] == 6


def test_sessions_dir_gitignores_itself(client: TestClient, tmp_path) -> None:
    client.post("/api/live/session", json={"name": "gi"})
    gi = tmp_path / ".gitignore"
    assert gi.exists() and "*" in gi.read_text()


def test_api_surface_snapshot() -> None:
    # spec_21 #17: losing or renaming a route should fail CI by name.
    from app.main import app

    paths = sorted(
        {r.path for r in app.routes if r.path.startswith("/api")}  # type: ignore[attr-defined]
    )
    assert paths == [
        "/api/anatomy",
        "/api/anatomy/{anatomy_id}",
        "/api/health",
        "/api/levels",
        "/api/live/config",
        "/api/live/import",
        "/api/live/ingest",
        "/api/live/ingest/batch",
        "/api/live/latest",
        "/api/live/session",
        "/api/live/sessions",
        "/api/live/sessions/{session_id}",
        "/api/live/sessions/{session_id}/download",
        "/api/live/sessions/{session_id}/events.csv",
        "/api/live/sessions/{session_id}/summary",
        "/api/live/sessions/{session_id}/trace",
        "/api/live/stream",
        "/api/measurements",
        "/api/profiles",
        "/api/profiles/default",
        "/api/simulate",
        "/api/tour",
        "/api/tour/recordings/{lesson_id}",
    ]
