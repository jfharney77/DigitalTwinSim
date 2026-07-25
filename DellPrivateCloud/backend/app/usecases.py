"""Use cases: three private clouds, as backend data.

Each is a build sheet whose category and option ids must resolve against
``catalog.py`` — enforced in ``tests/test_catalog.py``. The narratives are
written for a reader who understands virtualization but has spent a decade
being told that fusing compute and storage was the modern answer.

All three turn on optionality from different angles. What differs is which
option the organization actually needs to keep open — the platform, the
purchase ratio, or the timing.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="hypervisor-exit",
        title="An estate that wants the option to leave, without leaving yet",
        summary=(
            "Renewal is in eighteen months. The goal is not to migrate — "
            "it is to be able to."
        ),
        narrative=[
            "The situation a great many infrastructure teams recognized "
            "at once: a virtualization renewal arrives with a number "
            "attached that nobody budgeted for, and the negotiating "
            "position turns out to be nonexistent, because migrating the "
            "estate is not a project anyone can complete before the "
            "invoice is due. The problem is not the price. The problem is "
            "that there was never an alternative, and a platform you "
            "cannot leave will always eventually price like one.",
            "The useful move is usually not a migration. It is building "
            "the capacity to migrate, which is a much smaller and far less "
            "disruptive undertaking: new capacity goes onto disaggregated "
            "pools under a control plane that supports several "
            "hypervisors, a modest tranche of non-critical workloads moves "
            "to a second platform to prove the path works, and the "
            "remainder stays exactly where it is. The estate has now "
            "demonstrated it can move, which changes the conversation "
            "entirely.",
            "Be honest internally about the cost. Cross-hypervisor "
            "migration is real work — format conversion, testing, and "
            "attention to guest tooling, snapshots, and network constructs "
            "that do not translate cleanly. This twin's trace makes the "
            "migration its longest stage for exactly that reason. The "
            "claim is not that switching is easy; it is that switching is "
            "possible without an outage, and in a coupled architecture the "
            "alternative to a slow migration is a new estate.",
        ],
        config=[
            UseCaseItem(
                category_id="architecture", option_id="mixed-estate", qty=1,
                rationale=(
                    "Nobody replaces a working estate on architectural "
                    "grounds; new capacity goes disaggregated while the "
                    "old runs out its depreciation."
                ),
            ),
            UseCaseItem(
                category_id="hypervisor", option_id="vmware", qty=1,
                rationale=(
                    "Most workloads stay. Staying is a good decision; "
                    "having no alternative is not."
                ),
            ),
            UseCaseItem(
                category_id="hypervisor", option_id="nutanix", qty=1,
                rationale=(
                    "The closest like-for-like target, so proving the path "
                    "does not require relearning virtualization."
                ),
            ),
            UseCaseItem(
                category_id="control", option_id="unified", qty=1,
                rationale=(
                    "Two hypervisors and one console — otherwise this buys "
                    "two problems instead of an option."
                ),
            ),
            UseCaseItem(
                category_id="workloads", option_id="migration", qty=1,
                rationale=(
                    "A modest tranche moved for real, because a migration "
                    "path nobody has walked is a hypothesis."
                ),
            ),
            UseCaseItem(
                category_id="compute", option_id="general-compute", qty=1,
                rationale=(
                    "Sized for the workload mix rather than for a storage "
                    "ratio."
                ),
            ),
            UseCaseItem(
                category_id="storage", option_id="powerstore", qty=1,
                rationale=(
                    "General-purpose block and file for a mixed estate."
                ),
            ),
            UseCaseItem(
                category_id="network", option_id="fabric-design", qty=1,
                rationale=(
                    "Once storage leaves the chassis the fabric is part of "
                    "the storage performance envelope."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Workloads migrated", value="A proving tranche, not the estate"),
            Stat(label="Downtime", value="None"),
            Stat(label="What was bought", value="A negotiating position"),
            Stat(label="Consoles", value="One"),
        ],
    ),
    UseCase(
        id="lopsided-growth",
        title="A business whose data grows and whose compute does not",
        summary=(
            "Capacity doubles every two years; processor demand is flat. "
            "Fixed-ratio scaling has been paying for the wrong resource "
            "for years."
        ),
        narrative=[
            "Some workloads are simply lopsided. Video archives, imaging, "
            "log retention, regulated records — the data grows relentlessly "
            "and the processing required to serve it barely moves. On a "
            "hyperconverged cluster this shape is expensive in a way that "
            "is easy to miss, because the cost does not appear as waste. "
            "It appears as nodes. Capacity is added by adding nodes, and "
            "each node brings processors and memory that the workload will "
            "never ask for — racked, licensed, powered, cooled, and "
            "depreciating for years.",
            "Independent scaling addresses this directly and "
            "unglamorously: storage is added, and nothing else is. This "
            "twin's trace shows the moment — capacity doubles from 200 to "
            "400 TB and the compute figure does not move. It is not a "
            "clever property, and that is rather the point. It is the "
            "obvious behaviour that coupling made impossible.",
            "The lifecycle version of the same argument is the one that "
            "compounds. Servers and storage have genuinely different "
            "useful lives, and fusing them imposes the shorter one on "
            "both. Refreshing servers on a four-year cycle while keeping "
            "storage for seven is straightforward when they are separate "
            "purchases and impossible when they arrive in the same box.",
        ],
        config=[
            UseCaseItem(
                category_id="architecture", option_id="disaggregated", qty=1,
                rationale=(
                    "The whole reason for the build: capacity that grows "
                    "without dragging processors along."
                ),
            ),
            UseCaseItem(
                category_id="storage", option_id="powerscale", qty=1,
                rationale=(
                    "Unstructured growth is the least predictable, so "
                    "independent scaling pays best here."
                ),
            ),
            UseCaseItem(
                category_id="compute", option_id="general-compute", qty=1,
                rationale=(
                    "Modest and flat, because that is what the workload "
                    "actually needs."
                ),
            ),
            UseCaseItem(
                category_id="hypervisor", option_id="microsoft", qty=1,
                rationale=(
                    "Chosen on licensing arithmetic, which drives more of "
                    "these decisions than technical merit does."
                ),
            ),
            UseCaseItem(
                category_id="control", option_id="unified", qty=1,
                rationale=(
                    "Disaggregation without a unified control plane is "
                    "just three-tier again."
                ),
            ),
            UseCaseItem(
                category_id="operations", option_id="observability", qty=1,
                rationale=(
                    "The useful question is which pool runs short and "
                    "when — now answerable as its own purchase."
                ),
            ),
            UseCaseItem(
                category_id="operations", option_id="consumption", qty=1,
                rationale=(
                    "If storage can be added without compute, it can be "
                    "billed without compute."
                ),
            ),
            UseCaseItem(
                category_id="network", option_id="switching", qty=1,
                rationale=(
                    "Traffic here is east-west between pools, not campus "
                    "traffic to users."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Storage growth", value="Doubled, independently"),
            Stat(label="Compute added", value="None"),
            Stat(label="Refresh cycles", value="Servers and storage, decoupled"),
            Stat(label="Stranded capacity", value="Not purchased in the first place"),
        ],
    ),
    UseCase(
        id="platform-team",
        title="A platform team running virtual machines and containers forever",
        summary=(
            "Containers are the direction of travel and the virtual "
            "machines are not going anywhere. One set of pools underneath "
            "both."
        ),
        narrative=[
            "The honest position of most platform teams: new applications "
            "are containerized, the existing estate is virtual machines, "
            "and the virtual machines will still be running in ten years "
            "because a great deal of them work and nobody is funded to "
            "rewrite them. The failure mode is quietly building two "
            "operating models — two provisioning paths, two monitoring "
            "stacks, two on-call rotations — and then maintaining both "
            "indefinitely.",
            "Decoupling the platform from the pools is what prevents that. "
            "The compute, storage, and network underneath are indifferent "
            "to whether a virtual machine or a container is running, so "
            "the second operating model, if it appears at all, appears "
            "only at the platform layer where it is at least visible and "
            "bounded. A hypervisor that runs both workload types on one "
            "platform narrows it further.",
            "This configuration also pairs naturally with declarative "
            "infrastructure. A disaggregated estate whose shape is "
            "expected to change needs its intended shape written down "
            "somewhere authoritative, or the flexibility becomes drift — "
            "which is the subject of the automation spec elsewhere in this "
            "repo. The infrastructure that can change shape and the "
            "discipline of describing what shape it should be are two "
            "halves of one idea.",
        ],
        config=[
            UseCaseItem(
                category_id="architecture", option_id="disaggregated", qty=1,
                rationale=(
                    "Pools indifferent to what runs on them keep the "
                    "second operating model from spreading downward."
                ),
            ),
            UseCaseItem(
                category_id="hypervisor", option_id="redhat", qty=1,
                rationale=(
                    "Virtual machines as a workload type on the platform "
                    "the new applications already target."
                ),
            ),
            UseCaseItem(
                category_id="workloads", option_id="containers", qty=1,
                rationale=(
                    "Both workload types for the foreseeable future; an "
                    "architecture that treats one as a special case "
                    "creates a second model by accident."
                ),
            ),
            UseCaseItem(
                category_id="control", option_id="automation", qty=1,
                rationale=(
                    "An estate expected to change shape needs its intended "
                    "shape written down, or flexibility becomes drift."
                ),
            ),
            UseCaseItem(
                category_id="storage", option_id="powerflex", qty=1,
                rationale=(
                    "Disaggregated storage under a disaggregated cloud — "
                    "nothing in the stack forces a rebuild to change."
                ),
            ),
            UseCaseItem(
                category_id="compute", option_id="accelerated", qty=1,
                rationale=(
                    "GPU nodes join the pool without the estate becoming "
                    "an AI cluster."
                ),
            ),
            UseCaseItem(
                category_id="architecture", option_id="mixed-estate", qty=1,
                rationale=(
                    "Existing hyperconverged clusters run out their "
                    "depreciation alongside the new pools."
                ),
            ),
            UseCaseItem(
                category_id="operations", option_id="observability", qty=1,
                rationale=(
                    "Capacity trends matter more than utilization "
                    "snapshots when the inventory is no longer static."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Operating models", value="One below the platform layer"),
            Stat(label="Workload types", value="Virtual machines and containers"),
            Stat(label="Pools", value="Indifferent to both"),
            Stat(label="Intended shape", value="Written down, not implied"),
        ],
    ),
]
