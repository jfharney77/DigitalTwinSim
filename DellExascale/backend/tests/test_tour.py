"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is Exascale's."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import BULK_PHASES, DATA_SERVERS, simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE, build_tour, layer_map
from twinkit.testing import assert_deterministic, assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}
SERVERS = {f"data-{d}" for d in DATA_SERVERS}
MEDIA = {f"media-{d}" for d in DATA_SERVERS}


def test_tour_invariants():
    assert_tour_invariants(
        TOUR_RESPONSE,
        ANATOMY,
        simulate(),
        SIGNATURE_STEP_ID,
        module=app.tour,
        public_dir=PUBLIC,
    )


def test_tour_is_deterministic():
    assert_deterministic(lambda: build_tour(ANATOMY))


def test_six_to_nine_beats_exterior_first():
    """The storyboard shape: 6-9 beats, beat one shows the whole map at
    layer 0, beat two peels the first layer, the last closes it back up."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_signature_step_shows_the_metadata_server_dark():
    """The one idea on screen: every data server and its NVMe lit, the
    metadata server revealed but not lit — and all of it in frame."""
    step = STEPS[SIGNATURE_STEP_ID]
    lit = set(step.region_ids)
    assert SERVERS | MEDIA <= lit
    assert "metadata" not in lit
    assert step.layer_reveal == max(layer_map(ANATOMY).values())
    assert step.layer_reveal >= layer_map(ANATOMY)["metadata"]
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in lit | {"metadata"}:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid


def test_the_signature_step_pins_the_fan_out_trace_step():
    """The narration and the trace say the same thing at the same moment: the
    first step that moves bulk data, with the metadata server gone from it."""
    trace = simulate()
    i = STEPS[SIGNATURE_STEP_ID].trace_cursor
    state = trace[i]
    assert state.label == "Parallel read fans out — the metadata server steps aside"
    assert state.phase in BULK_PHASES
    assert "metadata" not in state.active_regions
    assert state.data_servers_streaming == len(DATA_SERVERS)
    # ...and the step before it still had the metadata server lit.
    assert "metadata" in trace[i - 1].active_regions


def test_the_tour_never_lights_metadata_on_a_bulk_step():
    """The tour holds itself to test_metadata_leaves_the_data_path: no beat
    pinned to a bulk-data phase lights the metadata server, and the beats that
    do light it are pinned to steps where the engine lights it too."""
    trace = simulate()
    for step in TOUR.steps:
        state = trace[step.trace_cursor]
        if state.phase in BULK_PHASES:
            assert "metadata" not in step.region_ids, step.id
        if "metadata" in step.region_ids:
            assert "metadata" in state.active_regions, step.id


def test_data_servers_light_in_lockstep_in_the_tour():
    """A striped read fans out to every server at once, so the tour never
    lights part of the data band, and never a server without its NVMe."""
    for step in TOUR.steps:
        lit = set(step.region_ids)
        servers = lit & SERVERS
        if servers:
            assert servers == SERVERS, step.id
            assert MEDIA <= lit, step.id


def test_the_longest_stage_gets_a_beat():
    """The checkpoint burst is the trace's longest stage; the tour stops on it."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert trace[longest].phase == "checkpoint"
    assert longest in {s.trace_cursor for s in TOUR.steps}


def test_the_peak_throughput_beat_pins_the_peak():
    trace = simulate()
    state = trace[STEPS["six-terabytes"].trace_cursor]
    assert state.throughput_gbps == max(s.throughput_gbps for s in trace) >= 48000


def test_every_script_is_authored_at_one_three_and_five():
    reg = registry()
    for step in TOUR.steps:
        variants = reg.get(step.script)
        assert variants is not None, f"{step.id}: script is not wrapped in L()"
        assert {1, 3, 5} <= set(variants), f"{step.id}: levels {sorted(variants)}"
        assert len(variants[1]) > len(variants[5]), step.id


def test_endpoint_serves_the_tour_at_every_level():
    client = TestClient(api)
    base = client.get("/api/tour").json()
    assert base["tour"]["steps"][0]["id"] == "two-racks"
    assert set(base["layers"]) == {r.id for r in ANATOMY.regions}
    assert base["mapWidth"] == ANATOMY.width
    scripts = {}
    for level in LEVELS:
        body = client.get(f"/api/tour?level={level}").json()
        assert [s["id"] for s in body["tour"]["steps"]] == list(STEPS)
        scripts[level] = [s["script"] for s in body["tour"]["steps"]]
        assert all(text.strip() for text in scripts[level])
    assert scripts[3] == [s.script for s in TOUR.steps]
    assert scripts[1] != scripts[5]


def test_every_beat_frames_what_it_lights():
    """A lit region off camera is a pointer at nothing: the caption would talk
    about a block the viewer cannot see."""
    boxes = {r.id: r for r in ANATOMY.regions}
    for step in TOUR.steps:
        cam = step.camera
        for rid in step.region_ids:
            r = boxes[rid]
            assert cam.x - 1e-6 <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, (step.id, rid)
            assert cam.y - 1e-6 <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, (step.id, rid)


def test_the_peak_beat_shows_where_the_bytes_land():
    """The six-terabytes script ends in GPU memory, so the GPU racks and the
    fabric are lit and in frame, as the trace lights them at that step."""
    step = STEPS["six-terabytes"]
    state = simulate()[step.trace_cursor]
    assert {"clients", "fabric"} <= set(step.region_ids)
    assert set(state.active_regions) <= set(step.region_ids)


def test_the_closing_beat_lights_the_steady_state_and_leaves_metadata_dark():
    """The last beat says the metadata server stays dark in steady state; it
    lights what the pinned trace step lights, and nothing more."""
    step = TOUR.steps[-1]
    state = simulate()[step.trace_cursor]
    assert state.phase == "steady"
    assert set(step.region_ids) == set(state.active_regions)
    assert "metadata" not in step.region_ids
