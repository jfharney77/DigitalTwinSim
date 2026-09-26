"""The coolant-fault scenario: liquid before silicon, tested.

House style — full-trace assertions on the pure engine, no server needed
except for the two wire checks at the end. The signature invariants are the
things that must hold *because* the failure happened:

* no GPU draws power without verified flow on its branch;
* ``gpusInDomain`` is only ever 0 or 72 — never 68;
* power drops before temperature rises.
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest
from fastapi.testclient import TestClient

from app.anatomy import ANATOMY
from app.engine import (
    FAULT_PHASE_ORDER,
    FAULT_TRAY,
    FAULT_TRAY_REGIONS,
    SCENARIOS,
    simulate,
)
from app.leveling import variant_for
from app.main import app
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_trace_invariants,
)

FAULT = "coolant-fault"
PROFILE = TraceProfile(phases=FAULT_PHASE_ORDER, anatomy=ANATOMY)

# The nine fields PowerOnState had before the scenario work, minus the leveled
# prose (test_prose.py and the reading-level passes own that).
ORIGINAL_FIELDS = (
    "step", "phase", "label", "active_regions", "power_watts",
    "gpus_in_domain", "elapsed_seconds", "cycle_cost",
)
# sha256 of the nominal trace over ORIGINAL_FIELDS, taken before this file
# existed. If it moves, the happy path moved — do that on purpose or not at all.
# Moved once, on purpose: the fabric and fused step labels were reworded
# (5,000 is the cable count, not the link count; 72 GPUs form one domain, not
# one device). No number, region or phase changed.
NOMINAL_SHA256 = "0f5c8cb0b4e929c6dc53fefeca0d7d8a51724568845c0322020db0f8340844a8"


def _digest(trace) -> str:
    rows = [{f: getattr(s, f) for f in ORIGINAL_FIELDS} for s in trace]
    blob = json.dumps(rows, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def fault():
    return simulate(FAULT)


# --- the shared invariants ---------------------------------------------------


def test_fault_trace_invariants():
    assert_trace_invariants(fault(), PROFILE)
    assert_deterministic(fault)


def test_failed_regions_are_real_and_never_lit():
    """A faulted block is drawn in the error colour *instead of* lit: it is on
    the map, and it is never doing work at the same step."""
    known = {r.id for r in ANATOMY.regions}
    for s in fault():
        assert set(s.failed_regions) <= known, f"step {s.step}: unknown failed region"
        both = set(s.failed_regions) & set(s.active_regions)
        assert not both, f"step {s.step}: {sorted(both)} both failed and active"
        assert set(s.failed_regions) <= set(FAULT_TRAY_REGIONS), (
            f"step {s.step}: the fault spread beyond tray {FAULT_TRAY}"
        )


# --- the happy path did not move -----------------------------------------------


def test_the_happy_path_is_unchanged():
    nominal = simulate()
    assert _digest(nominal) == NOMINAL_SHA256
    assert [s.model_dump() for s in simulate("nominal")] == [
        s.model_dump() for s in nominal
    ]
    # Additive fields only: nothing on the happy path is ever failed.
    assert all(s.failed_regions == [] for s in nominal)
    assert {s.gpus_in_domain for s in nominal} == {0, 72}


def test_the_recovered_bring_up_is_the_nominal_one_running_late():
    """After re-verify the fault trace replays trayboot → ready exactly — same
    labels, prose, regions, watts and dwell — only the clock differs. Recovery
    is not a special path; it is the ordinary one, late."""
    nominal = {s.phase: s for s in simulate()}
    late = {s.phase: s for s in fault()}
    delays = set()
    for phase in ("trayboot", "gpuinit", "fabric", "fused", "ready"):
        a, b = nominal[phase], late[phase]
        drop = {"step", "elapsed_seconds"}
        assert a.model_dump(exclude=drop) == b.model_dump(exclude=drop), phase
        delays.add(b.elapsed_seconds - a.elapsed_seconds)
    assert len(delays) == 1 and delays.pop() > 0, "the repair must cost time, once"


# --- signature invariants ------------------------------------------------------


@pytest.mark.parametrize("scenario", [s.id for s in SCENARIOS])
def test_no_gpu_draws_power_without_verified_flow(scenario):
    """Four GPUs per tray, one branch per tray: the GPUs drawing power can
    never outnumber the GPUs sitting on a verified branch. Holds on the happy
    path too — the fault trace is where it is under pressure."""
    for s in simulate(scenario):
        assert s.gpus_powered <= 4 * s.branches_verified, (
            f"step {s.step} ({s.phase}): {s.gpus_powered} GPUs powered on "
            f"{s.branches_verified} verified branches"
        )
        lit_gpus = [r for r in s.active_regions if r.startswith("gpu-")]
        if lit_gpus:
            assert s.gpus_powered > 0 and s.branches_verified >= 17


def test_the_bring_up_hold_is_rack_wide():
    """Seventeen good branches are not enough for this site. Until all 18
    verify for the first time, no GPU has power and no tray boots — the
    operators do not start a bring-up they could only finish at 68. (A policy
    of the modelled site, and the prose must say so: real hardware can form a
    smaller partition.)"""
    trace = fault()
    first_full = next(i for i, s in enumerate(trace) if s.branches_verified == 18)
    assert trace[first_full].phase == "reverify"
    for s in trace[:first_full + 1]:
        assert s.gpus_powered == 0, f"step {s.step}: GPUs powered before 18/18"
        assert s.phase not in ("trayboot", "gpuinit", "fabric", "fused")
        assert not any(r.startswith(("gpu-", "cpu-")) for r in s.active_regions)
    # And the fault was real: a branch genuinely failed before that.
    assert any(s.branches_verified == 17 for s in trace[:first_full])
    held = next(s for s in trace if s.phase == "flowfault")
    assert "policy" in held.description and "smaller NVLink partition" in held.description


def test_the_fault_prose_labels_what_the_twin_invented():
    """Two things in this trace are the twin's devices, not documented
    behaviour, and the reader must be told at every level: per-branch flow
    verification (per-tray leak sensing is documented; per-branch flow
    metering is not), and collapsing the BMC's shutdown timer into one step."""
    trace = fault()
    flowfault = next(s for s in trace if s.phase == "flowfault")
    leak = next(s for s in trace if s.phase == "leak")
    for level in (1, 3, 5):
        a = variant_for(flowfault.description, level)
        assert "this twin's" in a or "this model's" in a, f"flowfault level {level}"
        b = variant_for(leak.description, level)
        # Level 1 says "countdown" where the others say "timer"; either way
        # the reader is told the tray is counting, not measuring temperature.
        assert "timer" in b or "countdown" in b, f"leak level {level}"


