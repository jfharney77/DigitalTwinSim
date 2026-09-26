"""The attestation-fails scenario: what must hold BECAUSE a device failed.

House style: full-trace assertions over the pure scenario engine. The HTTP
layer is touched only to pin that the happy path's bytes did not move and
that the scenario is reachable where the README says it is.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

import app.scenarios as scenarios_module
from app.anatomy import ANATOMY
from app.engine import simulate
from app.leveling import leveled
from app.main import app
from app.models import OnboardResponse
from app.scenarios import (
    ATTESTATION_FAILS,
    BAD,
    SCENARIOS,
    simulate_attestation_fails,
    simulate_scenario,
)
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "crated", "power", "attest", "quarantine", "onboard", "provision",
    "blueprint", "workload", "managed", "replace", "recovered",
]
PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)

ENDPOINT_IDS = {r.id for r in ANATOMY.regions if r.kind == "endpoint"}
HEALTHY = ENDPOINT_IDS - {BAD}
# Phases in which payload (OS, blueprint, workloads, policy) is delivered.
DELIVERY_PHASES = {"provision", "blueprint", "workload", "managed"}

# sha256 of the happy-path response (sorted-key JSON) at every level. First
# recomputed from the committed (pre-scenario) backend during review; re-pinned
# when the happy-path PROSE was deliberately revised after the student review
# (one site of four devices, "on-site action", level 4-5 in domain terms).
# Numbers, phases and regions did not move. The pin's job is unchanged: the
# scenario machinery must not perturb the default response.
HAPPY_PATH_DIGESTS = {
    1: "8f37f53af65dc0b9b358e5a149439a8c8f89cda07128bcedab9db79213469fc4",
    2: "58308d25df1d65c3e9110446c6203864f15d6c3ce28bbab35ac776baeb5cdfc9",
    3: "8d6d91a3e1c649b459d6cf18cbeb95ad0c3d81ea2856b2b41db6436fe0a5ae25",
    4: "587a541936c17987bf818cfece5f2ec7121ed6da897889cb7bb5bb25961c13a8",
    5: "364a10aa0b7dbca1f343bf2eea9158994545730f3e4f247ba7031b1cf9b13495",
}


def _digest(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def test_trace_invariants():
    assert_trace_invariants(simulate_attestation_fails(), PROFILE)
    assert_deterministic(simulate_attestation_fails)


def test_scenario_engine_is_pure():
    assert_engine_is_pure(scenarios_module)


def test_nothing_is_deployed_to_an_unattested_device():
    """THE invariant of the scenario. On every step, every endpoint holding
    any payload has a true verdict of its own; and the failed hardware is
    never lit while payload is being delivered."""
    for s in simulate_attestation_fails():
        for e in s.deployed_to:
            assert s.endpoint_trust[e], (
                f"step {s.step} ({s.phase}): payload on unattested {e}"
            )
        assert not set(s.deployed_to) & set(s.failed_endpoints), (
            f"step {s.step} ({s.phase}): payload on a quarantined device"
        )
        if s.phase in DELIVERY_PHASES:
            assert BAD not in s.active_regions, (
                f"step {s.step} ({s.phase}): the quarantined device took part"
            )


def test_the_failure_actually_happens():
    """Silence proves nothing unless something went wrong: a device really
    is quarantined, from the verdict until it is physically removed."""
    trace = simulate_attestation_fails()
    quarantined = [s for s in trace if s.failed_endpoints]
    assert quarantined, "no step ever quarantines a device"
    assert {tuple(s.failed_endpoints) for s in quarantined} == {(BAD,)}
    first = quarantined[0]
    assert first.phase == "quarantine"
    for s in trace[first.step:]:
        if s.recovery_actions == 0:
            assert s.failed_endpoints == [BAD], (
                f"step {s.step}: quarantine lifted without a replacement"
            )


def test_one_bad_device_never_blocks_the_estate():
    """The healthy three reach every phase at the same second they do on
    the happy path, and reach `managed` before any recovery work starts."""
    happy = {s.phase: s.elapsed_seconds for s in simulate()}
    trace = simulate_attestation_fails()
    for s in trace:
        if s.phase in happy and s.recovery_actions == 0:
            assert s.elapsed_seconds == happy[s.phase], (
                f"{s.phase}: the failure delayed the healthy endpoints "
                f"({s.elapsed_seconds}s vs {happy[s.phase]}s)"
            )
    managed = next(s for s in trace if s.phase == "managed")
    assert managed.endpoints_online == len(HEALTHY)
    assert set(managed.deployed_to) == HEALTHY
    assert managed.recovery_actions == 0


def test_healthy_endpoints_move_in_lockstep():
    for s in simulate_attestation_fails():
        if s.phase in DELIVERY_PHASES or s.phase == "onboard":
            lit = {r for r in s.active_regions if r in ENDPOINT_IDS}
            assert lit == HEALTHY, f"step {s.step} ({s.phase}): lit {lit}"


def test_trust_is_per_device():
    """Every step carries a verdict for every endpoint; healthy trust is
    never revoked; and while three devices are trusted one is not — a
    site-level flag could not express that."""
    trace = simulate_attestation_fails()
    seen_split = False
    trusted_before: set[str] = set()
    for s in trace:
        assert set(s.endpoint_trust) == ENDPOINT_IDS, f"step {s.step}"
        trusted = {e for e, ok in s.endpoint_trust.items() if ok}
        assert trusted_before <= trusted, f"step {s.step}: trust revoked"
        trusted_before = trusted
        if trusted == HEALTHY:
            seen_split = True
    assert seen_split, "the trace never shows trust split across devices"


def test_the_failed_hardware_is_never_trusted():
    """The slot only turns trusted after a human has swapped the unit: no
    central action makes a device that failed attestation trustworthy."""
    for s in simulate_attestation_fails():
        if s.endpoint_trust[BAD]:
            assert s.recovery_actions >= 1, (
                f"step {s.step} ({s.phase}): failed unit trusted in place"
            )
            assert BAD not in s.failed_endpoints


def test_online_counts_only_trusted_claimed_devices():
    for s in simulate_attestation_fails():
        trusted = sum(s.endpoint_trust.values())
        assert s.endpoints_online <= trusted, f"step {s.step}"
        assert s.endpoints_online == len(s.deployed_to) or s.phase in (
            "quarantine", "onboard",
        ), f"step {s.step} ({s.phase})"
    assert simulate_attestation_fails()[-1].endpoints_online == len(ENDPOINT_IDS)


def test_human_actions_are_counted_honestly():
    """operator_actions keeps its ceiling of one (the plug-in). The swap is
    a real human action and is counted under its own name: zero until the
    replace phase, one from then on."""
    trace = simulate_attestation_fails()
    replace_at = next(s.step for s in trace if s.phase == "replace")
    for s in trace:
        assert s.operator_actions <= 1
        assert s.recovery_actions == (0 if s.step < replace_at else 1), (
            f"step {s.step} ({s.phase}): recovery_actions={s.recovery_actions}"
        )
    assert trace[-1].operator_actions + trace[-1].recovery_actions == 2


def test_recovery_ordering():
    """Quarantine precedes any claim; the healthy site is managed before the
    swap; the replacement is trusted only after it is plugged in."""
    phases = [s.phase for s in simulate_attestation_fails()]
    assert phases.index("quarantine") < phases.index("onboard")
    assert phases.index("managed") < phases.index("replace")
    assert phases.index("replace") < phases.index("recovered")
    replace = next(
        s for s in simulate_attestation_fails() if s.phase == "replace"
    )
    assert not replace.endpoint_trust[BAD], "a replacement arrives untrusted"


def test_attestation_is_still_the_longest_stage():
    trace = simulate_attestation_fails()
    top = max(s.cycle_cost for s in trace)
    assert [s.phase for s in trace if s.cycle_cost == top] == ["attest"]


def test_progress_is_monotonic_to_100():
    progress = [s.progress_percent for s in simulate_attestation_fails()]
    assert progress == sorted(progress)
    assert progress[0] == 0 and progress[-1] == 100


def test_the_story_is_identical_until_the_verdict():
    """Nobody can tell which box is bad before attestation answers, so the
    first three steps are the happy path's, field for field."""
    for bad, good in zip(simulate_attestation_fails()[:3], simulate()[:3]):
        assert bad.model_dump(include=set(good.model_dump())) == good.model_dump()


