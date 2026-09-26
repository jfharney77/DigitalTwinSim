"""Presets and the teaching layer for the fleet simulator."""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    Explain,
    FleetConfig,
    GuidedScenario,
    GlossaryTerm,
    Intro,
    Scenario,
    ScenarioVariant,
    SimEvent,
    Workload,
    WorkloadPreset,
)

# --- Config presets --------------------------------------------------------

VXRAIL_8 = FleetConfig(product="vxrail", sites=1, nodes_per_site=8,
                       ops_mode="automated", ftt=1)
VXRAIL_MANUAL = VXRAIL_8.model_copy(update={"ops_mode": "manual"})
VXRAIL_3NODE = FleetConfig(product="vxrail", sites=1, nodes_per_site=3,
                           ops_mode="automated", ftt=1)
VXRAIL_4NODE = VXRAIL_3NODE.model_copy(update={"nodes_per_site": 4})
PRIVATE_2STACK = FleetConfig(product="privatecloud", sites=1, nodes_per_site=12,
                             ops_mode="automated", stacks=2, catalog=True)
# Sized to serve its own spike: base 150 × (1 + 50% buffer) = 225 VMs =
# the ×1.5 peak, on 16 nodes × 15 VMs (APEX_WL) = 240 installed. At a
# 30% buffer and 10 VMs/node the "as-a-service wins" scenario opened on
# a capacity outage every spike.
APEX_SPIKY = FleetConfig(product="apex", sites=1, nodes_per_site=16,
                         committed_vms=150, buffer_pct=50,
                         demand_curve="spiky")
EDGE_500 = FleetConfig(product="nativeedge", sites=500, nodes_per_site=1,
                       ops_mode="automated", two_node_ha=False,
                       site_class="store")
EDGE_HA = FleetConfig(product="nativeedge", sites=50, nodes_per_site=2,
                      ops_mode="automated", two_node_ha=True,
                      site_class="factory")
STUDIO = FleetConfig(product="automationstudio", sites=1, nodes_per_site=12,
                     ops_mode="automated", test_gate=True)

CONFIG_PRESETS = [
    ConfigPreset(id="vxrail-8", compare_preset_id="vxrail-manual", name="VxRail ×8 · automated", config=VXRAIL_8,
                 blurb="The lifecycle bundle doing its job."),
    ConfigPreset(id="vxrail-manual", compare_preset_id="vxrail-8", name="VxRail ×8 · manual", config=VXRAIL_MANUAL,
                 blurb="Same cluster, artisanal ops — watch the ledger."),
    ConfigPreset(id="vxrail-3", name="VxRail ×3 (the trap)", config=VXRAIL_3NODE,
                 blurb="The minimum cluster, and why minimums exist."),
    ConfigPreset(id="vxrail-4", name="VxRail ×4 (the spare)", config=VXRAIL_4NODE,
                 blurb="One node past the minimum: somewhere to rebuild."),
    ConfigPreset(id="private", name="Private Cloud · 2 stacks", config=PRIVATE_2STACK,
                 blurb="Two hypervisors, one pane, one catalog."),
    ConfigPreset(id="apex", name="APEX · spiky demand", config=APEX_SPIKY,
                 blurb="Consumption economics on a spiky curve."),
    ConfigPreset(id="edge-500", name="NativeEdge · 500 stores", config=EDGE_500,
                 blurb="The zero-touch headline: half an hour vs a site visit."),
    ConfigPreset(id="edge-ha", name="NativeEdge · 2-node HA", config=EDGE_HA,
                 blurb="Factories that cannot wait for the truck."),
    ConfigPreset(id="studio", name="Automation Studio", config=STUDIO,
                 blurb="Changes as pipelines, with the gate that earns its keep."),
]

# --- Workload presets ------------------------------------------------------

