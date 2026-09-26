"""Graded labs for the fleet-operations simulator (``docs/LAB_PATTERN.md``).

A guided scenario sets the dials and narrates. A lab states a goal and leaves
the dials to you: build a Scenario with the ordinary controls, the engine runs
it, and ``grade_scenario`` scores the trace.

Pure module, same rule as ``engine.py``: no FastAPI, no IO, no clock, no
randomness (AST-checked in ``tests/test_labs.py``). ``main.py`` is the only
caller that touches HTTP, so the static-hosting build runs this same grading
in the browser.

What is this app's own here (everything else is ``twinkit.labs``):

* ``measure()`` — one run as named numbers. The un-gameable one is
  ``workVms``: VMs actually served, averaged over every day of the run. A VM
  is served only if demand asked for it, installed nodes that are up can host
  it, and (on APEX) the base+buffer ceiling admits it. An empty fleet serves
  nothing; an undersized one serves only what fits. It is an illustrative
  proxy for useful output, not a benchmark, and is labeled so.
* ``LABS`` — three labs of rising difficulty, the engine's acceptance
  scenarios turned into problems with a twist: the 3-node trap on an estate
  that *grows*, the automation gap pushed until automation itself hits the
  16 h/day ceiling, and the APEX commitment sized against a spike that is
  bigger at the end of the run than at the start.
* ``REFERENCE_SOLUTIONS`` / ``GAMING_ATTEMPTS`` — a scenario that passes each
  lab and the cheap tricks that must not. Server-side only.
"""

from __future__ import annotations

from twinkit.labs import Criterion, Lab, LabGoal, LabResult, Objective, grade

from .constants import value as C
from .engine import simulate
from .leveling import L
from .models import (
    FleetConfig,
    Scenario,
    SimEvent,
    SimState,
    Summary,
    Validation,
    Workload,
)
from .presets import APEX_SPIKY, VXRAIL_3NODE
from .validation import validate

# The equations, exactly as the Explain entries display them.
EQ_HOURS = "Σ actions × cost(action, ops_mode);  capacity = 16 h/day, excess backlogs"
EQ_N1 = "fault → failover iff (survivors ≥ 1 node) ∧ (capacity ≥ demand) ∧ (down ≤ FTT)"
EQ_AVAIL = "availability = 1 − outage-minutes / (site-days × 1440)"
EQ_APEX = "bill = base + 1.5 × overage;  vs capex = capacity × amortized rate"

NO_FAULT_D = 9999.0   # "first fault day" when no fault ever landed


# --- Measurement ----------------------------------------------------------

def measure(
    scenario: Scenario,
    trace: list[SimState],
    summary: Summary,
    validations: list[Validation],
) -> dict[str, float]:
    """One run as named numbers. Keys are the wire names criteria refer to."""
    cfg = scenario.config
    n = len(trace)
    apex = cfg.product == "apex"
    buffer_cap = cfg.committed_vms * (1.0 + cfg.buffer_pct / 100.0)

    served_sum = 0.0
    short_days = 0
    unprotected = 0
    fault_days: list[int] = []
    bill_sum = 0.0
    prev_faults = 0
    served_last = 0.0
    for s in trace:
        ceiling = float(s.capacity_vms)
        if apex:
            ceiling = min(ceiling, buffer_cap)
        served = min(float(s.vms_running), ceiling)
        served_sum += served
        served_last = served
        if s.vms_demand > ceiling:
            short_days += 1
        landed = s.faults_cum > prev_faults
        if landed:
            fault_days.append(s.t_d)
        # The day a fault lands is always exposed; what a design controls is
        # whether the window is still open on the days after.
        if s.exposure and not landed:
            unprotected += 1
        prev_faults = s.faults_cum
        bill_sum += s.monthly_bill / 30.0

    demands = [float(s.vms_demand) for s in trace]
    mean_demand = sum(demands) / n
    hard_outage = summary.outage_minutes - C("ha_failover_minutes") * summary.faults
    return {
        "durationD": float(trace[-1].t_d),
        "workVms": round(served_sum / n, 1),
        "finalVmsServed": round(served_last, 1),
        "faults": float(summary.faults),
        "firstFaultD": float(fault_days[0]) if fault_days else NO_FAULT_D,
        "lastFaultD": float(fault_days[-1]) if fault_days else -1.0,
        "hardOutageMinutes": round(max(0.0, hard_outage), 1),
        "unprotectedDays": float(unprotected),
        "capacityShortDays": float(short_days),
        "vsanCluster": 1.0 if cfg.product == "vxrail" else 0.0,
        "nodesTotal": float(max(s.nodes_total for s in trace)),
        "meanVersionCurrentPct": round(
            sum(s.version_current_pct for s in trace) / n, 2
        ),
        "adminHoursTotal": float(summary.admin_hours_total),
        "truckRolls": float(summary.truck_rolls),
        "peakToMeanDemand": round(max(demands) / mean_demand, 3) if mean_demand else 0.0,
        "costPerKVmHour": round(
            1000.0 * bill_sum / (served_sum * 24.0), 3
        ) if served_sum else 9999.0,
        "validationErrors": float(sum(1 for v in validations if v.level == "error")),
    }


