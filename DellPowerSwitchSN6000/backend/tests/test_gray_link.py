"""The gray-link failure scenario (app/scenarios.py), in the house style:
full-trace assertions, no HTTP layer except the two endpoint checks at the
bottom.

The healthy trace proves the fabric never loses a packet to congestion. This
one is about the failure that guarantee does not cover: a link that stays UP
while it corrupts frames. The signature invariants are the ones that must
hold *because* the failure happened.
"""

from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from app.anatomy import ANATOMY
from app.engine import simulate
from app.main import app
from app.scenarios import (
    BLIND_PHASES,
    GRAY_LINK,
    GRAY_LINK_PHASES,
    HEALTHY_STEADY_TBPS,
    SCENARIOS,
    SICK_LEAF,
    SICK_LINK,
    SICK_SPINE,
    simulate_gray_link,
)
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PROFILE = TraceProfile(phases=GRAY_LINK_PHASES, anatomy=ANATOMY)

# The fields FabricState had before the scenario existed, and the sha256 of
# the healthy trace over exactly those fields, taken before scenarios.py was
# written. Editing the healthy trace's prose or numbers on purpose means
# updating this hash on purpose. (Updated once since: the congestion and
# reroute steps were rewritten so the hotspot is a spine downlink, which
# adaptive routing can relieve, and not a last-hop incast, which it cannot.)
ORIGINAL_FIELDS = [
    "step", "phase", "label", "description", "activeRegions", "fabricTbps",
    "peakLinkPercent", "droppedPackets", "elapsedSeconds", "cycleCost",
]
HEALTHY_SHA256 = "a8f48fedabc03fa270c6ec7660136a20e9654d06b08633ea87dfc110c6042274"
SCENARIO_FIELDS = {
    "sickLink": None,
    "sickLinkStatus": None,
    "sickLinkLocated": False,
    "trafficSteered": False,
    "symbolErrorsPerSec": 0,
    "retransmitsPerSec": 0,
    "collectiveMs": 0,
}


# What losslessness costs, added after the scenario fields. These are part of
# the healthy story on purpose (nonzero on its congestion step), so they are
# allowed on the healthy trace and pinned in test_engine.py instead.
COST_FIELDS = ["hotLink", "ecnMarkedPercent", "pfcPausesPerSec"]


def _phase(trace, name):
    return [s for s in trace if s.phase == name]


# --- the shared invariants ---------------------------------------------------


def test_trace_invariants():
    assert_trace_invariants(simulate_gray_link(), PROFILE)
    assert_deterministic(simulate_gray_link)


def test_the_scenario_module_is_as_pure_as_the_engine():
    import app.scenarios as scenarios_module

    assert_engine_is_pure(scenarios_module)


# --- the happy path is untouched ----------------------------------------------


def test_the_healthy_trace_is_byte_identical_to_before():
    """The scenario extended FabricState additively. Over the fields that
    existed before, the healthy trace must hash to what it hashed to then."""
    dumped = [s.model_dump(by_alias=True) for s in simulate()]
    original = [{k: d[k] for k in ORIGINAL_FIELDS} for d in dumped]
    blob = json.dumps(original, sort_keys=True, ensure_ascii=False)
    assert hashlib.sha256(blob.encode()).hexdigest() == HEALTHY_SHA256


def test_the_healthy_trace_never_touches_the_scenario_fields():
    """Every added field sits at its nothing-is-wrong default on every
    healthy step, and nothing was added beyond the declared set."""
    for s in simulate():
        d = s.model_dump(by_alias=True)
        assert set(d) == set(ORIGINAL_FIELDS) | set(SCENARIO_FIELDS) | set(COST_FIELDS)
        for field, default in SCENARIO_FIELDS.items():
            assert d[field] == default, f"step {s.step}: {field} = {d[field]!r}"


# --- what must hold because the failure happened -------------------------------


def test_congestion_loss_is_still_zero():
    """The healthy twin's invariant survives the failure: no buffer ever
    overflowed. Corruption loss is counted separately, as retransmissions."""
    for s in simulate_gray_link():
        assert s.dropped_packets == 0, f"step {s.step} ({s.phase})"


def test_the_sick_link_reports_up_through_the_blind_steps():
    """THE point. While the job is slow and nobody knows why, the link's
    operational state is 'up' and it has not been located."""
    trace = simulate_gray_link()
    blind = [s for s in trace if s.phase in BLIND_PHASES]
    assert len(blind) >= 2, "the blind stretch must be dwelt on, not skipped"
    for s in blind:
        assert s.sick_link == SICK_LINK
        assert s.sick_link_status == "up", f"step {s.step}"
        assert not s.sick_link_located, f"step {s.step}"
        assert not s.traffic_steered, f"step {s.step}"


