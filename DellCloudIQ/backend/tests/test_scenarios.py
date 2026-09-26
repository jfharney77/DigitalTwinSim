"""The "connected, but no data" failure scenario.

House style: assert over the whole trace. The shared invariants come from
``twinkit.testing``; what stays here is what must hold *because* the failure
happened — nothing is concluded from telemetry that never arrived, the silence
is surfaced rather than painted green, nothing collected is dropped, and the
fix comes from the customer's side of a one-way link.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

import app.scenarios as scenarios_module
from app.anatomy import ANATOMY
from app.engine import simulate
from app.main import app as api
from app.scenarios import (
    SCENARIO_IDS,
    CONNECTED_NO_DATA,
    CONNECTED_NO_DATA_PHASES,
    HEALTHY,
    INTERVAL_SECONDS,
    POINTS_PER_INTERVAL,
    SCENARIOS,
    simulate_connected_no_data,
    simulate_scenario,
)
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PROFILE = TraceProfile(phases=CONNECTED_NO_DATA_PHASES, anatomy=ANATOMY)
KIND = {r.id: r.kind for r in ANATOMY.regions}

# The regions that turn telemetry into a conclusion. ``insight`` is the app
# itself — it is allowed to be lit on no data, because saying "no data" is its job.
CONCLUDING_KINDS = {"analytics", "security", "assistant", "action"}
# The customer's side of the one-way link.
CUSTOMER_KINDS = {"source", "gateway"}
# CloudIQ's "Good" band (95-100) is the one drawn green.
GREEN_FROM = 95

# sha256 of the healthy trace's original ten fields, taken before the scenario
# fields existed. If this moves, the happy path changed — do that deliberately.
# Moved once, deliberately: the final step's label, prose, clock and point count
# now say the score recovers at a later collection, not when the ticket opens.
# Moved again, deliberately: that final step now *lights* the collection path it
# describes, and steps 5 and 6 carry level-1 prose written as a change of
# register rather than a paraphrase of level 3.
HEALTHY_SHA256 = "9c7eb7b21f6988523fb524a52d6b88f2f52bf947d38b8b61f87e2026a1be010e"
ORIGINAL_FIELDS = {
    "step", "phase", "label", "description", "activeRegions", "progressPercent",
    "healthScore", "dataPoints", "elapsedSeconds", "cycleCost",
}


def trace():
    return simulate_connected_no_data()


def first(phase: str) -> int:
    return next(i for i, s in enumerate(trace()) if s.phase == phase)


# --- shared invariants --------------------------------------------------------


def test_trace_invariants():
    assert_trace_invariants(trace(), PROFILE)
    assert_deterministic(simulate_connected_no_data)


def test_scenarios_module_is_pure():
    assert_engine_is_pure(scenarios_module)


def test_failed_regions_exist_and_progress_is_monotonic():
    known = set(KIND)
    prog = [s.progress_percent for s in trace()]
    assert prog[0] == 0 and prog[-1] == 100
    assert all(a <= b for a, b in zip(prog, prog[1:])), "progress regressed"
    for s in trace():
        assert set(s.failed_regions) <= known, f"step {s.step}: unknown failed region"


# --- the failure actually happens --------------------------------------------


def test_the_gateway_says_connected_before_anything_is_blocked():
    """The trap is real: the handshake passes (nothing failing) strictly before
    the upload is refused. A scenario that failed the handshake would be a
    different, easier failure — the admin would be told."""
    t = trace()
    hs = t[first("handshake")]
    assert hs.active_regions == ["gateway"] and not hs.failed_regions
    assert first("handshake") < first("blocked")
    assert "gateway" in t[first("blocked")].failed_regions


def test_ingest_genuinely_starves():
    """Silence proves nothing unless telemetry demonstrably exists and is
    demonstrably not arriving — both halves, as in the CyberDetect twin."""
    starved = [s for s in trace() if s.phase in ("starved", "stale")]
    assert starved
    for s in starved:
        assert s.backlog_points > 0, "nothing was collected — nothing to starve of"
        assert s.data_points == 0, "telemetry arrived during the block"
        assert "ingest" in s.failed_regions


# --- signature invariants -----------------------------------------------------


def test_no_insight_is_ever_generated_from_missing_data():
    """Analytics, cybersecurity, the Assistant and notifications never run while
    the cloud holds nothing from the system, or while it is going without."""
    for s in trace():
        concluding = [r for r in s.active_regions if KIND[r] in CONCLUDING_KINDS]
        if s.data_points == 0 or s.minutes_without_data > 0:
            assert not concluding, (
                f"step {s.step} ({s.phase}): {concluding} ran on no data"
            )
    # ...and it is not vacuous: analysis does run once data has arrived.
    assert any("analytics" in s.active_regions for s in trace())
    assert first("backfill") < first("analyze") < first("resume")


def test_never_a_green_score_on_no_data():
    """The signature behaviour. Until a score has been computed from delivered
    telemetry the readout is 'no-data' (a grey dash in the product) and the
    number behind it is never in the green band."""
    t = trace()
    for s in t:
        if s.data_points == 0:
            assert s.score_state == "no-data", f"step {s.step}: score shown on no data"
        if s.score_state != "fresh":
            assert s.health_score < GREEN_FROM, f"step {s.step}: green on no data"
    # A fresh score appears only after analysis has run on delivered data.
    first_fresh = next(i for i, s in enumerate(t) if s.score_state == "fresh")
    assert first_fresh > first("analyze")
    assert t[-1].score_state == "fresh" and t[-1].phase == "resume"


def test_staleness_is_surfaced_in_the_app():
    """The stale step lights the app (the Connectivity view) and nothing that
    concludes; it is the unique longest stage, because silence is only provable
    by waiting out missed intervals."""
    t = trace()
    stale = t[first("stale")]
    assert stale.active_regions == ["insight"]
    assert stale.failed_regions, "the flag has nothing to point at"
    top = max(s.cycle_cost for s in t)
    assert stale.cycle_cost == top
    assert sum(1 for s in t if s.cycle_cost == top) == 1
    assert stale.minutes_without_data == max(s.minutes_without_data for s in t[: first("repair")])


def test_minutes_without_data_climbs_until_delivery_then_is_zero():
    t = trace()
    before = [s.minutes_without_data for s in t[: first("backfill")]]
    assert all(a <= b for a, b in zip(before, before[1:]))
    assert before[-1] > 60, "never silent long enough to miss an hourly send"
    assert all(s.minutes_without_data == 0 for s in t[first("backfill"):])


def test_nothing_collected_is_dropped():
    """The ledger: while egress is blocked everything collected waits on the
    customer side (one batch per interval); after the fix all of it has been
    delivered. Collected = delivered + backlog on every step. (The full
    backfill is the twin's illustrative choice — see scenarios.py.)"""
    t = trace()
    totals = [s.data_points + s.backlog_points for s in t]
    assert all(a <= b for a, b in zip(totals, totals[1:])), "telemetry vanished"
    for s in t[first("collect"): first("backfill")]:
        expected = POINTS_PER_INTERVAL * (s.elapsed_seconds // INTERVAL_SECONDS)
        assert s.backlog_points == expected and s.data_points == 0
    # The identity itself, on every step — including after the fix, where a
    # quietly dropped batch would otherwise hide behind a monotonic total.
    for s in t:
        collected = POINTS_PER_INTERVAL * (s.elapsed_seconds // INTERVAL_SECONDS)
        assert s.data_points + s.backlog_points == collected, (
            f"step {s.step} ({s.phase}): collected != delivered + backlog"
        )
    peak_backlog = max(s.backlog_points for s in t)
    assert t[-1].backlog_points == 0
    assert t[-1].data_points >= peak_backlog


def test_the_fix_comes_from_the_customer_side_and_flow_stays_one_way():
    """Dell's cloud has no inbound path, so it cannot repair the egress. The
    repair step lights only customer-side regions, no cloud region is active
    before the backfill except the app and the starving ingest, and delivery
    precedes the score — source to cloud to insight, never the reverse."""
    t = trace()
    repair = t[first("repair")]
    assert repair.active_regions
    assert all(KIND[r] in CUSTOMER_KINDS for r in repair.active_regions)
    assert not repair.failed_regions, "the repair step is the fix, not the fault"
    # Nothing in the cloud does work on this system before the telemetry gets
    # there: the only cloud regions lit before the backfill are the app saying
    # "no data" and the ingest that is starving, and the ingest is lit only
    # while it is also marked failing.
    for s in t[: first("backfill")]:
        for r in s.active_regions:
            if KIND[r] in CUSTOMER_KINDS or KIND[r] == "insight":
                continue
            assert r == "ingest" and r in s.failed_regions, (
                f"step {s.step} ({s.phase}): cloud region {r} working on no data"
            )
    backfill = t[first("backfill")]
    assert {"gateway", "ingest"} <= set(backfill.active_regions)
    assert not backfill.failed_regions
    assert first("blocked") < first("repair") < first("backfill") < first("resume")


def test_failures_clear_only_after_the_repair():
    t = trace()
    failing = [i for i, s in enumerate(t) if s.failed_regions]
    assert failing == list(range(first("blocked"), first("repair")))


# --- the happy path did not move ----------------------------------------------


def test_the_happy_path_is_byte_identical_in_every_original_field():
    dumped = [
        {k: v for k, v in s.model_dump(by_alias=True).items() if k in ORIGINAL_FIELDS}
        for s in simulate()
    ]
    blob = json.dumps(dumped, sort_keys=True, ensure_ascii=False)
    assert hashlib.sha256(blob.encode()).hexdigest() == HEALTHY_SHA256


def test_the_happy_path_carries_only_default_scenario_fields():
    for s in simulate():
        assert s.failed_regions == []
        assert s.score_state == "fresh"
        assert s.minutes_without_data == 0
        assert s.backlog_points == 0
    assert simulate_scenario(HEALTHY) == simulate()


# --- the HTTP edge ------------------------------------------------------------


def test_pipeline_endpoint_default_is_the_healthy_trace():
    client = TestClient(api)
    plain = client.get("/api/pipeline").json()
    named = client.get("/api/pipeline", params={"scenario": HEALTHY}).json()
    assert plain == named
    assert plain["scenario"] == HEALTHY
    assert [s["phase"] for s in plain["trace"]] == [s.phase for s in simulate()]


def test_pipeline_endpoint_serves_the_scenario_and_404s_on_unknown():
    client = TestClient(api)
    body = client.get("/api/pipeline", params={"scenario": CONNECTED_NO_DATA}).json()
    assert body["scenario"] == CONNECTED_NO_DATA
    assert [s["phase"] for s in body["trace"]] == CONNECTED_NO_DATA_PHASES
    assert body["trace"][3]["failedRegions"] == ["gateway"]
    assert body["trace"][5]["scoreState"] == "no-data"
    assert client.get("/api/pipeline", params={"scenario": "nope"}).status_code == 404


def test_scenarios_listing_is_sourced():
    listed = TestClient(api).get("/api/scenarios").json()
    assert [s["id"] for s in listed] == [s.id for s in SCENARIOS]
    failure = next(s for s in listed if s["id"] == CONNECTED_NO_DATA)
    assert failure["heroField"] == "minutesWithoutData"
    assert failure["phases"] == CONNECTED_NO_DATA_PHASES
    assert len(failure["sources"]) >= 3
    assert all(src["url"].startswith("https://") for src in failure["sources"])


@pytest.mark.parametrize("level", [1, 3, 5])
def test_every_scenario_step_is_leveled(level):
    client = TestClient(api)
    at = client.get(
        "/api/pipeline", params={"scenario": CONNECTED_NO_DATA, "level": level}
    ).json()["trace"]
    std = client.get(
        "/api/pipeline", params={"scenario": CONNECTED_NO_DATA, "level": 3}
    ).json()["trace"]
    for a, s in zip(at, std):
        assert a["description"].strip()
        if level != 3:
            assert a["description"] != s["description"], f"step {a['step']} not leveled"
    if level == 1:
        expert = client.get(
            "/api/pipeline", params={"scenario": CONNECTED_NO_DATA, "level": 5}
        ).json()["trace"]
        for a, e in zip(at, expert):
            assert len(a["description"]) > len(e["description"]), "scale inverted"


def test_page_intros_and_notes_follow_the_reading_level():
    """The pipeline page's opening paragraph and panel note are scenario data,
    so they change register with the step prose instead of staying at level 3."""
    client = TestClient(api)
    by_level = {
        lv: {s["id"]: s for s in client.get(f"/api/scenarios?level={lv}").json()}
        for lv in (1, 3, 5)
    }
    for sid in SCENARIO_IDS:
        for field in ("intro", "note"):
            novice, standard, expert = (by_level[lv][sid][field] for lv in (1, 3, 5))
            assert novice and standard and expert, (sid, field)
            assert len(novice) > len(standard) > len(expert), (sid, field)
    # "Egress" is never left undefined for a newcomer.
    for lv in (1, 2):
        body = client.get(
            f"/api/pipeline?scenario={CONNECTED_NO_DATA}&level={lv}"
        ).json()
        scen = {s["id"]: s for s in client.get(f"/api/scenarios?level={lv}").json()}
        text = scen[CONNECTED_NO_DATA]["intro"] + " ".join(
            s["label"] + " " + s["description"] for s in body["trace"]
        )
        assert "egress" not in text.lower(), f"level {lv}"