# --- Criteria shared between labs ------------------------------------------

def _work(floor: int, explain_id: str, equation: str) -> Criterion:
    return Criterion(
        id="work", label=f"At least {floor} VMs served on average",
        metric="workVms", op=">=", threshold=floor, unit="VMs",
        weight=2.0, guards_work=True, explain_id=explain_id, equation=equation,
        why=L(
            standard=(
                f"Work is VMs actually served, averaged over every day of the "
                f"run; {floor} is the floor. A VM counts only when demand asks "
                "for it and running nodes (and, on APEX, base+buffer) can host "
                "it, so shrinking the estate or starving it is not a way "
                "through. The proxy is illustrative, not a benchmark."
            ),
            novice=(
                f"The fleet has to do real work the whole time: on an average "
                f"day at least {floor} virtual machines (VMs — the software "
                "computers your servers host) must actually be running. A VM "
                "only counts if somebody wanted it AND there was a healthy "
                "server with room for it. So you cannot win by making the "
                "estate tiny, and you cannot win by asking for more than the "
                "servers can hold. This is a simple stand-in for useful "
                "output, not a real benchmark."
            ),
            expert=(
                f"Mean over all days of min(demand, healthy capacity, APEX "
                f"ceiling) ≥ {floor} VMs. Illustrative proxy."
            ),
        ),
    )


def _full_run(days: int, explain_id: str, equation: str) -> Criterion:
    return Criterion(
        id="full-run", label=f"Run lasts at least {days} days",
        metric="durationD", op=">=", threshold=days, unit="days",
        explain_id=explain_id, equation=equation,
        why=L(
            standard=(
                f"Fleet effects are slow: update waves arrive every 30 days "
                f"and growth compounds daily. A run shorter than {days} days "
                "would be graded before the thing it is graded on had happened."
            ),
            novice=(
                f"Things happen slowly in a fleet. Software updates arrive "
                f"once a month, and demand grows a little every day. If the "
                f"run were shorter than {days} days it would end before the "
                "hard part arrived, so the lab needs the full length it "
                "starts with."
            ),
            expert=f"durationD ≥ {days}: spans the update waves and the compounding.",
        ),
    )


def _no_hard_outage() -> Criterion:
    return Criterion(
        id="no-hard-outage", label="No outage beyond 2-minute failovers",
        metric="hardOutageMinutes", op="<=", threshold=0, unit="min", weight=2.0,
        explain_id="availability", equation=EQ_AVAIL,
        why=L(
            standard=(
                "Every fault costs 2 minutes when survivors can restart its "
                "VMs. Anything above that — 240 minutes for a fault with no "
                "headroom, 120 for a capacity shortfall — is an outage a "
                "design choice caused. This line is outage minutes minus "
                "2 × faults, and it must be zero."
            ),
            novice=(
                "When a server dies, its VMs restart on the other servers in "
                "about 2 minutes — if the others have room. That small "
                "hiccup is allowed. What is not allowed is the big outage: "
                "240 minutes when a server dies and there is nowhere for its "
                "VMs to go, or 120 minutes when demand simply outgrows the "
                "fleet. This line takes all outage minutes, subtracts "
                "2 minutes per fault, and needs the answer to be zero."
            ),
            expert="outage − 2 min × faults ≤ 0: failovers only, no 240s or 120s.",
        ),
    )


def _never_short(explain_id: str, equation: str) -> Criterion:
    return Criterion(
        id="never-short", label="Demand never exceeds what can be served",
        metric="capacityShortDays", op="<=", threshold=0, unit="days", weight=2.0,
        explain_id=explain_id, equation=equation,
        why=L(
            standard=(
                "Counts the days demand sat above the serving ceiling — the "
                "healthy nodes' capacity and, on APEX, base × (1 + buffer). "
                "Growth moves demand every day; the ceiling only moves when "
                "you move it."
            ),
            novice=(
                "This counts the days when people wanted more VMs than the "
                "fleet could run. The limit is how many VMs your healthy "
                "servers can hold — and, if you are renting capacity (APEX), "
                "also the most the contract lets you use: the committed base "
                "plus the buffer. Demand creeps up every day when growth is "
                "on. The limit stays where you put it."
            ),
            expert="days with demand > min(healthy capacity, base×(1+buffer)) = 0.",
        ),
    )


def _valid_build() -> Criterion:
    return Criterion(
        id="valid-build", label="Build has no configuration errors",
        metric="validationErrors", op="<=", threshold=0, unit="errors",
        explain_id="n-plus-one", equation=EQ_N1,
        why=L(
            standard=(
                "The configuration rules flag a fleet whose day-one demand "
                "already exceeds installed capacity as an error. Warnings are "
                "allowed; a fleet that is undersized before anything fails "
                "is not."
            ),
            novice=(
                "The 'Configuration rules' panel checks your build. A red "
                "error means the fleet cannot even hold its VMs on the first "
                "day, before anything has gone wrong. Yellow warnings are "
                "fine — they are advice — but red errors are not."
            ),
            expert="Zero error-level rule findings (day-0 demand ≤ installed capacity).",
        ),
    )


