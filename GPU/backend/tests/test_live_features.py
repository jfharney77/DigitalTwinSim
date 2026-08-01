"""Feature invariants for specs 10/12/14/15/16/17 (live-path extensions)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.live import (
    DEFAULT_SM_COUNT,
    StampedEvent,
    replay,
)

DEVICE_48 = {
    "type": "device_info",
    "name": "Test-48SM",
    "smCount": 48,
    "maxThreadsPerSm": 2048,
    "warpSize": 32,
}


def kernel(grid_x: int, blocks: list[dict], **extra) -> dict:
    return {
        "type": "kernel_launch",
        "kernel": extra.pop("name", "k"),
        "grid": [grid_x, 1, 1],
        "block": [64, 1, 1],
        "blocks": blocks,
        **extra,
    }


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import live_store
    from app.main import app

    monkeypatch.setattr(live_store, "SESSIONS_DIR", tmp_path)
    live_store.HUB.stop_session()
    return TestClient(app)


# -- spec_12: device-agnostic sessions ----------------------------------------


def test_default_die_without_device_info(client: TestClient) -> None:
    r = client.post("/api/live/ingest", json={"type": "gpu_sample", "utilPct": 1})
    assert len(r.json()["smActivity"]) == DEFAULT_SM_COUNT


def test_device_info_resizes_the_die(client: TestClient) -> None:
    r = client.post("/api/live/ingest", json=DEVICE_48)
    body = r.json()
    assert body["kind"] == "device"
    assert body["device"]["smCount"] == 48
    assert len(body["smActivity"]) == 48
    # smid 47 now valid, 48 not.
    ok = client.post(
        "/api/live/ingest",
        json=kernel(1, [{"smid": 47, "start": 0, "end": 1}]),
    )
    assert ok.status_code == 200
    bad = client.post(
        "/api/live/ingest",
        json=kernel(1, [{"smid": 48, "start": 0, "end": 1}]),
    )
    assert bad.status_code == 422


def test_smid_beyond_default_die_rejected_without_device(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json=kernel(1, [{"smid": DEFAULT_SM_COUNT, "start": 0, "end": 1}]),
    )
    assert r.status_code == 422


def test_device_change_under_kernels_rejected_and_not_persisted(
    client: TestClient,
) -> None:
    sid = client.post("/api/live/session", json={"name": "dev"}).json()["id"]
    client.post("/api/live/ingest", json=DEVICE_48)
    client.post("/api/live/ingest", json=kernel(1, [{"smid": 0, "start": 0, "end": 1}]))
    r = client.post("/api/live/ingest", json={**DEVICE_48, "smCount": 24})
    assert r.status_code == 422
    # The rejected event must not have corrupted the recording.
    t = client.get(f"/api/live/sessions/{sid}/trace")
    assert t.status_code == 200
    assert len(t.json()["trace"]) == 2


# -- spec_10: block spans for the Gantt ---------------------------------------


def test_kernel_frames_carry_normalized_spans(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json=kernel(
            3,
            [
                {"smid": 0, "start": 100, "end": 200},
                {"smid": 1, "start": 150, "end": 300},
                {"smid": 2, "start": 100, "end": 300},
            ],
        ),
    )
    spans = r.json()["blockSpans"]
    assert len(spans) == 3
    for s in spans:
        assert 0.0 <= s["startNorm"] <= s["endNorm"] <= 1.0
    assert min(s["startNorm"] for s in spans) == 0.0
    assert max(s["endNorm"] for s in spans) == 1.0


def test_sample_frames_have_no_spans(client: TestClient) -> None:
    r = client.post("/api/live/ingest", json={"type": "gpu_sample"})
    assert r.json()["blockSpans"] is None


# -- spec_16: declared sampling ------------------------------------------------


def test_sampled_event_scales_to_estimates(client: TestClient) -> None:
    # 1000-block grid, 1-in-10 sample: 100 records -> ~1000 estimated.
    recs = [{"smid": i % 24, "start": i, "end": i + 5} for i in range(100)]
    r = client.post(
        "/api/live/ingest",
        json=kernel(1000, recs, sampled=True, sampleStride=10),
    )
    body = r.json()
    assert body["recordsDropped"] == 0  # declared sampling is not data loss
    total = sum(a["blocksRun"] for a in body["smActivity"])
    assert total == 1000
    assert all(a["estimated"] for a in body["smActivity"] if a["blocksRun"])


def test_unsampled_event_is_not_estimated(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest", json=kernel(1, [{"smid": 3, "start": 0, "end": 1}])
    )
    assert not any(a["estimated"] for a in r.json()["smActivity"])


# -- spec_14: mid-kernel progress ---------------------------------------------


def test_progress_accumulates_then_launch_is_authoritative(
    client: TestClient,
) -> None:
    p1 = client.post(
        "/api/live/ingest",
        json={
            "type": "kernel_progress",
            "kernel": "long_k",
            "counts": [{"smid": 0, "started": 3, "ended": 1}],
        },
    ).json()
    assert p1["kind"] == "progress" and p1["running"] is True
    assert p1["smActivity"][0]["blocksRun"] == 3
    assert p1["smActivity"][0]["busy"] is True  # 2 still resident

    p2 = client.post(
        "/api/live/ingest",
        json={
            "type": "kernel_progress",
            "kernel": "long_k",
            "counts": [{"smid": 0, "started": 7, "ended": 7}],
        },
    ).json()
    assert p2["smActivity"][0]["blocksRun"] == 7  # monotonic
    assert p2["smActivity"][0]["busy"] is False

    final = client.post(
        "/api/live/ingest",
        json=kernel(
            8,
            [{"smid": 0, "start": 0, "end": 1} for _ in range(8)],
            name="long_k",
            elapsedMs=1234.5,
        ),
    ).json()
    assert final["running"] is False
    assert final["smActivity"][0]["blocksRun"] == 8  # authoritative replace


def test_progress_ended_over_started_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json={
            "type": "kernel_progress",
            "kernel": "k",
            "counts": [{"smid": 0, "started": 1, "ended": 2}],
        },
    )
    assert r.status_code == 422


# -- spec_17: cupti-shaped events ---------------------------------------------


def test_cupti_event_is_timing_only_and_honest(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json=kernel(
            4096,
            [],
            source="cupti",
            elapsedMs=3.2,
            occupancyPct=87.5,
            occupancySource="measured",
        ),
    )
    body = r.json()
    assert body["source"] == "cupti"
    assert body["occupancySource"] == "measured"
    assert body["recordsDropped"] == 0  # timing-only by design, not an accident
    assert not any(a["busy"] for a in body["smActivity"])  # no fake placement


# -- spec_15: measurements ------------------------------------------------------


def test_measurement_persists_and_is_not_a_frame(client: TestClient) -> None:
    sid = client.post("/api/live/session", json={"name": "m"}).json()["id"]
    client.post("/api/live/ingest", json={"type": "gpu_sample", "utilPct": 1})
    r = client.post(
        "/api/live/ingest",
        json={
            "type": "measurement",
            "metric": "stream_gbps",
            "value": 241.0,
            "kernel": "stream_copy",
        },
    )
    assert r.status_code == 200
    m = client.get("/api/measurements").json()
    assert m["stream_gbps"]["value"] == 241.0
    assert m["stream_gbps"]["measuredAt"]
    # Not a frame: the session recorded only the sample.
    t = client.get(f"/api/live/sessions/{sid}/trace").json()
    assert len(t["trace"]) == 1


def test_measurement_validation(client: TestClient) -> None:
    for bad in [
        {"type": "measurement", "metric": "stream_gbps", "value": 0},
        {"type": "measurement", "metric": "nonsense", "value": 5},
    ]:
        assert client.post("/api/live/ingest", json=bad).status_code == 422


# -- replay coherence across all new event kinds ------------------------------


def test_mixed_session_replays_deterministically(client: TestClient) -> None:
    sid = client.post("/api/live/session", json={"name": "mix"}).json()["id"]
    for ev in [
        DEVICE_48,
        {"type": "gpu_sample", "utilPct": 2},
        {"type": "kernel_progress", "kernel": "k", "counts": [{"smid": 1, "started": 2, "ended": 0}]},
        kernel(4, [{"smid": i, "start": i, "end": i + 9} for i in range(4)], name="k"),
        {"type": "gpu_sample", "utilPct": 9},
    ]:
        assert client.post("/api/live/ingest", json=ev).status_code == 200
    a = client.get(f"/api/live/sessions/{sid}/trace").text
    b = client.get(f"/api/live/sessions/{sid}/trace").text
    assert a == b
    trace = client.get(f"/api/live/sessions/{sid}/trace").json()["trace"]
    assert [s["kind"] for s in trace] == [
        "device",
        "sample",
        "progress",
        "kernel",
        "sample",
    ]
    assert all(len(s["smActivity"]) == 48 for s in trace)


def test_streaming_converges_to_launch_only_result() -> None:
    # spec_14 core invariant: progress frames are presentation; the closing
    # launch alone determines the final picture.
    recs = [{"smid": i % 5, "start": i, "end": i + 10} for i in range(20)]
    launch = {
        "tMs": 100.0,
        "event": kernel(20, recs, name="conv"),
    }
    with_progress = [
        {"tMs": 10.0, "event": {"type": "kernel_progress", "kernel": "conv",
                                "counts": [{"smid": 0, "started": 2, "ended": 1}]}},
        {"tMs": 50.0, "event": {"type": "kernel_progress", "kernel": "conv",
                                "counts": [{"smid": 0, "started": 4, "ended": 4},
                                           {"smid": 1, "started": 3, "ended": 3}]}},
        launch,
    ]
    only_launch = [launch]
    a = replay("s", [StampedEvent.model_validate(e) for e in with_progress])
    b = replay("s", [StampedEvent.model_validate(e) for e in only_launch])
    assert a[-1].model_dump(exclude={"t_ms"}) == b[-1].model_dump(exclude={"t_ms"})