MARKUP = re.compile(r"\*[^*\s][^*]*\*|`")


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
def test_fault_prose_has_no_markdown_markers(level):
    """test_prose.py covers the default trace only; the fault trace is served
    from the same endpoint and needs the same guarantee."""
    body = client.get(f"/api/poweron?scenario={FAULT}", params={"level": level}).json()
    offenders = [
        s for st in body["trace"] for s in (st["label"], st["description"])
        if MARKUP.search(s)
    ]
    assert offenders == []
    listing = client.get("/api/scenarios", params={"level": level}).json()
    assert not [
        s for sc in listing for s in (sc["name"], sc["summary"], sc["hero"])
        if MARKUP.search(s)
    ]


def test_the_prose_does_not_invent_a_per_tray_valve():
    """A GB200 tray has quick disconnects, not an actuated valve: liquid
    isolation of one tray is a technician unseating it. Automatic valves are
    rack-level (BMS) and not modelled."""
    for s in fault():
        for level in (1, 3, 5):
            assert "branch valve" not in variant_for(s.description, level), s.phase


def test_the_domain_is_only_ever_0_or_72_never_68():
    trace = fault()
    assert {s.gpus_in_domain for s in trace} == {0, 72}
    # The interesting half: 68 GPUs *are* powered while the domain reads 0,
    # so the twin had the chance to say 68 and did not.
    after_leak = [s for s in trace if s.phase in ("leak", "traydown", "held")]
    assert after_leak and all(
        s.gpus_powered == 68 and s.gpus_in_domain == 0 for s in after_leak
    )
    # And the fuse still happens, exactly once, only after the re-verify.
    phases = [s.phase for s in trace]
    fused_at = [i for i, s in enumerate(trace) if s.gpus_in_domain == 72]
    assert fused_at[0] == phases.index("fused") > phases.index("reverify")
    assert fused_at == list(range(fused_at[0], phases.index("leak")))


