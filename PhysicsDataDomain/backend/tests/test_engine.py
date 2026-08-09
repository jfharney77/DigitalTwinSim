"""Full-trace invariants for the dedupe engine — the capacity-conservation
ledger, the emergent-ratio claims, and the spec's three scenarios as
acceptance tests (physics_specs/10-additional-products.md, product #4)."""

from __future__ import annotations

from app.anatomy import ANATOMY
from app.constants import APPLIANCES, value as C
from app.engine import local_compression, simulate
from app.models import Dataset, Scenario, Schedule, SimEvent
from app.presets import THIRTY_FULLS

# Trace values are rounded independently (3–4 decimals), so ledger checks
# allow a small tolerance.
TOL = 0.05


def run(scenario: Scenario):
    return simulate(scenario)


def plain(full=50.0, c=1.0, e=30.0, r=30, d=60, appliance="dd9910") -> Scenario:
    return Scenario(
        appliance=appliance,
        dataset=Dataset(full_tb=full, daily_change_pct=c, entropy_pct=e),
        schedule=Schedule(retention_days=r),
        duration_days=d,
    )


def test_determinism():
    s = plain()
    a, _, _ = run(s)
    b, _, _ = run(s)
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]


def test_capacity_conservation_every_day():
    """THE identity: physical(t) = physical(t−1) + (novel − reclaimed) ×
    (1 + metadata overhead), every day of every scenario — the ledger the
    ratio is a quotient of."""
    ovh = 1.0 + C("metadata_overhead_fraction")
    scenarios = [
        plain(),
        plain(c=8.0, e=70.0, r=7, d=40),
        Scenario(
            appliance="dd9910",
            dataset=Dataset(full_tb=100, daily_change_pct=2, entropy_pct=30),
            schedule=Schedule(retention_days=20),
            duration_days=50,
            events=[
                SimEvent(at_day=15, action="ransomware-start", value=4.0),
                SimEvent(at_day=25, action="ransomware-stop"),
                SimEvent(at_day=35, action="enable-host-encryption"),
            ],
        ),
    ]
    for s in scenarios:
        trace, _, _ = run(s)
        for prev, cur in zip(trace, trace[1:]):
            expected = prev.physical_tb + (
                cur.todays_novel_physical_tb - cur.gc_reclaimed_tb
            ) * ovh
            assert abs(cur.physical_tb - expected) <= TOL, f"day={cur.day}"


def test_ratio_is_the_quotient_and_logical_is_generational():
    trace, _, _ = run(plain())
    full = 50.0
    for s in trace:
        assert s.generations_retained == min(s.day, 30)
        assert abs(s.logical_tb - s.generations_retained * full) < 1e-6
        if s.physical_tb > 0:
            assert abs(s.dedupe_ratio - s.logical_tb / s.physical_tb) <= 0.05, (
                f"day={s.day}"
            )


def test_physical_matches_closed_form_with_no_events():
    """The analytic model is exactly its own closed form: physical(t) =
    (1+ovh) · (full/cf) · (1 + (retained−1)·c) while t ≤ retention."""
    full, c_pct, e, r = 80.0, 2.5, 40.0, 25
    trace, _, _ = run(plain(full=full, c=c_pct, e=e, r=r, d=r))
    cf = local_compression(e)
    ovh = 1.0 + C("metadata_overhead_fraction")
    c = c_pct / 100.0
    for s in trace[1:]:
        expected = ovh * (full / cf) * (1.0 + (s.day - 1) * c)
        assert abs(s.physical_tb - expected) <= max(TOL, expected * 1e-3), (
            f"day={s.day}: {s.physical_tb} vs {expected}"
        )


def test_ratio_grows_with_retention():
    """More generations = better ratio — the spec's generational-dedupe
    claim, asserted across runs and within one."""
    short, _, _ = run(plain(r=7, d=30))
    long, _, _ = run(plain(r=60, d=90))
    assert long[-1].dedupe_ratio > short[-1].dedupe_ratio * 3

    # Within one run the ratio is non-decreasing while generations accrue.
    trace, _, _ = run(plain(r=90, d=90))
    ratios = [s.dedupe_ratio for s in trace[1:]]
    assert all(b >= a - 0.01 for a, b in zip(ratios, ratios[1:]))


def test_host_encryption_collapses_the_ratio_toward_one():
    s = plain(full=100, r=10, d=25)
    s.events = [SimEvent(at_day=0, action="enable-host-encryption")]
    trace, _, _ = run(s)
    final = trace[-1]
    assert 0.85 <= final.dedupe_ratio <= 1.05, final.dedupe_ratio
    # Every backup is wholly novel ciphertext.
    assert abs(final.todays_novel_physical_tb - 100.0) < 0.01


def test_static_high_entropy_still_dedupes_but_does_not_compress():
    """The honest distinction the spec's entropy point rests on: entropy
    alone kills local compression; only *session-keyed* encryption kills
    cross-generation dedupe."""
    low, _, _ = run(plain(e=0.0, d=30, r=30))
    high, _, _ = run(plain(e=100.0, d=30, r=30))
    assert high[-1].dedupe_ratio < low[-1].dedupe_ratio
    # But generational dedupe survives: ratio still far above 1.
    assert high[-1].dedupe_ratio > 10


