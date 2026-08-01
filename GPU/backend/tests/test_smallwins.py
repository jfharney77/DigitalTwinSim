"""spec_19 — the twenty-small-wins batch (backend slice)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.live_store import load_recording
from app.main import TOURS_DIR


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import live_store
    from app.main import app

    monkeypatch.setattr(live_store, "SESSIONS_DIR", tmp_path)
    live_store.HUB.stop_session()
    return TestClient(app)


def test_latest_404_then_200(client: TestClient) -> None:
    from app import live_store

    live_store.HUB.stop_session()
    assert client.get("/api/live/latest").status_code == 404
    client.post("/api/live/ingest", json={"type": "gpu_sample", "utilPct": 7})
    r = client.get("/api/live/latest")
    assert r.status_code == 200 and r.json()["utilPct"] == 7


def test_delete_session_but_never_the_active_one(client: TestClient) -> None:
    a = client.post("/api/live/session", json={"name": "old"}).json()["id"]
    client.post("/api/live/ingest", json={"type": "gpu_sample"})
    b = client.post("/api/live/session", json={"name": "new"}).json()["id"]
    client.post("/api/live/ingest", json={"type": "gpu_sample"})
    assert client.delete(f"/api/live/sessions/{b}").status_code == 409  # active
    assert client.delete(f"/api/live/sessions/{a}").status_code == 200
    assert client.delete(f"/api/live/sessions/{a}").status_code == 404  # gone
    ids = [s["id"] for s in client.get("/api/live/sessions").json()]
    assert ids == [b]


def test_download_is_the_raw_jsonl(client: TestClient) -> None:
    sid = client.post("/api/live/session", json={"name": "dl"}).json()["id"]
    client.post("/api/live/ingest", json={"type": "gpu_sample", "utilPct": 1})
    r = client.get(f"/api/live/sessions/{sid}/download")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert '"utilPct":1' in r.text.replace(" ", "")
    assert client.get("/api/live/sessions/none/download").status_code == 404


def test_sessions_newest_first_with_limit(client: TestClient, monkeypatch) -> None:
    import time as _t

    stamps = iter(["20260731-100000", "20260731-100001", "20260731-100002"])
    monkeypatch.setattr(_t, "strftime", lambda fmt: next(stamps))
    for name in ("one", "two", "three"):
        client.post("/api/live/session", json={"name": name})
        client.post("/api/live/ingest", json={"type": "gpu_sample"})
    names = [s["name"] for s in client.get("/api/live/sessions").json()]
    assert names == ["three", "two", "one"]
    assert len(client.get("/api/live/sessions?limit=2").json()) == 2


def test_health_is_informative(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "version" in body and "sessions" in body and "activeSession" in body


def test_hour_plus_elapsed_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json={
            "type": "kernel_launch",
            "kernel": "k",
            "grid": [1, 1, 1],
            "block": [1, 1, 1],
            "blocks": [],
            "elapsedMs": 4_000_000,
        },
    )
    assert r.status_code == 422


def test_tour_recordings_account_for_their_grids() -> None:
    # spec_19 #7: golden fixtures held to the same honesty as live ingest.
    for p in sorted(TOURS_DIR.glob("*.jsonl")):
        for frame in load_recording(p):
            if frame.kind != "kernel" or frame.source == "cupti":
                continue
            grid = frame.grid
            assert grid is not None
            total = sum(a.blocks_run for a in frame.sm_activity)
            assert total == grid[0] * grid[1] * grid[2], p.name