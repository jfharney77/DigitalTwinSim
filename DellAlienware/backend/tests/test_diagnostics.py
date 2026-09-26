"""The charging-diagnostics failure walk (app/diagnostics.py).

House style: assert over the whole trace. The shared trace invariants first,
then what must hold *because* the failures happened — no charge into a hot
pack, no charge from an adapter the EC could not identify, a taper that only
falls — and last that the plug-in trace is served exactly as it was.
"""

from __future__ import annotations

import hashlib
import itertools
import json

import pytest
from fastapi.testclient import TestClient

from app import diagnostics
from app.anatomy import ANATOMIES
from app.catalog import DEFAULT_PROFILE, PROFILES
from app.diagnostics import (
    AC_USE_CAP_PCT,
    BASELINE_ID,
    CHECKS,
    DIAGNOSTIC_PHASES,
    DIAGNOSTIC_SCENARIO,
    PACK_CHARGE_LIMIT_C,
    PACK_CHARGE_RESUME_C,
    SCENARIO_ID,
    SOURCES,
    TAPER_KNEE_PCT,
    simulate_charge_diagnostics,
    taper_w,
    walk_adapters,
)
from app.engine import _cc_rate, simulate
from app.leveling import leveled
from app.main import app as api
from app.models import PowerState, Scenario
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)


def _cases():
    for profile in PROFILES.values():
        for adapter in profile.adapters:
            yield pytest.param(profile, adapter, id=f"{profile.id}-{adapter.id}")


CASES = list(_cases())


def _scenario(profile, adapter):
    return Scenario(
        profile_id=profile.id, adapter_id=adapter.id, start_battery_pct=30,
        thermal_mode="balanced", workload="gaming",
    )


BODY = {"scenario": {
    "profileId": DEFAULT_PROFILE.id,
    "adapterId": DEFAULT_PROFILE.default_adapter_id,
    "startBatteryPct": 30, "thermalMode": "balanced", "workload": "gaming",
}}


def _walk(profile, adapter):
    scenario = _scenario(profile, adapter)
    return simulate_charge_diagnostics(profile, adapter, scenario)


# --- shared invariants --------------------------------------------------------


@pytest.mark.parametrize("profile,adapter", CASES)
def test_trace_invariants(profile, adapter):
    check = TraceProfile(
        phases=DIAGNOSTIC_PHASES, anatomy=ANATOMIES[profile.anatomy_id]
    )
    assert_trace_invariants(_walk(profile, adapter), check)
    assert_deterministic(lambda: _walk(profile, adapter))


def test_the_walk_is_pure():
    assert_engine_is_pure(diagnostics, also_ban=["random"])


def test_the_walk_ignores_the_scenario_dials():
    """A fixed script: every symptom is reached whatever the sliders say."""
    profile = DEFAULT_PROFILE
    adapter = profile.adapters[0]
    a = simulate_charge_diagnostics(
        profile, adapter,
        Scenario(profile_id=profile.id, adapter_id=adapter.id,
                 start_battery_pct=5, thermal_mode="quiet", workload="idle"),
    )
    assert a == _walk(profile, adapter)


# --- the task's four invariants -----------------------------------------------


@pytest.mark.parametrize("profile,adapter", CASES)
def test_energy_identity_every_state(profile, adapter):
    """acW + batteryW == systemW + chargeW — exact on the wire, since acW is
    derived from the rounded terms."""
    for s in _walk(profile, adapter):
        assert s.ac_w + s.battery_w == pytest.approx(
            s.system_w + s.charge_w, abs=0.05
        ), s.stage_id
        assert s.ac_w >= 0, s.stage_id


@pytest.mark.parametrize("profile,adapter", CASES)
def test_ac_never_exceeds_the_genuine_adapter(profile, adapter):
    good, _ = walk_adapters(profile, adapter)
    for s in _walk(profile, adapter):
        assert s.ac_w <= good.watts + 0.05, s.stage_id


@pytest.mark.parametrize("profile,adapter", CASES)
def test_charge_power_never_rises_through_the_taper(profile, adapter):
    """Once the pack is on the constant-voltage leg, every state that charges
    at all charges at or below the one before it — across the heat pause and
    the adapter swap too. The interruptions cost time, never a second wind."""
    cv = [s for s in _walk(profile, adapter) if s.charge_stage == "cv"]
    assert len(cv) >= 4, "the taper must be more than a single step"
    for prev, s in zip(cv, cv[1:]):
        assert s.charge_w <= prev.charge_w, f"{s.stage_id}: taper rose"
    assert cv[-1].charge_w < cv[0].charge_w
    # and the taper sits strictly below the constant-current rate
    cc = [s.charge_w for s in _walk(profile, adapter) if s.charge_stage == "cc"]
    assert cc and max(s.charge_w for s in cv) < min(cc)