STEADY_WL = Workload(vms_per_site=20, growth_pct_month=3, vm_size_capacity=10)
APEX_WL = Workload(vms_per_site=150, growth_pct_month=0, vm_size_capacity=15)
DENSE_WL = Workload(vms_per_site=60, growth_pct_month=5, vm_size_capacity=10)
EDGE_WL = Workload(vms_per_site=5, growth_pct_month=1, vm_size_capacity=8)

WORKLOAD_PRESETS = [
    WorkloadPreset(id="steady", name="Steady estate", workload=STEADY_WL),
    WorkloadPreset(id="dense", name="Dense & growing", workload=DENSE_WL),
    WorkloadPreset(id="edge", name="Edge apps", workload=EDGE_WL),
    WorkloadPreset(id="apex-wl", name="Committed estate (APEX)", workload=APEX_WL),
]

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="rolling-upgrade",
        title="Rolling upgrade under load",
        narration=[
            L(
                novice=(
                    "A software update arrives on day 30, as one "
                    "arrives every month, forever. In automated mode "
                    "the cluster patches itself node by node while "
                    "spare capacity keeps every workload running — the "
                    "availability number never moves. Load the manual "
                    "preset and rerun: the same update becomes days of "
                    "careful per-node work competing with everything "
                    "else the team must do, and the fleet drifts out "
                    "of date. The update is not the event; the "
                    "update *cadence* is."
                ),
                standard=(
                    "The monthly release wave against the 16 h/day "
                    "ops budget: automated, patching costs 0.2 h/node "
                    "and version currency snaps back within days with "
                    "zero outage minutes; manual costs 2 h/node and "
                    "the version gauge saws tooth-shaped and never "
                    "reaches 100 before the next wave. Lifecycle "
                    "management is the product, priced in the ledger. "
                    "The updating flag shows the rolling window."
                ),
                expert=(
                    "0.2 vs 2 h/node against 16 h/day, monthly "
                    "cadence. Auto: currency sawtooth closes; manual: "
                    "never. LCM is the SKU."
                ),
            ),
        ],
        question="Does the manual fleet's version gauge ever reach 100% before the next release lands?",
        scenario=Scenario(config=VXRAIL_8, workload=STEADY_WL, duration_d=120),
    ),
    GuidedScenario(
        id="three-node-trap",
        title="The 3-node trap",
        narration=[
            L(
                novice=(
                    "Three servers (nodes) is the smallest standard "
                    "cluster. So that one server can die without "
                    "losing anything, every piece of data is kept on "
                    "two different servers, with a small tie-breaker "
                    "record on a third. On day 20 one server dies. "
                    "The programs it was running restart on the other "
                    "two in about two minutes. The data is a "
                    "different matter: some pieces are down to one "
                    "good copy, and making the second copies again "
                    "needs three healthy servers to spread them over. "
                    "Only two are left. So the red exposure warning "
                    "stays up for three days, until the broken server "
                    "is repaired (three days is this model's "
                    "estimate), and a second failure in that time "
                    "would lose data. Now press 4 nodes in the table "
                    "below. The failure is the same, but the fourth "
                    "server gives the copies somewhere to go and the "
                    "warning clears the next day — one day is this "
                    "model's estimate for the rebuild, as three days "
                    "is for the repair. The event log "
                    "records the day the warning opened and the day "
                    "it closed, and the exposure days instrument "
                    "keeps the total."
                ),
                standard=(
                    "3 nodes at FTT=1 (failures to tolerate: one), "
                    "and a day-20 fault. HA restarts the VMs with "
                    "about 2 minutes of downtime, but the exposure "
                    "flag stays up for the whole 3-day repair window "
                    "(an estimate): FTT=1 needs three hosts standing "
                    "to re-protect the data, two are left, so there "
                    "is no rebuild target and protection waits for "
                    "the repair. The validation panel warned before "
                    "the run started. Press 4 nodes in the table "
                    "below: same fault, and exposure closes the next "
                    "day as the rebuild lands on the spare host — "
                    "that one day is an estimate too; a real vSAN "
                    "resync depends on capacity, object count and the "
                    "repair delay timer. The "
                    "event log records the open and the close, and "
                    "exposure days keeps the total. This is "
                    "PhysicsStorage's exposure-window lesson wearing "
                    "vSAN's badge."
                ),
                expert=(
                    "N=3, FTT=1: fault → HA ok, no rebuild target → "
                    "exposure = repair window (3 d, est.). N=4: 1 d "
                    "(est.). "
                    "Log and exposure days carry both."
                ),
            ),
        ],
        question=L(
            novice=(
                "How many days did the red exposure warning stay up "
                "with three servers, and how many with four? What "
                "ended it each time?"
            ),
            standard=(
                "How many days did the exposure flag stay up on three "
                "nodes, how many on four, and what closed it each time?"
            ),
        ),
        scenario=Scenario(
            config=VXRAIL_3NODE, workload=EDGE_WL, duration_d=60,
            events=[SimEvent(at_d=20, action="node-fault")],
        ),
        variants=[
            ScenarioVariant(label="3 nodes (as loaded)", config=VXRAIL_3NODE),
            ScenarioVariant(label="4 nodes", config=VXRAIL_4NODE),
        ],
    ),
    GuidedScenario(
        id="catalog-vs-artisanal",
        title="Catalog vs artisanal",
        narration=[
            L(
                novice=(
                    "A private cloud of twelve servers running two "
                    "different software platforms (stacks), managed "
                    "from one central console (the control plane). "
                    "Two switches in the Build panel decide how much "
                    "human work that takes. Stacks: a second platform "
                    "means more to patch every month, but because one "
                    "console patches both, the extra is about a "
                    "quarter of the patching, not double it — twelve "
                    "servers take about 2.4 hours to patch, so the "
                    "second platform adds about 0.6 hours a month. In "
                    "the table below that is the monthly figure going "
                    "from 3.4 to 4.0 hours; the rest of those hours "
                    "is the other work, which the second platform "
                    "does not change. Catalog: this estate grows "
                    "by about three new workloads a month. Taken from "
                    "a self-service catalog (a menu of ready-made, "
                    "tested builds) each one costs about a quarter of "
                    "an hour of admin time. Built by hand each time, "
                    "which is what artisanal means here, each one "
                    "costs about sixteen hours, two working days. The "
                    "table below runs all three builds over the same "
                    "120 days. Read the admin-hours column, then "
                    "press a row to load that build and watch the "
                    "event log add up each month's deployments. Every "
                    "hour figure is an estimate; the gaps are the "
                    "lesson."
                ),
                standard=(
                    "Stack pluralism priced: twelve nodes, two "
                    "stacks, one control plane. The second stack adds "
                    "about 25% to each monthly patch wave instead of "
                    "doubling it, because the shared control plane "
                    "runs both: 12 nodes × 0.2 h is a 2.4 h wave for "
                    "one stack, and the second adds 0.6 h. That is "
                    "the table's monthly rate moving 3.4 → 4.0 h — "
                    "the 25% is of the patch wave, not of the whole "
                    "rate, and the rest of the rate is deploys and "
                    "routine upkeep the second stack leaves alone. "
                    "That is the DellPrivateCloud twin's "
                    "single control plane, priced in hours; switch "
                    "Ops mode to manual and the same second stack "
                    "doubles the wave. The other entry is deployment: "
                    "the estate grows by about three workloads a "
                    "month, each charged 0.25 h from the catalog or "
                    "16 h hand-built. The table below runs the loaded "
                    "build, the one-stack build and the hand-built "
                    "build over the same 120 days; press a row to "
                    "load it, and the event log totals each month's "
                    "deploys. All hour figures are estimates."
                ),
                expert=(
                    "Per workload deploy: 0.25 h from the catalog vs "
                    "16 h hand-built, ~3 deploys/month. Second stack: "
                    "+25% patch hours under one control plane (2.4 h "
                    "wave → +0.6 h; monthly rate 3.4 → 4.0), +100% "
                    "manual. Three builds tabulated below; estimates."
                ),
            ),
        ],
        question=L(
            novice=(
                "Using the table: how many admin-hours a month did "
                "the second platform add to the one-platform figure? "
                "And how many hours did the same number of workloads "
                "cost hand-built instead of from the catalog?"
            ),
            standard=(
                "From the table: how much did the second stack add to "
                "the monthly admin-hours rate, and what did the same "
                "13 deploys cost hand-built rather than from the "
                "catalog?"
            ),
        ),
        scenario=Scenario(config=PRIVATE_2STACK, workload=DENSE_WL, duration_d=120),
        variants=[
            ScenarioVariant(label="Two stacks · catalog (as loaded)",
                            config=PRIVATE_2STACK),
            ScenarioVariant(label="One stack · catalog",
                            config=PRIVATE_2STACK.model_copy(update={"stacks": 1})),
            ScenarioVariant(label="Two stacks · hand-built deploys",
                            config=PRIVATE_2STACK.model_copy(update={"catalog": False})),
        ],
    ),
    GuidedScenario(
        id="spiky-demand",
        title="Spiky demand (as-a-service wins)",
        narration=[
            L(
                novice=(
                    "A workload that spikes hard for ten days out of "
                    "every sixty — a tax season, a launch, a sale. "
                    "Two cost meters run side by side: renting "
                    "(committed base plus premium overage) and owning "
                    "(hardware amortized whether busy or idle). With "
                    "spikes, owning means buying the peak and idling "
                    "it; renting means paying premiums briefly. Watch "
                    "the per-VM-hour meters cross. Then load the "
                    "steady curve and watch them cross back. Neither "
                    "answer is right; the demand's shape decides."
                ),
                standard=(
                    "Archetype F: spiky demand (×1.5 for 10 days in "
                    "60) drives the as-a-service $/VM-hour below the "
                    "owned figure, because ownership must buy the "
                    "peak and amortize its idleness. Rerun with "
                    "'steady' and the ranking inverts — the tests pin "
                    "both directions. The buffer slider prices its "
                    "own failure modes: outage minutes under it, "
                    "utilization-of-commitment above it. Rates are "
                    "estimates; the crossover is the lesson. The "
                    "overage premium is the generic model — Dell "
                    "states its APEX Infrastructure offer uses one "
                    "rate with no overage fees."
                ),
                expert=(
                    "Spiky: asvc < capex per VM-h (peak-buying "
                    "amortizes idle). Steady: inverts. Buffer: "
                    "outage vs air. Shape decides; both pinned."
                ),
            ),
        ],
        question="Which cost meter won here, and what happens to the ranking on the steady curve?",
        scenario=Scenario(config=APEX_SPIKY, workload=APEX_WL, duration_d=240),
    ),
    GuidedScenario(
        id="roll-out-500",
        title="Roll out to 500 stores",
        narration=[
            L(
                novice=(
                    "Fifty new shops open on day 10, and a hundred "
                    "more in two later waves. Zero-touch, each box is "
                    "half an hour of remote effort; the log prices "
                    "every wave as it lands. Now imagine the same "
                    "waves in manual mode — eight hours and a drive "
                    "per site — and check the arithmetic: at 500 "
                    "sites, the difference between the two numbers "
                    "is roughly two people's entire working year. "
                    "That difference is the product."
                ),
                standard=(
                    "The headline lesson, run live: deploy waves at "
                    "0.5 h/site zero-touch vs 8 h/site manual — the "
                    "log prices each wave, and the summary's "
                    "admin-hours total against the manual rerun is "
                    "≈ 15× (the tests pin the order of magnitude). "
                    "Watch the backlog drain at 16 h/day: even "
                    "zero-touch waves queue, which is itself honest. "
                    "Companion: DellNativeEdge (:5187), operator-"
                    "actions ≤ 1 per site — this is that invariant's "
                    "price tag."
                ),
                expert=(
                    "0.5 vs 8 h/site, waves of 50–100: ~15× ledger "
                    "gap ≈ 2 FTE-years at 500 sites. The twin's "
                    "one-action invariant, invoiced."
                ),
            ),
        ],
        question="What did the three waves cost in admin-hours, and what would manual mode have charged?",
        scenario=Scenario(
            config=EDGE_500.model_copy(update={"sites": 50}),
            workload=EDGE_WL, duration_d=120,
            events=[
                SimEvent(at_d=10, action="deploy-sites", value=50),
                SimEvent(at_d=40, action="deploy-sites", value=100),
                SimEvent(at_d=70, action="deploy-sites", value=100),
            ],
        ),
    ),
    GuidedScenario(
        id="disconnected",
        title="The disconnected factory",
        narration=[
            L(
                novice=(
                    "On day 30 the network line to the factories "
                    "goes down for a week. Nothing stops — the sites "
                    "run themselves, which is the design — but watch "
                    "the drift counter: with the control plane "
                    "unreachable, every small local variation "
                    "accumulates unreconciled. When the line "
                    "returns, reconciliation sweeps the drift back "
                    "to zero over a few days. Autonomy is not the "
                    "absence of management; it is management with a "
                    "memory."
                ),
                standard=(
                    "WAN-down for 7 days: workloads keep running "
                    "(availability unmoved — the autonomy claim), "
                    "drift accumulates at the unmanaged rate, and on "
                    "reconnect the automated reconciliation drains "
                    "it back to zero — accumulate-then-resolve, the "
                    "DellNativeEdge twin's disconnected-operation "
                    "story as a curve. The 2-node HA preset also "
                    "absorbs a mid-outage fault without a truck."
                ),
                expert=(
                    "WAN 7 d: availability flat, drift ↑ at "
                    "unmanaged rate, reconcile → 0 on return. "
                    "Autonomy + memory."
                ),
            ),
        ],
        question="How high did drift climb during the outage, and how long did reconciliation take?",
        scenario=Scenario(
            config=EDGE_HA, workload=EDGE_WL, duration_d=90,
            events=[SimEvent(at_d=30, action="wan-outage", value=7)],
        ),
    ),
    GuidedScenario(
        id="failed-in-test",
        title="Failed in test, saved in prod",
        narration=[
            L(
                novice=(
                    "Twice in this run, someone pushes a broken "
                    "infrastructure change. The first time, the "
                    "pipeline's test stage catches it — one log "
                    "line, zero user impact, a mildly embarrassed "
                    "engineer. Then the test gate is switched off "
                    "and the same push happens again: four hours of "
                    "production outage while it is rolled back. The "
                    "pipeline did not make anyone smarter; it made "
                    "the mistake cheap. That is the entire theory "
                    "of CI/CD, in one afternoon."
                ),
                standard=(
                    "The gate's A/B in one trace: bad-change at day "
                    "20 with the gate (caught-in-test log, zero "
                    "outage minutes) and the same event at day 40 "
                    "gateless (240 outage minutes, availability dented "
                    "for the rest of the run — check the cumulative "
                    "gauge). Pipelines as drift enforcement is the "
                    "quieter benefit: re-runs reconcile. Built last, "
                    "per spec: it orchestrates the same fleet engine "
                    "everything else in this app runs on."
                ),
                expert=(
                    "Gate: 0 min + log. No gate: 240 min. Same "
                    "mistake, two prices. Cheap mistakes are the "
                    "product."
                ),
            ),
        ],
        question="What did the identical mistake cost with and without the gate?",
        scenario=Scenario(
            config=STUDIO, workload=DENSE_WL, duration_d=60,
            events=[
                SimEvent(at_d=20, action="bad-change"),
                SimEvent(at_d=40, action="bad-change"),
            ],
        ),
    ),
]

