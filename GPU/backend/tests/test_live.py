"""spec_08 — live CUDA co-browsing invariants.

The pure layer (``live.py``) is tested like the engine: AST-checked purity and
full-trace assertions against a canned session fixture. The transport edge is
exercised through the FastAPI TestClient with an isolated sessions directory.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.live import SM_COUNT, LiveState, StampedEvent, replay

FIXTURE = Path(__file__).parent / "fixtures" / "live_session.jsonl"

# Modules the pure layer may import. Anything else (fastapi, asyncio, time,
# pathlib, ...) is the impure edge leaking in — live_store.py's job, not live.py's.
PURE_ALLOWED = {"__future__", "typing", "pydantic", "app", ""}


def _fixture_events() -> list[StampedEvent]:
    return [
        StampedEvent.model_validate_json(line)
        for line in FIXTURE.read_text().splitlines()
        if line.strip()
    ]


def test_live_module_is_pure() -> None:
    src = (Path(__file__).parent.parent / "app" / "live.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] in PURE_ALLOWED, f"impure import {a.name}"
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            assert node.level > 0 or mod in PURE_ALLOWED, f"impure import {mod}"
        elif isinstance(node, ast.Call):
            fn = node.func
            assert not (
                isinstance(fn, ast.Name) and fn.id == "open"
            ), "live.py must not touch files"


def test_replay_is_deterministic() -> None:
    events = _fixture_events()
    a = replay("fixture", events)
    b = replay("fixture", events)
    assert [s.model_dump_json(by_alias=True) for s in a] == [
        s.model_dump_json(by_alias=True) for s in b
    ]
    assert len(a) == len(events)


def test_stamps_monotonic_and_activity_shape() -> None:
    trace = replay("fixture", _fixture_events())
    last_t = -1.0
    for s in trace:
        assert s.t_ms >= last_t
        last_t = s.t_ms
        assert len(s.sm_activity) == SM_COUNT
        assert all(a.sm_id == i for i, a in enumerate(s.sm_activity))
        assert all(a.blocks_run >= 0 for a in s.sm_activity)


def test_non_monotonic_recording_is_rejected() -> None:
    events = _fixture_events()
    events[1], events[2] = events[2], events[1]
    with pytest.raises(ValueError, match="non-monotonic"):
        replay("fixture", events)


def test_kernel_blocks_account_for_the_whole_grid() -> None:
    # The probe flushes after completion, so every block in the grid appears
    # exactly once in the records — and the fold must not lose any.
    events = _fixture_events()
    trace = replay("fixture", events)
    for st, ev in zip(trace, events):
        if st.kind != "kernel":
            continue
        launch = ev.event
        total = sum(a.blocks_run for a in st.sm_activity)
        assert total == launch.grid_blocks()
        assert st.kernel == launch.kernel


def test_one_block_lights_one_sm() -> None:
    # Fixture kernel 'hello_thread' is a <<<1, 8>>> launch: exactly one SM
    # busy — the spec_09 lesson-01 moment, pinned as data.
    trace = replay("fixture", _fixture_events())
    hello = next(s for s in trace if s.kernel == "hello_thread")
    busy = [a for a in hello.sm_activity if a.busy]
    assert len(busy) == 1
    assert busy[0].blocks_run == 1


def test_samples_carry_kernel_context_forward() -> None:
    trace = replay("fixture", _fixture_events())
    final = trace[-1]
    assert final.kind == "sample"
    assert final.kernel == "vector_add"  # last kernel still on the counters
    assert final.util_pct == 21.0
    assert not any(a.busy for a in final.sm_activity)  # nothing resident now
    assert sum(a.blocks_run for a in final.sm_activity) == 8  # picture retained


# -- transport edge -----------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import live_store
    from app.main import app

    monkeypatch.setattr(live_store, "SESSIONS_DIR", tmp_path)
    live_store.HUB.stop_session()
    return TestClient(app)


def test_ingest_records_and_trace_replays(client: TestClient) -> None:
    r = client.post("/api/live/session", json={"name": "pytest run"})
    assert r.status_code == 200
    sid = r.json()["id"]

    for line in FIXTURE.read_text().splitlines():
        event = json.loads(line)["event"]
        r = client.post("/api/live/ingest", json=event)
        assert r.status_code == 200
        assert len(r.json()["smActivity"]) == SM_COUNT

    r = client.get(f"/api/live/sessions/{sid}/trace")
    assert r.status_code == 200
    body = r.json()
    assert body["sessionId"] == sid
    assert len(body["trace"]) == 6
    # The recorded trace revalidates as LiveState (the wire shape is the model).
    for s in body["trace"]:
        LiveState.model_validate(s)

    sessions = client.get("/api/live/sessions").json()
    assert any(s["id"] == sid and s["eventCount"] == 6 for s in sessions)


def test_ingest_without_session_autostarts_one(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json={"type": "gpu_sample", "utilPct": 5.0},
    )
    assert r.status_code == 200
    assert "adhoc" in r.json()["sessionId"]


def test_out_of_range_smid_is_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/live/ingest",
        json={
            "type": "kernel_launch",
            "kernel": "bad",
            "grid": [1, 1, 1],
            "block": [32, 1, 1],
            "blocks": [{"smid": SM_COUNT, "start": 0, "end": 1}],
        },
    )
    assert r.status_code == 422


def test_unknown_trace_is_404(client: TestClient) -> None:
    assert client.get("/api/live/sessions/nope/trace").status_code == 404


# -- probe contract (spec_09) --------------------------------------------------
# One representative kernel_launch event per CUDA lesson, in exactly the JSON
# twinprobe.cuh emits. CUDA can't run in CI, so this is where the header <->
# backend wire format is pinned: if either side drifts, this fails first.

SAMPLES = sorted((Path(__file__).parent / "fixtures" / "probe_samples").glob("*.json"))


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda p: p.stem)
def test_probe_samples_ingest(client: TestClient, sample: Path) -> None:
    event = json.loads(sample.read_text())
    r = client.post("/api/live/ingest", json=event)
    assert r.status_code == 200, r.text
    state = r.json()
    assert state["kind"] == "kernel"
    assert state["kernel"] == event["kernel"]
    assert len(state["smActivity"]) == SM_COUNT
    grid_blocks = event["grid"][0] * event["grid"][1] * event["grid"][2]
    assert sum(a["blocksRun"] for a in state["smActivity"]) == grid_blocks


def test_samples_cover_every_probed_lesson() -> None:
    lessons_dir = Path(__file__).parent.parent.parent / "cuda" / "lessons"
    probed = {
        p.stem
        for p in lessons_dir.glob("*.cu")
        if "twinprobe" in p.read_text()
    }
    assert probed, "no lessons found — did GPU/cuda/lessons move?"
    assert probed == {p.stem for p in SAMPLES}