def test_acceptance_thirty_backups_fit_in_two_x():
    """Spec scenario 1: 30 dailies at low change land under 2× the first
    backup's physical footprint, and the ratio emerges high."""
    trace, _, _ = run(THIRTY_FULLS)
    first = next(s for s in trace if s.day == 1)
    last = trace[-1]
    assert last.generations_retained == 30
    assert last.physical_tb <= 2.0 * first.physical_tb, (
        f"{last.physical_tb} vs first {first.physical_tb}"
    )
    assert last.dedupe_ratio >= 20


def test_acceptance_encrypted_source_breaks_the_curve():
    """Spec scenario 2: host-side encryption at day 30 — the daily
    physical delta explodes and the store fills mid-run."""
    s = Scenario(
        appliance="dd9910",
        dataset=Dataset(full_tb=100, daily_change_pct=2.0, entropy_pct=30),
        schedule=Schedule(retention_days=30),
        duration_days=60,
        events=[SimEvent(at_day=30, action="enable-host-encryption")],
    )
    trace, log, summary = run(s)
    by_day = {st.day: st for st in trace}
    delta_before = by_day[29].physical_tb - by_day[28].physical_tb
    delta_after = by_day[35].physical_tb - by_day[34].physical_tb
    assert delta_after > 10 * delta_before
    # Ratio collapses from healthy to near-nothing.
    assert by_day[29].dedupe_ratio > 15
    assert trace[-1].dedupe_ratio < 3
    # Capacity planning explodes: the 1.5 PB flagship fills within weeks.
    assert summary.capacity_full_day != -1
    assert any("host-side encryption" in e.message for e in log)
    # The backup window explodes too — the SLA symptom.
    assert by_day[35].backup_window_hours > 5 * by_day[29].backup_window_hours


def test_acceptance_entropy_alarm_fires_before_capacity_notices():
    """Spec scenario 3: ransomware from day 40 — the stream-entropy alarm
    fires within days, while the capacity curve takes weeks to leave its
    pre-attack trend."""
    s = Scenario(
        appliance="dd9910",
        dataset=Dataset(full_tb=100, daily_change_pct=2.0, entropy_pct=30),
        schedule=Schedule(retention_days=45),
        duration_days=90,
        events=[
            SimEvent(at_day=40, action="ransomware-start", value=3.0),
            SimEvent(at_day=70, action="ransomware-stop"),
        ],
    )
    trace, log, summary = run(s)
    assert summary.alarm_day != -1
    assert 40 <= summary.alarm_day <= 42, summary.alarm_day

    # Capacity-side detection: first day physical exceeds the pre-attack
    # linear trend by 10%.
    by_day = {st.day: st for st in trace}
    slope = (by_day[40].physical_tb - by_day[30].physical_tb) / 10.0
    capacity_notice = next(
        (
            st.day for st in trace
            if st.day > 40
            and st.physical_tb
            > 1.10 * (by_day[40].physical_tb + slope * (st.day - 40))
        ),
        None,
    )
    assert capacity_notice is not None, "the attack must eventually show in capacity"
    assert summary.alarm_day < capacity_notice, (
        f"alarm {summary.alarm_day} must precede capacity notice {capacity_notice}"
    )
    assert any("Entropy alarm" in e.message for e in log)
    # Entropy of *changed* data spikes even while the dataset average is low.
    assert by_day[41].stream_entropy_pct > 60
    assert by_day[39].stream_entropy_pct < 40


def test_index_knee_degrades_ingest_before_the_store_fills():
    s = Scenario(
        appliance="dd3410",
        dataset=Dataset(full_tb=20, daily_change_pct=3.0, entropy_pct=30),
        schedule=Schedule(retention_days=60),
        duration_days=60,
    )
    trace, _, _ = run(s)
    base = APPLIANCES["dd3410"].base_ingest_gbps
    kneed = [st for st in trace if st.index_pressure_pct > 0]
    assert kneed, "the entry appliance must reach index pressure in this run"
    first_knee = kneed[0]
    assert first_knee.capacity_used_pct < 85, (
        "the knee must arrive before the disks are the story"
    )
    assert trace[-1].ingest_gbps < 0.8 * base
    # Ingest is non-increasing once pressure exists.
    after = [st.ingest_gbps for st in trace if st.day >= first_knee.day]
    assert all(b <= a + 1e-9 for a, b in zip(after, after[1:]))


def test_gc_starts_exactly_when_retention_first_expires():
    r = 7
    trace, log, _ = run(plain(r=r, d=20))
    first_gc = next((s.day for s in trace if s.gc_reclaimed_tb > 0), None)
    assert first_gc == r + 1
    for s in trace:
        if s.day <= r:
            assert s.gc_reclaimed_tb == 0
    assert any("cleaning" in e.message.lower() for e in log)
    # After the window fills, physical plateaus (deltas ~0 at steady state).
    steady = [s.physical_tb for s in trace if s.day >= r + 2]
    assert max(steady) - min(steady) < 0.5


def test_region_load_matches_anatomy():
    region_ids = {r.id for r in ANATOMY.regions}
    trace, _, _ = run(plain(d=10))
    for s in trace:
        assert set(s.region_load.keys()) == region_ids
        for v in s.region_load.values():
            assert 0.0 <= v <= 1.0


def test_trace_shape():
    trace, _, _ = run(plain(d=45))
    assert len(trace) == 46
    assert [s.day for s in trace] == list(range(46))
    assert trace[0].physical_tb == 0 and trace[0].logical_tb == 0


def test_engine_is_pure():
    """The engine must not import FastAPI/IO/randomness — house rule."""
    import ast

    import app.engine as engine_module

    tree = ast.parse(open(engine_module.__file__, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {
        "fastapi", "time", "asyncio", "threading", "os", "io", "random",
    }
