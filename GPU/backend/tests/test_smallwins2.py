"""spec_20 — second twenty-small-wins batch (backend slice)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURE = Path(__file__).parent / "fixtures" / "live_session.jsonl"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import live_store
    from app.main import app

    monkeypatch.setattr(live_store, "SESSIONS_DIR", tmp_path)
    live_store.HUB.stop_session()
    return TestClient(app)


def _record_fixture(client: TestClient, name: str = "fx") -> str:
    sid = client.post("/api/live/session", json={"name": name}).json()["id"]
    for line in FIXTURE.read_text().splitlines():
        client.post("/api/live/ingest", json=json.loads(line)["event"])
    return sid


def test_summary(client: TestClient) -> None:
    sid = _record_fixture(client)
    s = client.get(f"/api/live/sessions/{sid}/summary").json()
    assert s["frames"] == 6
    assert s["kernelLaunches"] == 3
    va = next(k for k in s["kernelStats"] if k["kernel"] == "vector_add")
    assert va["runs"] == 2
    assert va["bestMs"] <= va["worstMs"]
    assert client.get("/api/live/sessions/none/summary").status_code == 404


def test_import_roundtrip_and_rejection(client: TestClient) -> None:
    sid = _record_fixture(client)
    raw = client.get(f"/api/live/sessions/{sid}/download").text
    r = client.post("/api/live/import", json={"name": "copy", "jsonl": raw})
    assert r.status_code == 200
    new = r.json()
    assert new["eventCount"] == 6 and new["id"] != sid
    # The imported copy replays identically to the original.
    a = client.get(f"/api/live/sessions/{sid}/trace").json()["trace"]
    b = client.get(f"/api/live/sessions/{new['id']}/trace").json()["trace"]
    strip = lambda t: [{**s, "sessionId": ""} for s in t]  # noqa: E731
    assert strip(a) == strip(b)
    # Garbage and empty uploads are rejected whole — nothing gets written.
    before = len(client.get("/api/live/sessions").json())
    assert (
        client.post("/api/live/import", json={"name": "bad", "jsonl": "{oops}"})
    ).status_code == 422
    assert (
        client.post("/api/live/import", json={"name": "bad", "jsonl": ""})
    ).status_code == 422
    assert len(client.get("/api/live/sessions").json()) == before


def test_rename(client: TestClient) -> None:
    sid = _record_fixture(client, "before")
    client.post("/api/live/session", json={"name": "other"})  # deactivate sid
    r = client.patch(f"/api/live/sessions/{sid}", json={"name": "After Runs"})
    assert r.status_code == 200
    new = r.json()
    assert new["name"] == "after-runs" and new["eventCount"] == 6
    assert new["id"].startswith("-".join(sid.split("-", 3)[:3]))
    assert client.get(f"/api/live/sessions/{new['id']}/trace").status_code == 200
    # Active session refuses rename.
    active = [s for s in client.get("/api/live/sessions").json() if s["active"]]
    if active:
        assert (
            client.patch(
                f"/api/live/sessions/{active[0]['id']}", json={"name": "x"}
            ).status_code
            == 409
        )


def test_events_csv(client: TestClient) -> None:
    sid = _record_fixture(client)
    r = client.get(f"/api/live/sessions/{sid}/events.csv")
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0] == "kernel,tMs,elapsedMs,occupancyPct,source"
    assert len(lines) == 1 + 3  # three kernel frames, samples excluded
    assert lines[1].startswith("hello_thread,")


def test_event_cap_is_409(client: TestClient, monkeypatch) -> None:
    from app import live_store

    monkeypatch.setattr(live_store, "MAX_SESSION_EVENTS", 3)
    client.post("/api/live/session", json={"name": "tiny"})
    for _ in range(3):
        assert (
            client.post("/api/live/ingest", json={"type": "gpu_sample"}).status_code
            == 200
        )
    r = client.post("/api/live/ingest", json={"type": "gpu_sample"})
    assert r.status_code == 409
    assert "full" in r.json()["detail"]


def test_measurement_history(client: TestClient) -> None:
    for v in (240.0, 245.0, 238.0):
        client.post(
            "/api/live/ingest",
            json={"type": "measurement", "metric": "stream_gbps", "value": v},
        )
    m = client.get("/api/measurements").json()["stream_gbps"]
    assert m["value"] == 238.0
    assert m["history"] == [240.0, 245.0]
