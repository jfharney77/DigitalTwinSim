"""Edge-case regressions for the live path (spec_08 hardening).

Each test here pins a defect found in the 2026-07 review so it stays fixed:
session-id collisions, unvalidated launch dims, silent record truncation, and
silent SSE frame drops.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.live import SM_COUNT

FIXTURE_KERNEL = {
    "type": "kernel_launch",
    "kernel": "k",
    "grid": [4, 1, 1],
    "block": [32, 1, 1],
    "blocks": [{"smid": i, "start": 0, "end": 1} for i in range(4)],
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import live_store
    from app.main import app

    monkeypatch.setattr(live_store, "SESSIONS_DIR", tmp_path)
    live_store.HUB.stop_session()
    return TestClient(app)


# -- defect 1: session-id collisions ------------------------------------------


def test_same_second_same_name_sessions_get_distinct_files(
    client: TestClient, monkeypatch
) -> None:
    # Pin the wall-clock stamp so both starts land in the "same second".
    monkeypatch.setattr(time, "strftime", lambda fmt: "20260731-120000")
    a = client.post("/api/live/session", json={"name": "dup"}).json()["id"]
    client.post("/api/live/ingest", json={"type": "gpu_sample", "utilPct": 1})
    b = client.post("/api/live/session", json={"name": "dup"}).json()["id"]
    client.post("/api/live/ingest", json={"type": "gpu_sample", "utilPct": 2})
    assert a != b
    # Both recordings replay independently — neither was corrupted.
    for sid in (a, b):
        r = client.get(f"/api/live/sessions/{sid}/trace")
        assert r.status_code == 200, r.text
        assert len(r.json()["trace"]) == 1


def test_session_name_survives_the_uuid_suffix(client: TestClient) -> None:
    client.post("/api/live/session", json={"name": "My Run 42"})
    client.post("/api/live/ingest", json={"type": "gpu_sample"})
    (info,) = client.get("/api/live/sessions").json()
    assert info["name"] == "my-run-42"


# -- defect 2: launch-dimension validation ------------------------------------


@pytest.mark.parametrize("grid", [[0, 1, 1], [-4, 1, 1], [1, 1, 0]])
def test_non_positive_grid_rejected(client: TestClient, grid) -> None:
    r = client.post(
        "/api/live/ingest",
        json={**FIXTURE_KERNEL, "grid": grid, "blocks": []},
    )
    assert r.status_code == 422


def test_non_positive_block_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest", json={**FIXTURE_KERNEL, "block": [0, 1, 1]}
    )
    assert r.status_code == 422


# -- defect 3: truncated records must be flagged, excess rejected -------------


def test_truncated_records_are_counted_not_silent(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json={
            **FIXTURE_KERNEL,
            "grid": [100, 1, 1],
            "blocks": [{"smid": 0, "start": 0, "end": 1}],
        },
    )
    assert r.status_code == 200
    state = r.json()
    assert state["recordsDropped"] == 99
    assert sum(a["blocksRun"] for a in state["smActivity"]) == 1


def test_complete_recording_reports_zero_dropped(client: TestClient) -> None:
    r = client.post("/api/live/ingest", json=FIXTURE_KERNEL)
    assert r.json()["recordsDropped"] == 0


def test_more_records_than_grid_blocks_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json={
            **FIXTURE_KERNEL,
            "grid": [2, 1, 1],
            "blocks": [{"smid": i % SM_COUNT, "start": 0, "end": 1} for i in range(3)],
        },
    )
    assert r.status_code == 422


def test_sample_frames_carry_partial_flag_forward(client: TestClient) -> None:
    client.post(
        "/api/live/ingest",
        json={
            **FIXTURE_KERNEL,
            "grid": [100, 1, 1],
            "blocks": [{"smid": 0, "start": 0, "end": 1}],
        },
    )
    r = client.post("/api/live/ingest", json={"type": "gpu_sample", "utilPct": 5})
    assert r.json()["recordsDropped"] == 99  # still describing the last kernel


# -- defect 4: SSE frame drops are counted ------------------------------------


def test_slow_subscriber_drops_are_counted_and_reset(client: TestClient) -> None:
    from app import live_store

    sub = live_store.HUB.subscribe()
    try:
        for i in range(300):  # queue maxsize is 256
            client.post(
                "/api/live/ingest", json={"type": "gpu_sample", "utilPct": i % 100}
            )
        assert sub.queue.qsize() == 256
        assert sub.dropped > 0
        n = sub.take_dropped()
        assert n > 0
        assert sub.dropped == 0  # take resets, so the stream reports each drop once
    finally:
        live_store.HUB.unsubscribe(sub)


# -- honest error codes for broken recordings ---------------------------------


def test_corrupt_recording_is_422_not_404(client: TestClient, tmp_path) -> None:
    sid = client.post("/api/live/session", json={"name": "corrupt"}).json()["id"]
    client.post("/api/live/ingest", json={"type": "gpu_sample", "utilPct": 1})
    with (tmp_path / f"{sid}.jsonl").open("a") as f:
        f.write("{not json}\n")
    r = client.get(f"/api/live/sessions/{sid}/trace")
    assert r.status_code == 422
    assert "corrupt" in r.json()["detail"]


def test_missing_recording_is_still_404(client: TestClient) -> None:
    assert client.get("/api/live/sessions/never-existed/trace").status_code == 404