# --- Lab 1: the fourth node is not enough ----------------------------------

_GROWING = Workload(vms_per_site=24, growth_pct_month=5, vm_size_capacity=10)
_TWO_FAULTS = [
    SimEvent(at_d=20, action="node-fault"),
    SimEvent(at_d=150, action="node-fault"),
]

_HEADROOM_START = Scenario(
    config=VXRAIL_3NODE, workload=_GROWING, duration_d=180, events=_TWO_FAULTS,
)

HEADROOM = Lab(
    id="headroom-for-the-last-day",
    title="Headroom for the last day",
    difficulty=1,
    goal=LabGoal(
        statement=L(
            standard=(
                "A VxRail cluster hosts 24 VMs growing 5% a month, and takes "
                "a node fault on day 20 and another on day 150. Size the "
                "cluster so both faults are 2-minute failovers with no open "
                "protection window — using as few nodes as you can."
            ),
            novice=(
                "You run one VxRail cluster (a group of servers that pool "
                "their disks and share the work). It hosts 24 VMs today and "
                "grows 5% every month. One server will fail on day 20 and "
                "another on day 150. Choose how many servers (nodes) to buy "
                "so that both failures are only 2-minute hiccups, and the "
                "data is never left without a spare copy after the day of "
                "the failure. Fewer nodes scores higher — but only once "
                "everything passes."
            ),
            expert=(
                "VxRail, 24 VMs +5%/mo, faults at d20 and d150. Both must "
                "fail over, no standing exposure, minimum nodes."
            ),
        ),
        constraints=[
            L(standard="A VxRail (vSAN) cluster, run for 180 days.",
              novice="Keep the product set to VxRail, and keep the 180-day run the lab starts with.",
              expert="product = vxrail, 180 d."),
            L(standard="One fault on or before day 30 and one on or after day 150.",
              novice="A server must fail early (day 30 or sooner) and another late (day 150 or later). The lab starts with both failures already scheduled; if you press Reset they disappear, so use 'Reset to the lab's start' instead.",
              expert="firstFaultD ≤ 30, lastFaultD ≥ 150."),
            L(standard="The estate still serves at least 32 VMs on the last day.",
              novice="The estate must really grow: on the final day at least 32 VMs must be running. Turning the growth off is not allowed.",
              expert="finalVmsServed ≥ 32."),
            L(standard="No outage beyond failovers, no unprotected days, never short of capacity.",
              novice="No big outages (only the 2-minute hiccups), no days where the data has no spare copy after the failure day, and never more VMs wanted than the healthy servers can hold.",
              expert="hard outage 0, exposure beyond fault day 0, short days 0."),
        ],
        delivered_work=L(
            standard="At least 27 VMs served, averaged over the run.",
            novice="On an average day at least 27 VMs must actually be running. A shrunken estate does not count.",
            expert="workVms ≥ 27.",
        ),
    ),
    criteria=[
        _work(27, "n-plus-one", EQ_N1),
        Criterion(
            id="grown", label="At least 32 VMs served on the last day",
            metric="finalVmsServed", op=">=", threshold=32, unit="VMs",
            explain_id="n-plus-one", equation=EQ_N1,
            why=L(
                standard=(
                    "24 VMs at 5% a month is about 32 by day 180. The "
                    "'capacity ≥ demand' term is evaluated on the day the "
                    "fault lands, with that day's demand — so the estate has "
                    "to actually grow for the late fault to mean anything."
                ),
                novice=(
                    "24 VMs growing 5% a month becomes about 32 VMs by day "
                    "180. The lab is about the late failure, when the estate "
                    "is bigger than it was at the start. If you switch growth "
                    "off, the late failure is as easy as the early one, so "
                    "the lab checks that at least 32 VMs are running on the "
                    "last day."
                ),
                expert="Demand must reach 32 VMs; the capacity term uses fault-day demand.",
            ),
        ),
        Criterion(
            id="early-fault", label="A fault lands on or before day 30",
            metric="firstFaultD", op="<=", threshold=30, unit="day",
            explain_id="n-plus-one", equation=EQ_N1,
            why=L(
                standard="The early fault tests the cluster while demand is small. Without a fault, headroom is never tested at all.",
                novice="Spare capacity only matters when something breaks. A server must fail on day 30 or earlier, while the estate is still small — use the 'Fault a node' button, or keep the one the lab starts with.",
                expert="firstFaultD ≤ 30; no fault = 9999.",
            ),
        ),
        Criterion(
            id="late-fault", label="A fault lands on or after day 150",
            metric="lastFaultD", op=">=", threshold=150, unit="day",
            explain_id="n-plus-one", equation=EQ_N1,
            why=L(
                standard="The late fault is the one that matters: by day 150 demand has grown about 28%, and the survivors have to hold all of it.",
                novice="A second server must fail on day 150 or later. By then the estate has grown by more than a quarter, so the servers that are left have much more to carry than they did on day 20.",
                expert="lastFaultD ≥ 150: the same fault against +28% demand.",
            ),
        ),
        _no_hard_outage(),
        Criterion(
            id="protected", label="No unprotected days after a fault lands",
            metric="unprotectedDays", op="<=", threshold=0, unit="days", weight=2.0,
            explain_id="n-plus-one", equation=EQ_N1,
            why=L(
                standard=(
                    "vSAN re-protects a lost node's data the day it fails if "
                    "a rebuild target exists: FTT=n needs 2n+1 hosts still "
                    "standing. Three nodes at FTT=1 leaves two, so the window "
                    "stays open for the 3-day repair. Raising FTT raises the "
                    "number of hosts you need, not the protection you have."
                ),
                novice=(
                    "vSAN keeps spare copies of your data on different "
                    "servers. When a server dies, it rebuilds the lost copies "
                    "onto another server the same day — if there is one to "
                    "spare. The rule: with FTT=1 (survive one failure) you "
                    "need 3 servers still standing after the failure; with "
                    "FTT=2 you need 5. With too few, the data sits with no "
                    "spare copy for the whole 3-day repair. The day of the "
                    "failure itself is not counted; the days after are."
                ),
                expert="Rebuild target iff nodes − down ≥ 2·FTT + 1; else exposed until repair (3 d).",
            ),
        ),
        _never_short("n-plus-one", EQ_N1),
        Criterion(
            id="vsan", label="A VxRail (vSAN) cluster",
            metric="vsanCluster", op=">=", threshold=1, unit="",
            explain_id="n-plus-one", equation=EQ_N1,
            why=L(
                standard="The rebuild-target rule is vSAN's. Switching product removes the rule rather than satisfying it.",
                novice="The spare-copy rule in this lab belongs to VxRail's vSAN storage. Changing the product makes the rule disappear instead of solving it, so the product has to stay VxRail.",
                expert="product = vxrail; other personalities do not model the 2n+1 rule.",
            ),
        ),
        _full_run(180, "availability", EQ_AVAIL),
        _valid_build(),
    ],
    objective=Objective(
        label="Nodes in the cluster", metric="nodesTotal",
        direction="minimize", par=5, worst=8, unit="nodes",
        explain_id="n-plus-one", equation=EQ_N1,
    ),
    hints=[
        L(standard="Run the start and read the event log and the exposure flag after day 20. Three nodes at FTT=1 has no rebuild target — that is the 3-node trap, and the fix for it is well known.",
          novice="Play the lab's start and watch what happens after the day-20 failure: the exposure warning stays on for days. Three servers is the famous '3-node trap' — after one dies, there is nowhere to rebuild the spare copies. The Configuration rules panel tells you the usual cure.",
          expert="Start = the 3-node trap; exposure holds through repair."),
        L(standard="Four nodes closes the protection window, and the day-20 fault becomes a failover. Now look at day 150: three survivors hold 30 VMs, and demand has grown past 30.",
          novice="Four servers fixes the spare-copy problem, and the day-20 failure becomes a 2-minute hiccup. But look at day 150. Each server holds 10 VMs, so the three survivors hold 30 — and by day 150 the estate wants about 31. There is nowhere for the last VM to go.",
          expert="4 nodes: d150 survivors 30 VMs < ~31 demand → 240 min."),
        L(standard="Size N+1 against the last day's demand, not the first: five nodes. Leave FTT at 1 — FTT=2 needs five hosts standing after the fault, which would be six nodes.",
          novice="Work out spare capacity for the END of the run, not the start: about 32 VMs needs four healthy servers, plus one spare makes five. Leave FTT at 1. FTT=2 sounds safer, but it needs 5 servers still standing after a failure — so you would have to buy six.",
          expert="N+1 at d180 demand → 5 nodes, FTT=1 (FTT=2 ⇒ 6)."),
    ],
    start=_HEADROOM_START.model_dump(by_alias=True),
)


