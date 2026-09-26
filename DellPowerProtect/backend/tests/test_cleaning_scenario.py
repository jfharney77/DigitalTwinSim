"""The cleaning (garbage collection) failure scenario.

Full-trace assertions in the house style. The first half holds the new trace
to the shared invariants and to the things that must be true *because* the
failure happened; the second half proves the happy path did not move.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

import app.cleaning as cleaning_module
from app.anatomy import ANATOMY
from app.cleaning import (
    ALERT_PERCENT,
    CLEAN_PHASES,
    DEFAULT_SCENARIO_ID,
    SCENARIO_ID,
    SCENARIOS,
    simulate_cleaning,
)
from app.engine import VAULT, simulate
from app.leveling import LEVELS, leveled, registry
from app.main import app
from app.models import CleaningResponse
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "steady", "expire", "ingest", "alert", "clean",
    "pinned", "release", "reclean", "settled",
]

PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)

# Build once at import so the prose is registered whatever order pytest
# collects the files in (test_leveling.py reads the registry).
TRACE = simulate_cleaning()


def _held(s) -> int:
    return s.held_by_replication_tb + s.held_by_snapshot_tb + s.held_by_lock_tb


def _pairs():
    return list(zip(TRACE, TRACE[1:]))


# --- the shared invariants ---------------------------------------------------


def test_trace_invariants():
    assert_trace_invariants(simulate_cleaning(), PROFILE)
    assert_deterministic(simulate_cleaning)


def test_the_scenario_module_is_pure():
    assert_engine_is_pure(cleaning_module)


def test_the_capacity_ledger_closes_on_every_step():
    """stored = live + reclaimable + held. No tolerance: every terabyte on
    the appliance is accounted for as in use, freeable, or held."""
    for s in TRACE:
        assert s.stored_tb == s.live_tb + s.reclaimable_tb + _held(s), (
            f"step {s.step} ({s.phase}): ledger does not close"
        )
        assert 0 < s.stored_tb <= s.capacity_tb, f"step {s.step}: over capacity"
        assert s.stored_tb <= s.logical_tb


# --- what must hold because the failure happened -------------------------------


def test_expiry_alone_never_frees_space():
    """At the expiry step the catalog shrinks and the appliance does not."""
    expiries = [(a, b) for a, b in _pairs() if b.phase == "expire"]
    assert expiries, "the trace never expires anything"
    for a, b in expiries:
        assert b.logical_tb < a.logical_tb, "nothing expired at the expire step"
        assert b.stored_tb == a.stored_tb, (
            f"step {b.step}: expiry freed {a.stored_tb - b.stored_tb} TB by itself"
        )
        assert b.reclaimed_tb == a.reclaimed_tb
    # And more generally: whenever logical falls outside a clean, stored does not.
    for a, b in _pairs():
        if b.logical_tb < a.logical_tb and b.phase not in CLEAN_PHASES:
            assert b.stored_tb >= a.stored_tb, f"step {b.step}"


def test_stored_falls_only_during_a_clean():
    fell = [b for a, b in _pairs() if b.stored_tb < a.stored_tb]
    assert fell, "cleaning never returned any space"
    for s in fell:
        assert s.phase in CLEAN_PHASES and s.clean_running, (
            f"step {s.step}: stored fell during {s.phase!r}"
        )
    assert {s.phase for s in fell} == set(CLEAN_PHASES), (
        "both the scheduled clean and the second clean must return space"
    )
    # reclaimed_tb is the same fact counted from the other side.
    for a, b in _pairs():
        assert b.reclaimed_tb >= a.reclaimed_tb
        if b.reclaimed_tb > a.reclaimed_tb:
            assert b.phase in CLEAN_PHASES


def test_a_clean_frees_exactly_what_was_reclaimable_and_nothing_held():
    """Cleaning takes dead, unreferenced segments and only those: held space
    is untouched by it, and live data is never touched at all."""
    for a, b in _pairs():
        if b.phase not in CLEAN_PHASES:
            continue
        freed = b.reclaimed_tb - a.reclaimed_tb
        assert freed == a.reclaimable_tb - b.reclaimable_tb
        assert freed == a.stored_tb - b.stored_tb
        assert _held(b) == _held(a), f"step {b.step}: cleaning freed held space"
        assert b.live_tb == a.live_tb, f"step {b.step}: cleaning touched live data"


def test_locked_data_is_never_reclaimed_before_its_lock_ends():
    locked = [s for s in TRACE if s.held_by_lock_tb > 0]
    assert locked, "nothing is ever under lock, so the invariant tests nothing"
    for a, b in _pairs():
        if a.lock_days_left > 0:
            assert b.held_by_lock_tb >= a.held_by_lock_tb, (
                f"step {b.step}: {a.held_by_lock_tb - b.held_by_lock_tb} TB of "
                f"locked data went with {a.lock_days_left} days of lock left"
            )
    # The lock genuinely outlasts both cleans, so it was tested under pressure.
    for s in TRACE:
        if s.phase in CLEAN_PHASES:
            assert s.lock_days_left > 0 and s.held_by_lock_tb > 0
    days = [s.lock_days_left for s in TRACE]
    assert days == sorted(days, reverse=True), "the lock clock ran backwards"


def test_the_first_clean_returns_less_than_the_estimate():
    """The trap. The administrator's expectation is the Cleanable figure at
    the alert; the shortfall is exactly what was held."""
    alert = next(s for s in TRACE if s.phase == "alert")
    after = [s for s in TRACE if s.phase == "clean"][-1]
    referenced = alert.held_by_replication_tb + alert.held_by_snapshot_tb
    assert referenced > 0
    assert after.reclaimed_tb < alert.cleanable_tb
    assert alert.cleanable_tb - after.reclaimed_tb == referenced
    # Once the references are released a second clean makes the estimate good.
    assert TRACE[-1].reclaimed_tb == alert.cleanable_tb
    pinned = next(s for s in TRACE if s.phase == "pinned")
    assert pinned.held_by_replication_tb > 0
    assert pinned.held_by_snapshot_tb > 0
    assert pinned.held_by_lock_tb > 0


def test_locked_files_are_never_counted_as_cleanable():
    """A refused delete leaves the file in the namespace, so the appliance has
    no reason to call it cleanable. The estimate covers deleted files only."""
    for s in TRACE:
        assert s.cleanable_tb == (
            s.reclaimable_tb + s.held_by_replication_tb + s.held_by_snapshot_tb
        ), f"step {s.step}"


def test_release_moves_held_to_reclaimable_without_freeing_anything():
    before = next(s for s in TRACE if s.phase == "pinned")
    rel = next(s for s in TRACE if s.phase == "release")
    assert rel.held_by_replication_tb == 0 and rel.held_by_snapshot_tb == 0
    assert rel.held_by_lock_tb == before.held_by_lock_tb
    assert rel.reclaimable_tb == (
        before.held_by_replication_tb + before.held_by_snapshot_tb
    )
    assert rel.stored_tb >= before.stored_tb
    # Recovery ordering: release strictly before the clean that benefits.
    assert rel.step < next(s for s in TRACE if s.phase == "reclean").step


def test_the_alert_is_the_appliance_over_its_threshold_and_nothing_else():
    for s in TRACE:
        over = s.stored_tb * 100 > ALERT_PERCENT * s.capacity_tb
        assert (s.failed_regions == ["dd-prod"]) == over, f"step {s.step}"
        assert bool(s.alerts) == over, f"step {s.step}"
        assert set(s.failed_regions) <= set(s.active_regions)
    assert any(s.failed_regions for s in TRACE), "the appliance never alerts"
    assert not TRACE[-1].failed_regions, "the scenario must end recovered"
    assert TRACE[-1].stored_tb < next(
        s for s in TRACE if s.phase == "alert"
    ).stored_tb


def test_no_stored_backup_is_lost_to_the_full_appliance():
    """Data Domain never deletes on its own: live data only changes by
    ingest (up) or by the catalog expiring it (logical falls with it)."""
    for a, b in _pairs():
        if b.live_tb < a.live_tb:
            assert b.logical_tb < a.logical_tb, (
                f"step {b.step}: live data vanished without an expiry"
            )


def test_air_gap_discipline_carries_over():
    """The gap lights only in ``release``, with the vault on the other end;
    nothing else in the scenario reaches the vault side."""
    for s in TRACE:
        if s.phase == "release":
            assert {"dd-prod", "gap", "dd-vault"} <= set(s.active_regions)
        else:
            assert "gap" not in s.active_regions
            assert not set(VAULT) & set(s.active_regions)


def test_the_copy_forward_pass_is_the_longest_stage():
    top = max(s.cycle_cost for s in TRACE)
    longest = [s for s in TRACE if s.cycle_cost == top]
    assert len(longest) == 1 and longest[0].phase == "clean"
    assert longest[0].stored_tb < TRACE[longest[0].step - 1].stored_tb


# --- prose -------------------------------------------------------------------


def test_every_step_is_authored_at_levels_one_three_and_five():
    reg = registry()
    for s in TRACE:
        variants = reg.get(s.description)
        assert variants and {1, 3, 5} <= set(variants), f"step {s.step}"
        assert len(variants[1]) > len(variants[5])
    base = CleaningResponse(scenario=SCENARIO_ID, trace=TRACE)
    assert leveled(base, 3).model_dump() == base.model_dump()
    for level in LEVELS:
        for st in leveled(base, level).trace:
            assert st.description.strip()


def test_the_scenario_cites_its_sources():
    failure = next(s for s in SCENARIOS if s.id == SCENARIO_ID)
    assert failure.is_failure and len(failure.sources) >= 4
    for src in failure.sources:
        assert src.url.startswith("https://") and "dell.com" in src.url
    assert [s.id for s in SCENARIOS][0] == DEFAULT_SCENARIO_ID


def test_the_lifecycle_page_prose_is_leveled():
    """The intro and the counters note on the lifecycle page come from the
    default scenario, so a reader who lands on #phase=attack at level 1 gets
    level-1 prose. Both call the numbers illustrative, never typical."""
    reg = registry()
    default = SCENARIOS[0]
    for text in (default.intro, default.counters_note):
        variants = reg.get(text)
        assert variants and {1, 3, 5} <= set(variants)
        assert len(variants[1]) > len(variants[5])
        for v in variants.values():
            assert "typical" not in v.lower()
    for v in reg[default.counters_note].values():
        assert "illustrative" in v.lower()


# --- the happy path did not move ---------------------------------------------

# sha256 of GET /api/lifecycle?level=N. First recorded before this scenario
# existed; re-recorded once, deliberately, when the happy path itself was edited
# (student-review fixes: novice prose for scan/attack/recover, the scan called
# costliest rather than longest, and the copiesScanned/copiesFlagged counters).
# The scenario code still must not move it.
HAPPY_PATH_SHA256 = {
    1: "4676d0c51d9614269ec9393e9e57ca2981642f0ac58a69b750dba63a141890a1",
    3: "4b847e18b15a455bee3a0f9c86a9c3d79b9a5f978aac98fad72df0675702e6e9",
    5: "744082b0a69701faac456cb96a05e65e9b30796a88cd3ce7098388c1b61b6490",
}
# sha256 of the engine's own dump (sorted keys), same vintage.
HAPPY_TRACE_SHA256 = "5fa2387a44b53ba0b0f02ff57cba4a1c530739c05b7e9f7da095edce967230e2"

client = TestClient(app)


def test_the_happy_path_trace_is_byte_identical():
    dump = json.dumps(
        [s.model_dump(by_alias=True) for s in simulate()], sort_keys=True
    ).encode()
    assert hashlib.sha256(dump).hexdigest() == HAPPY_TRACE_SHA256


@pytest.mark.parametrize("level", sorted(HAPPY_PATH_SHA256))
def test_the_happy_path_endpoint_is_byte_identical(level):
    plain = client.get(f"/api/lifecycle?level={level}")
    assert plain.status_code == 200
    assert hashlib.sha256(plain.content).hexdigest() == HAPPY_PATH_SHA256[level]
    named = client.get(f"/api/lifecycle?level={level}&scenario={DEFAULT_SCENARIO_ID}")
    assert named.content == plain.content
    assert "failedRegions" not in plain.text and "cleanableTb" not in plain.text


def test_the_failure_trace_is_served_on_the_same_endpoint():
    r = client.get(f"/api/lifecycle?scenario={SCENARIO_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["scenario"] == SCENARIO_ID
    assert [s["phase"] for s in body["trace"]] == [s.phase for s in TRACE]
    first = body["trace"][0]
    for key in (
        "capacityTb", "liveTb", "reclaimableTb", "heldByReplicationTb",
        "heldBySnapshotTb", "heldByLockTb", "cleanableTb", "reclaimedTb",
        "lockDaysLeft", "cleanRunning", "failedRegions", "alerts",
    ):
        assert key in first, key
    novice = client.get(f"/api/lifecycle?scenario={SCENARIO_ID}&level=1").json()
    assert novice["trace"][1]["description"] != body["trace"][1]["description"]


def test_scenarios_are_listed_and_unknown_ones_are_refused():
    listed = client.get("/api/scenarios").json()
    assert [s["id"] for s in listed] == [DEFAULT_SCENARIO_ID, SCENARIO_ID]
    assert listed[1]["isFailure"] and listed[1]["sources"]
    assert client.get("/api/lifecycle?scenario=nope").status_code == 404
