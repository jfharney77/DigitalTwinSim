"""Stack anatomy data: Dell Private Cloud drawn as layers, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over rack accuracy (project scope
guardrail).

This map is drawn as a stack rather than a floorplan, because the subject
is what is decoupled from what. Two features of the drawing carry the
lesson and are pinned in ``tests/test_anatomy.py``:

* The hypervisor band is **four identical slots**. Not one platform with
  alternatives listed underneath it — four interchangeable choices, drawn
  the same size, because a diagram that made one bigger would be picking a
  winner on the customer's behalf.
* The resource pools are **three separate columns**, side by side and
  disjoint. On a hyperconverged diagram — this repo's VxRail twin — compute
  and storage are the same box, because in that architecture they are the
  same purchase. Here they are not, and the drawing has to say so.
"""

from __future__ import annotations

from .leveling import L
from .models import CloudAnatomy, CloudRegion, Photo, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell product image — with an honest credit line.
STACK_ILLO = Photo(
    url="/privatecloud-stack.svg",
    caption=(
        "Compute, storage, and networking as three separate pools; four "
        "interchangeable hypervisor slots above them; one control plane "
        "over the lot. Every join in this picture is a decision you can "
        "revisit later."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)

HV_W = 22.0
HV_H = 11.0
HV_Y = 25.0

_HYPERVISORS = [
    (
        "hv-vmware", "VMware", 2.0,
        "The platform most of these estates are already running, and the "
        "reason many of them are now shopping. Nothing here is an argument "
        "against it — for a great many workloads it remains the most "
        "capable option, and staying is a perfectly good decision. The "
        "argument is against having no alternative: a platform you cannot "
        "leave prices itself accordingly, and the last few years made that "
        "abstract concern concrete for a lot of people at once.",
    ),
    (
        "hv-redhat", "Red Hat", 27.0,
        "OpenShift Virtualization, running virtual machines beside "
        "containers on the same platform. The appeal is for organizations "
        "whose direction of travel is containers anyway: rather than "
        "operating a virtualization stack and a container stack in "
        "parallel forever, the VMs become another workload type on the "
        "platform the new applications already target. The trade is that "
        "virtual-machine features which are decades mature elsewhere are "
        "younger here.",
    ),
    (
        "hv-nutanix", "Nutanix", 52.0,
        "Added to Dell Private Cloud in February 2026, and the most direct "
        "like-for-like alternative for an estate that wants to move "
        "without relearning how virtualization works. Worth noting the "
        "irony in this repo's context: Nutanix built its reputation on "
        "hyperconverged infrastructure, and here it appears as a hypervisor "
        "layered onto disaggregated pools — which is a fair indication of "
        "which way the architecture argument has gone.",
    ),
    (
        "hv-microsoft", "Microsoft", 77.0,
        "Hyper-V and Azure Stack HCI, most compelling where the estate is "
        "already deeply committed to Microsoft licensing and identity — at "
        "which point the marginal cost of the hypervisor is genuinely "
        "different from what it looks like on a price list. Licensing "
        "arithmetic drives more hypervisor decisions than technical merit "
        "does, and pretending otherwise does not help anyone choose.",
    ),
]


ANATOMY = CloudAnatomy(
    id="privatecloud",
    name="Dell Private Cloud — disaggregated infrastructure",
    vendor="Dell Technologies",
    form_factor="Pooled compute, storage, and networking under one control plane",
    generation="Multi-hypervisor: VMware, Red Hat, Nutanix (Feb 2026), Microsoft",
    year=2026,
    width=100,
    height=66,
    overview=L(
        novice=(
            "This is about how you buy and arrange the equipment behind a "
            "company's applications. One popular approach puts computing power "
            "and storage together in identical boxes: simple to run, but you "
            "can only grow by adding another whole box, so if you need more "
            "space you also buy processors you did not want. You are also "
            "committed to one vendor's software for as long as you keep the "
            "equipment. Dell Private Cloud separates the three ingredients — "
            "computing, storage, and networking — so each can be bought and "
            "grown on its own, while a single management system keeps it as "
            "easy to run as the all-in-one version. The software layer that "
            "divides physical machines into virtual ones also becomes a choice "
            "you can change later, rather than something baked in. Watch the "
            "story: the storage doubles without a single server being added, "
            "and a second software platform appears without any application "
            "noticing or anyone gaining a second set of tools to learn."
        ),
        plain=(
            "Dell Private Cloud separates compute, storage, and networking "
            "into "
            "pools that are bought and scaled on their own, joins them under "
            "one management system, and treats the hypervisor — the layer that "
            "turns physical servers into virtual ones — as a swappable choice: "
            "VMware, Red Hat, Nutanix, or Microsoft. It is best read against "
            "this repo's VxRail twin, which is the opposite bargain. "
            "Hyperconverged systems fuse compute and storage into one node and "
            "buy real simplicity with that coupling: you grow by adding nodes, "
            "so both resources grow in a fixed ratio whether or not that ratio "
            "suits you, and you are committed to one software stack for the "
            "life of the estate. Separating them un-buys the coupling and "
            "keeps "
            "most of the simplicity, because the control plane now does what "
            "the fused node did. Dell cites 52% of IT leaders weighing "
            "multiple "
            "hypervisors to reduce lock-in. Watch the trace: storage doubles "
            "with no server added, and a second hypervisor arrives unnoticed."
        ),
        standard=(
            "Dell Private Cloud is Dell's disaggregated-infrastructure answer: "
            "compute, storage, and networking pooled and scaled separately, "
            "one "
            "control plane across all of them, and the hypervisor as a "
            "swappable layer on top — VMware, Red Hat, Nutanix, or Microsoft. "
            "It is best understood against this repo's VxRail twin, which "
            "models the opposite bargain. Hyperconverged infrastructure fused "
            "compute and storage into one node and bought real simplicity with "
            "that coupling: you grow by adding nodes, which means you grow "
            "both "
            "resources in a fixed ratio whether or not the ratio is what you "
            "need, and you are committed to one software stack for the life of "
            "the estate. Disaggregation un-buys the coupling and keeps most of "
            "the simplicity, because a single control plane now does what the "
            "fused node used to do. Dell cites research that 52% of IT leaders "
            "are considering multiple hypervisors to reduce lock-in, which is "
            "a "
            "fairly direct summary of what the last few years taught the "
            "market. Watch the trace: storage doubles without a single server "
            "being added, and a second hypervisor appears without a workload "
            "noticing or an operator gaining a second console."
        ),
        technical=(
            "Disaggregated infrastructure: compute, storage, and networking "
            "pooled and scaled independently under one control plane, with the "
            "hypervisor as a swappable layer — VMware, Red Hat, Nutanix, or "
            "Microsoft. Read against the VxRail twin, which models the "
            "opposite "
            "bargain. HCI fuses compute and storage into a node and buys "
            "operational simplicity with the coupling: growth is by node, so "
            "the compute-to-capacity ratio is fixed at the SKU, and the "
            "software stack is a commitment for the life of the estate. "
            "Disaggregation removes the coupling and retains the simplicity "
            "because the control plane now supplies what the fused node did. "
            "Dell cites 52% of IT leaders weighing multi-hypervisor to reduce "
            "lock-in. The trace shows capacity doubling with compute flat and "
            "a "
            "second hypervisor arriving without workload or operational "
            "impact."
        ),
        expert=(
            "Disaggregated pools under a unified control plane; hypervisor as "
            "a "
            "swappable layer across VMware, Red Hat, Nutanix, Microsoft. The "
            "inverse of the VxRail twin's bargain: HCI trades fixed "
            "compute-to-capacity ratios and platform commitment for "
            "operational "
            "simplicity, and the control plane now supplies that simplicity "
            "without the trade. Trace demonstrates independent scaling and "
            "hypervisor addition at zero workload impact and constant "
            "control-plane count."
        ),
    ),
    regions=[
        CloudRegion(
            id="control", kind="controlplane", label="One control plane",
            x=2, y=2, w=96, h=8,
            description=(
                "The single management plane over everything below, and "
                "the component that makes the rest of this architecture "
                "worth having. Disaggregation on its own is just the old "
                "three-tier world — separate compute, separate storage, "
                "separate teams, separate consoles — which the industry "
                "left for hyperconverged infrastructure precisely because "
                "operating it was tedious. What changed is that the "
                "control plane now provides the unified operational "
                "experience the fused node used to provide, so you get "
                "HCI's simplicity without HCI's coupling. Note what stays "
                "constant in the trace: one control plane, even once two "
                "hypervisors are running. Multi-hypervisor is not worth "
                "having if it also means multi-management, and that is the "
                "trap most 'we support everything' claims fall into."
            ),
        ),
        CloudRegion(
            id="workloads", kind="workload", label="Workloads",
            x=2, y=13, w=96, h=9,
            description=(
                "The virtual machines and containers — the only thing in "
                "this diagram that anybody outside the infrastructure team "
                "cares about. The test of every layer beneath is whether "
                "changes down there are visible up here, and in this trace "
                "they are not: storage doubles and a second hypervisor "
                "arrives while the workload count and the downtime counter "
                "both hold still. That invisibility is the product. An "
                "architecture that offers flexibility the applications can "
                "feel has not offered anything, because nobody will use it."
            ),
        ),
        *[
            CloudRegion(
                id=hid, kind="hypervisor", label=label,
                x=x, y=HV_Y, w=HV_W, h=HV_H, description=desc,
            )
            for hid, label, x, desc in _HYPERVISORS
        ],
        CloudRegion(
            id="compute", kind="compute", label="Compute pool",
            x=2, y=39, w=30, h=12,
            description=(
                "Servers, pooled and scaled on their own. The contrast "
                "with hyperconverged infrastructure is exact and worth "
                "stating plainly: on a VxRail cluster, adding capacity "
                "means adding a node, and a node brings processors, "
                "memory, and drives together in whatever ratio the model "
                "offers. If you need storage you buy compute too. Estates "
                "routinely end up with a third more of one resource than "
                "they ever use, paid for and racked and drawing power. "
                "Here the pools are bought separately, and the trace shows "
                "storage doubling with this number untouched."
            ),
        ),
        CloudRegion(
            id="storage", kind="storage", label="Storage pool",
            x=35, y=39, w=30, h=12,
            description=(
                "Storage, pooled and scaled on its own — PowerStore, "
                "PowerFlex, PowerMax, or PowerScale depending on the "
                "workload, all twinned separately in this repo. The "
                "interesting consequence of disaggregating storage is not "
                "the purchasing flexibility but the lifecycle one: storage "
                "and servers have genuinely different useful lives, and "
                "fusing them forces the shorter one on both. Replacing "
                "servers on a four-year cycle while keeping storage for "
                "seven is impossible when they arrive in the same box."
            ),
        ),
        CloudRegion(
            id="network", kind="network", label="Network pool",
            x=68, y=39, w=30, h=12,
            description=(
                "Networking, pooled and scaled on its own. It is the "
                "resource most often treated as plumbing and it is the one "
                "disaggregation leans on hardest — once compute and "
                "storage are no longer in the same chassis, every access "
                "between them crosses the network, so the fabric's "
                "capability is now part of the storage system's "
                "performance envelope. This repo's PowerFlex twin makes "
                "the same point from the storage side and the SN6000 twin "
                "from the network side."
            ),
        ),
        CloudRegion(
            id="fabric", kind="fabric", label="Fabric",
            x=2, y=54, w=96, h=8,
            description=(
                "What joins the pools, and the reason this architecture is "
                "practical now rather than in 2012. Disaggregation was "
                "always the obvious idea; what made hyperconvergence win "
                "for a decade was that crossing a network to reach storage "
                "cost more than keeping the drives local. At current "
                "fabric speeds and latencies that penalty has shrunk to "
                "the point where the coupling is no longer worth what it "
                "costs. The architecture did not become smarter — the "
                "interconnect became fast enough that the compromise "
                "stopped being necessary."
            ),
        ),
    ],
    stats=[
        Stat(label="Architecture", value="Disaggregated — pools, not fused nodes"),
        Stat(label="Hypervisors", value="VMware · Red Hat · Nutanix · Microsoft"),
        Stat(label="Nutanix support", value="Added February 2026"),
        Stat(label="Control plane", value="One, regardless of hypervisor count"),
        Stat(label="Scaling", value="Compute, storage, network independently"),
        Stat(label="Market driver", value="52% of IT leaders weighing multi-hypervisor"),
        Stat(label="Compared with", value="HCI (see this repo's VxRail twin)"),
        Stat(label="Workload impact", value="None — no downtime on any step"),
    ],
    photo=STACK_ILLO,
    sources=[
        SourceLink(
            label="Dell — why Dell Private Cloud outperforms HCI",
            url="https://www.dell.com/en-us/blog/rethinking-infrastructure-why-dell-private-cloud-outperforms-hci/",
        ),
        SourceLink(
            label="Dell Private Cloud and HCI solutions",
            url="https://www.dell.com/en-us/shop/private-cloud-and-hci-solutions/sc/private-cloud-solutions",
        ),
        SourceLink(
            label="Dell unveils disaggregated infrastructure strategy (Computer Weekly)",
            url="https://www.computerweekly.com/news/366624041/Dell-unveils-disaggregated-infrastructure-strategy",
        ),
        SourceLink(
            label="Dell Private Cloud expands choice with Nutanix support",
            url="https://www.hpcwire.com/bigdatawire/this-just-in/dell-private-cloud-expands-choice-with-nutanix-support/",
        ),
    ],
)