def test_taper_curve_is_non_increasing_in_charge_level():
    samples = [taper_w(90.0, p / 2) for p in range(0, 201)]
    assert all(b <= a for a, b in zip(samples, samples[1:]))
    assert taper_w(90.0, TAPER_KNEE_PCT) == 90.0
    assert taper_w(90.0, 100.0) == 0.0


@pytest.mark.parametrize("profile,adapter", CASES)
def test_no_charge_while_the_pack_is_over_its_temperature_limit(profile, adapter):
    trace = _walk(profile, adapter)
    hot = [s for s in trace if s.pack_temp_c > PACK_CHARGE_LIMIT_C]
    assert hot, "the walk must actually overheat the pack"
    for s in hot:
        assert s.charge_w == 0, f"{s.stage_id}: charging a hot pack"
        assert s.charge_limiter == "temperature", s.stage_id
        assert "battery" in s.failed_regions, s.stage_id


@pytest.mark.parametrize("profile,adapter", CASES)
def test_never_charging_and_discharging_at_once(profile, adapter):
    for s in _walk(profile, adapter):
        assert not (s.charge_w > 0 and s.battery_w > 0), s.stage_id
        if s.hybrid:
            assert s.battery_w > 0, s.stage_id


# --- signature invariants: what holds because the failure happened -------------


@pytest.mark.parametrize("profile,adapter", CASES)
def test_the_heat_pause_is_not_a_budget_problem(profile, adapter):
    """In the heat phase the adapter has watts to spare and the pack is below
    full: the only thing stopping the charge is temperature. Silence proves
    nothing unless there was headroom to charge with."""
    good, _ = walk_adapters(profile, adapter)
    heat = [s for s in _walk(profile, adapter) if s.phase == "heat"]
    assert heat
    for s in heat:
        assert s.charge_w == 0
        wanted = taper_w(_cc_rate(profile, good), s.battery_pct)
        assert wanted > 0
        assert good.watts - s.system_w >= wanted, "headroom must be real"
        assert s.battery_pct < 100
        assert s.adapter_readout.endswith(" W"), "adapter reads correctly"


@pytest.mark.parametrize("profile,adapter", CASES)
def test_charge_resumes_unprompted_only_after_the_pack_cools(profile, adapter):
    trace = _walk(profile, adapter)
    last_hot = max(s.cycle for s in trace if s.pack_temp_c > PACK_CHARGE_LIMIT_C)
    resumed = next(s for s in trace if s.phase == "resume")
    assert resumed.cycle > last_hot
    assert resumed.charge_w > 0
    assert resumed.pack_temp_c <= PACK_CHARGE_LIMIT_C
    assert resumed.failed_regions == []


@pytest.mark.parametrize("profile,adapter", CASES)
def test_the_charge_cap_stops_a_healthy_charge(profile, adapter):
    """Stuck at the cap: adapter recognized, pack cool, watts to spare — and
    nothing is drawn as failed, because nothing has."""
    trace = _walk(profile, adapter)
    stuck = next(s for s in trace if s.stage_id == "d6-stuck-at-cap")
    assert stuck.charge_mode == "primarily-ac"
    assert stuck.battery_pct == AC_USE_CAP_PCT == stuck.charge_cap_pct
    assert stuck.charge_w == 0 and stuck.charge_limiter == "charge-cap"
    assert stuck.pack_temp_c <= PACK_CHARGE_LIMIT_C
    assert stuck.failed_regions == []
    # no state ever charges at or past its own cap
    for prev, s in zip(trace, trace[1:]):
        if s.charge_w > 0:
            assert prev.battery_pct < s.charge_cap_pct, s.stage_id
    # the recovery action is the mode change, and the taper follows it
    first_cv = next(s for s in trace if s.charge_stage == "cv")
    assert first_cv.charge_mode == "standard"
    assert first_cv.cycle > stuck.cycle


