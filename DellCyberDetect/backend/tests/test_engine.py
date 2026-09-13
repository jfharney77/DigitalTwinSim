"""Full-trace invariants for the Cyber Detect engine (style of the GPU,
R760, and PowerStore twins): assert over the whole simulate() trace, no HTTP
layer."""

from __future__ import annotations

from app.anatomy import ANATOMY, CLEAN_SNAPSHOTS
from app.engine import ANALYSIS_PHASES, CORRUPTION_PHASES, simulate
from twinkit.testing import (
    TraceProfile,
    assert_deterministic,
    assert_engine_is_pure,
    assert_trace_invariants,
)

PHASE_ORDER = [
    "clean", "intrusion", "encrypt", "blind",
    "inspect", "classify", "verdict", "recover", "restored",
]


PROFILE = TraceProfile(phases=PHASE_ORDER, anatomy=ANATOMY)


def test_trace_invariants():
    """Steps from zero, phases in order and all reached, the clock advancing,
    only real regions lit, every step at least one cycle — and deterministic.
    The shared definitions live in twinkit.testing."""
    assert_trace_invariants(simulate(), PROFILE)
    assert_deterministic(simulate)


def test_engine_is_pure():
    import app.engine as engine_module

    assert_engine_is_pure(engine_module)


def test_metadata_detection_is_blind_while_corruption_spreads():
    """THE invariant, and this twin's reason for existing. During the
    corruption phases data is demonstrably being ruined and the metadata and
    behaviour detectors raise nothing — not because they are broken, but
    because the attack was deliberately shaped to keep them quiet:
    extensions preserved, entropy raised gradually, no mass rename, I/O
    inside the normal range. Everything watching a *description* of the data
    is satisfied while the data is destroyed."""
    trace = simulate()
    blind = [s for s in trace if s.phase in CORRUPTION_PHASES]
    assert blind, "no corruption phases — the premise would be untested"
    for s in blind:
        assert s.snapshots_corrupted > 0, (
            f"step {s.step} ({s.phase}): nothing corrupted, so silence "
            f"proves nothing"
        )
        assert s.metadata_alerts == 0, (
            f"step {s.step}: metadata analysis raised {s.metadata_alerts} "
            f"alerts — if it could see this attack the product would be "
            f"unnecessary"
        )


def test_metadata_never_catches_it_at_any_point():
    """Not once, in the whole incident. The counter is carried on every
    state precisely so its flatness is visible."""
    assert all(s.metadata_alerts == 0 for s in simulate())


def test_confidence_comes_only_from_reading_content():
    """There is no shortcut to certainty here. Confidence is zero until the
    inspection stage has actually opened the snapshots, and only becomes
    real once the classifier has scored what it found."""
    trace = simulate()
    inspect_idx = next(i for i, s in enumerate(trace) if s.phase == "inspect")
    for s in trace[:inspect_idx + 1]:
        assert s.content_confidence_percent == 0, (
            f"step {s.step} ({s.phase}): confidence before the bytes were read"
        )
    for s in trace:
        if s.phase in ANALYSIS_PHASES:
            assert s.content_confidence_percent >= 99, (
                f"step {s.step}: {s.content_confidence_percent}% is not the "
                f"99.99%-class accuracy the product claims"
            )


def test_the_deliverable_is_a_date_not_an_alert():
    """A detection product that emits 'you have ransomware' has not finished
    its job — by the time anyone runs this, that is not news. The output has
    to name a copy, and it may not do so before the evidence exists."""
    trace = simulate()
    verdict_idx = next(i for i, s in enumerate(trace) if s.phase == "verdict")
    for s in trace[:verdict_idx]:
        assert s.last_clean_snapshot == -1, (
            f"step {s.step} ({s.phase}): named a clean copy before the "
            f"verdict"
        )
    for s in trace[verdict_idx:]:
        assert s.last_clean_snapshot >= 1, (
            f"step {s.step}: no copy named after the verdict"
        )


def test_the_named_copy_is_actually_clean():
    """The one way this product can genuinely fail a customer: certify a
    corrupted snapshot as safe. The named copy must be strictly older than
    the first corrupted one — a false negative here is somebody restoring
    the attack."""
    trace = simulate()
    verdict = next(s for s in trace if s.phase == "verdict")
    first_corrupt = CLEAN_SNAPSHOTS + 1
    assert verdict.last_clean_snapshot < first_corrupt, (
        f"named snapshot {verdict.last_clean_snapshot} but corruption "
        f"starts at {first_corrupt}"
    )
    assert f"snap-{verdict.last_clean_snapshot}" in {
        r.id for r in ANATOMY.regions
    }, "the named copy must be a snapshot that exists"


def test_no_verdict_without_evidence():
    """The verdict region may not light up before the inspection region
    has. Evidence precedes conclusion — the geometry says so too."""
    trace = simulate()
    first_inspect = next(
        i for i, s in enumerate(trace) if "inspect" in s.active_regions
    )
    first_verdict = next(
        i for i, s in enumerate(trace) if "verdict" in s.active_regions
    )
    assert first_inspect < first_verdict


def test_corruption_only_grows_until_it_is_repaired():
    """Nothing un-corrupts itself. The count rises monotonically right up to
    the recovery, and only the recovery brings it down."""
    trace = simulate()
    recover_idx = next(i for i, s in enumerate(trace) if s.phase == "recover")
    before = [s.snapshots_corrupted for s in trace[:recover_idx]]
    assert all(a <= b for a, b in zip(before, before[1:])), (
        "corruption decreased without a recovery"
    )
    assert trace[recover_idx].snapshots_corrupted == 0
    for s in trace[recover_idx:]:
        assert s.snapshots_corrupted == 0


def test_snapshots_are_never_lost():
    """The timeline only grows; snapshots are not deleted to tidy the
    story, because in a real incident the attacker deleting them is a
    separate problem the vault exists to solve."""
    trace = simulate()
    taken = [s.snapshots_taken for s in trace]
    assert all(a <= b for a, b in zip(taken, taken[1:]))


def test_recovery_uses_the_copy_the_verdict_named():
    """The recovery step lights the recovery region, the verdict that drove
    it, and the clean snapshot itself — not the newest copy, and not an
    over-cautious ancient one."""
    trace = simulate()
    rec = next(s for s in trace if s.phase == "recover")
    active = set(rec.active_regions)
    assert "recovery" in active
    assert "verdict" in active
    assert f"snap-{rec.last_clean_snapshot}" in active


def test_content_inspection_is_the_longest_stage():
    """Reading every byte of every snapshot is by some distance the slowest
    thing here, and that expense is the entire product — the UI dwells on
    it for the same reason the R760 twin dwells on memory training."""
    trace = simulate()
    insp = [s for s in trace if s.phase == "inspect"]
    assert insp, "no inspection step in the trace"
    max_cost = max(s.cycle_cost for s in trace)
    assert insp[0].cycle_cost == max_cost
    assert sum(1 for s in trace if s.cycle_cost == max_cost) == 1
