"""Pure cloud engine for the Dell Private Cloud disaggregated-infrastructure
twin.

``simulate()`` returns the deterministic trace of a private cloud being
built from separate pools, running workloads, growing *one* resource, and
then acquiring a second hypervisor beside the first — with nothing above
the infrastructure layer noticing any of it. Same purity rule as every
other twin in this repo: no FastAPI, no IO, no timers — the frontend owns
the playback clock, and each ``CloudState`` is plain data the renderer
consumes. (``leveling`` imports nothing but ``typing``, so wrapping the
prose in ``L(...)`` leaves the engine as pure as it was.)

The idea this twin exists to teach: **you can change your mind.**

This repo's VxRail twin models the opposite bargain, and the two are meant
to be read together. Hyperconverged infrastructure fused compute and
storage into one node and bought real, substantial simplicity with that
coupling. The price was paid in two currencies. You scale in fixed ratios,
so needing storage means buying processors as well, and estates routinely
end up with a third more of one resource than they will ever use — racked,
powered, and depreciating. And the software stack that performs the magic
is the stack you are married to for the life of the estate.

Disaggregation un-buys the coupling while keeping most of the simplicity,
because a single control plane now provides what the fused node used to.
Compute, storage, and networking are pooled separately and bought
separately; the hypervisor becomes a swappable layer — VMware, Red Hat,
Nutanix (added February 2026), or Microsoft. Dell cites research that 52%
of IT leaders are weighing multiple hypervisors to reduce lock-in.

Worth being honest about why this is possible now rather than in 2012. The
idea was never clever; hyperconvergence won for a decade because crossing a
network to reach storage cost more than keeping the drives local. The
architecture did not get smarter — the interconnect got fast enough that
the compromise stopped being necessary.

Two counters carry the claim. ``workloads`` and
``workload_downtime_seconds`` hold still through both the storage expansion
and the hypervisor migration, and ``control_planes`` stays at one even with
two hypervisors running — because multi-hypervisor is not worth having if
it also means multi-management. ``tests/test_engine.py`` asserts both.

Counts and timings are illustrative but plausible; favor a correct mental
model over measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import CloudState

# The pools, and the four interchangeable hypervisor slots.
POOLS = ["compute", "storage", "network"]
HYPERVISORS = ["hv-vmware", "hv-redhat", "hv-nutanix", "hv-microsoft"]

# Phases in which each resource is legitimately allowed to change. Anything
# else moving is the coupling this architecture exists to remove.
COMPUTE_CHANGE_PHASES = {"pools"}
STORAGE_CHANGE_PHASES = {"pools", "growstorage"}

# Phases from which workloads are running and must not be disturbed.
SERVING_PHASES = {"deploy", "run", "growstorage", "switch", "mixed"}


def simulate() -> list[CloudState]:
    """A private cloud that keeps its options open."""
    return [
        CloudState(
            step=0,
            phase="off",
            label="Racks of separate compute, storage, and networking",
            description=L(
                novice=(
                    "We are starting with three separate piles of "
                    "equipment. One pile is servers — the computers that "
                    "run programs. One is storage — the machines that hold "
                    "files. One is switches, which are the boxes that let "
                    "everything talk to everything else. Right now none of "
                    "it is connected or configured. The question this whole "
                    "story answers is how you join them together without "
                    "locking yourself into decisions you will regret."
                ),
                plain=(
                    "Servers in one rack, storage in another, switches in a "
                    "third. This is the classic way data centres were built, "
                    "and the industry moved away from it because running it "
                    "meant three separate teams and three separate tools. "
                    "Nothing is assembled yet. The question ahead is whether "
                    "you can get the convenience of the newer approach "
                    "without also inheriting its restrictions."
                ),
                standard=(
                    "Servers in one place, storage in another, switches in a "
                    "third. This is what the industry called three-tier "
                    "architecture and spent a decade moving away from, "
                    "because operating it meant three teams, three consoles, "
                    "and three procurement conversations. Nothing here is "
                    "assembled yet, and the interesting question for "
                    "everything that follows is whether the simplicity of "
                    "hyperconverged infrastructure can be recovered without "
                    "also recovering its coupling."
                ),
                technical=(
                    "Classic three-tier: separate compute, storage, and "
                    "switching. The industry left it for HCI because "
                    "operating it meant three teams, three consoles, and "
                    "three procurement cycles. Nothing is assembled. The "
                    "question for the rest of the trace is whether HCI's "
                    "operational simplicity survives without HCI's coupling."
                ),
                expert=(
                    "Three-tier, unassembled. The open question: can the HCI "
                    "operational model be recovered without the fused-node "
                    "scaling ratio and the platform commitment that paid "
                    "for it?"
                ),
            ),
            active_regions=[],
            compute_units=0,
            storage_tb=0,
            hypervisors_active=0,
            workloads=0,
            control_planes=0,
            workload_downtime_seconds=0,
            elapsed_minutes=0,
        ),
        CloudState(
            step=1,
            phase="pools",
            label="Resources pooled independently — not fused into nodes",
            description=L(
                novice=(
                    "The forty-eight servers are grouped into one shared "
                    "set. The storage is grouped into another. The network "
                    "gear into a third. The important word is *separately*. "
                    "There is a popular alternative design where every box "
                    "contains both computing power and storage, so you buy "
                    "them together and always in the same proportion. Here "
                    "they are three different purchases, and they stay "
                    "three different purchases forever."
                ),
                plain=(
                    "Forty-eight servers become a compute pool, 200 TB "
                    "becomes a storage pool, and the switching becomes a "
                    "network pool. They are pooled *independently*. In a "
                    "hyperconverged cluster — where each box carries "
                    "processors and drives together — these would be one "
                    "set of identical nodes, with the balance between "
                    "computing and storage fixed by whichever model you "
                    "ordered. Here the three quantities are three separate "
                    "decisions."
                ),
                standard=(
                    "Forty-eight servers become a compute pool; 200 TB "
                    "becomes a storage pool; the switching becomes a network "
                    "pool. The word doing the work is *independently*. On a "
                    "hyperconverged cluster — this repo's VxRail twin — "
                    "these would not be three pools but one set of nodes, "
                    "each carrying processors and drives together, and the "
                    "ratio between them fixed by whichever model was "
                    "ordered. Here the three quantities are three separate "
                    "decisions, and they stay separate for the life of the "
                    "estate."
                ),
                technical=(
                    "48 servers, 200 TB, and the switching become three "
                    "independent pools. On an HCI cluster these would be one "
                    "set of nodes with the compute-to-capacity ratio fixed "
                    "at the SKU level. Here they are three separate "
                    "decisions, and they stay separate for the life of the "
                    "estate."
                ),
                expert=(
                    "Three pools rather than one node class: 48 compute, "
                    "200 TB, switching. No fixed compute-to-capacity ratio "
                    "baked in at procurement."
                ),
            ),
            active_regions=[*POOLS, "fabric"],
            compute_units=48,
            storage_tb=200,
            hypervisors_active=0,
            workloads=0,
            control_planes=0,
            workload_downtime_seconds=0,
            elapsed_minutes=30,
            cycle_cost=2,
        ),
        CloudState(
            step=2,
            phase="control",
            label="One control plane claims all three pools",
            description=L(
                novice=(
                    "A single piece of management software takes charge of "
                    "all three pools. This matters more than it sounds. "
                    "Splitting the equipment into separate pools would "
                    "otherwise mean going back to managing three things "
                    "separately, which is exactly the tedium everyone was "
                    "trying to escape. One place to set things up, watch "
                    "them, and update them means you get the convenience "
                    "without the restriction. Watch this number — it stays "
                    "at one for the rest of the story."
                ),
                plain=(
                    "One management system takes charge of all three pools. "
                    "This is what makes separating them worth doing. Without "
                    "it you are back to managing compute, storage, and "
                    "network as three separate jobs, which is what people "
                    "moved away from. The control plane gives you the single "
                    "place to provision, monitor, and patch that the "
                    "all-in-one box used to give you. Note the number: one, "
                    "and it does not change again."
                ),
                standard=(
                    "The component that makes disaggregation worth doing "
                    "rather than merely possible. Without it this is the old "
                    "three-tier world with better hardware, and the industry "
                    "already decided how it feels about that. The control "
                    "plane provides the unified operational experience the "
                    "fused node used to provide — one place to provision, "
                    "monitor, and patch — so what is left is HCI's "
                    "simplicity without HCI's coupling. Note the number, "
                    "because it does not change again for the rest of this "
                    "trace: one."
                ),
                technical=(
                    "The component that makes disaggregation worth doing "
                    "rather than merely possible — without it this is "
                    "three-tier with better hardware. The control plane "
                    "supplies the unified provisioning, monitoring, and "
                    "patching the fused node used to, leaving HCI's "
                    "simplicity without HCI's coupling. The count stays at "
                    "one for the rest of the trace."
                ),
                expert=(
                    "Unified control plane over all three pools. Without it, "
                    "disaggregation is just three-tier. Count holds at one "
                    "throughout — including under two hypervisors."
                ),
            ),
            active_regions=[*POOLS, "fabric", "control"],
            compute_units=48,
            storage_tb=200,
            hypervisors_active=0,
            workloads=0,
            control_planes=1,
            workload_downtime_seconds=0,
            elapsed_minutes=45,
        ),
        CloudState(
            step=3,
            phase="install",
            label="A hypervisor is chosen — and it is a choice",
            description=L(
                novice=(
                    "Now we install a hypervisor. That is the software layer "
                    "that lets one physical server pretend to be many "
                    "separate computers, so a hundred programs can share "
                    "forty-eight machines safely. VMware goes on first, "
                    "because it is what this organization already uses. The "
                    "word to notice is *chosen*. In the all-in-one approach "
                    "this software is baked in — you picked it when you "
                    "bought the hardware and you are stuck with it. Here it "
                    "sits in a slot, with three empty slots beside it."
                ),
                plain=(
                    "VMware is installed as the hypervisor — the layer that "
                    "divides physical servers into virtual ones. It goes on "
                    "first because it is what this estate already runs, and "
                    "there is no reason to change everything at once. The "
                    "significant word is *chosen*. In a hyperconverged "
                    "system the hypervisor is not something you select "
                    "later; it is part of what you bought. Here it fills one "
                    "slot and three sit empty beside it."
                ),
                standard=(
                    "VMware goes on first, because that is what this estate "
                    "already runs and there is no reason to change "
                    "everything at once. The significant thing is the word "
                    "'chosen'. In a hyperconverged system the hypervisor is "
                    "not a layer you select, it is the thing the "
                    "architecture is made of, and the decision was taken "
                    "when the hardware was ordered. Here it sits in a slot "
                    "with three empty ones beside it, and the estate below "
                    "it does not care which slot is filled."
                ),
                technical=(
                    "VMware first, because that is the incumbent and there "
                    "is no case for changing everything at once. The word is "
                    "'chosen': in HCI the hypervisor is not a selectable "
                    "layer, it is what the architecture is made of, and the "
                    "decision was taken at the purchase order. Here it fills "
                    "one slot of four and the pools beneath are indifferent."
                ),
                expert=(
                    "VMware installed as incumbent. Hypervisor is a "
                    "selectable layer, not an architectural substrate — one "
                    "slot of four, pools indifferent."
                ),
            ),
            active_regions=[*POOLS, "fabric", "control", "hv-vmware"],
            compute_units=48,
            storage_tb=200,
            hypervisors_active=1,
            workloads=0,
            control_planes=1,
            workload_downtime_seconds=0,
            elapsed_minutes=70,
            cycle_cost=2,
        ),
        CloudState(
            step=4,
            phase="deploy",
            label="120 workloads land",
            description=L(
                novice=(
                    "A hundred and twenty workloads start up. A workload is "
                    "just an application doing its job — a website, a "
                    "database, a payroll system. These are the only things "
                    "in this whole diagram that anyone outside the "
                    "technology team actually cares about. From here on, the "
                    "test of everything underneath is simple: when the "
                    "infrastructure changes, do the applications notice? "
                    "Keep an eye on this count and on the downtime figure. "
                    "Neither is going to move again."
                ),
                plain=(
                    "A hundred and twenty virtual machines and containers "
                    "start running — the applications this whole estate "
                    "exists to serve. They are the only things here that "
                    "anyone outside the infrastructure team cares about, and "
                    "from now on the test of every layer beneath them is "
                    "whether changes down there are visible up here. Watch "
                    "this number and the downtime counter for the rest of "
                    "the trace."
                ),
                standard=(
                    "Virtual machines and containers arrive — the only "
                    "things in this entire diagram that anyone outside the "
                    "infrastructure team cares about. From here on, the test "
                    "of every layer beneath them is whether changes down "
                    "there are visible up here. Watch this number and the "
                    "downtime counter for the rest of the trace: the storage "
                    "pool will double and a second hypervisor will appear, "
                    "and neither of these two figures will move."
                ),
                technical=(
                    "120 VMs and containers land — the only tenants of this "
                    "diagram anyone outside infrastructure cares about. The "
                    "test of every layer beneath is whether its changes "
                    "surface here. Storage will double and a second "
                    "hypervisor will appear; neither this count nor the "
                    "downtime counter moves."
                ),
                expert=(
                    "120 workloads deployed. Baseline for the two "
                    "invariants: constant workload count and zero downtime "
                    "across both the capacity expansion and the hypervisor "
                    "migration."
                ),
            ),
            active_regions=[*POOLS, "fabric", "control", "hv-vmware", "workloads"],
            compute_units=48,
            storage_tb=200,
            hypervisors_active=1,
            workloads=120,
            control_planes=1,
            workload_downtime_seconds=0,
            elapsed_minutes=100,
        ),
        CloudState(
            step=5,
            phase="run",
            label="Steady state",
            description=L(
                novice=(
                    "Everything is running normally. One management system, "
                    "one hypervisor, three pools of equipment, a hundred and "
                    "twenty applications. Nobody is thinking about how any "
                    "of it was designed, and the choices made when it was "
                    "purchased have not yet helped or hurt anyone. That is "
                    "worth saying plainly: you cannot tell a good "
                    "infrastructure design from a bad one while everything "
                    "is working. You find out when something has to change."
                ),
                plain=(
                    "The ordinary working state, and the baseline for the "
                    "next two steps. One control plane, one hypervisor, "
                    "three pools, 120 workloads. Everything works, nobody is "
                    "thinking about the architecture, and the decisions made "
                    "at purchase have not yet cost or saved anybody "
                    "anything. Designs are not judged here. They are judged "
                    "when something has to change."
                ),
                standard=(
                    "The ordinary condition of the system, and the baseline "
                    "against which the next two steps should be read. One "
                    "control plane, one hypervisor, three pools, 120 "
                    "workloads. Everything is working, nobody is thinking "
                    "about the architecture, and the choices made at "
                    "procurement have not yet cost or saved anybody "
                    "anything. Architectures are not judged here. They are "
                    "judged when something has to change."
                ),
                technical=(
                    "Baseline for the next two steps: one control plane, one "
                    "hypervisor, three pools, 120 workloads. Procurement "
                    "decisions have not yet cost or saved anything. "
                    "Architectures are not judged in steady state; they are "
                    "judged at the change."
                ),
                expert=(
                    "Steady state — the baseline. Architectural choices are "
                    "invisible here and priced at the next change."
                ),
            ),
            active_regions=[*POOLS, "fabric", "control", "hv-vmware", "workloads"],
            compute_units=48,
            storage_tb=200,
            hypervisors_active=1,
            workloads=120,
            control_planes=1,
            workload_downtime_seconds=0,
            elapsed_minutes=160,
        ),
        CloudState(
            step=6,
            phase="growstorage",
            label="Storage doubles — and not one server is added",
            description=L(
                novice=(
                    "They run out of space, so they add 200 TB more storage. "
                    "Now look at the server count: still forty-eight. "
                    "Nothing was added there. This is the moment the whole "
                    "design pays off. In the all-in-one approach, more space "
                    "means buying another complete box, and that box arrives "
                    "with processors and memory whether or not anyone needed "
                    "them — sitting in the rack, drawing power, losing value "
                    "every year. That is not a rare mistake. It is what "
                    "normally happens, and it is why so many organizations "
                    "own far more of one resource than they will ever use."
                ),
                plain=(
                    "Capacity runs short, so 200 TB of storage is added. The "
                    "compute figure does not move: still forty-eight "
                    "servers. On a hyperconverged cluster the same need is "
                    "met by adding nodes, and a node brings processors and "
                    "memory along whether or not there is demand for them — "
                    "so the estate ends up owning compute it does not need, "
                    "racked, powered, licensed, and losing value. There is "
                    "also a lifecycle point: servers and storage wear out on "
                    "different schedules, and fusing them forces the shorter "
                    "schedule on both."
                ),
                standard=(
                    "The estate runs short of capacity, so 200 TB more "
                    "storage is added. Look at the compute figure: "
                    "unchanged, at forty-eight. On a hyperconverged cluster "
                    "this same need would have been met by adding nodes, and "
                    "nodes bring processors and memory whether or not there "
                    "is any demand for them — so the estate would now own "
                    "compute it does not need, racked, powered, licensed, "
                    "and depreciating. That is not a hypothetical "
                    "inefficiency; it is the routine outcome, and it is why "
                    "estates so often carry a third more of one resource "
                    "than they will ever use. There is also a lifecycle "
                    "version of the same point: servers and storage have "
                    "genuinely different useful lives, and fusing them "
                    "imposes the shorter one on both."
                ),
                technical=(
                    "Capacity short, so 200 TB is added and compute holds at "
                    "48. On HCI the same requirement is met by adding nodes, "
                    "which drag processors and memory in at the SKU ratio — "
                    "stranded capacity, racked, powered, licensed, "
                    "depreciating. It is the routine outcome, not an edge "
                    "case. The lifecycle argument is the same shape: compute "
                    "and storage have different useful lives, and fusion "
                    "imposes the shorter on both."
                ),
                expert=(
                    "+200 TB, compute unchanged at 48. HCI meets this by "
                    "node addition at a fixed SKU ratio, stranding compute. "
                    "Same argument applies to refresh cadence: fusion "
                    "imposes the shorter useful life on both resources."
                ),
            ),
            active_regions=[*POOLS, "fabric", "control", "hv-vmware", "workloads"],
            compute_units=48,
            storage_tb=400,
            hypervisors_active=1,
            workloads=120,
            control_planes=1,
            workload_downtime_seconds=0,
            elapsed_minutes=220,
            cycle_cost=3,
        ),
        CloudState(
            step=7,
            phase="switch",
            label="Some workloads move to a second hypervisor",
            description=L(
                novice=(
                    "Some of the applications are moved onto a different "
                    "hypervisor — Nutanix — while the rest stay on VMware. "
                    "This step takes by far the longest, and that is honest: "
                    "moving applications between two different "
                    "virtualization platforms is genuinely hard work. Files "
                    "have to be converted, everything has to be retested, "
                    "and small details often do not carry across cleanly. "
                    "Nobody should tell you this is easy. The point is that "
                    "it is *possible at all*, and that the applications keep "
                    "running while it happens. With the all-in-one approach "
                    "the alternative is not a slow move — it is buying an "
                    "entirely new set of equipment."
                ),
                plain=(
                    "Part of the estate moves onto Nutanix — supported in "
                    "Dell Private Cloud since February 2026 — while the rest "
                    "stays on VMware. This is slow, and the trace says so "
                    "honestly: migrating workloads between virtualization "
                    "platforms means converting disk formats, retesting "
                    "everything, and handling the details that do not "
                    "translate cleanly. The freedom is real but it is not "
                    "free, and anyone selling it as effortless is selling "
                    "something. What matters is that it is possible at all, "
                    "and that the workloads stay up while it happens."
                ),
                standard=(
                    "The long stage, and the one that justifies the whole "
                    "architecture. A portion of the estate moves onto "
                    "Nutanix — supported in Dell Private Cloud since "
                    "February 2026 — while the rest stays on VMware. This is "
                    "slow, and the trace says so honestly: migrating "
                    "workloads between virtualization platforms is real "
                    "work, involving format conversion, testing, and a great "
                    "deal of care about the things that do not translate "
                    "cleanly. The freedom is genuine but it is not free, and "
                    "anyone selling it as effortless is selling something. "
                    "What matters is that it is *possible* at all, and that "
                    "the workloads stay up throughout — the alternative, in "
                    "a coupled architecture, is not a slow migration but a "
                    "new estate."
                ),
                technical=(
                    "The long stage, and the one that justifies the "
                    "architecture. A tranche moves to Nutanix — supported "
                    "since February 2026 — while the rest stays on VMware. "
                    "It is slow and the trace says so: format conversion, "
                    "regression testing, and the guest tooling, snapshot, "
                    "and network constructs that do not translate. The "
                    "freedom is real and not free. The claim is that it is "
                    "possible without an outage; in a coupled architecture "
                    "the alternative is not a slow migration but a new "
                    "estate."
                ),
                expert=(
                    "Partial migration to Nutanix, VMware retained. "
                    "Expensive — format conversion, regression, untranslated "
                    "guest tooling and network constructs. Claim is "
                    "feasibility without outage, not speed. Coupled "
                    "alternative is a rebuild, not a migration."
                ),
            ),
            active_regions=[
                *POOLS, "fabric", "control", "hv-vmware", "hv-nutanix", "workloads",
            ],
            compute_units=48,
            storage_tb=400,
            hypervisors_active=2,
            workloads=120,
            control_planes=1,
            workload_downtime_seconds=0,
            elapsed_minutes=520,
            cycle_cost=6,
        ),
        CloudState(
            step=8,
            phase="mixed",
            label="Two hypervisors, one control plane, steady",
            description=L(
                novice=(
                    "Two different hypervisors are now running side by side, "
                    "and the management count is still one. That is the "
                    "number to stare at. Running two platforms is only an "
                    "improvement if the people operating them do not also "
                    "end up with two sets of tools, two update schedules, "
                    "and two sets of habits to remember. Otherwise "
                    "'we support both' just means twice the work. And what "
                    "this organization has really bought is not VMware or "
                    "Nutanix. It is the ability to have this argument again "
                    "next year, with better information, without it meaning "
                    "starting over."
                ),
                plain=(
                    "Two hypervisors, and the control-plane count is still "
                    "one. Running two platforms only helps if the operators "
                    "do not also acquire a second console, a second patching "
                    "schedule, and a second set of habits — otherwise "
                    "'multi-hypervisor support' means 'we will sell you both "
                    "problems'. What the estate has actually bought is not "
                    "Nutanix or VMware. It is the ability to revisit the "
                    "decision next year, with different information, without "
                    "it being a rebuild."
                ),
                standard=(
                    "The end state, and the number worth staring at is the "
                    "control-plane count: still one. Running two hypervisors "
                    "is only an improvement if the operators do not also "
                    "acquire a second console, a second patching schedule, "
                    "and a second set of habits — otherwise 'multi-hypervisor "
                    "support' means 'we will sell you both problems', which "
                    "is the trap most such claims fall into. What the estate "
                    "has actually bought is not Nutanix or VMware. It is the "
                    "ability to have this argument again next year, with "
                    "different information, without it being a rebuild. That "
                    "optionality is the product, and it is the one thing a "
                    "specification sheet cannot show you."
                ),
                technical=(
                    "End state, and the figure that matters is the "
                    "control-plane count: one. Two hypervisors only help if "
                    "the operators do not inherit a second console, patching "
                    "cadence, and operational model — otherwise "
                    "'multi-hypervisor support' means both problems sold "
                    "together, which is where most such claims land. What "
                    "was bought is not a hypervisor but the ability to "
                    "revisit the decision without a rebuild. Optionality is "
                    "the product, and no specification sheet shows it."
                ),
                expert=(
                    "Two hypervisors, one control plane. Multi-hypervisor "
                    "without unified management is just both problems. The "
                    "asset acquired is optionality — revisit the platform "
                    "decision without a rebuild — which no spec sheet "
                    "captures."
                ),
            ),
            active_regions=[
                *POOLS, "fabric", "control", "hv-vmware", "hv-nutanix", "workloads",
            ],
            compute_units=48,
            storage_tb=400,
            hypervisors_active=2,
            workloads=120,
            control_planes=1,
            workload_downtime_seconds=0,
            elapsed_minutes=640,
        ),
    ]
