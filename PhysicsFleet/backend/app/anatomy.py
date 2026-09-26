"""Fleet maps — one shared layered diagram (control plane → sites →
nodes → workloads, with the ops ledger, economics, pipeline, catalog,
and WAN blocks around it), reused by all five products with per-product
overviews. The uniform geometry is deliberate: the five products are
five management philosophies over the same physical estate, and drawing
them identically makes the differences show up where they actually live
— in the admin-hours ledger, not the racks."""

from __future__ import annotations

from .leveling import L
from .models import FleetMap, MapRegion


def _regions() -> list[MapRegion]:
    return [
        MapRegion(
            id="controlplane", kind="controlplane", label="Control plane",
            x=2, y=1, w=64, h=8,
            description=(
                "The single pane — lit bright when operations run "
                "automated, dim when every action is a person at a "
                "keyboard. One control plane regardless of how many "
                "stacks or sites sit beneath it is most of what these "
                "products sell."
            ),
        ),
        MapRegion(
            id="pipeline", kind="pipeline", label="CI/CD pipeline",
            x=70, y=1, w=13, h=8,
            description=(
                "Automation Studio's territory: infrastructure changes "
                "as pipelines with a test→prod gate. Lit when the gate "
                "exists; the bad-change event shows what it's for."
            ),
        ),
        MapRegion(
            id="catalog", kind="catalog", label="Catalog",
            x=86, y=1, w=12, h=8,
            description=(
                "The self-service catalog — deploys in minutes against "
                "artisanal installs in days. Lit when enabled."
            ),
        ),
        MapRegion(
            id="wan", kind="wan", label="WAN",
            x=2, y=12, w=96, h=5,
            description=(
                "The link between the control plane and the estate. "
                "NativeEdge's personality lives in what happens when "
                "this goes dark: sites run autonomously, drift "
                "accumulates, and reconciliation happens on reconnect."
            ),
        ),
        MapRegion(
            id="sites", kind="site", label="Sites",
            x=2, y=20, w=96, h=9,
            description=(
                "The estate's footprint — one datacenter cluster or a "
                "thousand shops. Deploying a site costs 8 admin-hours "
                "by hand and half an hour zero-touch; at 500 sites that "
                "difference is a department."
            ),
        ),
        MapRegion(
            id="nodes", kind="node", label="Nodes",
            x=2, y=32, w=96, h=10,
            description=(
                "The servers. Colored by health: deterministic wear "
                "faults arrive every 3,000 node-days, and whether one "
                "is a 2-minute failover or a 4-hour outage is decided "
                "entirely by the N+1 headroom above."
            ),
        ),
        MapRegion(
            id="workloads", kind="workload", label="Workloads",
            x=2, y=45, w=96, h=9,
            description=(
                "The VMs/containers the estate exists for, colored by "
                "how full the surviving capacity is. Demand grows "
                "monthly whether or not anyone patches anything."
            ),
        ),
        MapRegion(
            id="ops", kind="ops", label="Admin-hours ledger",
            x=2, y=57, w=46, h=8,
            description=(
                "The teaching instrument: every action costs hours, "
                "the team has 16 a day, and work beyond that backlogs "
                "— which is how fleets quietly fall a version behind."
            ),
        ),
        MapRegion(
            id="economics", kind="economics", label="Economics",
            x=52, y=57, w=46, h=8,
            description=(
                "APEX's layer: committed base + overage vs owned "
                "capacity amortized. Colored by commitment "
                "utilization — paying for air shows up here. The "
                "overage premium is a generic consumption model, not "
                "Dell's rate card."
            ),
        ),
    ]


def _map(map_id: str, name: str, gen: str, overview: str,
         sources: list[dict[str, str]]) -> FleetMap:
    return FleetMap(
        id=map_id,
        name=name,
        vendor="Dell Technologies",
        form_factor="Fleet-operations view",
        generation=gen,
        year=2026,
        width=100,
        height=67,
        overview=overview,
        regions=_regions(),
        sources=[
            {"label": "physics_specs/04-cloud-edge-automation.md (this repo)",
             "url": "../physics_specs/04-cloud-edge-automation.md"},
            *sources,
        ],
    )