def test_the_damage_is_real_while_the_status_is_green():
    """Silence proves nothing unless damage is happening (the Cyber Detect
    twin's rule). On every blind step the job is measurably slower, frames
    are being retransmitted, and no coarse signal shows it: link up, no
    link saturated."""
    trace = simulate_gray_link()
    baseline = trace[0]
    for s in _phase(trace, "blind"):
        assert s.collective_ms >= 1.5 * baseline.collective_ms
        assert s.fabric_tbps < baseline.fabric_tbps
        assert s.retransmits_per_sec > 0
        assert s.peak_link_percent < 90, "a saturated link would be a clue"
        assert s.sick_link_status == "up"


def test_fec_hides_the_first_errors():
    """Before the blind stretch there is a step where symbol errors are
    rising and nothing else has changed — the early warning."""
    trace = simulate_gray_link()
    degrade = _phase(trace, "degrade")
    assert degrade
    for s in degrade:
        assert s.symbol_errors_per_sec > 0
        assert s.retransmits_per_sec == 0
        assert s.collective_ms == trace[0].collective_ms
        assert s.fabric_tbps == trace[0].fabric_tbps


def test_the_link_is_located_by_telemetry_and_not_before():
    trace = simulate_gray_link()
    first_located = next(s for s in trace if s.sick_link_located)
    assert first_located.phase == "telemetry"
    assert "telemetry" in first_located.active_regions
    for s in trace[: first_located.step]:
        assert "telemetry" not in s.active_regions or s.phase == "steady", (
            f"step {s.step}: telemetry consulted before the telemetry step"
        )
    # located is monotone: once named, it stays named
    flags = [s.sick_link_located for s in trace]
    assert flags == sorted(flags)


def test_finding_the_link_fixes_nothing():
    """Detection is not recovery. On the telemetry step the link is known
    and the job is exactly as slow as it was blind."""
    trace = simulate_gray_link()
    blind = _phase(trace, "blind")[-1]
    for s in _phase(trace, "telemetry"):
        assert s.fabric_tbps == blind.fabric_tbps
        assert s.collective_ms == blind.collective_ms
        assert not s.traffic_steered


def test_throughput_recovers_only_after_traffic_is_steered():
    trace = simulate_gray_link()
    degraded_rate = _phase(trace, "blind")[0].fabric_tbps
    first_steered = next(s for s in trace if s.traffic_steered)
    assert first_steered.phase == "steer"
    # Between the first slow step and the steer, nothing recovers.
    first_slow = next(s for s in trace if s.fabric_tbps < trace[0].fabric_tbps)
    for s in trace[first_slow.step : first_steered.step]:
        assert s.fabric_tbps == degraded_rate, f"step {s.step} recovered early"
    assert first_steered.fabric_tbps > degraded_rate
    assert first_steered.collective_ms < _phase(trace, "blind")[0].collective_ms
    assert first_steered.retransmits_per_sec == 0


def test_steering_happens_while_the_link_is_still_up():
    """The order is steer, then drain: traffic leaves first so that taking
    the port down interrupts nothing."""
    trace = simulate_gray_link()
    steer = _phase(trace, "steer")[0]
    assert steer.sick_link_status == "up"
    first_not_up = next(s for s in trace if s.sick_link_status != "up")
    assert first_not_up.phase == "drain"
    assert first_not_up.sick_link_status == "admin-down"
    assert first_not_up.step > steer.step
    assert first_not_up.fabric_tbps == steer.fabric_tbps, "the drain cost work"


def test_the_link_never_goes_down_by_itself():
    """Status leaves 'up' only by operator action, and the sequence is
    up -> admin-down -> training -> up. There is no flap to notice."""
    statuses = [s.sick_link_status for s in simulate_gray_link()]
    collapsed = [x for i, x in enumerate(statuses) if i == 0 or x != statuses[i - 1]]
    assert collapsed == ["up", "admin-down", "training", "up"]


def test_errors_need_a_live_link_and_retransmits_need_traffic_on_it():
    """The two counters have physical preconditions. A link that is shut or
    retraining signals nothing, so it counts no symbol errors; a link with
    no job traffic on it corrupts no frames, so nothing is retransmitted.
    An idle link that is still up does keep counting symbol errors."""
    trace = simulate_gray_link()
    for s in trace:
        if s.sick_link_status != "up":
            assert s.symbol_errors_per_sec == 0, f"step {s.step}"
        if s.traffic_steered or s.sick_link_status != "up":
            assert s.retransmits_per_sec == 0, f"step {s.step}"
    steer = _phase(trace, "steer")[0]
    assert steer.symbol_errors_per_sec > 0, "an idle up link still signals"


def test_moving_traffic_is_an_operator_action_not_adaptive_routing():
    """Adaptive routing selects by congestion and never leaves a corrupting
    link unprompted, so the steer step must show the management plane
    acting, and no blind step may."""
    trace = simulate_gray_link()
    for s in _phase(trace, "steer") + _phase(trace, "drain"):
        assert "mgmt" in s.active_regions, f"step {s.step}"
    for s in _phase(trace, "blind"):
        assert "mgmt" not in s.active_regions
        assert "telemetry" not in s.active_regions