# --- Lab 2: how big a fleet can two people run? ------------------------------

_TEAM_START = Scenario(
    config=FleetConfig(product="nativeedge", sites=80, nodes_per_site=2,
                       ops_mode="manual", two_node_ha=True, site_class="factory"),
    workload=Workload(vms_per_site=15, growth_pct_month=0, vm_size_capacity=10),
    duration_d=180,
)

TWO_PERSON_CEILING = Lab(
    id="two-person-ceiling",
    title="How big a fleet can two people run?",
    difficulty=2,
    goal=LabGoal(
        statement=L(
            standard=(
                "A two-person team runs a NativeEdge estate of two-node sites "
                "on 16 admin-hours a day. Grow the fleet "
                "as large as it will go — most VMs served — while software "
                "currency averages 88% or better across six monthly update "
                "waves and every fault is a failover."
            ),
            novice=(
                "Two people look after this estate of small edge sites (two "
                "servers each), and between them they "
                "have 16 working hours a day. Every month a software update "
                "arrives and every server has to be patched, which takes "
                "hours. Make the fleet as big as you can — the more VMs it "
                "runs, the higher the score — but on average at least 88% of "
                "the servers must be on the latest software, and a server "
                "failure must never be more than a 2-minute hiccup."
            ),
            expert=(
                "Edge estate, 16 h/day. Maximize served VMs s.t. mean version currency "
                "≥ 88% over 180 d, failovers only, never short."
            ),
        ),
        constraints=[
            L(standard="Mean version currency at least 88% over the 180-day run.",
              novice="Averaged over all 180 days, at least 88% of servers must be on the latest software. Each monthly update drops the number to zero, and it climbs back as the team works through the patching.",
              expert="mean(version current) ≥ 88%."),
            L(standard="No outage beyond 2-minute failovers, no truck rolls, demand never above capacity.",
              novice="Only 2-minute hiccups when servers fail — no big outages, nobody driving out to a site that went dark — and never more VMs wanted than the healthy servers can hold.",
              expert="hard outage 0, truck rolls 0, short days 0."),
            L(standard="A 180-day run and no configuration errors.",
              novice="Keep the 180-day run, and no red errors in the Configuration rules panel.",
              expert="180 d, zero errors."),
        ],
        delivered_work=L(
            standard="At least 1200 VMs served on average — the fleet you start with; the objective is to serve many more.",
            novice="On an average day at least 1200 VMs must be running — that is what the starting fleet already does. The score rewards going far beyond it.",
            expert="workVms ≥ 1200; objective maximizes it.",
        ),
    ),
    criteria=[
        _work(1200, "admin-hours", EQ_HOURS),
        Criterion(
            id="current", label="Mean version currency at least 88%",
            metric="meanVersionCurrentPct", op=">=", threshold=88, unit="%",
            weight=2.0, explain_id="admin-hours", equation=EQ_HOURS,
            why=L(
                standard=(
                    "Each wave queues nodes × patch cost (2 h manual, 0.2 h "
                    "automated) against 16 h/day, and currency climbs from 0 "
                    "as the hours are worked. A wave that takes T days to "
                    "clear costs about T/60 of mean currency, so 88% means "
                    "clearing each wave in roughly a week. Fault remediation "
                    "draws on the same 16 hours."
                ),
                novice=(
                    "When an update arrives, every server needs patching: "
                    "2 hours each by hand, or 0.2 hours each with automation. "
                    "The team only has 16 hours a day, so a big fleet takes "
                    "many days to patch, and until it is done part of the "
                    "fleet runs old software. To average 88% you need each "
                    "monthly update finished in about a week. Fixing broken "
                    "servers uses the same 16 hours, so it slows patching "
                    "down a little."
                ),
                expert="Wave = nodes × {2, 0.2} h vs 16 h/day; mean deficit ≈ T_clear/60. 88% ⇒ T ≈ 7 d.",
            ),
        ),
        _no_hard_outage(),
        Criterion(
            id="no-trucks", label="No site waits for a truck",
            metric="truckRolls", op="<=", threshold=0, unit="visits",
            explain_id="n-plus-one", equation=EQ_N1,
            why=L(
                standard=(
                    "A single-node site has no survivor to fail over to: its "
                    "fault is a 1,440-minute outage for that site and a truck "
                    "roll. Spread over hundreds of sites the fleet-wide "
                    "average hides it; the site that was dark does not."
                ),
                novice=(
                    "If a site has only one server and it dies, there is no "
                    "other server to take over. The site is down for a whole "
                    "day (1,440 minutes) until someone drives out to fix it. "
                    "Across hundreds of sites that barely moves the average, "
                    "but the shop that was closed for a day still noticed. "
                    "So this lab allows no truck visits at all."
                ),
                expert="survivors ≥ 1 fails at 1 node/site: 1,440 min + a truck. Zero allowed.",
            ),
        ),
        _never_short("n-plus-one", EQ_N1),
        _full_run(180, "admin-hours", EQ_HOURS),
        _valid_build(),
    ],
    objective=Objective(
        label="VMs served, averaged over the run", metric="workVms",
        direction="maximize", par=6950, worst=1200, unit="VMs",
        explain_id="admin-hours", equation=EQ_HOURS,
    ),
    hints=[
        L(standard="Watch the version-currency gauge after day 30 on the start: 160 nodes × 2 h is 320 h of patching against 16 h a day — twenty days per wave.",
          novice="Play the start and watch the 'version currency' gauge after day 30. The fleet has 160 servers, and patching each by hand takes 2 hours: 320 hours of work, 16 hours a day, so twenty days before everyone is up to date — and then the next update is nearly due.",
          expert="Start: 160 × 2 h / 16 h·d⁻¹ = 20 d per wave."),
        L(standard="Automated ops makes patching 0.2 h a node and passes at once. But automation has the same ceiling ten times further out: push sites × nodes up and find where mean currency falls to 88%.",
          novice="Switch Ops mode to automated: patching drops to 0.2 hours a server and the lab passes. Now grow the fleet. Automation does not remove the 16-hour limit, it just moves it ten times further away. Keep adding sites and nodes and watch the average currency fall toward 88%.",
          expert="Automated = 10× further ceiling, not no ceiling. Find nodes at 88%."),
        L(standard="The ceiling is about 736 nodes — 368 two-node sites. Then fill them: each node hosts 10 VMs, so a site holds 20, but leave headroom for the node that is down — 19 VMs a site — or the first fault is a 240-minute outage. Keep two nodes a site: a single-node site waits for a truck.",
          novice="The limit is about 736 servers — 368 sites of two. Then fill them with VMs: each server holds 10, so a site holds 20. Do not fill them completely. 19 VMs a site leaves room so that when a server dies its VMs have somewhere to go; otherwise the first failure is a 240-minute outage. And keep two servers at every site: with only one, a failure means a day's wait for a truck.",
          expert="~736 nodes (368 × 2), 19 VMs/site: currency-bound, then N+1-bound; 1-node sites roll trucks."),
    ],
    start=_TEAM_START.model_dump(by_alias=True),
)