@pytest.mark.parametrize("profile,adapter", CASES)
def test_an_unrecognized_adapter_powers_but_never_charges(profile, adapter):
    trace = _walk(profile, adapter)
    unknown = [s for s in trace if s.adapter_readout == "Unknown"]
    assert unknown and {s.phase for s in unknown} == {"swap"}
    for s in unknown:
        assert s.charge_w == 0 and s.charge_limiter == "adapter"
        assert s.failed_regions == ["dc-in"]
        assert s.ac_w > 0 and s.battery_w == 0, "it still runs the system"
        assert s.battery_pct < 100, "there was charge left to refuse"
    # the adapter is the only hardware fault in the walk
    assert {s.phase for s in trace if "dc-in" in s.failed_regions} == {"swap"}
    # recovery: charge re-arms only after the genuine adapter is back
    after = [s for s in trace if s.cycle > unknown[-1].cycle]
    assert after[0].adapter_readout.endswith(" W") and after[0].charge_w > 0


@pytest.mark.parametrize("profile,adapter", CASES)
def test_the_pack_ends_full_and_the_limiter_explains_every_zero(profile, adapter):
    trace = _walk(profile, adapter)
    assert trace[-1].battery_pct == 100 and trace[-1].charge_limiter == "full"
    seen = {s.charge_limiter for s in trace}
    assert {"charge-cap", "taper", "temperature", "adapter", "full"} <= seen
    for s in trace:
        if s.charge_stage == "cc":
            # a 100 W USB-C adapter cannot fund the full rate: that is budget
            assert s.charge_limiter in {"none", "budget"}
        if s.charge_stage == "cv":
            assert s.charge_limiter in {"taper", "budget"}
    # failed regions are real regions
    ids = {r.id for r in ANATOMIES[profile.anatomy_id].regions}
    assert all(set(s.failed_regions) <= ids for s in trace)


def test_checks_point_at_real_phases_and_sources_are_cited():
    trace = _walk(DEFAULT_PROFILE, DEFAULT_PROFILE.adapters[0])
    for check in CHECKS:
        states = [s for s in trace if s.phase == check.phase]
        assert states, check.id
        assert any(s.charge_limiter == check.limiter for s in states), check.id
    assert len(SOURCES) >= 4
    assert all(s.url.startswith("https://") for s in SOURCES)
    assert "illustrative" in DIAGNOSTIC_SCENARIO.illustrative


def test_step_prose_is_leveled():
    trace = _walk(DEFAULT_PROFILE, DEFAULT_PROFILE.adapters[0])
    novice = [leveled(s, 1) for s in trace]
    expert = [leveled(s, 5) for s in trace]
    assert [leveled(s, 3) for s in trace] == trace
    for n, s, e in zip(novice, trace, expert):
        assert n.description != s.description != e.description, s.stage_id
        assert len(n.description) > len(e.description), s.stage_id


# --- the plug-in trace is untouched -------------------------------------------

client = TestClient(api)

# sha256 over every non-prose field of the plug-in trace, across profiles,
# adapters, modes, workloads and start levels. Computed from the engine as it
# stood before diagnostics.py existed; a change here means the happy path moved.
PLUG_IN_DIGEST = "8af618079aedaa701016e89ee1dc49c7857df75cce98636e9097527ebaddd642"


def test_plug_in_trace_numbers_are_byte_identical_to_before():
    h = hashlib.sha256()
    for p in PROFILES.values():
        for a in p.adapters:
            for mode, load, start in itertools.product(
                ["quiet", "fullSpeed"], ["idle", "gaming", "fullLoad"], [0, 30, 100]
            ):
                sc = Scenario(profile_id=p.id, adapter_id=a.id,
                              start_battery_pct=start, thermal_mode=mode,
                              workload=load)
                for s in simulate(p, a, sc):
                    d = s.model_dump(by_alias=True)
                    d.pop("label"), d.pop("description")
                    h.update(json.dumps(d, sort_keys=True).encode())
    assert h.hexdigest() == PLUG_IN_DIGEST


def test_plug_in_states_carry_no_diagnostic_fields():
    p = DEFAULT_PROFILE
    a = p.adapters[0]
    trace = simulate(p, a, _scenario(p, a))
    assert all(type(s) is PowerState for s in trace)
    assert not {s.phase for s in trace} & {"cap", "taper", "heat", "resume", "swap"}


def test_endpoint_without_the_param_is_the_plug_in_trace_byte_for_byte():
    body = BODY
    plain = client.post("/api/simulate", json=body)
    named = client.post(f"/api/simulate?scenario={BASELINE_ID}", json=body)
    assert plain.status_code == named.status_code == 200
    assert plain.content == named.content
    data = plain.json()
    assert set(data) == {"profile", "scenario", "adapter", "summary", "trace"}
    assert "chargeLimiter" not in data["trace"][0]