def test_seven_uplinks_are_not_eight():
    """While the link is out, the job runs below the healthy rate and the
    surviving uplink on that leaf runs hotter. Full recovery needs the
    repair, not only the workaround."""
    trace = simulate_gray_link()
    for s in trace:
        if s.traffic_steered:
            assert s.fabric_tbps < HEALTHY_STEADY_TBPS
            assert s.peak_link_percent > trace[0].peak_link_percent
    final = trace[-1]
    assert final.phase == "restored"
    assert final.fabric_tbps == HEALTHY_STEADY_TBPS
    assert final.collective_ms == trace[0].collective_ms
    assert final.symbol_errors_per_sec == 0
    assert final.sick_link_status == "up"
    assert not final.traffic_steered


def test_the_fabric_never_exceeds_healthy_capacity():
    ceiling = max(s.fabric_tbps for s in simulate())
    for s in simulate_gray_link():
        assert s.fabric_tbps <= ceiling, f"step {s.step}"
        assert s.fabric_tbps <= HEALTHY_STEADY_TBPS, f"step {s.step}"


def test_the_hero_number_tracks_delivered_throughput():
    """All-reduce time is the same gradients at the rate the fabric
    delivers: slower fabric, longer collective, never the reverse."""
    trace = simulate_gray_link()
    for a, b in zip(trace, trace[1:]):
        if b.fabric_tbps < a.fabric_tbps:
            assert b.collective_ms > a.collective_ms
        elif b.fabric_tbps > a.fabric_tbps:
            assert b.collective_ms < a.collective_ms
        else:
            assert b.collective_ms == a.collective_ms


def test_the_blind_hunt_is_the_longest_stage():
    trace = simulate_gray_link()
    longest = max(trace, key=lambda s: s.cycle_cost)
    assert longest.phase == "blind"
    assert [s.cycle_cost for s in trace].count(longest.cycle_cost) == 1


def test_the_sick_link_is_a_real_leaf_spine_pair():
    kinds = {r.id: r.kind for r in ANATOMY.regions}
    assert kinds[SICK_LEAF] == "leaf"
    assert kinds[SICK_SPINE] == "spine"
    for s in simulate_gray_link():
        assert s.sick_link == f"{SICK_LEAF}:{SICK_SPINE}"
        # traffic still crosses both tiers on every step
        assert SICK_LEAF in s.active_regions and SICK_SPINE in s.active_regions


def test_the_scenario_cites_its_sources():
    by_id = {s.id: s for s in SCENARIOS}
    assert list(by_id)[0] == "healthy"
    gray = by_id[GRAY_LINK]
    assert gray.phases == GRAY_LINK_PHASES
    assert gray.hero_field == "collectiveMs"
    assert len(gray.sources) >= 2
    for src in gray.sources:
        assert src.url.startswith("https://")
        assert src.label


def test_the_steps_are_leveled_and_point_at_physics_fabric():
    from app.leveling import variant_for  # noqa: F401  (import guard)
    from app.leveling import registry

    reg = registry()
    trace = simulate_gray_link()
    for s in trace:
        variants = reg.get(s.description)
        assert variants, f"step {s.step} is not leveled"
        assert {1, 3, 5} <= set(variants), f"step {s.step}: {sorted(variants)}"
    assert "PhysicsFabric" in trace[-1].description


# --- the wire -------------------------------------------------------------------

client = TestClient(app)


def test_the_default_endpoint_is_the_healthy_trace():
    plain = client.get("/api/fabric").json()
    named = client.get("/api/fabric?scenario=healthy").json()
    assert plain == named
    assert plain["scenario"] == "healthy"
    assert [s["phase"] for s in plain["trace"]] == [s.phase for s in simulate()]
    original = [{k: d[k] for k in ORIGINAL_FIELDS} for d in plain["trace"]]
    blob = json.dumps(original, sort_keys=True, ensure_ascii=False)
    assert hashlib.sha256(blob.encode()).hexdigest() == HEALTHY_SHA256


def test_the_scenario_endpoint_and_listing():
    body = client.get("/api/fabric?scenario=gray-link&level=1").json()
    assert body["scenario"] == "gray-link"
    assert len(body["trace"]) == len(simulate_gray_link())
    assert body["trace"][3]["sickLinkStatus"] == "up"
    assert body["trace"][3]["description"] != simulate_gray_link()[3].description
    assert client.get("/api/fabric?scenario=nope").status_code == 404
    listing = client.get("/api/scenarios").json()
    assert [s["id"] for s in listing] == ["healthy", "gray-link"]
    assert listing[1]["sources"]