def test_power_drops_before_temperature_rises():
    """At the steady-state leak the tray is cut from the busbar ahead of any
    thermal excursion: watts fall on the very step the sensor trips, and the
    hottest GPU is never hotter than it was at full, healthy load."""
    trace = fault()
    i = next(i for i, s in enumerate(trace) if s.phase == "leak")
    before, leak = trace[i - 1], trace[i]
    assert before.phase == "ready" and before.gpus_powered == 72
    assert leak.power_watts < before.power_watts
    assert leak.gpus_powered == before.gpus_powered - 4, "one tray, four GPUs"
    ceiling = before.gpu_temp_c
    temps = [s.gpu_temp_c for s in trace[i:]]
    assert max(temps) <= ceiling, "temperature rose after the leak"
    assert temps == sorted(temps, reverse=True), "survivors must only cool"
    # Nowhere in the failure trace is silicon hotter than the happy path's peak.
    assert max(s.gpu_temp_c for s in trace) == max(s.gpu_temp_c for s in simulate())


def test_the_leaking_tray_is_sealed_and_the_loop_keeps_flowing():
    for s in fault():
        if s.phase in ("isolate", "leak", "traydown", "held"):
            assert set(s.failed_regions) == set(FAULT_TRAY_REGIONS)
            assert s.branches_verified == 17, "the other 17 branches stay in flow"
    sealed = next(s for s in fault() if s.phase == "traydown")
    assert "cdu" in sealed.active_regions and "manifold" in sealed.active_regions


def test_recovery_ordering():
    """Detect → isolate → repair → re-verify → boot. The repair is the longest
    of the fault stages, and still shorter on screen than fabric training, so
    the nominal trace's longest-stage lesson survives in this one."""
    trace = fault()
    phases = [s.phase for s in trace]
    order = ["coolant", "flowfault", "isolate", "repair", "reverify", "trayboot"]
    assert [phases.index(p) for p in order] == sorted(phases.index(p) for p in order)
    cost = {s.phase: s.cycle_cost for s in trace}
    assert cost["repair"] == max(cost[p] for p in ("flowfault", "isolate", "repair", "reverify"))
    assert cost["fabric"] > cost["repair"]
    assert sum(1 for s in trace if s.cycle_cost == cost["fabric"]) == 1


# --- scenario data, prose, and the wire ---------------------------------------


def test_scenarios_are_listed_and_the_failure_cites_its_sources():
    ids = [s.id for s in SCENARIOS]
    assert ids == ["nominal", FAULT]
    failure = SCENARIOS[1]
    assert len(failure.sources) >= 3
    assert all(src.url.startswith("https://") for src in failure.sources)
    assert any("nvidia.com" in src.url for src in failure.sources)
    assert any("dell.com" in src.url for src in failure.sources)
    assert "illustrative" in failure.summary
    reached = {s.phase for s in fault()}
    assert set(failure.key_phases) <= reached
    with pytest.raises(KeyError):
        simulate("no-such-scenario")


def test_fault_prose_is_leveled_at_1_3_5_and_cross_references_the_cooling_twins():
    own = [s for s in fault() if s.phase in set(FAULT_PHASE_ORDER) - {
        "off", "power", "coolant", "trayboot", "gpuinit", "fabric", "fused", "ready",
    }]
    assert len(own) == 7
    for s in own:
        novice, expert = variant_for(s.description, 1), variant_for(s.description, 5)
        assert novice != s.description != expert, s.phase
        assert len(novice) > len(expert), f"{s.phase}: scale inverted"
    prose = " ".join(s.description for s in own)
    assert "IR7000" in prose and "PhysicsCDU" in prose


client = TestClient(app)


def test_default_endpoint_still_serves_the_nominal_trace():
    plain = client.get("/api/poweron").json()
    named = client.get("/api/poweron?scenario=nominal").json()
    assert plain == named and plain["scenario"] == "nominal"
    assert [s["phase"] for s in plain["trace"]] == [s.phase for s in simulate()]
    assert all(s["failedRegions"] == [] for s in plain["trace"])


def test_fault_endpoint_and_listing():
    body = client.get(f"/api/poweron?scenario={FAULT}&level=1").json()
    assert body["scenario"] == FAULT
    assert [s["phase"] for s in body["trace"]] == FAULT_PHASE_ORDER
    assert {s["gpusInDomain"] for s in body["trace"]} == {0, 72}
    assert client.get("/api/poweron?scenario=nope").status_code == 404
    listing = client.get("/api/scenarios").json()
    assert [s["id"] for s in listing] == ["nominal", FAULT]
    assert listing[1]["keyPhases"] and listing[1]["sources"]