# --- Page intro and instrument glossary ----------------------------------------

INTRO = Intro(
    body=L(
        novice=(
            "This page simulates a company's fleet of servers (nodes), "
            "spread over one site or many, one day at a time. Things "
            "keep happening to it: a software update arrives every "
            "month, a server breaks now and then, and settings slowly "
            "wander away from what they should be. Each of those takes "
            "a person's working hours to deal with. The number to "
            "watch is admin-hours: how many hours of human work the "
            "fleet needs each month. Pick one of the five Dell "
            "products, switch between doing the work by hand and "
            "letting software do it, and watch that number change by "
            "about ten times. Every hour figure is an estimate; the "
            "size of the gap is the lesson."
        ),
        standard=(
            "One fleet engine under five management styles: VxRail's "
            "lifecycle bundle, Private Cloud's catalog, APEX's "
            "consumption pricing, NativeEdge's zero-touch estates, and "
            "Automation Studio's pipelines. The engine models sites "
            "and nodes, N+1 spare capacity (one node more than the "
            "load needs), a monthly wave of software updates, hardware "
            "faults on a fixed wear schedule, and configuration drift. "
            "The instrument to watch is the admin-hours ledger. "
            "Automation moves it by about ten times, and the rest of "
            "the app follows from that. One tick is one simulated day."
        ),
        expert=(
            "Sites × nodes, N+1, monthly release wave, deterministic "
            "wear faults, drift; five ops models. Ledger in "
            "admin-hours; automation ≈ 10×. Tick = 1 day."
        ),
    ),
    glossary=[
        GlossaryTerm(
            term="admin-hours / month",
            gloss="Hours of human operations work over the last 30 days.",
        ),
        GlossaryTerm(
            term="headroom",
            gloss=(
                "Spare capacity: the share of the healthy nodes' VM "
                "slots that demand is not using."
            ),
        ),
        GlossaryTerm(
            term="FTT",
            gloss=(
                "Failures to tolerate, a vSAN storage setting. FTT=1 "
                "(mirror) keeps two copies of the data plus a "
                "tie-breaker record on three different nodes, so one "
                "node can die without loss."
            ),
        ),
        GlossaryTerm(
            term="exposure",
            gloss=(
                "Everything is still running, but the data has lost "
                "its spare copy, so one more failure would lose data. "
                "Exposure days counts the days spent in that state."
            ),
        ),
        GlossaryTerm(
            term="version currency",
            gloss=(
                "The share of the fleet on the latest software. It "
                "drops to 0% when an update is released and climbs "
                "back as the patching hours are worked."
            ),
        ),
        GlossaryTerm(
            term="drift",
            gloss=(
                "A count of settings that have wandered from the "
                "standard. It builds up on hand-managed nodes; "
                "automation corrects it while the sites are connected."
            ),
        ),
        GlossaryTerm(
            term="faults · trucks",
            gloss=(
                "Hardware faults so far, and truck rolls: a technician "
                "driving to a remote edge site. A datacenter node is "
                "swapped on site inside the 3-day repair window "
                "(an estimate), so a VxRail fault shows 0 trucks."
            ),
        ),
    ],
)