def test_the_scenario_cites_its_sources():
    info = next(s for s in SCENARIOS if s.id == ATTESTATION_FAILS)
    assert info.sources and all(s.url.startswith("https://") for s in info.sources)
    assert "llustrative" in info.illustrative
    assert simulate_scenario("zero-touch") is None
    assert simulate_scenario("no-such-scenario") is None


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
def test_the_happy_path_is_byte_identical(level):
    """The scenario work is additive: the default response, through the
    engine and through HTTP, hashes to what it did before."""
    direct = leveled(OnboardResponse(trace=simulate()), level)
    assert _digest(direct.model_dump(by_alias=True)) == HAPPY_PATH_DIGESTS[level]
    client = TestClient(app)
    for query in (f"?level={level}", f"?level={level}&scenario=zero-touch"):
        body = client.get(f"/api/onboard{query}").json()
        assert _digest(body) == HAPPY_PATH_DIGESTS[level], query


def test_the_scenario_is_served_and_leveled():
    client = TestClient(app)
    ids = [s["id"] for s in client.get("/api/scenarios").json()]
    assert ids == ["zero-touch", ATTESTATION_FAILS]
    texts = set()
    for level in (1, 3, 5):
        body = client.get(
            f"/api/onboard?scenario={ATTESTATION_FAILS}&level={level}"
        ).json()
        assert body["scenario"]["id"] == ATTESTATION_FAILS
        assert len(body["trace"]) == len(simulate_attestation_fails())
        step = next(s for s in body["trace"] if s["phase"] == "quarantine")
        assert step["failedEndpoints"] == [BAD]
        texts.add(step["description"])
    assert len(texts) == 3, "quarantine prose does not change with level"
    assert client.get("/api/onboard?scenario=nope").status_code == 404
