"""The failure scenario: an iDRAC firmware update that fails its boot check
and rolls back. House style — assert over the whole pure trace.

The shared trace invariants come first. Then what must hold *because* the
failure happened: the host never changes power state, nothing unverified is
written and nothing at all is written to the running partition, there is
always a bootable image, and the management outage is bounded. Last, the
bring-up is pinned unchanged, in the engine and over the wire.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.anatomy import ANATOMY
from app.engine import (
    MAX_MANAGEMENT_OUTAGE_S,
    NEW_VERSION,
    RUNNING_VERSION,
    SCENARIO_IDS,
    simulate,
    simulate_firmware_rollback,
    simulate_scenario,
)
from app.leveling import variant_for
from app.main import app
from app.scenarios import SCENARIOS
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "ready",
    "upload",
    "verify",
    "stage",
    "reboot",
    "bootcheck",
    "rollback",
    "restored",
]
PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)

SCENARIO = "firmware-update-rollback"

# The bring-up trace's structure as it stood before scenarios existed:
# sha256 over [step, phase, label, activeRegions, watts, progress, elapsed,
# cycleCost] for all 14 steps. Prose is left out so that a copy edit does not
# trip a test about the failure scenario; the key set is pinned separately.
BRING_UP_STEPS = 14
BRING_UP_STRUCTURE_SHA256 = (
    "1f83044214d34bd71a7104fa9cb9023c3caffd86c160145b89debe4558ee8d47"
)
BRING_UP_WIRE_KEYS = {
    "step",
    "phase",
    "label",
    "description",
    "activeRegions",
    "powerWatts",
    "progressPercent",
    "elapsedSeconds",
    "cycleCost",
}


@pytest.fixture(scope="module")
def trace():
    return simulate_firmware_rollback()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# --- the shared invariants ---------------------------------------------------


def test_trace_invariants(trace):
    assert_trace_invariants(trace, PROFILE)
    assert_deterministic(simulate_firmware_rollback)


def test_engine_is_still_pure():
    import app.engine as engine_module

    assert_engine_is_pure(engine_module)


# --- what must hold because the failure happened ------------------------------


def test_the_host_power_state_never_changes(trace):
    """Management is lost; the workload is not. The host is up on the first
    step and on every step after it — including the ones where iDRAC is dark."""
    assert trace[0].host_powered is True
    assert all(s.host_powered is True for s in trace)
    dark = [s for s in trace if not s.management_reachable]
    assert dark, "the scenario never loses management — nothing was tested"
    assert all(s.host_powered for s in dark)


def test_bmc_draw_stays_in_the_standby_envelope(trace):
    """``power_watts`` is still the BMC domain's draw, not the host's."""
    assert all(0 < s.power_watts <= 20 for s in trace)


def test_nothing_unverified_is_written_and_never_to_the_active_partition(trace):
    writes = [s for s in trace if s.writing_partition is not None]
    assert writes, "the image is never staged"
    for s in writes:
        assert s.signature_verified, f"step {s.step}: wrote before verifying"
        assert s.writing_partition != s.active_partition, (
            f"step {s.step}: wrote to the running partition"
        )
    # Verification precedes the first flash write, and the flash block is dark
    # until it has happened.
    first_verified = next(s.step for s in trace if s.signature_verified)
    assert first_verified < writes[0].step
    for s in trace:
        if s.step > 0 and not s.signature_verified:
            assert "flash" not in s.active_regions


def test_the_running_partition_and_version_never_change(trace):
    """The rollback is a return to something that was never disturbed — the
    new version is never the running one in this trace."""
    assert {s.active_partition for s in trace} == {"A"}
    assert {s.running_version for s in trace} == {RUNNING_VERSION}
    assert RUNNING_VERSION != NEW_VERSION


def test_there_is_always_one_bootable_image(trace):
    assert all(s.bootable_images >= 1 for s in trace)
    # Genuinely tested: redundancy is lost during the write and after the
    # failed boot check, so the floor of one is reached, not merely possible.
    assert min(s.bootable_images for s in trace) == 1
    for s in trace:
        if s.writing_partition is not None:
            assert s.bootable_images == 1, (
                "a half-written partition is not bootable"
            )


def test_the_failure_is_marked_and_stays_marked_until_repaired(trace):
    """The failed block is drawn from the failed boot check to the end: the
    twin is honest that rollback leaves one good image, not two."""
    known = {r.id for r in ANATOMY.regions}
    first_fail = next(s.step for s in trace if s.failed_regions)
    assert trace[first_fail].phase == "bootcheck"
    for s in trace:
        assert set(s.failed_regions) <= known
        if s.step < first_fail:
            assert s.failed_regions == []
        else:
            assert s.failed_regions == ["flash"]
            assert s.bootable_images == 1


def test_management_outage_is_real_and_bounded(trace):
    outage = [s.management_outage_seconds for s in trace]
    assert outage == sorted(outage), "the outage counter ran backwards"
    assert outage[0] == 0
    assert 0 < outage[-1] <= MAX_MANAGEMENT_OUTAGE_S
    # The counter moves only while management is dark, and it tracks the clock.
    dark = [s for s in trace if not s.management_reachable]
    assert {s.phase for s in dark} == {"reboot", "bootcheck", "rollback"}
    went_dark = dark[0].elapsed_seconds
    for s in dark:
        assert s.management_outage_seconds == s.elapsed_seconds - went_dark
    back = next(s for s in trace if s.step > dark[-1].step)
    assert back.management_reachable
    assert back.management_outage_seconds == back.elapsed_seconds - went_dark
    assert trace[-1].management_outage_seconds == back.management_outage_seconds
    # While dark, none of the outside-facing blocks is lit.
    outside = {r.id for r in ANATOMY.regions if r.kind in ("network", "io")}
    for s in dark:
        assert not outside & set(s.active_regions), f"step {s.step}"


def test_recovery_ordering(trace):
    """Fail, then fall back, then boot, then answer — and the Root of Trust
    checks the old image too before it runs."""
    step_of = {}
    for s in trace:
        step_of.setdefault(s.phase, s.step)
    assert (
        step_of["verify"]
        < step_of["stage"]
        < step_of["reboot"]
        < step_of["bootcheck"]
        < step_of["rollback"]
        < step_of["restored"]
    )
    first_rollback = trace[step_of["rollback"]]
    assert "rot" in first_rollback.active_regions
    assert trace[-1].management_reachable


def test_the_admin_is_told(trace):
    """iDRAC returns with a Lifecycle log entry naming the reboot, and the
    version the admin sees is the old one."""
    back = next(s for s in trace if s.phase == "restored")
    assert "RAC0182" in back.log_entry
    assert "SUP0520" in back.log_entry
    assert NEW_VERSION in back.log_entry
    assert RUNNING_VERSION in back.log_entry
    staging = next(s for s in trace if s.writing_partition)
    assert "SUP0516" in staging.log_entry


def test_borrowed_message_ids_name_the_generation_they_come_from(trace):
    """RED007 is published in an iDRAC7/iDRAC8 article and the SUP0516,
    RAC0182, SUP0520 sequence in an iDRAC10 case on 17G servers. Wherever the
    prose borrows one, at any reading level, it says whose message it is —
    otherwise the twin is claiming a documented iDRAC9 message it does not
    have."""
    for s in trace:
        for level in (1, 2, 3, 4, 5):
            text = variant_for(s.description, level)
            if "RED007" in text:
                assert "iDRAC7" in text, f"step {s.step} level {level}: RED007"
            if "SUP0520" in text or "RAC0182" in text:
                assert "iDRAC10" in text, f"step {s.step} level {level}: SUPxxxx"


def test_staging_is_the_longest_stage(trace):
    top = max(s.cycle_cost for s in trace)
    longest = [s for s in trace if s.cycle_cost == top]
    assert len(longest) == 1 and longest[0].writing_partition == "B"


def test_every_step_is_leveled(trace):
    for s in trace:
        for level in (1, 5):
            assert variant_for(s.description, level) != s.description, (
                f"step {s.step} has no level-{level} prose"
            )
        assert len(variant_for(s.description, 1)) > len(
            variant_for(s.description, 5)
        )


def test_the_scenario_cites_its_sources():
    ids = [s.id for s in SCENARIOS]
    assert tuple(ids) == SCENARIO_IDS
    failure = next(s for s in SCENARIOS if s.id == SCENARIO)
    assert failure.phases == PHASE_ORDER
    assert len(failure.sources) >= 3
    assert all(src.url.startswith("https://") for src in failure.sources)
    assert "llustrative" in failure.basis


# --- the happy path is what it was ----------------------------------------------


def _structure(states) -> str:
    keys = [
        "step",
        "phase",
        "label",
        "active_regions",
        "power_watts",
        "progress_percent",
        "elapsed_seconds",
        "cycle_cost",
    ]
    blob = json.dumps([[getattr(s, k) for k in keys] for s in states], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def test_bring_up_trace_is_unchanged():
    happy = simulate()
    assert len(happy) == BRING_UP_STEPS
    assert _structure(happy) == BRING_UP_STRUCTURE_SHA256
    assert [s.model_dump() for s in simulate_scenario("bring-up")] == [
        s.model_dump() for s in happy
    ]
    # None of the scenario's fields leak into it.
    for s in happy:
        assert set(s.model_dump(by_alias=True, exclude_none=True)) == BRING_UP_WIRE_KEYS


def test_bring_up_is_byte_identical_over_the_wire(client):
    plain = client.get("/api/bringup")
    named = client.get("/api/bringup?scenario=bring-up")
    assert plain.status_code == 200
    assert plain.content == named.content
    for state in plain.json()["trace"]:
        assert set(state) == BRING_UP_WIRE_KEYS
    # And it is exactly the engine's trace at the standard level.
    expected = [
        s.model_dump(by_alias=True, exclude_none=True) for s in simulate()
    ]
    assert plain.json()["trace"] == expected


def test_failure_scenario_is_served_and_leveled(client):
    r = client.get(f"/api/bringup?scenario={SCENARIO}")
    assert r.status_code == 200
    states = r.json()["trace"]
    assert [s["phase"] for s in states][0] == "ready"
    assert all(s["hostPowered"] is True for s in states)
    novice = client.get(f"/api/bringup?scenario={SCENARIO}&level=1").json()["trace"]
    assert novice[3]["description"] != states[3]["description"]
    assert [s["managementOutageSeconds"] for s in novice] == [
        s["managementOutageSeconds"] for s in states
    ]


def test_unknown_scenario_is_a_404(client):
    assert client.get("/api/bringup?scenario=nope").status_code == 404
    with pytest.raises(KeyError):
        simulate_scenario("nope")


def test_scenarios_are_listed(client):
    listed = client.get("/api/scenarios").json()
    assert [s["id"] for s in listed] == list(SCENARIO_IDS)
    assert listed[1]["heroLabel"] == "management outage"
    assert listed[1]["sources"]
