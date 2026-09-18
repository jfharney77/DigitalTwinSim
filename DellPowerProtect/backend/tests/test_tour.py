"""The narrated tour (ACTIVE_TWIN_SPEC.md section 6), checked against this
twin's own map and trace. The shared rules live in
``twinkit.testing.assert_tour_invariants``; what stays here is PowerProtect's."""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

import app.tour
from app.anatomy import ANATOMY
from app.engine import VAULT, simulate
from app.leveling import LEVELS, registry
from app.main import app as api
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE, build_tour, layer_map
from twinkit.testing import assert_deterministic, assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"
TOUR = TOUR_RESPONSE.tour
STEPS = {s.id: s for s in TOUR.steps}
TRACE = simulate()


def test_tour_invariants():
    assert_tour_invariants(
        TOUR_RESPONSE,
        ANATOMY,
        TRACE,
        SIGNATURE_STEP_ID,
        module=app.tour,
        public_dir=PUBLIC,
    )


def test_tour_is_deterministic():
    assert_deterministic(lambda: build_tour(ANATOMY))


def test_six_to_nine_beats_exterior_first():
    """Beat one shows both sites whole at layer 0, beat two peels, the last
    reassembles."""
    steps = TOUR.steps
    assert 6 <= len(steps) <= 9
    first = steps[0]
    assert first.layer_reveal == 0
    assert (first.camera.w, first.camera.h) == (ANATOMY.width, ANATOMY.height)
    assert {"dd-prod", "dd-vault"} <= set(first.region_ids)
    assert steps[1].layer_reveal >= 1
    assert steps[-1].layer_reveal == 0


def test_the_vault_sits_on_the_deepest_layer():
    layers = layer_map(ANATOMY)
    deepest = max(layers.values())
    assert {rid for rid, n in layers.items() if n == deepest} == set(VAULT)


def test_the_signature_step_pins_the_gap_opening_from_the_vault():
    """The narration and the trace say the same thing at the same moment:
    the gap opens for replication, and the beat frames both appliances and
    the gap between them."""
    step = STEPS[SIGNATURE_STEP_ID]
    state = TRACE[step.trace_cursor]
    assert state.phase == "replicate"
    assert state.label == "The air gap opens — a copy crosses into the vault"
    assert {"dd-prod", "gap", "dd-vault"} <= set(step.region_ids)
    assert "gap" in state.active_regions
    boxes = {r.id: r for r in ANATOMY.regions}
    cam = step.camera
    for rid in step.region_ids:
        r = boxes[rid]
        assert cam.x <= r.x and r.x + r.w <= cam.x + cam.w + 1e-6, rid
        assert cam.y <= r.y and r.y + r.h <= cam.y + cam.h + 1e-6, rid
    assert step.duration_ms == max(s.duration_ms for s in TOUR.steps)


def test_the_tour_lights_the_gap_only_when_the_trace_opens_it():
    """Air-gap discipline carries into the narration: a beat lights the gap
    exactly when its pinned trace step has the gap open, and those beats are
    the replicate and recover phases."""
    gap_phases = set()
    for step in TOUR.steps:
        state = TRACE[step.trace_cursor]
        assert ("gap" in step.region_ids) == ("gap" in state.active_regions), step.id
        if "gap" in step.region_ids:
            gap_phases.add(state.phase)
    assert gap_phases == {"replicate", "recover"}


def test_the_attack_beat_lights_nothing_in_the_vault():
    attack = [s for s in TOUR.steps if TRACE[s.trace_cursor].phase == "attack"]
    assert len(attack) == 1
    lit = set(attack[0].region_ids)
    assert lit and not (lit & (set(VAULT) | {"gap"}))


def test_the_seal_precedes_the_attack_in_the_tour():
    phases = [TRACE[s.trace_cursor].phase for s in TOUR.steps]
    assert phases.index("airgap") < phases.index("attack")


def test_the_longest_stage_gets_a_beat():
    """The CyberSense scan is the trace's longest stage; the tour stops on it."""
    longest = max(range(len(TRACE)), key=lambda i: TRACE[i].cycle_cost)
    assert TRACE[longest].phase == "scan"
    assert longest in {s.trace_cursor for s in TOUR.steps}


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
    assert base["tour"]["steps"][0]["id"] == "two-sites"
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


def test_titles_carry_no_end_punctuation():
    """The player renders ``<title>. <script>``; a title ending in '?' or '.'
    would read as 'Which copy is clean?.'"""
    for step in TOUR.steps:
        assert step.title[-1] not in ".?!:", step.id


def test_the_dedupe_numbers_are_the_trace_numbers():
    """The dedupe beat quotes 100 -> 500 TB logical and 20 -> 25 TB stored;
    those are the backup and dedupe states the two beats pin."""
    before = TRACE[STEPS["first-backup"].trace_cursor]
    after = TRACE[STEPS["dedupe-arithmetic"].trace_cursor]
    assert (before.logical_tb, before.stored_tb) == (100, 20)
    assert (after.logical_tb, after.stored_tb) == (500, 25)
    script = STEPS["dedupe-arithmetic"].script
    for n in ("100", "500", "20", "25"):
        assert n in script


def test_the_scripts_do_not_talk_about_the_tour_itself():
    """'Signature beat' is authoring vocabulary, not something a reader knows."""
    reg = registry()
    for step in TOUR.steps:
        for text in reg[step.script].values():
            assert "signature" not in text.lower(), step.id