# --- Lab 3: commit to the trough, buffer to the last spike ------------------

_GROWING_APEX = Workload(vms_per_site=150, growth_pct_month=1, vm_size_capacity=15)

_COMMIT_START = Scenario(
    config=APEX_SPIKY, workload=_GROWING_APEX, duration_d=180,
)

COMMITMENT = Lab(
    id="commit-to-the-trough",
    title="Commit to the trough, buffer to the last spike",
    difficulty=3,
    goal=LabGoal(
        statement=L(
            standard=(
                "An APEX estate of 150 VMs grows 1% a month on a spiky curve "
                "(×1.5 for 10 days in 60, ×0.85 otherwise). Choose the "
                "committed base and the buffer so every spike is served and "
                "the as-a-service cost is $46.00 per 1000 VM-hours or less — "
                "then push it lower."
            ),
            novice=(
                "You rent capacity (APEX) for an estate of 150 VMs that "
                "grows 1% a month. Demand is spiky: for 10 days out of every "
                "60 it jumps to one and a half times normal, and the rest of "
                "the time it sits at 85%. You choose two numbers: the "
                "committed base (VMs you pay for whether you use them or "
                "not) and the buffer (extra room above the base, charged at "
                "a higher rate only when used). Serve every spike, and get "
                "the cost down to $46.00 or less per 1000 VM-hours. Lower "
                "scores higher."
            ),
            expert=(
                "APEX, 150 VMs +1%/mo, spiky. Pick base and buffer: zero "
                "short days, ≤ $46.00/kVM-h, minimize."
            ),
        ),
        constraints=[
            L(standard="Demand really is spiky: peak at least 1.5× the mean.",
              novice="Keep the spiky demand. The highest day must be at least 1.5 times the average day — switching to a flat curve is not allowed.",
              expert="peak/mean demand ≥ 1.5."),
            L(standard="Demand never above base × (1 + buffer), nor above installed capacity.",
              novice="Never a day when people want more VMs than the contract allows (base plus buffer) or more than the servers can hold.",
              expert="short days = 0 against min(buffer cap, installed)."),
            L(standard="A 180-day run — it ends on a spike day.",
              novice="Keep the 180-day run. Notice that day 180 is itself the first day of a spike.",
              expert="180 d; d180 is a spike day."),
        ],
        delivered_work=L(
            standard="At least 147 VMs served, averaged over the run.",
            novice="On an average day at least 147 VMs must actually be running. Shrinking the estate to shrink the bill does not count.",
            expert="workVms ≥ 147.",
        ),
    ),
    criteria=[
        _work(147, "apex-econ", EQ_APEX),
        Criterion(
            id="spiky", label="Peak demand at least 1.5× the mean",
            metric="peakToMeanDemand", op=">=", threshold=1.5, unit="×",
            explain_id="apex-econ", equation=EQ_APEX,
            why=L(
                standard="The lab is about the shape of the curve. On flat demand the commitment question is trivial — commit to demand — so the spike has to be there.",
                novice="This lab is about spiky demand. If demand were flat, the answer would be easy: commit to exactly what you use. So the lab checks that the busiest day is at least 1.5 times the average day.",
                expert="Shape constraint: max/mean ≥ 1.5 (spiky ≈ 1.6; seasonal ≈ 1.4).",
            ),
        ),
        Criterion(
            id="served", label="Every spike served",
            metric="capacityShortDays", op="<=", threshold=0, unit="days", weight=2.0,
            explain_id="apex-econ", equation=EQ_APEX,
            why=L(
                standard=(
                    "The serving ceiling is base × (1 + buffer). The spike "
                    "grows with the estate: ×1.5 on 150 VMs is 225 on day 0 "
                    "and about 238 on day 180. A buffer sized to the first "
                    "spike is an outage on the later ones."
                ),
                novice=(
                    "The most you can use is the base plus the buffer — for "
                    "example a base of 150 with a 50% buffer allows 225 VMs. "
                    "The first spike is 225 VMs, which just fits. But the "
                    "estate grows 1% a month, so later spikes are bigger: "
                    "about 238 VMs on day 180. A ceiling that fitted the "
                    "first spike fails the later ones."
                ),
                expert="base×(1+buffer) ≥ 1.5 × 150 × growth(d180) ≈ 238.",
            ),
        ),
        Criterion(
            id="cost", label="As-a-service cost at most $46.00 per 1000 VM-hours",
            metric="costPerKVmHour", op="<=", threshold=46.0, unit="$/kVM-h",
            weight=2.0, explain_id="apex-econ", equation=EQ_APEX,
            why=L(
                standard=(
                    "The base is paid every day, used or not; overage is "
                    "paid at 1.5× but only on spike days. Demand sits at the "
                    "trough five days in six, so every committed VM above "
                    "the trough is idle most of the time — dearer than "
                    "renting it at 1.5× for one day in six. Rates are "
                    "illustrative; Dell states its own offer has no overage "
                    "premium."
                ),
                novice=(
                    "You pay for the base every single day, even when it is "
                    "not used. You pay for the buffer at one and a half "
                    "times the price, but only on days you use it. Demand is "
                    "low five days out of six. So a VM in the base that is "
                    "only needed during spikes sits idle most of the time — "
                    "which costs more than renting it at the higher rate for "
                    "the few spike days. These prices are made up to show "
                    "the shape; Dell says its own APEX offer charges no "
                    "premium for buffer use."
                ),
                expert="Base above trough idles 5/6 of days; 1.5× overage for 1/6 is cheaper. Illustrative rates.",
            ),
        ),
        _no_hard_outage(),
        _full_run(180, "apex-econ", EQ_APEX),
        _valid_build(),
    ],
    objective=Objective(
        label="As-a-service cost per 1000 VM-hours", metric="costPerKVmHour",
        direction="minimize", par=44.55, worst=46.0, unit="$/kVM-h",
        explain_id="apex-econ", equation=EQ_APEX,
    ),
    hints=[
        L(standard="Play the start to the end. Base 150 with a 50% buffer tops out at 225 VMs, and the event log shows capacity outages on the later spikes: the estate grew, the ceiling did not.",
          novice="Play the start all the way through and read the event log. A base of 150 with a 50% buffer allows 225 VMs. That was enough for the first spike, but the estate keeps growing, and the later spikes hit the ceiling and cause outages.",
          expert="150/50 ⇒ 225 cap < later spikes (~238)."),
        L(standard="Raising the buffer fixes the outages but not the cost. Look at where demand sits between spikes: about 128–135 VMs. A base of 150 pays for VMs nobody uses five days in six.",
          novice="A bigger buffer stops the outages, but the cost is still too high. Look at the demand line between spikes: it sits around 128 to 135 VMs. A base of 150 means paying every day for VMs that are only used during spikes.",
          expert="Trough ≈ 0.85 × demand ≈ 128–135; base 150 is idle commitment."),
        L(standard="Commit near the trough — about 130 VMs — and let the buffer reach the last spike: 130 × 1.84 ≈ 239. Lower than the trough and you pay 1.5× every day; higher and you pay for air.",
          novice="Set the base close to the low-demand level, about 130 VMs, and make the buffer big enough to reach the last spike: 84% gives 130 × 1.84 ≈ 239 VMs. If the base is lower than the usual demand you pay the higher rate every day; if it is higher you pay for VMs nobody uses.",
          expert="base ≈ 130, buffer ≈ 84%: cap ≈ 239, cost ≈ $44.5/kVM-h."),
    ],
    start=_COMMIT_START.model_dump(by_alias=True),
)