# --- Explain-mode entries --------------------------------------------------

EXPLAINS = [
    Explain(
        id="admin-hours",
        title="The admin-hours model",
        equation="Σ actions × cost(action, ops_mode);  capacity = 16 h/day, excess backlogs",
        inputs=["actions", "ops mode", "hours", "backlog", "version currency"],
        explanation=L(
            novice=(
                "Every operation costs human hours: deploying a site, "
                "patching a server, fixing a fault. Automation does "
                "not remove the work — it changes the price by "
                "roughly ten times. And the team only has so many "
                "hours a day, so work beyond that waits, which is how "
                "fleets quietly fall behind on updates without anyone "
                "deciding to."
            ),
            standard=(
                "The ledger is the app: deploy 8 vs 0.5 h, patch 2 vs "
                "0.2 h/node, remediate 6 vs 1 h, truck rolls +8 h — "
                "all against a 16 h/day budget with a backlog. The "
                "order of magnitude is the lesson (the absolute "
                "figures are labeled estimates), and version currency "
                "is the backlog made visible: unworked patch-hours ARE "
                "the version gap."
            ),
            expert=(
                "~10× per action, 16 h/day, backlog ⇒ currency decay. "
                "The gap is the product; the hours are estimates."
            ),
        ),
    ),
    Explain(
        id="n-plus-one",
        title="N+1 headroom",
        equation="fault → failover iff (survivors ≥ 1 node) ∧ (capacity ≥ demand) ∧ (down ≤ FTT)",
        inputs=["nodes", "demand", "headroom", "fault", "outage or failover"],
        explanation=L(
            novice=(
                "Spare capacity is the insurance policy: when a "
                "server dies, its workloads restart on the spares in "
                "about two minutes. No spares, and the same death "
                "becomes hours of outage while someone repairs "
                "hardware. The N+1 rule — always own one node more "
                "than you need — is the whole difference between "
                "those two mornings."
            ),
            standard=(
                "The branch every fault takes: with headroom, "
                "2 minutes (VM restart); without, 240 (wait for "
                "repair); single-node edge without HA, 1,440 and a "
                "truck. The exposure flag marks the subtler state — "
                "service restored but protection not (the 3-node "
                "trap), the same window PhysicsStorage draws around "
                "rebuilds."
            ),
            expert=(
                "2 / 240 / 1440 min by headroom class; exposure = "
                "served-but-unprotected. Storage's window, fleet "
                "edition."
            ),
        ),
    ),
    Explain(
        id="availability",
        title="Availability arithmetic",
        equation="availability = 1 − outage-minutes / (site-days × 1440)",
        inputs=["outage minutes", "fleet size", "availability %"],
        explanation=L(
            novice=(
                "The nines are just minutes counted honestly: a "
                "four-hour outage across a year of one site is 99.95%. "
                "Every design choice in this app — spares, gates, HA "
                "pairs — is ultimately a bet about which outage "
                "minutes never happen."
            ),
            standard=(
                "Cumulative outage minutes over fleet-minutes. The "
                "instructive part is attribution: this app's minutes "
                "come from named branches (no-headroom faults, "
                "truck-roll days, ungated changes, capacity "
                "shortfalls), so the availability figure decomposes "
                "into decisions rather than luck."
            ),
            expert=(
                "1 − Σmin/fleet-min, every term attributable to a "
                "config choice. Nines are decisions, not weather."
            ),
        ),
    ),
    Explain(
        id="apex-econ",
        title="Consumption economics",
        equation="bill = base + 1.5 × overage;  vs capex = capacity × amortized rate",
        inputs=["demand curve", "base", "buffer", "$/VM-hour", "crossover"],
        explanation=L(
            novice=(
                "Renting compute has a retainer (the committed base, "
                "paid regardless), a premium meter above it (the "
                "generic shape; Dell says its own offer has no overage "
                "fees), and a ceiling. Owning has a mortgage that ignores whether "
                "anyone's home. Spiky demand favors renting — you "
                "stop paying for the idle peak. Flat demand favors "
                "owning. The shape of the curve, not the rate card, "
                "decides."
            ),
            standard=(
                "Both meters run every day: as-a-service (base + "
                "overage at 1.5×) and ownership (base+buffer capacity "
                "amortized at ~2/3 the committed rate, idle or not), "
                "divided into $/VM-hour. Spiky curves push asvc under "
                "capex; steady curves invert it; the buffer prices "
                "outage-vs-air at its two ends. All rates are labeled "
                "estimates — the crossover's existence, not its "
                "coordinates, is the claim. The 1.5× overage is a "
                "generic as-a-service shape: Dell states APEX "
                "Infrastructure (Flex on Demand) charges buffer use at "
                "the same single rate, with billing capped at 85% of "
                "installed capacity on storage-metered offers."
            ),
            expert=(
                "asvc/capex per VM-h, both accrued daily. Spiky → "
                "asvc wins; steady → capex. Buffer = outage|air. "
                "Shape > rates."
            ),
        ),
    ),
]
