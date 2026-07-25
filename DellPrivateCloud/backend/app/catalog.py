"""Component catalog: what you actually choose when building a Dell Private
Cloud, as backend data.

Written for a technically skilled reader new to private cloud:
hyperconverged, disaggregated, three-tier, hypervisor, control plane, live
migration, and lock-in are all spelled out on first use. Categories map to
the stack regions in ``anatomy.py`` via ``region_ids``, and
``tests/test_catalog.py`` enforces that every id resolves.

The ordering makes the argument. The first category is the *architecture*
— disaggregated or hyperconverged — because that decision determines
whether any of the later ones remain decisions at all. On a hyperconverged
cluster the hypervisor is not chosen from a catalog; it is what the thing
is made of.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="architecture",
        name="Architecture",
        blurb=(
            "The decision that determines whether the later decisions stay "
            "open."
        ),
        limits="Disaggregated pools, hyperconverged nodes, or both in one estate",
        region_ids=["control", "compute", "storage"],
        options=[
            CatalogOption(
                id="disaggregated",
                name="Disaggregated",
                summary=(
                    "Compute, storage, and networking pooled and scaled "
                    "separately, under one control plane."
                ),
                details=(
                    "The subject of this twin. Resources are bought and "
                    "grown independently, so needing capacity does not mean "
                    "buying processors, and the hypervisor becomes a "
                    "swappable layer rather than the substance of the "
                    "architecture. The historical objection was that "
                    "crossing a network to reach storage cost more than "
                    "keeping drives local — which was true, and is why "
                    "hyperconvergence won for a decade. Current fabric "
                    "speeds have shrunk that penalty to the point where "
                    "the coupling is no longer worth what it costs."
                ),
            ),
            CatalogOption(
                id="hci",
                name="Hyperconverged",
                summary=(
                    "Compute and storage fused into identical nodes; grow "
                    "by adding nodes."
                ),
                details=(
                    "Modelled in full by this repo's VxRail twin, and "
                    "genuinely excellent at what it does — the simplicity "
                    "is real and the operational model is hard to beat for "
                    "estates of predictable shape. The price is coupling. "
                    "Capacity arrives in fixed ratios whether or not the "
                    "ratio suits you, servers and storage are forced onto a "
                    "shared refresh cycle despite having different useful "
                    "lives, and the software stack is a commitment for the "
                    "life of the estate. For a small, stable, "
                    "single-platform environment none of that may ever "
                    "bite."
                ),
            ),
            CatalogOption(
                id="mixed-estate",
                name="Both, in one estate",
                summary=(
                    "Existing hyperconverged clusters alongside new "
                    "disaggregated pools."
                ),
                details=(
                    "The realistic answer for most organizations, because "
                    "nobody replaces a working estate on architectural "
                    "grounds alone. New capacity is built disaggregated "
                    "while existing clusters run out their depreciation, "
                    "and the control plane's job is to make that "
                    "coexistence unremarkable rather than a second "
                    "operating model. Judge a private-cloud platform "
                    "substantially on how well it handles this, since it "
                    "is the state almost every estate is actually in."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="hypervisor",
        name="Hypervisor",
        blurb=(
            "The layer that stopped being a foundation and became a choice."
        ),
        limits="VMware, Red Hat, Nutanix (February 2026), Microsoft",
        region_ids=["hv-vmware", "hv-redhat", "hv-nutanix", "hv-microsoft"],
        options=[
            CatalogOption(
                id="vmware",
                name="VMware",
                summary=(
                    "What most of these estates already run, and for many "
                    "workloads still the most capable option."
                ),
                details=(
                    "Nothing in this twin is an argument against VMware; "
                    "staying is a perfectly good decision and the depth of "
                    "the platform is not in dispute. The argument is "
                    "against having no alternative. A platform you cannot "
                    "leave prices itself accordingly, and the last few "
                    "years turned that abstract concern into a budget line "
                    "for a great many organizations simultaneously — which "
                    "is why 52% of IT leaders now report weighing multiple "
                    "hypervisors."
                ),
            ),
            CatalogOption(
                id="redhat",
                name="Red Hat OpenShift Virtualization",
                summary=(
                    "Virtual machines and containers as workload types on "
                    "one platform."
                ),
                details=(
                    "Compelling where the direction of travel is "
                    "containers anyway: rather than operating a "
                    "virtualization stack and a container stack in "
                    "parallel indefinitely, virtual machines become "
                    "another workload type on the platform new "
                    "applications already target. The honest trade is "
                    "maturity — virtual-machine features that are decades "
                    "old elsewhere are younger here, and the gaps tend to "
                    "be in the unglamorous operational corners rather than "
                    "in the headline capabilities."
                ),
            ),
            CatalogOption(
                id="nutanix",
                name="Nutanix",
                summary=(
                    "Added to Dell Private Cloud in February 2026 — the "
                    "closest like-for-like alternative."
                ),
                details=(
                    "The option for an estate that wants to move without "
                    "relearning how virtualization works, since the "
                    "operational concepts map closely. There is an irony "
                    "worth noticing in this repo's context: Nutanix built "
                    "its reputation on hyperconverged infrastructure, and "
                    "here it appears as a hypervisor layered onto "
                    "disaggregated pools — a fair indication of which way "
                    "the architecture argument has gone."
                ),
            ),
            CatalogOption(
                id="microsoft",
                name="Microsoft",
                summary=(
                    "Hyper-V and Azure Stack HCI, where the licensing "
                    "arithmetic already favours it."
                ),
                details=(
                    "Most compelling in estates already deeply committed "
                    "to Microsoft licensing and identity, at which point "
                    "the marginal cost of the hypervisor is genuinely "
                    "different from what a price list suggests. Licensing "
                    "arithmetic drives more hypervisor decisions than "
                    "technical merit does, and pretending otherwise does "
                    "not help anyone choose."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="control",
        name="Control plane",
        blurb=(
            "What makes disaggregation worth doing rather than merely "
            "possible."
        ),
        limits="One management plane across all pools and all hypervisors",
        region_ids=["control"],
        options=[
            CatalogOption(
                id="unified",
                name="Unified management",
                summary=(
                    "One place to provision, monitor, and patch — whatever "
                    "runs below."
                ),
                details=(
                    "Without this, disaggregation is the old three-tier "
                    "world with better hardware, and the industry already "
                    "decided how it feels about operating that. The "
                    "control plane provides what the fused node used to "
                    "provide, which is why the simplicity survives the "
                    "decoupling. The number to interrogate in any vendor "
                    "conversation is how many consoles an operator "
                    "actually touches once two hypervisors are running: if "
                    "the answer is two, 'multi-hypervisor support' means "
                    "'we will sell you both problems'."
                ),
            ),
            CatalogOption(
                id="automation",
                name="Automation and infrastructure as code",
                summary=(
                    "Declarative provisioning across pools, with the "
                    "Automation Platform."
                ),
                details=(
                    "A control plane that only offers a console has "
                    "automated nothing. Declarative provisioning — "
                    "describing the intended state and letting the "
                    "platform converge on it — is what makes a "
                    "disaggregated estate operable at scale, and it is the "
                    "subject of the DellAutomationStudio spec in this "
                    "repo. The two pair naturally: this twin is the "
                    "infrastructure that can change shape, that one is the "
                    "discipline of describing what shape it should be."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="compute",
        name="Compute pool",
        blurb=("Servers, bought and grown on their own schedule."),
        limits="PowerEdge servers, scaled independently of storage",
        region_ids=["compute"],
        options=[
            CatalogOption(
                id="general-compute",
                name="General-purpose compute",
                summary=(
                    "PowerEdge servers sized for the workload mix, not for "
                    "a storage ratio."
                ),
                details=(
                    "This repo's R760 twin covers a general-purpose server "
                    "in detail. The relevant property in a disaggregated "
                    "estate is that its specification is answerable to the "
                    "workloads alone. On a hyperconverged cluster the node "
                    "specification is a compromise between compute needs "
                    "and capacity needs, and the compromise is struck once, "
                    "at purchase, for years."
                ),
            ),
            CatalogOption(
                id="accelerated",
                name="Accelerated compute",
                summary=(
                    "GPU-equipped nodes in the same pool, for AI "
                    "workloads."
                ),
                details=(
                    "Accelerated nodes can join the pool without the whole "
                    "estate becoming an AI cluster — which matters, "
                    "because GPU servers are expensive and the demand for "
                    "them is lumpy. This repo's XE7745 spec covers the "
                    "air-cooled AI server that typically fills this role, "
                    "and the XE9712 twin covers what happens when the "
                    "requirement outgrows anything that fits in a shared "
                    "pool."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="storage",
        name="Storage pool",
        blurb=(
            "Capacity on its own lifecycle, which is a different lifecycle "
            "from servers."
        ),
        limits="PowerStore, PowerFlex, PowerMax, PowerScale",
        region_ids=["storage"],
        options=[
            CatalogOption(
                id="powerstore",
                name="PowerStore",
                summary=(
                    "All-NVMe block and file for the general workload "
                    "mix."
                ),
                details=(
                    "Twinned separately in this repo. The dual-controller "
                    "architecture it uses is a useful contrast to what "
                    "disaggregation is doing here: PowerStore centralizes "
                    "deliberately and engineers around the centrality, "
                    "while this architecture decentralizes. Both are "
                    "coherent; they answer different questions about where "
                    "you want your complexity."
                ),
            ),
            CatalogOption(
                id="powerflex",
                name="PowerFlex",
                summary=(
                    "Software-defined block that is itself disaggregated "
                    "all the way down."
                ),
                details=(
                    "The natural fit, and twinned separately here. "
                    "PowerFlex applies the same instinct one layer lower: "
                    "no controller, capacity spread across interchangeable "
                    "servers, and the pool's shape changeable while "
                    "running. A disaggregated private cloud on a "
                    "disaggregated storage pool means nothing in the stack "
                    "forces a rebuild to change."
                ),
            ),
            CatalogOption(
                id="powerscale",
                name="PowerScale",
                summary=(
                    "Scale-out file storage with one namespace across all "
                    "nodes."
                ),
                details=(
                    "For unstructured data, where capacity growth is least "
                    "predictable and therefore where independent scaling "
                    "pays best. The DellPowerScale spec in this repo "
                    "covers the namespace idea underneath it — one file "
                    "system spanning every node, so capacity is added by "
                    "adding hardware rather than by planning volumes."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="network",
        name="Network pool and fabric",
        blurb=(
            "The resource disaggregation leans on hardest, and the reason "
            "it works now."
        ),
        limits="PowerSwitch; fabric performance is part of the storage envelope",
        region_ids=["network", "fabric"],
        options=[
            CatalogOption(
                id="fabric-design",
                name="Fabric design",
                summary=(
                    "Once storage is not in the chassis, every access "
                    "crosses the network."
                ),
                details=(
                    "This is the trade disaggregation actually makes, and "
                    "it should be made deliberately. Hyperconvergence kept "
                    "drives local precisely to avoid it; current fabric "
                    "speeds have made the penalty small enough to accept, "
                    "but small is not zero and an under-provisioned fabric "
                    "will present as a storage problem. This repo's "
                    "SN6000 twin covers the network side and the PowerFlex "
                    "twin makes the same point from the storage side."
                ),
            ),
            CatalogOption(
                id="switching",
                name="Switching",
                summary=(
                    "PowerSwitch platforms, sized for east-west traffic "
                    "rather than for users."
                ),
                details=(
                    "A disaggregated estate's traffic is overwhelmingly "
                    "east-west — between pools rather than to users — "
                    "which is a different design problem from campus "
                    "networking. This repo's E3200 twin covers a campus "
                    "switch in detail, and the difference between it and "
                    "the SN6000 twin's fabric is a useful illustration of "
                    "how far apart those two problems are."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="workloads",
        name="Workloads and migration",
        blurb=(
            "Moving between platforms is possible, real work, and the "
            "whole point."
        ),
        limits="Live migration within a hypervisor; conversion between them",
        region_ids=["workloads"],
        options=[
            CatalogOption(
                id="migration",
                name="Cross-hypervisor migration",
                summary=(
                    "Slow, careful, and survivable — which is the claim, "
                    "not that it is quick."
                ),
                details=(
                    "Moving virtual machines between virtualization "
                    "platforms means format conversion, testing, and "
                    "attention to the things that do not translate "
                    "cleanly — guest tooling, snapshots, network "
                    "constructs, licensing. Anyone selling this as "
                    "effortless is selling something. What matters is that "
                    "it is possible at all and that the workloads stay up; "
                    "in a coupled architecture the alternative is not a "
                    "slow migration but a new estate."
                ),
            ),
            CatalogOption(
                id="containers",
                name="Containers alongside virtual machines",
                summary=(
                    "Two workload types, one set of pools."
                ),
                details=(
                    "Most estates will run both for a very long time, and "
                    "an architecture that treats containers as a special "
                    "case creates a second operating model by accident. "
                    "The pools underneath are indifferent to which is "
                    "running, which is the strongest practical argument "
                    "for decoupling them from the platform above."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="operations",
        name="Operations and consumption",
        blurb=(
            "How the estate is run, watched, and paid for."
        ),
        limits="Owned, subscription, or consumption-based",
        region_ids=["control"],
        options=[
            CatalogOption(
                id="observability",
                name="Observability",
                summary=(
                    "Watching an estate whose shape is expected to change."
                ),
                details=(
                    "Disaggregation means the inventory is no longer "
                    "static, so capacity trends matter more than snapshots "
                    "of utilization: the useful question is which pool "
                    "will run short and when, since that is now a purchase "
                    "you can make on its own. This repo's CloudIQ twin "
                    "covers the telemetry-to-insight path that answers it."
                ),
            ),
            CatalogOption(
                id="consumption",
                name="Subscription and consumption models",
                summary=(
                    "Paying for the pools as they are used rather than up "
                    "front."
                ),
                details=(
                    "Independent scaling has a financial counterpart: if "
                    "storage can be added without compute, it can also be "
                    "*billed* without compute. Consumption models install "
                    "buffer capacity that is racked and ready, meter what "
                    "is used, and cap billing below the installed total — "
                    "the subject of the DellAPEX spec in this repo. The "
                    "architecture and the commercial model reinforce each "
                    "other; neither is much use with the other absent."
                ),
            ),
        ],
    ),
]
