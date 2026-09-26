"""Graded labs for the network-fabrics simulator (``docs/LAB_PATTERN.md``;
pilot: ``DellPowerEdgeR760Thermal/backend/app/labs.py``).

A guided scenario sets the dials and says what to watch. A lab states a goal
and leaves the dials to the learner: build a Scenario with the ordinary
controls, the pure engine runs it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py`` and ``validation.py``: no FastAPI, no
IO, no clock, no randomness (AST-checked in ``tests/test_labs.py``).
``main.py`` is the only caller that touches HTTP, and a static-hosting build
runs this same file in the browser.

What is this app's own; everything else is ``twinkit.labs``:

* ``measure()`` — one run as named numbers. The un-gameable ones are rates
  averaged over the whole run: ``goodputRateGbps`` (mean delivered Gb/s, after
  drops, deferral and the gray-failure tax), ``allreduceRateGbps`` (mean
  effective collective rate) and ``otherGoodputGbps`` (mean delivered
  non-collective traffic). An idle fabric delivers nothing, so it passes
  nothing. They are the engine's illustrative flow-level figures, not a
  benchmark, and are labeled so.
* ``LABS`` — three labs of rising difficulty. Each is an acceptance test from
  ``tests/test_engine.py`` turned into a sizing problem: the hash collision
  under a power budget, the spine loss under a non-blocking rule, and SHARP's
  crossing counters with a gray failure taxing the result.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab, and the cheap tricks that must not. Server-side only: the API serves
  ``LABS``.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .engine import simulate
from .leveling import L
from .models import (
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
    Workload,
)
from .presets import SN6000_ADAPTIVE, SN6000_STATIC, X800_FABRIC
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_OVERSUB = "ratio = Σ downlink capacity ÷ Σ uplink capacity, per leaf"
EQ_QUEUE = "latency = hops × base × 1/(1−ρ) past ~90% utilization"
EQ_ECMP = "worst link = fair share × (1 + imbalance);  adaptive ⇒ imbalance × 0.15"
EQ_LOSSLESS = "Ethernet: drop · RoCE: pause upstream · InfiniBand: stall the sender"
EQ_OPTICS = "P_optics = ports × (18 W pluggable | 6 W CPO);  compare P_asic"
EQ_SHARP = (
    "all-reduce = delivered × collective share × 1.8 with SHARP;  "
    "link bytes × (1 − 0.5 × collective share)"
)
EQ_GRAY = "goodput = delivered × (1 − 35% ÷ leaves);  FCT × 2.4;  status = green"

#: "Never happened" for the first-event metrics, so ``<= 100`` fails honestly.
NEVER = 9999.0


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    events = sorted(scenario.events, key=lambda e: e.at_s)
    ei = 0
    wl = scenario.workload
    other = 0.0
    elephant_ticks = 0
    alltoall_ticks = 0
    worst_ratio = 0.0
    for s in trace:
        # Replay the traffic dial exactly as the engine applied it.
        while ei < len(events) and events[ei].at_s <= s.t:
            ev = events[ei]
            ei += 1
            if ev.action == "set-workload" and ev.workload is not None:
                wl = ev.workload
        other += s.delivered_gbps * (1.0 - wl.collective_pct / 100.0)
        if wl.pattern == "elephant":
            elephant_ticks += 1
        if wl.pattern == "alltoall":
            alltoall_ticks += 1
        up = max(s.spines_alive, 1) * cfg.uplink_gbps
        worst_ratio = max(
            worst_ratio, cfg.endpoints_per_leaf * cfg.downlink_gbps / up
        )
    n = len(trace)
    first_spine = next((s.t for s in trace if s.spines_alive < cfg.spines), NEVER)
    first_gray = next((s.t for s in trace if s.goodput_penalty_pct > 0), NEVER)
    return {
        "durationS": float(trace[-1].t),
        "goodputRateGbps": round(sum(s.delivered_gbps for s in trace) / n, 1),
        "allreduceRateGbps": round(sum(s.allreduce_gbps for s in trace) / n, 1),
        "otherGoodputGbps": round(other / n, 1),
        "elephantPct": round(100.0 * elephant_ticks / n, 1),
        "alltoallPct": round(100.0 * alltoall_ticks / n, 1),
        "peakWorstLinkPct": float(summary.peak_worst_link_pct),
        "secondsPastKnee": float(summary.seconds_congested),
        "damageSeconds": float(sum(
            1 for s in trace
            if s.lost_gbps > 0 or s.pause_events_s > 0 or s.stall_us_per_s > 0
        )),
        "peakFabricPowerW": float(max(s.fabric_power_w for s in trace)),
        "peakAsicPowerW": float(max(s.asic_power_w for s in trace)),
        "endpoints": float(cfg.leaves * cfg.endpoints_per_leaf),
        "worstOversubRatio": round(worst_ratio, 2),
        "firstSpineLossS": float(first_spine),
        "spineDownSeconds": float(sum(1 for s in trace if s.spines_alive < cfg.spines)),
        "firstGrayS": float(first_gray),
        "graySeconds": float(sum(1 for s in trace if s.goodput_penalty_pct > 0)),
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _goodput(floor: int) -> Criterion:
    return Criterion(
        id="goodput", label=f"Mean goodput at least {floor:,} Gb/s",
        metric="goodputRateGbps", op=">=", threshold=floor, unit="Gb/s",
        weight=2.0, guards_work=True, explain_id="lossless", equation=EQ_LOSSLESS,
        why=L(
            standard=(
                f"Goodput is delivered Gb/s averaged over every second of the "
                f"run; {floor:,} Gb/s is the floor. Demand the fabric drops, "
                "pauses or stalls is not delivered, and neither is demand "
                "nobody offered, so turning the traffic down is not a way "
                "through. The figure is the flow model's, illustrative rather "
                "than a benchmark."
            ),
            novice=(
                f"The network has to carry real traffic the whole time: at "
                f"least {floor:,} gigabits per second on average, counting "
                "every second of the run. Only traffic that actually arrives "
                "counts. Traffic that is thrown away, told to wait, or held "
                "back at the sender does not count, and traffic you never "
                "asked for does not count either. So you cannot pass by "
                "turning the Demand slider down. The number comes from this "
                "app's simple flow model; it is a stand-in, not a measured "
                "benchmark."
            ),
            expert=(
                f"Mean delivered Gb/s over all ticks ≥ {floor:,}; dropped, "
                "paused and stalled demand earns nothing. Illustrative."
            ),
        ),
    )


def _below_knee() -> Criterion:
    return Criterion(
        id="below-knee", label="Worst link never past 90%",
        metric="secondsPastKnee", op="<=", threshold=0, unit="s", weight=2.0,
        explain_id="queue-delay", equation=EQ_QUEUE,
        why=L(
            standard=(
                "Past 90% utilization the queue multiplier 1/(1−ρ) takes "
                "over and tail latency leaves single-digit microseconds. The "
                "line is graded on the worst link, not the mean, because the "
                "slowest flow sets the pace of a training step."
            ),
            novice=(
                "A link that is 80% full is fine. Past 90% full, packets "
                "start waiting in line, and the wait grows faster and faster "
                "as the link fills. This line counts the seconds in which "
                "the busiest single link in the fabric was past 90%, and it "
                "must be 0. It looks at the busiest link rather than the "
                "average because a training job moves at the speed of its "
                "slowest flow."
            ),
            expert="Σ ticks with worst-link ρ > 0.9 must be 0; tail = f(worst link).",
        ),
    )


def _no_damage() -> Criterion:
    return Criterion(
        id="no-damage", label="Nothing dropped, paused or stalled",
        metric="damageSeconds", op="<=", threshold=0, unit="s", weight=2.0,
        explain_id="lossless", equation=EQ_LOSSLESS,
        why=L(
            standard=(
                "When a link is offered more than it can carry, the excess "
                "goes somewhere: Ethernet drops it, lossless RoCE pauses "
                "upstream, InfiniBand stalls the sender. All three are "
                "damage relocated, and any second with drops, pauses or "
                "credit stalls fails this line. Lossless is not the same as "
                "unharmed."
            ),
            novice=(
                "If more traffic arrives at a link than it can carry, "
                "something has to give. Plain Ethernet throws the extra "
                "away. Lossless Ethernet tells the switches behind it to "
                "pause, so the jam spreads backward. InfiniBand makes the "
                "sender wait. Nothing is lost in the last two, but work is "
                "still delayed. This line counts the seconds in which any of "
                "the three happened, and it must be 0. A lossless fabric "
                "that is pausing has not solved the problem, it has moved it."
            ),
            expert="Σ ticks with drops ∨ PFC pauses ∨ credit stalls = 0. Lossless ≠ undamaged.",
        ),
    )


def _endpoints(n: int) -> Criterion:
    return Criterion(
        id="endpoints", label=f"At least {n} endpoints attached",
        metric="endpoints", op=">=", threshold=n, unit="ports",
        explain_id="oversub", equation=EQ_OVERSUB,
        why=L(
            standard=(
                f"The fabric exists to connect {n} GPU ports (leaves × "
                "endpoints per leaf). Every endpoint port carries an optic, "
                "so removing endpoints is the cheap way to cut power and "
                "improve the oversubscription ratio. It is not allowed."
            ),
            novice=(
                f"This network is being built for {n} GPU connections. The "
                "count is the number of leaf switches times the endpoints on "
                "each leaf. Unplugging GPUs would save power and make every "
                "ratio look better, which is why the lab does not allow it: "
                f"leaves × endpoints per leaf must be {n} or more."
            ),
            expert=f"leaves × endpoints/leaf ≥ {n}; no shrinking the downlink side.",
        ),
    )


def _full_run(seconds: int) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {seconds} s",
        metric="durationS", op=">=", threshold=seconds, unit="s",
        explain_id="queue-delay", equation=EQ_QUEUE,
        why=L(
            standard=(
                "The rates are averaged over the run, and the faults have to "
                "be lived with rather than glimpsed. A short run would be "
                f"graded before the fabric had carried anything; {seconds} s "
                "is the length the lab starts with."
            ),
            novice=(
                f"The run has to last at least {seconds} seconds, which is "
                "the length the lab starts with. The grades are averages "
                "over the whole run, and the faults in the harder labs have "
                "to stay in place for most of it. A very short run would not "
                "show whether the fabric really holds up."
            ),
            expert=f"durationS ≥ {seconds}; rates are whole-run means.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Build has no configuration errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="oversub", equation=EQ_OVERSUB,
        why=L(
            standard=(
                "Errors in the Configuration rules panel are feature "
                "mismatches: SHARP belongs to the InfiniBand personality, "
                "and adaptive routing, RoCE and co-packaged optics do not "
                "exist on the campus switch. Warnings are allowed."
            ),
            novice=(
                "The Configuration rules list under the build controls "
                "checks that your choices go together. A red error means "
                "the combination does not exist, for example SHARP on an "
                "Ethernet fabric. Yellow warnings are allowed. Red errors "
                "are not: the count must be 0."
            ),
            expert="Zero error-level findings (feature/personality mismatches).",
        ),
    )


def _pattern(metric: str, cid: str, name: str, label: str) -> Criterion:
    return Criterion(
        id=cid, label=label, metric=metric, op=">=", threshold=100, unit="%",
        explain_id="ecmp", equation=EQ_ECMP,
        why=L(
            standard=(
                f"The job's traffic is {name}, and its hash-collision skew "
                "is the imbalance term this lab is about. Switching the "
                "Pattern to something gentler would shrink the worst link "
                "for free, so the pattern is measured on every second."
            ),
            novice=(
                f"The traffic in this lab is {name}, and that is the hard "
                "part: this pattern lands unevenly on the links. Picking an "
                "easier Pattern in the Traffic panel would make the problem "
                f"go away without solving it, so the lab checks that {name} "
                "were running for 100% of the run."
            ),
            expert=f"Pattern must be {name} on 100% of ticks; the skew is the point.",
        ),
    )


# --- Lab 1: elephants on a power budget ------------------------------------

_ELEPHANTS_16 = Workload(demand_gbps=16000, pattern="elephant", collective_pct=0)

_L1_START = Scenario(config=SN6000_STATIC, workload=_ELEPHANTS_16, duration_s=600)

ELEPHANTS_ON_A_BUDGET = Lab(
    id="elephants-on-a-budget",
    title="Tame the elephants on a power budget",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "Carry 16,000 Gb/s of elephant flows with the worst link "
                "never past 90%, inside an 8,000 W fabric power budget. "
                "Then push the worst link as low as the budget allows."
            ),
            novice=(
                "A few giant data flows (people call them elephants) are "
                "crossing this network, 16,000 gigabits per second in all. "
                "Right now too many of them land on the same link and jam "
                "it. Your job: carry all of that traffic, never let the "
                "busiest link go past 90% full, and keep the whole fabric "
                "under 8,000 watts. After that, make the busiest link as "
                "quiet as you can."
            ),
            expert=(
                "16,000 Gb/s elephants, worst-link ρ ≤ 0.9 throughout, peak "
                "fabric power ≤ 8,000 W; minimize peak worst link."
            ),
        ),
        constraints=[
            L(standard="Elephant-flow traffic for the whole run.",
              novice="Keep the Pattern on 'Elephant flows' for the whole run.",
              expert="Pattern = elephant, 100% of ticks."),
            L(standard="Peak fabric power no higher than 8,000 W.",
              novice="The Fabric power reading must never go above 8,000 watts.",
              expert="max(P_fabric) ≤ 8,000 W."),
            L(standard="Worst link never past 90%; nothing dropped, paused or stalled.",
              novice="The busiest link must never pass 90% full, and no traffic may be thrown away or told to wait.",
              expert="ρ_worst ≤ 0.9; zero damage ticks."),
            L(standard="At least 128 endpoints, a 600 s run, no configuration errors.",
              novice="Keep at least 128 GPU connections, keep the 600-second run, and have no red errors in the Configuration rules.",
              expert="≥128 endpoints, ≥600 s, zero errors."),
        ],
        delivered_work=L(
            standard="At least 16,000 Gb/s of goodput, averaged over the run.",
            novice="On average at least 16,000 gigabits per second must actually arrive. An idle network does not count.",
            expert="goodputRateGbps ≥ 16,000.",
        ),
    ),
    criteria=[
        _goodput(16000),
        _pattern("elephantPct", "elephants", "elephant flows",
                 "Elephant-flow traffic for the whole run"),
        _below_knee(),
        _no_damage(),
        Criterion(
            id="power-budget", label="Peak fabric power at most 8,000 W",
            metric="peakFabricPowerW", op="<=", threshold=8000, unit="W",
            weight=2.0, explain_id="optics-power", equation=EQ_OPTICS,
            why=L(
                standard=(
                    "Fabric power is 550 W per switch ASIC plus one optic per "
                    "port, 18 W pluggable or 6 W co-packaged (all estimates). "
                    "Buying spines to dilute the collision adds ASICs and "
                    "ports; the budget is what makes that the wrong answer."
                ),
                novice=(
                    "Every switch in this model draws about 550 watts, and "
                    "every port has a small laser plug that draws 18 watts, "
                    "or 6 watts if the optics are built into the chip "
                    "package (co-packaged optics, CPO). These figures are "
                    "estimates. Adding more spine switches would spread the "
                    "traffic out, but each one adds a switch and a set of "
                    "ports. The 8,000 watt limit is there so that buying "
                    "more hardware is not the answer."
                ),
                expert="Σ 550 W/ASIC + ports × (18 | 6) W ≤ 8,000 W (estimates). No brute force.",
            ),
        ),
        _endpoints(128),
        _full_run(600),
        _valid_build(),
    ],
    objective=Objective(
        label="Peak worst-link utilization", metric="peakWorstLinkPct",
        direction="minimize", par=70.5, worst=90, unit="%",
        explain_id="ecmp", equation=EQ_ECMP,
    ),
    hints=[
        L(standard="Turn on Explain mode and compare worst link with mean link: the mean is fine, so capacity is not what is missing.",
          novice="Click 'Explain mode' and look at the worst-link and mean-link numbers. The average link is only about 60% full. The fabric has enough capacity; the traffic is just landing unevenly.",
          expert="Mean ≈ 62%, worst ≈ 116%: a placement problem, not a capacity one."),
        L(standard="Static ECMP puts elephants 85% over fair share on the worst link. Adaptive routing keeps 15% of that skew and costs no watts.",
          novice="With ordinary hashing, elephant flows put 85% more than a fair share on the unluckiest link. Adaptive routing watches the queues and moves flows away, leaving only 15% of that unfairness. It is a setting, not a switch, so it uses no extra power.",
          expert="imbalance 0.85 → 0.85 × 0.15 with adaptive; zero added watts."),
        L(standard="The start build is 10,056 W: 6,600 W of ASICs and 192 pluggable optics at 18 W. Co-packaged optics take the optics line to a third.",
          novice="The starting fabric draws 10,056 watts: 6,600 for the twelve switches and the rest for 192 port optics at 18 watts each. Switching Optics to CPO drops each one to 6 watts, which is what brings the total under 8,000.",
          expert="12 × 550 + 192 × 18 = 10,056 W; CPO → 7,752 W."),
        L(standard="With adaptive routing and CPO on, reshape the fabric inside the budget: worst link falls as leaves × spines rises, and 6 × 6 with 22 endpoints per leaf still fits.",
          novice="Once adaptive routing and CPO are on, you can go further. The busiest link gets quieter as leaves times spines gets bigger. Six leaves and six spines with 22 endpoints per leaf still fits under 8,000 watts and spreads the traffic over 36 paths instead of 32.",
          expert="ρ_worst ∝ 1/(L × S); 6 × 6 × 22 fits at 7,824 W."),
    ],
    start=_L1_START.model_dump(by_alias=True),
)


# --- Lab 2: non-blocking with a spine down ---------------------------------

_A2A_40 = Workload(demand_gbps=40000, pattern="alltoall", collective_pct=70)

_L2_START = Scenario(config=SN6000_ADAPTIVE, workload=_A2A_40, duration_s=600)

NON_BLOCKING_MINUS_ONE = Lab(
    id="non-blocking-minus-one",
    title="Non-blocking with a spine down",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "Carry 40,000 Gb/s of all-to-all training traffic while a "
                "spine is dead for most of the run. The fabric must stay "
                "non-blocking (1:1 or better) on the surviving spines, with "
                "the worst link never past 90%. Then minimize the peak "
                "fabric power you had to provision."
            ),
            novice=(
                "A training job sends 40,000 gigabits per second between "
                "every pair of racks at once. Early in the run one spine "
                "switch fails and stays failed. Build a fabric that does not "
                "care: even with that spine gone, each leaf must have at "
                "least as much bandwidth going up as coming in from its "
                "GPUs (that is what 1:1, or non-blocking, means), and the "
                "busiest link must never pass 90% full. After that, use as "
                "little power as you can."
            ),
            expert=(
                "40,000 Gb/s all-to-all, N−1 spines from t ≤ 100 s, "
                "post-failure oversubscription ≤ 1.0, ρ_worst ≤ 0.9; "
                "minimize peak fabric power."
            ),
        ),
        constraints=[
            L(standard="A spine fails by t+100 s and stays failed for at least 500 s.",
              novice="Use 'Kill a spine' within the first 100 seconds and leave that spine dead: it must be down for at least 500 seconds.",
              expert="First spine loss ≤ 100 s; ≥ 500 s degraded."),
            L(standard="Oversubscription on the surviving spines never above 1.0.",
              novice="With the spine dead, each leaf's GPU-side bandwidth divided by its remaining spine-side bandwidth must be 1.0 or less.",
              expert="max over ticks of Σdown/Σup(alive) ≤ 1.0."),
            L(standard="All-to-all traffic for the whole run; worst link never past 90%; nothing dropped, paused or stalled.",
              novice="Keep the Pattern on 'All-to-all', never let the busiest link pass 90% full, and let no traffic be thrown away or told to wait.",
              expert="Pattern = alltoall; ρ_worst ≤ 0.9; zero damage ticks."),
            L(standard="At least 128 endpoints, a 600 s run, no configuration errors.",
              novice="Keep at least 128 GPU connections, keep the 600-second run, and have no red errors in the Configuration rules.",
              expert="≥128 endpoints, ≥600 s, zero errors."),
        ],
        delivered_work=L(
            standard="At least 40,000 Gb/s of goodput, averaged over the run, failure included.",
            novice="On average at least 40,000 gigabits per second must actually arrive, and the seconds after the spine dies count too.",
            expert="goodputRateGbps ≥ 40,000 across the failure.",
        ),
    ),
    criteria=[
        _goodput(40000),
        _pattern("alltoallPct", "all-to-all", "all-to-all flows",
                 "All-to-all traffic for the whole run"),
        Criterion(
            id="spine-fails-early", label="A spine fails by t+100 s",
            metric="firstSpineLossS", op="<=", threshold=100, unit="s",
            explain_id="ecmp", equation=EQ_ECMP,
            why=L(
                standard=(
                    "Fair share is demand ÷ (leaves × surviving spines), so "
                    "a spine loss raises every remaining link at once. The "
                    "lab grades the fabric in that state; the first second "
                    "with fewer spines alive than configured must come by "
                    "t+100 s. A fabric with one spine cannot lose it, and "
                    "reads as never failed."
                ),
                novice=(
                    "Each link's fair share of the traffic is the demand "
                    "divided by leaves times the spines that are still "
                    "alive. Lose a spine and every other link gets busier "
                    "at the same moment. This lab is about that moment, so "
                    "you have to cause it: press 'Kill a spine' in the "
                    "first 100 seconds. If the fabric has only one spine "
                    "the button does nothing, and the lab treats that as "
                    "no failure at all."
                ),
                expert="fair = D/(L × S_alive); first tick with S_alive < S at t ≤ 100 s.",
            ),
        ),
        Criterion(
            id="spine-stays-down", label="The spine stays down at least 500 s",
            metric="spineDownSeconds", op=">=", threshold=500, unit="s",
            explain_id="ecmp", equation=EQ_ECMP,
            why=L(
                standard=(
                    "Replacing a spine is a truck roll, not a toggle. The "
                    "fabric has to carry the job degraded for at least "
                    "500 s, so a failure at the last tick or a quick "
                    "restore does not count."
                ),
                novice=(
                    "In a real data center a dead spine switch is not "
                    "back in a minute; someone has to come and replace it. "
                    "So the spine has to stay dead for at least 500 "
                    "seconds of the run. Killing it in the last second, or "
                    "bringing it straight back, does not count."
                ),
                expert="Σ ticks with S_alive < S ≥ 500.",
            ),
        ),
        Criterion(
            id="non-blocking", label="Oversubscription on survivors at most 1.0",
            metric="worstOversubRatio", op="<=", threshold=1.0, unit=": 1",
            weight=2.0, explain_id="oversub", equation=EQ_OVERSUB,
            why=L(
                standard=(
                    "The ratio is endpoints × downlink over surviving "
                    "spines × uplink, per leaf, taken at its worst second. "
                    "At 16 endpoints of 400 G per leaf, 1:1 after a loss "
                    "needs nine spines and the chassis offers eight, so the "
                    "downlink side has to be spread over more leaves. The "
                    "Oversubscription instrument shows the as-built ratio; "
                    "this line recomputes it on the survivors."
                ),
                novice=(
                    "Oversubscription compares what can come into a leaf "
                    "switch from its GPUs with what can leave it toward the "
                    "spines. This line uses the spines that are still "
                    "alive, at the worst second of the run, and the answer "
                    "must be 1.0 or less. With 16 GPUs at 400 gigabits on "
                    "each leaf you would need nine spines to get there "
                    "after one dies, and the slider stops at eight. The way "
                    "out is fewer GPUs per leaf and more leaves. Note that "
                    "the Oversubscription gauge on the page shows the ratio "
                    "as built, with every spine counted."
                ),
                expert="max_t E × 400 / (S_alive × uplink) ≤ 1.0 ⇒ E ≤ 2 × (S − 1) at 800 G.",
            ),
        ),
        _below_knee(),
        _no_damage(),
        _endpoints(128),
        _full_run(600),
        _valid_build(),
    ],
    objective=Objective(
        label="Peak fabric power", metric="peakFabricPowerW",
        direction="minimize", par=11640, worst=13300, unit="W",
        explain_id="optics-power", equation=EQ_OPTICS,
    ),
    hints=[
        L(standard="Kill a spine on the start build and read the validation panel: 40,000 Gb/s does not fit a 25,600 Gb/s bisection even before the failure.",
          novice="Press 'Kill a spine' on the starting fabric and read the Configuration rules. The fabric can carry 25,600 gigabits per second at best, and you are asking for 40,000. It was too small before anything broke.",
          expert="Bisection 25,600 < 40,000 before the loss."),
        L(standard="Size for the survivors. Non-blocking after a loss means endpoints per leaf ≤ 2 × (spines − 1) at 400 G down and 800 G up.",
          novice="Plan for the spines that are left, not the spines you bought. Each GPU port is 400 gigabits and each spine link is 800, so after one spine dies a leaf can have at most twice as many GPUs as it has surviving spines.",
          expert="E ≤ 2 × (S − 1)."),
        L(standard="128 endpoints then need leaves ≥ 128 ÷ endpoints per leaf. More spines allow fatter leaves and fewer of them; every switch is 550 W, so the cheapest shape is in the middle, not at either end.",
          novice="You still need 128 GPUs in total, so fewer GPUs per leaf means more leaves. More spines let each leaf hold more GPUs, so you need fewer leaves. Every switch costs 550 watts either way. Try a few shapes: the cheapest one is neither the most spines nor the most leaves.",
          expert="Minimize (L + S) × 550 + ports × optic subject to E ≤ 2(S − 1), L × E ≥ 128."),
        L(standard="Seven spines, eleven leaves of 12 endpoints, adaptive routing and CPO: 1.0 : 1 on six survivors, worst link about 81%, 11,616 W.",
          novice="One good answer: 7 spines, 11 leaves with 12 endpoints each, adaptive routing on and CPO optics. With one spine dead that is exactly 1.0 to 1, the busiest link sits near 81%, and the fabric peaks at 11,616 watts.",
          expert="S = 7, L = 11, E = 12, AR + CPO: 1.0 : 1, ρ ≈ 0.81, 11,616 W."),
    ],
    start=_L2_START.model_dump(by_alias=True),
)


# --- Lab 3: all-reduce past a gray failure ---------------------------------

_TRAIN_20 = Workload(demand_gbps=20000, pattern="alltoall", collective_pct=70)

_L3_START = Scenario(config=SN6000_ADAPTIVE, workload=_TRAIN_20, duration_s=600)

COLLECTIVES_PAST_A_LIAR = Lab(
    id="collectives-past-a-liar",
    title="All-reduce past a gray failure",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "With at most twelve switches and a gray failure active "
                "for most of the run, deliver an effective all-reduce rate "
                "of 25,000 Gb/s alongside 6,000 Gb/s of other traffic, with "
                "the worst link never past 90%. Then maximize the "
                "all-reduce rate."
            ),
            novice=(
                "A training job needs two things from the network at once: "
                "its GPUs must add their numbers together (all-reduce) at "
                "an effective 25,000 gigabits per second, and 6,000 "
                "gigabits per second of other traffic, such as loading "
                "data and saving checkpoints, must keep flowing. You may "
                "use at most twelve switches. One link is quietly faulty "
                "for most of the run and nothing will warn you. Keep the "
                "busiest link under 90% full, hit both targets, and then "
                "push the all-reduce rate as high as you can."
            ),
            expert=(
                "≤ 12 ASICs, gray failure from t ≤ 100 s, all-reduce ≥ "
                "25,000 Gb/s and non-collective goodput ≥ 6,000 Gb/s, "
                "ρ_worst ≤ 0.9; maximize all-reduce."
            ),
        ),
        constraints=[
            L(standard="A gray failure starts by t+100 s and is active for at least 500 s.",
              novice="Press 'Start a gray failure' within the first 100 seconds. It must be active for at least 500 seconds.",
              expert="Gray onset ≤ 100 s; ≥ 500 s active."),
            L(standard="ASIC power no higher than 6,600 W: twelve switches at most.",
              novice="Spines plus leaves must be 12 or fewer. The lab checks this as switch-chip power: 12 switches at 550 watts is 6,600 watts.",
              expert="max(P_asic) ≤ 6,600 W ⇒ L + S ≤ 12."),
            L(standard="Worst link never past 90%; nothing dropped, paused or stalled.",
              novice="The busiest link must never pass 90% full, and no traffic may be thrown away or told to wait.",
              expert="ρ_worst ≤ 0.9; zero damage ticks."),
            L(standard="At least 128 endpoints, a 600 s run, no configuration errors.",
              novice="Keep at least 128 GPU connections, keep the 600-second run, and have no red errors in the Configuration rules.",
              expert="≥128 endpoints, ≥600 s, zero errors."),
        ],
        delivered_work=L(
            standard="An effective all-reduce rate of at least 25,000 Gb/s and at least 6,000 Gb/s of non-collective goodput, both averaged over the run.",
            novice="On average the all-reduce rate must be at least 25,000 gigabits per second and the other traffic at least 6,000. Both are averages over every second, so an idle fabric earns nothing.",
            expert="allreduceRateGbps ≥ 25,000 ∧ otherGoodputGbps ≥ 6,000.",
        ),
    ),
    criteria=[
        Criterion(
            id="allreduce", label="Effective all-reduce at least 25,000 Gb/s",
            metric="allreduceRateGbps", op=">=", threshold=25000, unit="Gb/s",
            weight=2.0, guards_work=True, explain_id="sharp", equation=EQ_SHARP,
            why=L(
                standard=(
                    "The all-reduce rate is delivered Gb/s × collective "
                    "share, × 1.8 when SHARP reduces in the switches, "
                    "averaged over the run. On twelve Ethernet switches the "
                    "links run out near 16,500 Gb/s of it. SHARP also takes "
                    "half the collective bytes off the links, so the same "
                    "twelve switches carry more demand. Figures are the "
                    "model's estimates."
                ),
                novice=(
                    "All-reduce is the step where GPUs add their numbers "
                    "together. Its rate here is the traffic that arrives, "
                    "times the share of it that is all-reduce, averaged "
                    "over the run. On an Ethernet fabric of twelve switches "
                    "the links fill up at about 16,500, well short of "
                    "25,000. InfiniBand's SHARP feature lets the switches "
                    "do the adding: the rate counts 1.8 times over, and "
                    "half of those bytes never touch the links, so there is "
                    "room to offer more. These are estimates in this model."
                ),
                expert="mean(delivered × c × 1.8·[SHARP]) ≥ 25,000; links carry D × (1 − 0.5c).",
            ),
        ),
        Criterion(
            id="other-traffic", label="Other traffic at least 6,000 Gb/s",
            metric="otherGoodputGbps", op=">=", threshold=6000, unit="Gb/s",
            weight=2.0, guards_work=True, explain_id="gray-failure", equation=EQ_GRAY,
            why=L(
                standard=(
                    "Non-collective goodput is delivered Gb/s × (1 − "
                    "collective share): data loading and checkpoints. It "
                    "stops the collective share being pushed to 100%, and "
                    "it is where the gray failure shows: 20,000 Gb/s at 70% "
                    "collective offers exactly 6,000, and a silent 35% ÷ "
                    "leaves tax takes it below."
                ),
                novice=(
                    "Not all traffic is all-reduce. The rest, such as "
                    "reading training data and saving checkpoints, must "
                    "still get at least 6,000 gigabits per second. That "
                    "stops you setting the Collective share slider to 100%. "
                    "It is also where the faulty link bites: 20,000 offered "
                    "at 70% collective leaves exactly 6,000 for the rest, "
                    "and the gray failure quietly takes 35% divided by the "
                    "number of leaves off everything that arrives."
                ),
                expert="mean(delivered × (1 − c)) ≥ 6,000; the 35%/L tax applies.",
            ),
        ),
        Criterion(
            id="gray-starts-early", label="A gray failure starts by t+100 s",
            metric="firstGrayS", op="<=", threshold=100, unit="s",
            explain_id="gray-failure", equation=EQ_GRAY,
            why=L(
                standard=(
                    "The lab is about a fabric whose status is green and "
                    "whose goodput is wrong. The first second with a "
                    "goodput penalty must come by t+100 s. An idle fabric "
                    "shows no penalty, so the failure has to land on live "
                    "traffic."
                ),
                novice=(
                    "This lab is about a network that says it is healthy "
                    "and is not. You have to start the fault yourself: "
                    "press 'Start a gray failure' within the first 100 "
                    "seconds. It only shows up when there is traffic to "
                    "hurt, so the fabric must be busy when you press it."
                ),
                expert="First tick with goodput penalty > 0 at t ≤ 100 s.",
            ),
        ),
        Criterion(
            id="gray-persists", label="The gray failure lasts at least 500 s",
            metric="graySeconds", op=">=", threshold=500, unit="s",
            explain_id="gray-failure", equation=EQ_GRAY,
            why=L(
                standard=(
                    "Nothing alarms on a gray link, so nothing gets it "
                    "replaced quickly. The job has to meet its targets "
                    "with the tax in place for at least 500 s."
                ),
                novice=(
                    "Because no alarm goes off, nobody comes to fix a gray "
                    "failure quickly. The fault has to be active for at "
                    "least 500 seconds, and your targets have to be met "
                    "anyway."
                ),
                expert="Σ ticks with penalty > 0 ≥ 500.",
            ),
        ),
        Criterion(
            id="switch-budget", label="ASIC power at most 6,600 W (12 switches)",
            metric="peakAsicPowerW", op="<=", threshold=6600, unit="W",
            weight=2.0, explain_id="optics-power", equation=EQ_OPTICS,
            why=L(
                standard=(
                    "P_asic is 550 W per switch (an estimate), so 6,600 W "
                    "is twelve switches. It is set on the ASIC line rather "
                    "than total power so that the InfiniBand build, which "
                    "has no co-packaged option here, is not judged on its "
                    "optics."
                ),
                novice=(
                    "Each switch chip draws about 550 watts in this model, "
                    "so a limit of 6,600 watts means twelve switches: "
                    "spines plus leaves must be 12 or fewer. The limit is "
                    "on the switch chips only, not on the port optics, so "
                    "that choosing InfiniBand (which has no low-power "
                    "optics option in this app) is not punished for it."
                ),
                expert="max(P_asic) ≤ 12 × 550 W; optics excluded on purpose.",
            ),
        ),
        _below_knee(),
        _no_damage(),
        _endpoints(128),
        _full_run(600),
        _valid_build(),
    ],
    objective=Objective(
        label="Effective all-reduce rate", metric="allreduceRateGbps",
        direction="maximize", par=35000, worst=25000, unit="Gb/s",
        explain_id="sharp", equation=EQ_SHARP,
    ),
    hints=[
        L(standard="Start the gray failure on the start build and read the instruments: status stays green, and both rates fall short of what the sliders offered.",
          novice="Press 'Start a gray failure' on the starting fabric and look at the instruments. Every status light stays green. But the all-reduce rate and the delivered traffic are both lower than what the sliders asked for.",
          expert="Green status, goodput × (1 − 0.35/8)."),
        L(standard="On twelve Ethernet switches all-reduce tops out near 16,500 Gb/s whatever the sliders say. The target needs the fabric that reduces in the network: Quantum-X800 with SHARP on.",
          novice="With Ethernet and only twelve switches, no slider setting gets all-reduce past about 16,500. The target needs switches that do the adding themselves. Change Fabric to Quantum-X800 and make sure SHARP collectives is on.",
          expert="Ethernet ceiling ≈ 16,500 at L + S ≤ 12; x800 + SHARP required."),
        L(standard="The gray link taxes 35% ÷ leaves of everything delivered, so offering exactly the target falls short. Offer more, and check the worst link: with SHARP it carries demand × (1 − 0.5 × collective share) × 1.5 ÷ (leaves × spines).",
          novice="The faulty link takes 35% divided by the number of leaves off everything that arrives. If you offer exactly what you need, you end up short, so raise Demand. Then check the busiest link: with SHARP on, only part of the traffic rides the links, and the busiest link carries about one and a half times its fair share.",
          expert="Offer D/(1 − 0.35/L); ρ_worst = D(1 − 0.5c) × 1.5/(L × S × 800)."),
        L(standard="Raising the collective share helps twice: more all-reduce and fewer link bytes. Six leaves of 22 and six spines give 36 paths from twelve switches; about 28,000 Gb/s at 77% collective keeps the other traffic just above 6,000.",
          novice="Moving the Collective share slider up helps in two ways: more of the traffic is all-reduce, and SHARP takes more bytes off the links. The limit is the other traffic, which must stay above 6,000. Six leaves with 22 endpoints each and six spines give 36 paths from twelve switches. About 28,000 of demand at 77% collective just fits.",
          expert="6 × 6 × 22, D = 28,000, c = 77%: all-reduce ≈ 36,800, other ≈ 6,100."),
    ],
    start=_L3_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [ELEPHANTS_ON_A_BUDGET, NON_BLOCKING_MINUS_ONE, COLLECTIVES_PAST_A_LIAR]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Reference solutions and the tricks that must not work -----------------
# Server-side only: GET /api/labs serves LABS, never these.

_AR_CPO = SN6000_STATIC.model_copy(update={"adaptive_routing": True, "cpo_optics": True})
_N_MINUS_1 = _AR_CPO.model_copy(update={"spines": 7, "leaves": 11, "endpoints_per_leaf": 12})
_SHARP_6X6 = X800_FABRIC.model_copy(update={"spines": 6, "leaves": 6, "endpoints_per_leaf": 22})
_KILL_SPINE = [SimEvent(at_s=60, action="kill-spine")]
_GRAY = [SimEvent(at_s=60, action="gray-failure")]
_IDLE = Workload(demand_gbps=0)
_TRAIN_28 = Workload(demand_gbps=28000, pattern="alltoall", collective_pct=77)

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "elephants-on-a-budget": Scenario(
        config=_AR_CPO, workload=_ELEPHANTS_16, duration_s=600),
    "non-blocking-minus-one": Scenario(
        config=_N_MINUS_1, workload=_A2A_40, events=_KILL_SPINE, duration_s=600),
    "collectives-past-a-liar": Scenario(
        config=_SHARP_6X6, workload=_TRAIN_28, events=_GRAY, duration_s=600),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "elephants-on-a-budget": {
        "zero load": Scenario(config=_AR_CPO, workload=_IDLE, duration_s=600),
        "a gentler pattern": Scenario(
            config=_AR_CPO,
            workload=Workload(demand_gbps=16000, pattern="uniform"),
            duration_s=600),
        "brute-force spines": Scenario(
            config=SN6000_STATIC.model_copy(update={"spines": 8, "cpo_optics": True}),
            workload=_ELEPHANTS_16, duration_s=600),
        "adaptive routing without CPO": Scenario(
            config=SN6000_ADAPTIVE, workload=_ELEPHANTS_16, duration_s=600),
        "unplug the endpoints": Scenario(
            config=_AR_CPO.model_copy(update={"endpoints_per_leaf": 4}),
            workload=_ELEPHANTS_16, duration_s=600),
        "long run at low load": Scenario(
            config=_AR_CPO,
            workload=Workload(demand_gbps=2000, pattern="elephant"),
            duration_s=3600),
        "short run": Scenario(config=_AR_CPO, workload=_ELEPHANTS_16, duration_s=30),
        "idle first, elephants later": Scenario(
            config=_AR_CPO, workload=_IDLE, duration_s=600,
            events=[SimEvent(at_s=500, action="set-workload", workload=_ELEPHANTS_16)]),
    },
    "non-blocking-minus-one": {
        "zero load": Scenario(
            config=_N_MINUS_1, workload=_IDLE, events=_KILL_SPINE, duration_s=600),
        "no spine failure": Scenario(
            config=_N_MINUS_1, workload=_A2A_40, duration_s=600),
        "restore the spine": Scenario(
            config=_N_MINUS_1, workload=_A2A_40, duration_s=600,
            events=_KILL_SPINE + [SimEvent(at_s=61, action="restore-spine")]),
        "kill the spine at the end": Scenario(
            config=_N_MINUS_1, workload=_A2A_40, duration_s=600,
            events=[SimEvent(at_s=599, action="kill-spine")]),
        "sized for the spines you bought": Scenario(
            config=_AR_CPO.model_copy(update={
                "spines": 8, "leaves": 8, "endpoints_per_leaf": 16}),
            workload=_A2A_40, events=_KILL_SPINE, duration_s=600),
        "static hashing": Scenario(
            config=_N_MINUS_1.model_copy(update={"adaptive_routing": False}),
            workload=_A2A_40, events=_KILL_SPINE, duration_s=600),
        "half the endpoints": Scenario(
            config=_N_MINUS_1.model_copy(update={"endpoints_per_leaf": 6}),
            workload=_A2A_40, events=_KILL_SPINE, duration_s=600),
        "a gentler pattern": Scenario(
            config=_N_MINUS_1,
            workload=Workload(demand_gbps=40000, pattern="uniform", collective_pct=70),
            events=_KILL_SPINE, duration_s=600),
        "long run at low load": Scenario(
            config=_N_MINUS_1,
            workload=Workload(demand_gbps=4000, pattern="alltoall", collective_pct=70),
            events=_KILL_SPINE, duration_s=3600),
    },
    "collectives-past-a-liar": {
        "zero load": Scenario(
            config=_SHARP_6X6, workload=_IDLE, events=_GRAY, duration_s=600),
        "no gray failure": Scenario(
            config=_SHARP_6X6, workload=_TRAIN_28, duration_s=600),
        "replace the gray link at once": Scenario(
            config=_SHARP_6X6, workload=_TRAIN_28, duration_s=600,
            events=_GRAY + [SimEvent(at_s=61, action="clear-gray")]),
        "gray failure at the end": Scenario(
            config=_SHARP_6X6, workload=_TRAIN_28, duration_s=600,
            events=[SimEvent(at_s=599, action="gray-failure")]),
        "offer exactly the target": Scenario(
            config=X800_FABRIC, workload=_TRAIN_20, events=_GRAY, duration_s=600),
        "all collective, no other traffic": Scenario(
            config=_SHARP_6X6,
            workload=Workload(demand_gbps=40000, pattern="alltoall", collective_pct=100),
            events=_GRAY, duration_s=600),
        "ethernet, more switches": Scenario(
            config=_AR_CPO.model_copy(update={"spines": 8, "leaves": 8}),
            workload=Workload(demand_gbps=42500, pattern="alltoall", collective_pct=85),
            events=_GRAY, duration_s=600),
        "infiniband without SHARP": Scenario(
            config=_SHARP_6X6.model_copy(update={"sharp": False}),
            workload=_TRAIN_28, events=_GRAY, duration_s=600),
        "short run": Scenario(
            config=_SHARP_6X6, workload=_TRAIN_28, 
            events=[SimEvent(at_s=1, action="gray-failure")], duration_s=30),
    },
}


# --- Grading ----------------------------------------------------------------

def grade_scenario(lab_id: str, scenario: Scenario) -> LabResult:
    """Run the engine on the learner's scenario and grade the trace.

    Pure and deterministic: no state is kept between calls, and the same
    scenario always earns the same result. Raises ``KeyError`` for an
    unknown lab id (``main.py`` turns that into a 404).
    """
    lab = LABS_BY_ID[lab_id]
    trace, _log, summary = simulate(scenario)
    metrics = measure(scenario, trace, summary, validate(scenario))
    return grade(lab, metrics)