VXRAIL = _map(
    "vxrail",
    "VxRail · lifecycle-managed HCI",
    "VxRail 8.x–9.x / VCF era",
    L(
        novice=(
            "A cluster of identical servers that pools its drives into "
            "shared storage, sold with one distinctive promise: the "
            "whole stack updates as one button-press, rolling node by "
            "node while spare capacity keeps every workload alive. Run "
            "the same update in manual mode and it becomes days of "
            "per-node work with a compatibility checklist. The other "
            "lesson is the three-node trap: the smallest standard "
            "cluster (two-node sites exist, but lean on an outside "
            "witness) has nowhere to rebuild when one node dies — "
            "minimums exist because arithmetic, not marketing."
        ),
        standard=(
            "The HCI personality: the lifecycle bundle IS the product. "
            "One-click updates roll drain→patch→return under N+1 "
            "(watch the updating flag with zero outage minutes); "
            "manual mode pays 2 h/node against the 16 h/day budget and "
            "falls behind the monthly release wave — version currency "
            "is the honest gauge. FTT trades capacity for tolerated "
            "failures, and the 3-node FTT=1 cluster demonstrates the "
            "trap: one fault leaves no rebuild target (the exposure "
            "flag). Companion narrative: DellVxRail (:5179)."
        ),
        expert=(
            "LCM bundle: rolling update under N+1, zero outage. "
            "Manual: 2 h/node vs 16 h/day → currency decays. FTT vs "
            "capacity; 3-node FTT=1 → exposure on first fault."
        ),
    ),
    sources=[
        {"label": "Dell VxRail Architecture Overview — sizing considerations (3-node clusters cannot self-heal)",
         "url": "https://www.dell.com/support/manuals/en-us/vxrail-appliance-series/vxrail_architecture_guide/sizing-considerations?guid=guid-b6878555-6aef-488f-80d1-e6d093b7bea9&lang=en-us"},
        {"label": "Dell VxRail Network Planning Guide — 2-node cluster (fixed at two nodes, requires a witness)",
         "url": "https://www.dell.com/support/manuals/en-us/vxrail-appliance-series/vxrail_planning_guide/2-node-cluster?guid=guid-519032f2-5b7e-43de-a822-823b4fb9b591&lang=en-us"},
        {"label": "VMware Cloud Foundation blog, June 2026 — VCF 9.1 path for VxRail customers (VxRail LCM stays integrated)",
         "url": "https://blogs.vmware.com/cloud-foundation/2026/06/16/vmware-cloud-foundation-9-1-path-for-dell-vxrail-customers/"},
    ],
)

PRIVATECLOUD = _map(
    "privatecloud",
    "Dell Private Cloud · disaggregated, catalog-driven",
    "Dell Automation Platform",
    L(
        novice=(
            "Two different cloud software stacks — say VMware and "
            "OpenShift — living under one management roof. The point "
            "is that adding the second stack doesn't double the "
            "operations bill, because one control plane runs both. "
            "The other point is the catalog: deploying a standard "
            "workload from a menu takes minutes, while building the "
            "same thing by hand takes days. Same outcome, two "
            "invoices for human time."
        ),
        standard=(
            "Stack pluralism under one control plane: two clusters, "
            "two hypervisors, one admin-hours curve (compare against "
            "running the sim twice). Catalog vs artisanal is the "
            "other ledger entry: 0.25 h against 16 h per workload. "
            "The DellPrivateCloud twin (:5198) argues the "
            "architecture; this app prices its operations."
        ),
        expert=(
            "2 stacks ⇒ ~1× ops (shared plane). Catalog 0.25 h vs "
            "artisanal 16 h. The twin argues; this app invoices."
        ),
    ),
    sources=[
        {"label": "Dell Private Cloud product page",
         "url": "https://www.dell.com/en-us/shop/dell-private-cloud/sf/private-cloud"},
        {"label": "Dell blog — Dell Private Cloud expands choice with Nutanix support (alongside VMware vSphere and Red Hat OpenShift)",
         "url": "https://www.dell.com/en-us/blog/dell-private-cloud-expands-choice-with-nutanix-support/"},
    ],
)

APEX = _map(
    "apex",
    "APEX · as-a-service consumption",
    "Dell APEX Infrastructure (Flex on Demand)",
    L(
        novice=(
            "Here nothing is bought — capacity is subscribed to: a "
            "committed base you always pay for, a buffer above it, "
            "and premium rates beyond that (a common rental shape "
            "used here for teaching; Dell says its own APEX offer "
            "charges one rate with no overage fees). Whether that beats "
            "owning depends entirely on the shape of your demand: "
            "spiky demand loves subscriptions (you stop paying for "
            "idle peaks), flat demand loves ownership (subscription "
            "margins buy you nothing). The buffer is the real "
            "decision — too small and you run out of cloud, too big "
            "and you rent air."
        ),
        standard=(
            "Pure Archetype F on the fleet: bill = base + overage×1.5 "
            "vs owned capacity amortized at ~2/3 the committed rate. "
            "The demand-curve selector is the whole lesson — spiky "
            "favors as-a-service ($/VM-hour crossover asserted in "
            "tests), steady favors ownership — and the buffer slider "
            "prices both failure modes: capacity outages under it, "
            "idle spend above it. Rates are estimates; the shape is "
            "the truth. The 1.5× overage is the generic consumption "
            "model, not Dell's rate card: Dell states APEX "
            "Infrastructure (Flex on Demand) bills committed plus "
            "metered buffer at a single rate with no overage fees, "
            "capped at 85% of installed capacity on storage-metered "
            "offers."
        ),
        expert=(
            "asvc = base + 1.5×overage; capex = amortized·capacity. "
            "Spiky → asvc wins, flat → capex wins; buffer trades "
            "outage vs air. Shape, not price. 1.5× is generic; Dell "
            "states single-rate buffer, 85% billing cap."
        ),
    ),
    sources=[
        {"label": "Dell APEX Infrastructure (Flex on Demand) — committed + buffer capacity, single rate, 85% billing cap",
         "url": "https://www.dell.com/en-us/dt/payment-solutions/flexible-consumption/flex-on-demand.htm"},
    ],
)

