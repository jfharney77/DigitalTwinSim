"""spec_28 — fleet replay: remap a recording onto another die.

Purity, conservation, determinism, provenance, isolation, API edges, and
the queue-shape claim — plus the grep-level check that the frontend renders
the mandatory "modeled placement" label (the spec_18 provenance precedent).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.live import (
    DeviceInfoEvent,
    KernelLaunchEvent,
    StampedEvent,
    replay,
)
from app.profiles import PROFILES, RTX_4060_LAPTOP
from app.remap import recorded_device_name, remap_events

FIXTURE = Path(__file__).parent / "fixtures" / "live_session.jsonl"
TOURS_DIR = Path(__file__).parent.parent / "tours" / "lessons"
FLEET = ["H100-SXM", "B300-Blackwell-Ultra", "RTX-5090", "MI300X"]

# Same allowlist as test_live.py: the remap is fold-layer code.
PURE_ALLOWED = {"__future__", "typing", "pydantic", "app", ""}


def _events(path: Path) -> list[StampedEvent]:
    return [
        StampedEvent.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def _fixtures() -> list[Path]:
    return [FIXTURE, *sorted(TOURS_DIR.glob("*.jsonl"))]


def test_remap_module_is_pure() -> None:
    src = (Path(__file__).parent.parent / "app" / "remap.py").read_text()
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
            ), "remap.py must not touch files"


@pytest.mark.parametrize("fixture", _fixtures(), ids=lambda p: p.stem)
@pytest.mark.parametrize("target", FLEET)
def test_conservation(fixture: Path, target: str) -> None:
    """What the remap preserves, verbatim: block totals, grid, kernel names,
    elapsed, stamps, telemetry — for every fixture × every fleet profile."""
    events = _events(fixture)
    profile = PROFILES[target]
    remapped = remap_events(events, profile)
    a = replay(fixture.stem, events)
    b = replay(fixture.stem, remapped)
    # Frame count: 1:1, except the one documented case — a recording that
    # never declared its device gains exactly one leading device frame so the
    # fold can size the target die.
    had_device = any(isinstance(e.event, DeviceInfoEvent) for e in events)
    assert len(b) == len(a) + (0 if had_device else 1)
    kernels_a = [s for s in a if s.kind == "kernel"]
    kernels_b = [s for s in b if s.kind == "kernel"]
    assert len(kernels_a) == len(kernels_b)
    for sa, sb in zip(kernels_a, kernels_b):
        assert sb.kernel == sa.kernel
        assert sb.grid == sa.grid and sb.block == sa.block
        assert sb.t_ms == sa.t_ms
        assert sb.elapsed_ms == sa.elapsed_ms
        assert sb.records_dropped == sa.records_dropped
        # Total blocks conserved; placement redistributed within the target.
        assert sum(x.blocks_run for x in sb.sm_activity) == sum(
            x.blocks_run for x in sa.sm_activity
        )
        assert len(sb.sm_activity) == profile.sm.rows * profile.sm.cols
        # Span count conserved (Gantt rows are invented, bars are not).
        assert len(sb.block_spans or []) == len(sa.block_spans or [])
    for sa, sb in zip(
        [s for s in a if s.kind == "sample"], [s for s in b if s.kind == "sample"]
    ):
        assert (sb.util_pct, sb.vram_mb, sb.power_w, sb.temp_c) == (
            sa.util_pct,
            sa.vram_mb,
            sa.power_w,
            sa.temp_c,
        )


def test_determinism_and_identity() -> None:
    events = _events(FIXTURE)
    target = PROFILES["H100-SXM"]
    once = remap_events(events, target)
    twice = remap_events(events, target)
    assert [e.model_dump_json(by_alias=True) for e in once] == [
        e.model_dump_json(by_alias=True) for e in twice
    ]
    # Remapping the remapped stream again is stable too (same launch order).
    again = remap_events(once, target)
    assert [e.model_dump_json(by_alias=True) for e in again] == [
        e.model_dump_json(by_alias=True) for e in once
    ]
    # Identity: the fixture has no device_info, so its recorded die is the
    # spec_07 default — remapping onto it returns the stream untouched.
    assert recorded_device_name(events) == RTX_4060_LAPTOP.name
    assert remap_events(events, RTX_4060_LAPTOP) is events


def test_identity_short_circuits_on_a_named_device() -> None:
    # A recording whose device_info names a fleet profile: remapping onto
    # that same profile must NOT relabel measured data as modeled.
    events = [
        StampedEvent(
            t_ms=0.0,
            event=DeviceInfoEvent(name="H100-SXM", sm_count=132),
        ),
        StampedEvent(
            t_ms=10.0,
            event=KernelLaunchEvent(
                kernel="k",
                grid=(2, 1, 1),
                block=(32, 1, 1),
                blocks=[
                    {"smid": 7, "start": 0, "end": 5},
                    {"smid": 90, "start": 1, "end": 6},
                ],
            ),
        ),
    ]
    assert remap_events(events, PROFILES["H100-SXM"]) is events
    trace = replay("t", events)
    assert all(s.placement == "measured" and s.recorded_on is None for s in trace)


@pytest.mark.parametrize("fixture", _fixtures(), ids=lambda p: p.stem)
def test_provenance_is_structural(fixture: Path) -> None:
    events = _events(fixture)
    recorded = recorded_device_name(events)
    remapped = replay(fixture.stem, remap_events(events, PROFILES["MI300X"]))
    for s in remapped:
        assert s.placement == "modeled"
        assert s.recorded_on == recorded and s.recorded_on
        # Measured occupancy never survives onto a modeled frame.
        assert s.occupancy_source == "theoretical"
    for s in replay(fixture.stem, events):
        assert s.placement == "measured"
        assert s.recorded_on is None


def test_timing_is_preserved_byte_for_byte() -> None:
    events = _events(FIXTURE)
    remapped = remap_events(events, PROFILES["B300-Blackwell-Ultra"])
    launches_a = [e.event for e in events if isinstance(e.event, KernelLaunchEvent)]
    launches_b = [
        e.event for e in remapped if isinstance(e.event, KernelLaunchEvent)
    ]
    for ea, eb in zip(launches_a, launches_b):
        assert sorted((r.start, r.end) for r in ea.blocks) == sorted(
            (r.start, r.end) for r in eb.blocks
        )
        assert eb.elapsed_ms == ea.elapsed_ms
        assert eb.sampled == ea.sampled and eb.sample_stride == ea.sample_stride


def test_spread_thinner_queue_shape() -> None:
    # On a target with smCount >= blockCount, every SM runs at most 1 block.
    events = _events(FIXTURE)  # biggest kernel: 8 blocks
    for name in FLEET:
        trace = replay("fixture", remap_events(events, PROFILES[name]))
        for s in trace:
            if s.kind != "kernel":
                continue
            assert max(a.blocks_run for a in s.sm_activity) <= 1
            # Round-robin from SM 0: the first N SMs, one block each.
            n = sum(a.blocks_run for a in s.sm_activity)
            assert [a.blocks_run for a in s.sm_activity[:n]] == [1] * n


# -- transport edge -----------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import live_store
    from app.main import app

    monkeypatch.setattr(live_store, "SESSIONS_DIR", tmp_path)
    live_store.HUB.stop_session()
    return TestClient(app)


def _record_fixture(client: TestClient) -> str:
    sid = client.post("/api/live/session", json={"name": "remap"}).json()["id"]
    for line in FIXTURE.read_text().splitlines():
        assert (
            client.post("/api/live/ingest", json=json.loads(line)["event"]).status_code
            == 200
        )
    return sid


def test_trace_as_profile(client: TestClient, tmp_path: Path) -> None:
    sid = _record_fixture(client)
    before = (tmp_path / f"{sid}.jsonl").read_bytes()
    r = client.get(f"/api/live/sessions/{sid}/trace?asProfile=H100-SXM")
    assert r.status_code == 200
    trace = r.json()["trace"]
    assert all(s["placement"] == "modeled" for s in trace)
    assert all(s["recordedOn"] for s in trace)
    kernel = next(s for s in trace if s["kind"] == "kernel")
    assert len(kernel["smActivity"]) == 132
    # Isolation: a remapped read leaves the recording byte-identical.
    assert (tmp_path / f"{sid}.jsonl").read_bytes() == before
    # And the plain read is still measured.
    plain = client.get(f"/api/live/sessions/{sid}/trace").json()["trace"]
    assert all(s["placement"] == "measured" for s in plain)


def test_tour_recording_as_profile(client: TestClient) -> None:
    r = client.get("/api/tour/recordings/01_hello_thread?asProfile=RTX-5090")
    assert r.status_code == 200
    trace = r.json()["trace"]
    assert trace[0]["kind"] == "device"
    assert trace[0]["device"]["smCount"] == 170
    assert trace[0]["device"]["name"] == "RTX-5090"
    assert all(s["placement"] == "modeled" for s in trace)


def test_as_profile_edges(client: TestClient) -> None:
    sid = _record_fixture(client)
    assert (
        client.get(f"/api/live/sessions/{sid}/trace?asProfile=Vega64").status_code
        == 404
    )
    assert (
        client.get(f"/api/live/sessions/{sid}/trace?asProfile=").status_code == 422
    )
    assert (
        client.get("/api/tour/recordings/01_hello_thread?asProfile=Vega64").status_code
        == 404
    )


def test_ingest_rejects_modeled_events(client: TestClient) -> None:
    modeled = {
        "type": "device_info",
        "name": "H100-SXM",
        "smCount": 132,
        "modeledFrom": "RTX-4060-Laptop",
    }
    assert client.post("/api/live/ingest", json=modeled).status_code == 422
    assert (
        client.post("/api/live/ingest/batch", json=[modeled]).status_code == 422
    )
    # Import of a remapped download is refused too — nothing modeled is ever
    # written under sessions/.
    jsonl = json.dumps({"tMs": 0.0, "event": modeled})
    r = client.post("/api/live/import", json={"name": "sneak", "jsonl": jsonl})
    assert r.status_code == 422


def test_frontend_renders_the_modeled_label() -> None:
    # spec_18 precedent: the provenance caption is load-bearing, so its
    # presence in the component is pinned at grep level.
    viz = (
        Path(__file__).parent.parent.parent
        / "frontend"
        / "src"
        / "components"
        / "LiveViz.tsx"
    ).read_text()
    assert "MODELED PLACEMENT" in viz
    assert "RECORDED ON" in viz