def test_endpoint_serves_the_walk_and_lists_scenarios():
    body = BODY
    r = client.post(f"/api/simulate?scenario={SCENARIO_ID}", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["traceScenario"]["id"] == SCENARIO_ID
    first = data["trace"][0]
    for key in ("chargeLimiter", "packTempC", "adapterReadout",
                "batteryReadout", "failedRegions", "chargeCapPct", "chargeMode"):
        assert key in first, key
    listed = client.get("/api/scenarios").json()
    assert [s["id"] for s in listed] == [BASELINE_ID, SCENARIO_ID]
    assert [s["kind"] for s in listed] == ["baseline", "failure"]
    assert client.post("/api/simulate?scenario=nope", json=body).status_code == 404
    # reading levels reach the walk
    easy = client.post(f"/api/simulate?scenario={SCENARIO_ID}&level=1", json=body)
    assert easy.json()["trace"][0]["description"] != first["description"]


# --- review additions: hysteresis, and one status line for three causes --------


@pytest.mark.parametrize("profile,adapter", CASES)
def test_the_thermal_inhibit_holds_until_the_resume_temperature(profile, adapter):
    """Dropping back under the limit is not enough: the inhibit clears only at
    the re-arm temperature. The walk must show a state in that band — under
    the limit, headroom to spare, still not charging — or the hysteresis is
    untested."""
    trace = _walk(profile, adapter)
    first_hot = min(s.cycle for s in trace if s.pack_temp_c > PACK_CHARGE_LIMIT_C)
    resumed = next(s for s in trace if s.phase == "resume")
    band = [
        s for s in trace
        if first_hot < s.cycle < resumed.cycle
        and PACK_CHARGE_RESUME_C < s.pack_temp_c <= PACK_CHARGE_LIMIT_C
    ]
    assert band, "no state sits between re-arm and trip"
    for s in band:
        assert s.charge_w == 0 and s.charge_limiter == "temperature", s.stage_id
        assert "battery" in s.failed_regions, s.stage_id
    assert resumed.pack_temp_c <= PACK_CHARGE_RESUME_C
    # every state between the first hot one and the resume is inhibited
    for s in trace[first_hot:resumed.cycle]:
        assert s.charge_w == 0, s.stage_id


@pytest.mark.parametrize("profile,adapter", CASES)
def test_every_zero_charge_state_past_the_handshake_names_its_limiter(
    profile, adapter
):
    """Once the charger can be armed at all, no state is left unexplained: a
    zero on the charge meter always carries a reason other than 'none'. Before
    the handshake there is nothing to explain — the charger is not armed yet —
    so those phases are excluded by name rather than by luck."""
    unarmed = {"off", "detect", "handshake", "budget"}
    for s in _walk(profile, adapter):
        if s.phase in unarmed:
            assert s.charge_w == 0 and s.charge_limiter == "none", s.stage_id
        elif s.charge_w == 0:
            assert s.charge_limiter != "none", s.stage_id


@pytest.mark.parametrize("profile,adapter", CASES)
def test_no_state_names_a_limiter_its_own_readouts_deny(profile, adapter):
    """The readouts are the evidence for the diagnosis, so they may not argue
    with it: a charge-mode cap is only named while the cap is actually the
    thing in the way, and a temperature limiter only while the pack is over
    the re-arm point."""
    for s in _walk(profile, adapter):
        if s.charge_limiter == "charge-cap":
            assert s.charge_cap_pct < 100.0, s.stage_id
            assert s.battery_pct >= s.charge_cap_pct, s.stage_id
        if s.charge_limiter == "temperature":
            assert s.pack_temp_c > PACK_CHARGE_RESUME_C, s.stage_id
        if s.charge_limiter == "adapter":
            assert s.adapter_readout == "Unknown", s.stage_id
        if s.charge_limiter == "full":
            assert s.battery_pct >= s.charge_cap_pct, s.stage_id


def test_the_status_line_does_not_name_the_cause():
    """Three different limiters read the same 'Not charging' on the machine;
    telling them apart takes the adapter line, the mode and the temperature."""
    trace = _walk(DEFAULT_PROFILE, DEFAULT_PROFILE.adapters[0])
    by_limiter = {
        s.charge_limiter: s for s in trace
        if s.battery_readout == "Not charging"
    }
    assert {"charge-cap", "temperature", "adapter"} <= set(by_limiter)
    distinguishing = {
        (s.adapter_readout, s.charge_mode, s.pack_temp_c > PACK_CHARGE_RESUME_C)
        for k, s in by_limiter.items() if k in {"charge-cap", "temperature", "adapter"}
    }
    assert len(distinguishing) == 3