NATIVEEDGE = _map(
    "nativeedge",
    "NativeEdge / Distributed Private Cloud · edge fleets",
    "Dell Automation Platform (rebrand kept visible)",
    L(
        novice=(
            "Hundreds of small sites — shops, factories, clinics — "
            "each with one or two small servers and nobody technical "
            "on staff. The product's whole argument is the delivery "
            "van: a box arrives, someone plugs in power and network, "
            "and the machine proves its identity and configures "
            "itself. Half an hour of remote effort instead of a "
            "day's site visit — multiplied by five hundred sites. "
            "When the network to a site dies, the site keeps "
            "running alone and syncs up when the line returns."
        ),
        standard=(
            "The fleet engine's most extreme use case: deploy-sites "
            "at 0.5 h zero-touch vs 8 h manual (the 500-store "
            "admin-hours bill is the headline test), 2-node HA vs "
            "the single-node truck-roll day (1,440 outage minutes), "
            "and disconnected operation — WAN down means autonomy "
            "plus drift, reconciled on reconnect. Dell's 2026 rename "
            "of NativeEdge to Distributed Private Cloud is kept "
            "visible, per spec. "
            "Narrative companion: DellNativeEdge (:5187)."
        ),
        expert=(
            "0.5 vs 8 h/site ×500. 2-node HA vs truck-roll day. "
            "WAN-down → autonomy + drift → reconcile. The rebrand "
            "stays on the label."
        ),
    ),
    sources=[
        {"label": "Dell Distributed Private Cloud (previously Dell NativeEdge) product page",
         "url": "https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/nativeedge"},
        {"label": "SDxCentral — Dell Private Cloud gains VMware support, 'edge' is now 'distributed' (2026 rename, zero-touch endpoint support)",
         "url": "https://www.sdxcentral.com/news/dell-private-cloud-gains-requested-vmware-support-edge-is-now-distributed/"},
    ],
)

AUTOMATIONSTUDIO = _map(
    "automationstudio",
    "Automation Studio · infrastructure as pipelines",
    "Dell Automation Platform toolkit (introduced May 2026)",
    L(
        novice=(
            "The finishing school: infrastructure changes written as "
            "pipelines — build, test, then and only then production. "
            "The simulator's demonstration is blunt: push a bad "
            "change with the test gate on and the log shows it "
            "caught, harmless; push it without the gate and "
            "production takes a four-hour outage. Pipelines also "
            "re-run, which quietly erases configuration drift — "
            "enforcement as a side effect."
        ),
        standard=(
            "The integrator, built last per spec: changes as "
            "pipelines over the same fleet engine. The bad-change "
            "event is the argument — gate on: caught-in-test log "
            "line, zero outage minutes; gate off: 240 outage "
            "minutes. Pipeline re-runs reconcile drift "
            "(enforcement), and the pipeline-vs-clicks admin-hours "
            "comparison is the same order-of-magnitude story the "
            "whole file tells. Dell describes the product as a "
            "CI/CD-native orchestration toolkit (blueprints, "
            "Terraform/Ansible reuse); the test gate is this app's "
            "model of such a pipeline, not a documented feature."
        ),
        expert=(
            "Gate on: caught, 0 min. Off: 240 min. Re-runs = drift "
            "enforcement. Pipelines vs clicks = the file's one "
            "lesson, again."
        ),
    ),
    sources=[
        {"label": "Dell Automation Studio product page — CI/CD-native infrastructure orchestration toolkit",
         "url": "https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/automation-studio"},
        {"label": "Dell blog, May 2026 — Dell Ushers in the Agentic Era of IT Operations (introduces Automation Studio)",
         "url": "https://www.dell.com/en-us/blog/dell-ushers-in-the-agentic-era-of-it-operations/"},
    ],
)


MAPS: dict[str, FleetMap] = {
    "vxrail": VXRAIL,
    "privatecloud": PRIVATECLOUD,
    "apex": APEX,
    "nativeedge": NATIVEEDGE,
    "automationstudio": AUTOMATIONSTUDIO,
}
