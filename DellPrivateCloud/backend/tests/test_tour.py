"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is Private
Cloud's."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE, build_tour, layer_map
from twinkit.testing import assert_deterministic, assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}
KIND = {r.id: r.kind for r in ANATOMY.regions}


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
    """Beat one shows the whole stack at layer 0, beat two peels the layers
    people use away, the last puts them back."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_surface_layer_is_what_people_use():
    """Layer 0 is the control plane and the workloads; everything beneath
    them (hypervisor slots, pools, fabric) is peeled to."""
    layers = layer_map(ANATOMY)
    surface = {rid for rid, n in layers.items() if n == 0}
    assert {KIND[rid] for rid in surface} == {"controlplane", "workload"}


def test_the_signature_step_frames_the_switch():
    """The migration beat lights both hypervisors, the workloads that must
    not notice, and the one control plane, and frames all of it."""
    step = STEPS[SIGNATURE_STEP_ID]
    assert {"hv-vmware", "hv-nutanix", "workloads", "control"} <= set(step.region_ids)
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid


def test_the_signature_step_pins_the_migration_trace_step():
    """The narration and the trace say the same thing at the same moment:
    a second hypervisor, zero downtime, one control plane, same workloads."""
    trace = simulate()
    state = trace[STEPS[SIGNATURE_STEP_ID].trace_cursor]
    assert state.phase == "switch"
    assert state.label == "Some workloads move to a second hypervisor"
    assert state.hypervisors_active == 2
    assert state.control_planes == 1
    assert state.workload_downtime_seconds == 0
    assert state.workloads == trace[-1].workloads > 0
    assert {"hv-vmware", "hv-nutanix"} <= set(state.active_regions)


def test_the_longest_stage_is_the_signature_beat():
    """Cross-hypervisor migration is the trace's unique longest stage, and
    the tour stops on it — and gives it the longest beat."""
    trace = simulate()
    longest = max(range(len(trace)), key=lambda i: trace[i].cycle_cost)
    assert STEPS[SIGNATURE_STEP_ID].trace_cursor == longest
    sig = STEPS[SIGNATURE_STEP_ID].duration_ms
    assert all(s.duration_ms < sig for s in TOUR.steps if s.id != SIGNATURE_STEP_ID)


def test_the_storage_beat_pins_storage_growing_alone():
    """The storage beat's claim — storage doubles, compute untouched — is
    what its pinned trace step records."""
    trace = simulate()
    i = STEPS["storage-grows-alone"].trace_cursor
    assert trace[i].phase == "growstorage"
    assert trace[i].storage_tb == 2 * trace[i - 1].storage_tb
    assert trace[i].compute_units == trace[i - 1].compute_units


def test_the_control_plane_beat_precedes_any_hypervisor():
    trace = simulate()
    i = STEPS["one-control-plane"].trace_cursor
    assert trace[i].control_planes == 1
    assert trace[i].hypervisors_active == 0


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
    assert base["tour"]["steps"][0]["id"] == "the-stack"
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


def test_the_last_beat_lights_what_it_narrates():
    """The end-state beat talks about two hypervisors under one control
    plane, so those are what it lights; an empty lit set would draw every
    hypervisor slot the same and show neither of them running."""
    trace = simulate()
    last = TOUR.steps[-1]
    state = trace[last.trace_cursor]
    lit_hv = {r for r in last.region_ids if KIND[r] == "hypervisor"}
    running_hv = {r for r in state.active_regions if KIND[r] == "hypervisor"}
    assert lit_hv == running_hv and len(lit_hv) == state.hypervisors_active == 2
    assert "control" in last.region_ids


def test_no_beat_leaves_a_running_hypervisor_unlit():
    """StackView labels an unlit hypervisor slot "available" whenever any
    region is lit, so a beat that lights something must light every
    hypervisor its trace step has running."""
    trace = simulate()
    for step in TOUR.steps:
        if not step.region_ids:
            continue
        running = {
            r for r in trace[step.trace_cursor].active_regions
            if KIND[r] == "hypervisor"
        }
        assert running <= set(step.region_ids), step.id


def test_scripts_carry_no_code_identifiers():
    """Narration is for people: no camelCase field names or internal tour
    vocabulary at any reading level."""
    import re

    reg = registry()
    for step in TOUR.steps:
        for level, text in reg[step.script].items():
            assert not re.search(r"\b[a-z]+[A-Z][A-Za-z]*\b", text), (step.id, level)
            assert "signature" not in text.lower(), (step.id, level)