LABS: list[Lab] = [HEADROOM, TWO_PERSON_CEILING, COMMITMENT]
LABS_BY_ID: dict[str, Lab] = {lab.id: lab for lab in LABS}


# --- Passing scenarios and the tricks that must not work -------------------
# Server-side only: GET /api/labs serves LABS, never these.

_VX = VXRAIL_3NODE
_AUTO_736 = FleetConfig(product="nativeedge", sites=368, nodes_per_site=2,
                        ops_mode="automated", two_node_ha=True,
                        site_class="factory")

REFERENCE_SOLUTIONS: dict[str, Scenario] = {
    "headroom-for-the-last-day": Scenario(
        config=_VX.model_copy(update={"nodes_per_site": 5}),
        workload=_GROWING, duration_d=180, events=_TWO_FAULTS,
    ),
    "two-person-ceiling": Scenario(
        config=_AUTO_736,
        workload=Workload(vms_per_site=19, growth_pct_month=0),
        duration_d=180,
    ),
    "commit-to-the-trough": Scenario(
        config=APEX_SPIKY.model_copy(update={"committed_vms": 130, "buffer_pct": 84}),
        workload=_GROWING_APEX, duration_d=180,
    ),
}

GAMING_ATTEMPTS: dict[str, dict[str, Scenario]] = {
    "headroom-for-the-last-day": {
        "zero load": Scenario(
            config=_VX.model_copy(update={"nodes_per_site": 5}),
            workload=Workload(vms_per_site=1, growth_pct_month=0),
            duration_d=180, events=_TWO_FAULTS),
        "four nodes, the textbook answer": Scenario(
            config=_VX.model_copy(update={"nodes_per_site": 4}),
            workload=_GROWING, duration_d=180, events=_TWO_FAULTS),
        "no faults at all": Scenario(
            config=_VX.model_copy(update={"nodes_per_site": 4}),
            workload=_GROWING, duration_d=180),
        "early fault only": Scenario(
            config=_VX.model_copy(update={"nodes_per_site": 4}),
            workload=_GROWING, duration_d=180, events=_TWO_FAULTS[:1]),
        "turn the growth off": Scenario(
            config=_VX.model_copy(update={"nodes_per_site": 4}),
            workload=Workload(vms_per_site=28, growth_pct_month=0),
            duration_d=180, events=_TWO_FAULTS),
        "slow start, late sprint": Scenario(
            config=_VX.model_copy(update={"nodes_per_site": 4}),
            workload=Workload(vms_per_site=21, growth_pct_month=7),
            duration_d=180, events=_TWO_FAULTS),
        "switch product to dodge vSAN": Scenario(
            config=FleetConfig(product="privatecloud", sites=1, nodes_per_site=3),
            workload=Workload(vms_per_site=20, growth_pct_month=0),
            duration_d=180, events=_TWO_FAULTS),
        "FTT=2 on five nodes": Scenario(
            config=_VX.model_copy(update={"nodes_per_site": 5, "ftt": 2}),
            workload=_GROWING, duration_d=180, events=_TWO_FAULTS),
        "short run": Scenario(
            config=_VX.model_copy(update={"nodes_per_site": 4}),
            workload=Workload(vms_per_site=33, growth_pct_month=0),
            duration_d=40, events=_TWO_FAULTS[:1]),
    },
    "two-person-ceiling": {
        "zero load": Scenario(
            config=_AUTO_736,
            workload=Workload(vms_per_site=1, growth_pct_month=0), duration_d=180),
        "small manual fleet that stays current": Scenario(
            config=FleetConfig(product="privatecloud", sites=9, nodes_per_site=8,
                               ops_mode="manual"),
            workload=Workload(vms_per_site=72, growth_pct_month=0), duration_d=180),
        "stay manual, fill the sites": Scenario(
            config=_AUTO_736.model_copy(update={"sites": 80, "ops_mode": "manual"}),
            workload=Workload(vms_per_site=19, growth_pct_month=0), duration_d=180),
        "max everything": Scenario(
            config=FleetConfig(product="privatecloud", sites=1000,
                               nodes_per_site=16, ops_mode="automated"),
            workload=Workload(vms_per_site=150, growth_pct_month=0), duration_d=180),
        "short run before the first update": Scenario(
            config=FleetConfig(product="privatecloud", sites=1000,
                               nodes_per_site=16, ops_mode="automated"),
            workload=Workload(vms_per_site=150, growth_pct_month=0), duration_d=25),
        "overfill the nodes": Scenario(
            config=_AUTO_736,
            workload=Workload(vms_per_site=40, growth_pct_month=0), duration_d=180),
        "no headroom": Scenario(
            config=_AUTO_736,
            workload=Workload(vms_per_site=20, growth_pct_month=0), duration_d=180),
        "single-node edge sites": Scenario(
            config=FleetConfig(product="nativeedge", sites=730, nodes_per_site=1,
                               ops_mode="automated", two_node_ha=False),
            workload=Workload(vms_per_site=9, growth_pct_month=0), duration_d=180),
    },
    "commit-to-the-trough": {
        "zero load": Scenario(
            config=APEX_SPIKY.model_copy(update={"committed_vms": 10, "buffer_pct": 100}),
            workload=Workload(vms_per_site=1, growth_pct_month=0, vm_size_capacity=15),
            duration_d=180),
        "flat demand": Scenario(
            config=APEX_SPIKY.model_copy(update={
                "committed_vms": 240, "buffer_pct": 0, "demand_curve": "steady"}),
            workload=Workload(vms_per_site=200, growth_pct_month=1, vm_size_capacity=15),
            duration_d=180),
        "seasonal instead of spiky": Scenario(
            config=APEX_SPIKY.model_copy(update={
                "committed_vms": 150, "buffer_pct": 60, "demand_curve": "seasonal"}),
            workload=_GROWING_APEX, duration_d=180),
        "tiny buffer, let the spikes drop": Scenario(
            config=APEX_SPIKY.model_copy(update={"committed_vms": 130, "buffer_pct": 10}),
            workload=_GROWING_APEX, duration_d=180),
        "buffer sized to the first spike": Scenario(
            config=APEX_SPIKY.model_copy(update={"committed_vms": 128, "buffer_pct": 76}),
            workload=_GROWING_APEX, duration_d=180),
        "commit to the peak": Scenario(
            config=APEX_SPIKY.model_copy(update={"committed_vms": 240, "buffer_pct": 0}),
            workload=_GROWING_APEX, duration_d=180),
        "short run between spikes": Scenario(
            config=APEX_SPIKY.model_copy(update={"committed_vms": 130, "buffer_pct": 84}),
            workload=_GROWING_APEX, duration_d=50),
        "not enough iron": Scenario(
            config=APEX_SPIKY.model_copy(update={
                "committed_vms": 130, "buffer_pct": 84, "nodes_per_site": 12}),
            workload=_GROWING_APEX, duration_d=180),
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
