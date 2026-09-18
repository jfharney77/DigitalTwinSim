"""The narrated tour of Dell Private Cloud — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats
that move a camera across the layered stack, peel away the layers people
use (control plane and workloads) to show the infrastructure beneath, pin
the cloud trace at the moments that carry the argument, and narrate each
one. The frontend player owns the clock; nothing here knows about time, IO
or the web (AST-checked in ``tests/test_tour.py``, the same rule as
``engine.py``).

The storyboard: the layered stack -> three separate pools -> one control
plane before any hypervisor -> a hypervisor chosen -> workloads land ->
storage grows alone -> the cross-hypervisor migration (the signature beat,
``hypervisor-switch``) -> two hypervisors under one control plane. Every
claim the scripts make is one the engine, the anatomy and
``tests/test_engine.py`` already make; each beat's ``trace_cursor`` is the
step whose description says the same thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``CloudAnatomy`` is unchanged:

    0  what people use and see: the control plane and the workloads
    1  the infrastructure beneath: hypervisor slots, the three pools, fabric
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import CloudAnatomy

#: The step the tests pin: the twin's one idea (you can change your mind)
#: is proved at the cross-hypervisor migration.
SIGNATURE_STEP_ID = "hypervisor-switch"

_SURFACE = 0
_INFRA = 1


def layer_map(anatomy: CloudAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    surface = {"controlplane", "workload"}
    return {
        r.id: (_SURFACE if r.kind in surface else _INFRA) for r in anatomy.regions
    }


def build_tour(anatomy: CloudAnatomy) -> Tour:
    """The Dell Private Cloud tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="the-stack",
            title="A stack drawn in layers",
            script=L(
                novice=(
                    "This is Dell Private Cloud, drawn as a stack of layers. At "
                    "the top is the control plane, the single console where the "
                    "operators set up, watch and patch everything. Below it are "
                    "the workloads, the virtual machines and containers that the "
                    "business actually uses. Then a row of four slots for the "
                    "hypervisor, the software that splits real servers into many "
                    "virtual ones: VMware, Red Hat, Nutanix and Microsoft. At the "
                    "bottom sit three separate pools, for computing, storage and "
                    "networking, joined by a fabric of switches. Right now none "
                    "of it is put together yet."
                ),
                standard=(
                    "Dell Private Cloud, drawn as a layered stack. One control "
                    "plane on top, the single place to provision, monitor and "
                    "patch. Below it the workloads, virtual machines and "
                    "containers. Then four identical hypervisor slots (VMware, "
                    "Red Hat, Nutanix, Microsoft), and at the bottom three "
                    "separate pools, compute, storage and network, over a "
                    "fabric. At the start of the trace none of it is assembled: "
                    "servers in one place, storage in another, switches in a "
                    "third."
                ),
                expert=(
                    "Layered stack: one control plane, workloads, four "
                    "hypervisor slots, three disaggregated pools over a fabric. "
                    "Trace start: unassembled."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_SURFACE,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="three-pools",
            title="Three pools, not one node",
            script=L(
                novice=(
                    "We fade out the top layers to look at the foundation. "
                    "Forty-eight servers become a pool of computing power, 200 "
                    "terabytes become a pool of storage, and the switches become "
                    "a pool of networking. These numbers are illustrative. The "
                    "important word is separately. In this repo's VxRail twin, a "
                    "hyperconverged system, computing and storage are fused "
                    "together inside every node, so the mix between them is fixed "
                    "by whichever model you ordered. Here they are three separate "
                    "purchases, and they stay separate for as long as the "
                    "equipment is in use."
                ),
                standard=(
                    "Peeling away the layers people use shows the foundation. "
                    "Forty-eight servers become a compute pool, 200 TB a storage "
                    "pool, and the switching a network pool (illustrative "
                    "figures). The word doing the work is independently. On a "
                    "hyperconverged cluster, this repo's VxRail twin, these would "
                    "be one set of nodes carrying processors and drives together, "
                    "the ratio fixed at ordering. Here they are three separate "
                    "decisions, and three separate lines rise from them in the "
                    "drawing."
                ),
                expert=(
                    "Disaggregated pools: 48 compute units, 200 TB, network "
                    "(illustrative). Independent quantities, unlike VxRail's "
                    "fixed-ratio fused nodes."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["compute", "storage", "network", "fabric"],
            layer_reveal=_INFRA,
            trace_cursor=1,
            duration_ms=28_000,
        ),
        TourStep(
            id="one-control-plane",
            title="One control plane, before any hypervisor",
            script=L(
                novice=(
                    "Now the control plane claims all three pools, and it does "
                    "so before any hypervisor is installed. This is what makes "
                    "the whole idea worth doing. Without one shared console, "
                    "separate pools would just be the old way of running a data "
                    "centre, with three teams and three consoles. With it, the "
                    "operators get the simple, all-in-one experience that the "
                    "fused hyperconverged node used to give them, without the "
                    "fusing. Remember the count of control planes: one. It will "
                    "not change again for the rest of the story."
                ),
                standard=(
                    "One control plane claims all three pools, and it arrives "
                    "before any hypervisor does. It is the component that makes "
                    "disaggregation worth doing rather than merely possible: "
                    "without it this is the old three-tier world with three teams "
                    "and three consoles. With it, the operators keep the unified "
                    "experience the fused node used to provide, without the "
                    "coupling. Note the control-plane count. It is one, and it "
                    "does not change again."
                ),
                expert=(
                    "Control plane claims all pools, preceding any hypervisor. "
                    "Unified operations without coupling. One control plane "
                    "from here on."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["control", "compute", "storage", "network", "fabric"],
            layer_reveal=_INFRA,
            trace_cursor=2,
            duration_ms=28_000,
        ),
        TourStep(
            id="a-hypervisor-chosen",
            title="A hypervisor goes in a slot",
            script=L(
                novice=(
                    "VMware goes in first, because that is what this organization "
                    "already runs, and there is no reason to change everything "
                    "at once. The key word is chosen. In a hyperconverged system "
                    "the hypervisor is not something you pick later: the whole "
                    "system is built around it, and the decision was made when "
                    "the hardware was ordered. Here VMware sits in one slot. The "
                    "empty Red Hat slot beside it stays drawn, faded but "
                    "visible, and so do the two slots past it, because an option "
                    "you have not taken is still an option."
                ),
                standard=(
                    "VMware goes in first, because that is what this estate "
                    "already runs. The significant word is chosen. In a "
                    "hyperconverged system the hypervisor is what the "
                    "architecture is made of, decided when the hardware was "
                    "ordered. Here it sits in one slot of four. The empty Red "
                    "Hat slot beside it, and the two past it, are drawn dimmed "
                    "rather than hidden. The empty slots are the product: an "
                    "option not taken is still an option, and the compute pool "
                    "below does not care which slot is filled."
                ),
                expert=(
                    "Hypervisor 1: VMware, in a slot, not a foundation. Three "
                    "slots left available; the pools are indifferent to which."
                ),
            ),
            # Close on the left of the stack: the chosen slot, an empty one
            # beside it, and the compute pool it runs on.
            camera=frame("hv-vmware", "hv-redhat", "compute", pad=3.0),
            region_ids=["hv-vmware"],
            layer_reveal=_INFRA,
            trace_cursor=3,
            duration_ms=26_000,
        ),
        TourStep(
            id="workloads-land",
            title="The only layer anyone else sees",
            script=L(
                novice=(
                    "Now 120 workloads arrive, an illustrative number of virtual "
                    "machines and containers. These are the only things in the "
                    "whole picture that anyone outside the infrastructure team "
                    "cares about. From here on, every change further down the "
                    "stack gets the same test: can the workloads tell it "
                    "happened? Keep an eye on two numbers from now on, the "
                    "workload count and the downtime counter. The storage is "
                    "about to double and a second hypervisor is about to appear, "
                    "and neither number will move."
                ),
                standard=(
                    "One hundred and twenty workloads land (an illustrative "
                    "count): virtual machines and containers, the only things in "
                    "the diagram that anyone outside the infrastructure team "
                    "cares about. From here on, the test of every layer beneath "
                    "them is whether changes down there are visible up here. "
                    "Watch the workload count and the downtime counter. The "
                    "storage pool is about to double and a second hypervisor "
                    "is about to appear, and neither figure will move."
                ),
                expert=(
                    "120 workloads deployed (illustrative). Workload count and "
                    "downtime stay fixed through the changes ahead."
                ),
            ),
            camera=frame("workloads", "hv-vmware", pad=3.0),
            region_ids=["workloads", "hv-vmware"],
            layer_reveal=_INFRA,
            trace_cursor=4,
            duration_ms=26_000,
        ),
        TourStep(
            id="storage-grows-alone",
            title="Storage doubles, compute stays put",
            script=L(
                novice=(
                    "The organization runs short of space, so 200 more terabytes of "
                    "storage are added, doubling it. Now look at the computing "
                    "pool: still forty-eight servers, exactly as before. On a "
                    "hyperconverged cluster, the only way to get more storage is "
                    "to add whole nodes, and every node brings processors and "
                    "memory whether anyone needs them or not. Those extra "
                    "servers would sit in the racks using power, needing "
                    "licences and losing value. Here, only the thing that was "
                    "asked for changes."
                ),
                standard=(
                    "The estate runs short of capacity, so 200 TB more storage "
                    "is added and the pool doubles to 400 TB. The compute figure "
                    "stays at forty-eight. On a hyperconverged cluster the same "
                    "need is met by adding nodes, which bring processors and "
                    "memory whether or not anyone wants them: racked, powered, "
                    "licensed and depreciating. Here nothing scales that was not "
                    "asked for, and the workloads carry on untouched."
                ),
                expert=(
                    "Storage 200 -> 400 TB; compute fixed at 48. Independent "
                    "scaling, no stranded compute. Workloads and downtime "
                    "unchanged."
                ),
            ),
            camera=frame("compute", "storage", pad=3.0),
            # VMware stays lit: it is still running, and StackView marks any
            # unlit hypervisor slot "available".
            region_ids=["storage", "compute", "hv-vmware"],
            layer_reveal=_INFRA,
            trace_cursor=6,
            duration_ms=30_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="A second hypervisor, and nobody notices",
            script=L(
                novice=(
                    "This is the moment the whole design exists for. Some of the "
                    "applications move onto a second hypervisor, Nutanix, which Dell "
                    "Private Cloud has supported since February 2026, while the "
                    "rest stay on VMware. Moving workloads between hypervisors "
                    "is slow, careful work, with files to convert and testing to "
                    "do, and it is the longest stage in this whole timeline. The "
                    "freedom is real, but it is not free. What matters is that "
                    "it can be done at all, and that it happens with zero "
                    "downtime: all 120 workloads stay running the entire time, "
                    "and the operators still have exactly one control plane. In "
                    "a fused system, the alternative is not a slow move. It is "
                    "buying a whole new set of equipment."
                ),
                standard=(
                    "The stage that justifies the architecture. Part of the "
                    "estate moves to Nutanix, supported in Dell Private Cloud "
                    "since February 2026, while the rest stays on VMware. It is "
                    "the longest stage in the trace, and honestly so: migrating "
                    "between virtualization platforms means format conversion, "
                    "testing and care over what does not translate. What matters "
                    "is that it is possible at all, and that downtime stays at "
                    "zero, all 120 workloads stay up, and the control-plane count "
                    "stays at one. In a coupled architecture the alternative is "
                    "not a slow migration but a new estate."
                ),
                expert=(
                    "Partial cross-hypervisor migration, VMware to Nutanix. "
                    "Longest stage in the trace. Downtime 0 s, 120 workloads, "
                    "one control plane throughout."
                ),
            ),
            camera=frame("control", "workloads", "hv-vmware", "hv-nutanix", pad=3.0),
            region_ids=["control", "workloads", "hv-vmware", "hv-nutanix"],
            layer_reveal=_INFRA,
            trace_cursor=7,
            duration_ms=42_000,
        ),
        TourStep(
            id="mixed-and-steady",
            title="Two hypervisors, one control plane",
            script=L(
                novice=(
                    "The layers come back together. The organization now runs two "
                    "hypervisors side by side, and the number worth staring at "
                    "is the count of control planes: still one. Two hypervisors "
                    "only help if the operators do not also get a second "
                    "console, a second patching schedule and a second set of "
                    "habits. What the organization really bought is not VMware or "
                    "Nutanix. It is the ability to have this choice again next "
                    "year without starting over. For the opposite bargain, open "
                    "the VxRail twin and compare the two side by side."
                ),
                standard=(
                    "Reassembled and steady: two hypervisors, one control plane. "
                    "Running two is only an improvement if the operators do not "
                    "also acquire a second console, a second patching schedule "
                    "and a second set of habits. What the estate has bought is "
                    "not a hypervisor; it is the ability to have this argument "
                    "again next year, with better information, without a "
                    "rebuild. Read it alongside the VxRail twin, which models "
                    "the opposite bargain."
                ),
                expert=(
                    "End state: VMware and Nutanix under one control plane. The "
                    "product is optionality. Contrast: VxRail twin."
                ),
            ),
            camera=whole_map(anatomy),
            # Light what the narration points at: the one control plane and
            # the two hypervisors now running side by side (StackView marks
            # the two unlit slots "available", which is true).
            region_ids=["control", "workloads", "hv-vmware", "hv-nutanix"],
            layer_reveal=_SURFACE,
            trace_cursor=8,
            duration_ms=28_000,
        ),
    ]

    return Tour(
        id="privatecloud-tour",
        title="Inside Dell Private Cloud, as it changes its mind",
        intro=L(
            novice=(
                "A guided walk through a private cloud as it is built, grown and "
                "then switched onto a second hypervisor, narrated beat by beat. "
                "Sit back and watch, or pause and click anything to look closer; "
                "the tour waits for you."
            ),
            standard=(
                "A narrated walk through the stack as it is assembled, grown and "
                "given a second hypervisor. Watch it play, or pause and explore; "
                "Resume tour brings the camera back."
            ),
            expert="Narrated build, grow and migrate walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: CloudAnatomy) -> TourResponse:
    """The ``GET /api/tour`` payload: the tour plus the layer map and bounds."""
    return TourResponse(
        tour=build_tour(anatomy),
        layers=layer_map(anatomy),
        map_width=anatomy.width,
        map_height=anatomy.height,
    )


# Built once at import, like ANATOMY: importing the module registers the
# narration's reading-level variants, which tests/test_leveling.py relies on.
from .anatomy import ANATOMY  # noqa: E402  (after the builders it feeds)

TOUR_RESPONSE = build_response(ANATOMY)
