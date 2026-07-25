"""Pure cloud engine for the Dell Private Cloud disaggregated-infrastructure
twin.

``simulate()`` returns the deterministic trace of a private cloud being
built from separate pools, running workloads, growing *one* resource, and
then acquiring a second hypervisor beside the first — with nothing above
the infrastructure layer noticing any of it. Same purity rule as every
other twin in this repo: no FastAPI, no IO, no timers — the frontend owns
the playback clock, and each ``CloudState`` is plain data the renderer
consumes.

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
            description=(
                "Servers in one place, storage in another, switches in a "
                "third. This is what the industry called three-tier "
                "architecture and spent a decade moving away from, because "
                "operating it meant three teams, three consoles, and three "
                "procurement conversations. Nothing here is assembled yet, "
                "and the interesting question for everything that follows "
                "is whether the simplicity of hyperconverged infrastructure "
                "can be recovered without also recovering its coupling."
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
            description=(
                "Forty-eight servers become a compute pool; 200 TB becomes "
                "a storage pool; the switching becomes a network pool. The "
                "word doing the work is *independently*. On a "
                "hyperconverged cluster — this repo's VxRail twin — these "
                "would not be three pools but one set of nodes, each "
                "carrying processors and drives together, and the ratio "
                "between them fixed by whichever model was ordered. Here "
                "the three quantities are three separate decisions, and "
                "they stay separate for the life of the estate."
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
            description=(
                "The component that makes disaggregation worth doing "
                "rather than merely possible. Without it this is the old "
                "three-tier world with better hardware, and the industry "
                "already decided how it feels about that. The control "
                "plane provides the unified operational experience the "
                "fused node used to provide — one place to provision, "
                "monitor, and patch — so what is left is HCI's simplicity "
                "without HCI's coupling. Note the number, because it does "
                "not change again for the rest of this trace: one."
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
            description=(
                "VMware goes on first, because that is what this estate "
                "already runs and there is no reason to change everything "
                "at once. The significant thing is the word 'chosen'. In a "
                "hyperconverged system the hypervisor is not a layer you "
                "select, it is the thing the architecture is made of, and "
                "the decision was taken when the hardware was ordered. "
                "Here it sits in a slot with three empty ones beside it, "
                "and the estate below it does not care which slot is "
                "filled."
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
            description=(
                "Virtual machines and containers arrive — the only things "
                "in this entire diagram that anyone outside the "
                "infrastructure team cares about. From here on, the test "
                "of every layer beneath them is whether changes down there "
                "are visible up here. Watch this number and the downtime "
                "counter for the rest of the trace: the storage pool will "
                "double and a second hypervisor will appear, and neither "
                "of these two figures will move."
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
            description=(
                "The ordinary condition of the system, and the baseline "
                "against which the next two steps should be read. One "
                "control plane, one hypervisor, three pools, 120 "
                "workloads. Everything is working, nobody is thinking "
                "about the architecture, and the choices made at "
                "procurement have not yet cost or saved anybody anything. "
                "Architectures are not judged here. They are judged when "
                "something has to change."
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
            description=(
                "The estate runs short of capacity, so 200 TB more storage "
                "is added. Look at the compute figure: unchanged, at "
                "forty-eight. On a hyperconverged cluster this same need "
                "would have been met by adding nodes, and nodes bring "
                "processors and memory whether or not there is any demand "
                "for them — so the estate would now own compute it does "
                "not need, racked, powered, licensed, and depreciating. "
                "That is not a hypothetical inefficiency; it is the "
                "routine outcome, and it is why estates so often carry a "
                "third more of one resource than they will ever use. "
                "There is also a lifecycle version of the same point: "
                "servers and storage have genuinely different useful "
                "lives, and fusing them imposes the shorter one on both."
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
            description=(
                "The long stage, and the one that justifies the whole "
                "architecture. A portion of the estate moves onto Nutanix "
                "— supported in Dell Private Cloud since February 2026 — "
                "while the rest stays on VMware. This is slow, and the "
                "trace says so honestly: migrating workloads between "
                "virtualization platforms is real work, involving format "
                "conversion, testing, and a great deal of care about the "
                "things that do not translate cleanly. The freedom is "
                "genuine but it is not free, and anyone selling it as "
                "effortless is selling something. What matters is that it "
                "is *possible* at all, and that the workloads stay up "
                "throughout — the alternative, in a coupled architecture, "
                "is not a slow migration but a new estate."
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
            description=(
                "The end state, and the number worth staring at is the "
                "control-plane count: still one. Running two hypervisors "
                "is only an improvement if the operators do not also "
                "acquire a second console, a second patching schedule, and "
                "a second set of habits — otherwise 'multi-hypervisor "
                "support' means 'we will sell you both problems', which is "
                "the trap most such claims fall into. What the estate has "
                "actually bought is not Nutanix or VMware. It is the "
                "ability to have this argument again next year, with "
                "different information, without it being a rebuild. That "
                "optionality is the product, and it is the one thing a "
                "specification sheet cannot show you."
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
