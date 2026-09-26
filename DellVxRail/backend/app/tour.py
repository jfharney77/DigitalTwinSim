"""The narrated tour of a VxRail cluster's first run — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
move a camera across the four-node rack elevation, open one node to show it
is a complete PowerEdge server, pin the first-run trace at the moments that
carry the story, and narrate each one. The frontend player owns the clock;
nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The storyboard: four-node rack elevation -> one node's interior -> lockstep
ESXi boot -> discovery -> primary election (exactly one node breaks
lockstep) -> the cluster build -> vSAN fuses local NVMe into one datastore ->
online. The signature beat is ``primary-election``, pinned to the trace step
``test_engine.py::test_primary_election_lights_exactly_one_node`` guards.
Every claim the scripts make is one the engine and the anatomy already make.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``ClusterAnatomy`` is unchanged:

    0  what you see on the rack: switches, NVMe bays, NIC ports, PSUs
    1  inside each node: CPU, DIMMs, the BOSS boot device, the iDRAC
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
from .models import ClusterAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "primary-election"

_RACK = 0
_NODE = 1

_NODES = ("n1", "n2", "n3", "n4")


def layer_map(anatomy: ClusterAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    inside = {"compute", "memory", "boot", "management"}
    return {
        region.id: _NODE if region.kind in inside else _RACK
        for region in anatomy.regions
    }


def _every(prefix: str) -> list[str]:
    """``prefix`` on every node, e.g. storage-n1 ... storage-n4."""
    return [f"{prefix}-{n}" for n in _NODES]


def build_tour(anatomy: ClusterAnatomy) -> Tour:
    """The VxRail first-run tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    node_one = [
        "storage-n1", "boot-n1", "mgmt-n1", "memory-n1",
        "compute-n1", "network-n1", "power-n1",
    ]

    steps = [
        TourStep(
            id="rack-elevation",
            title="Four identical nodes and a pair of switches",
            script=L(
                novice=(
                    "This is a Dell VxRail cluster, seen from the front of the "
                    "rack. Each of the four wide rows is a separate server, "
                    "called a node, and all four are identical. The two bars "
                    "across the top are network switches, and every node is "
                    "cabled to both of them, so losing one switch never cuts "
                    "a node off. The power cords are in, but everything is "
                    "still dark. What you are about to watch is not one "
                    "computer starting up. It is four computers joining into "
                    "one system, called hyperconverged infrastructure, where "
                    "every node does computing, storage and virtualization "
                    "together. Virtualization means running many pretend "
                    "computers, called virtual machines, on one real one."
                ),
                standard=(
                    "A Dell VxRail cluster in a front-of-rack elevation: four "
                    "identical nodes, and above them a redundant pair of "
                    "top-of-rack switches that every node is cabled to. AC is "
                    "connected and the nodes are dark. This is not one machine "
                    "booting. It is four building blocks about to fuse into "
                    "one hyperconverged (HCI) system, where compute, storage "
                    "and virtualization live together on every node. A real "
                    "cluster runs from 2 to 64 nodes; this twin draws four."
                ),
                expert=(
                    "Four-node VxRail cluster, front elevation, redundant ToR "
                    "pair. AC present, nodes dark. HCI: compute, storage, "
                    "virtualization on every node."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["tor-a", "tor-b"],
            layer_reveal=_RACK,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="node-interior",
            title="Every node is a whole PowerEdge server",
            script=L(
                novice=(
                    "Now we lift the lid on the top node. Inside is an "
                    "ordinary Dell PowerEdge server, the same family as the "
                    "R760 twin. Read the row left to right, from the front "
                    "of the server to the back. First come fast flash "
                    "drives called NVMe. Next to them is a tiny pair of mirrored drives "
                    "called BOSS, short for Boot Optimized Storage Solution, "
                    "that holds only the operating system. Below it is the "
                    "iDRAC, a small always-on computer that manages the "
                    "server. Then come the memory sticks and the processor, "
                    "and at the back the network card and power supplies. "
                    "The other three nodes are built exactly the same way."
                ),
                standard=(
                    "Peel the lid off the top node and it is a complete Dell "
                    "PowerEdge server, the same family as the R760 twin. NVMe "
                    "capacity drives at the front; the BOSS-N1 (Boot Optimized "
                    "Storage Solution), a mirrored pair of M.2 SSDs that holds "
                    "only the hypervisor; the iDRAC service processor; DDR5 "
                    "DIMMs and the CPU; then the NIC and redundant power "
                    "supplies at the rear. The other three nodes are identical, "
                    "region for region."
                ),
                expert=(
                    "Node 1 opened: PowerEdge. NVMe bay, BOSS-N1, iDRAC, DDR5, "
                    "CPU, NIC, PSUs. Nodes 2 to 4 identical."
                ),
            ),
            # Frame the whole of node 1. A node row spans the map's full
            # width, so at the map's aspect this box is the whole rack: a
            # tighter zoom would crop the NIC and PSUs the script names.
            camera=frame(*node_one, pad=1.0),
            region_ids=node_one,
            layer_reveal=_NODE,
            trace_cursor=0,
            duration_ms=30_000,
        ),
        TourStep(
            id="lockstep-boot",
            title="Four nodes boot in lockstep",
            script=L(
                novice=(
                    "Power flows in. On every node the iDRAC wakes first, "
                    "then the processors and memory start and each server "
                    "checks itself. Next each node loads VMware ESXi, the "
                    "hypervisor, which is software that lets one physical "
                    "server run many virtual computers. It loads from the "
                    "small BOSS drives, not from the big NVMe drives, which "
                    "are being saved for shared storage. Watch the four rows: "
                    "whatever lights on one node lights on all four at the "
                    "same moment. They are not coordinating yet; they are "
                    "simply four servers starting up side by side."
                ),
                standard=(
                    "Power comes up and every node wakes at once: iDRAC on "
                    "standby first, then CPUs, DDR5 training and the power-on "
                    "self-test. Each node then boots VMware ESXi, the "
                    "hypervisor, from its BOSS device, and leaves the NVMe "
                    "capacity drives untouched because they belong to vSAN, "
                    "not to ESXi. Whatever lights on one node lights on all "
                    "four. Every node runs the same sequence at the same time, "
                    "but none waits on another, so the design tolerates any "
                    "one of them being absent."
                ),
                expert=(
                    "Power, POST, ESXi from BOSS on all four nodes: same "
                    "sequence, same time, no node waiting on another. NVMe "
                    "untouched, reserved for vSAN."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=_every("boot") + _every("compute") + _every("memory"),
            layer_reveal=_NODE,
            trace_cursor=3,
            duration_ms=30_000,
        ),
        TourStep(
            id="discovery",
            title="Strangers find each other",
            script=L(
                novice=(
                    "Until now the four servers knew nothing about each "
                    "other. Now each one announces itself through the two "
                    "switches on a private network set aside for VxRail, and "
                    "every node hears the others. Nobody has handed out "
                    "network addresses yet. This is just the moment four "
                    "separate servers become candidates to form one cluster. "
                    "Notice that it is still symmetrical: all four network "
                    "cards light together."
                ),
                standard=(
                    "The nodes stop being strangers. Over the top-of-rack "
                    "switches, each freshly imaged node announces itself on "
                    "the private VxRail management VLAN using IPv6 multicast, "
                    "and every node hears the others. No IP addresses are "
                    "assigned yet; this is mutual discovery over the fabric. "
                    "It is still lockstep: all four NICs light at once."
                ),
                expert=(
                    "Discovery: IPv6 multicast on the private management "
                    "VLAN via the ToR pair. No IPs yet. Still symmetric."
                ),
            ),
            camera=frame(*_every("network"), "tor-a", "tor-b", pad=2.0),
            region_ids=_every("network") + ["tor-a", "tor-b"],
            layer_reveal=_NODE,
            trace_cursor=4,
            duration_ms=26_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="One node breaks lockstep",
            script=L(
                novice=(
                    "This is the most important moment in the tour. So far "
                    "every node has done exactly what the others did. Now "
                    "they hold an election, and by default the node with the "
                    "lowest serial number wins. The setup screen marks the "
                    "winner with a blue house icon. Only the winner, the top "
                    "node here, starts a special virtual machine called "
                    "VxRail Manager, the program that will build and look "
                    "after the whole cluster for the rest of its life. Look "
                    "at the picture: exactly one node is lit, and the other "
                    "three wait to be told what to do. From here on the "
                    "story is deliberately lopsided, because one node leads."
                ),
                standard=(
                    "The signature moment. Until now every node has done "
                    "exactly what the others did. Now they hold an election, "
                    "and by default the node with the lowest serial number "
                    "wins; the first-run UI marks it with a blue house icon. "
                    "Only that node powers up the VxRail Manager VM, the "
                    "appliance that orchestrates the build and then the "
                    "cluster's whole life, upgrades included. Exactly one "
                    "node is lit: lockstep is broken on purpose, and from "
                    "here one node leads while the others wait to be "
                    "configured."
                ),
                expert=(
                    "Signature: primary election. Lowest serial wins by "
                    "default; only "
                    "node 1 lights, running the VxRail Manager VM. Lockstep "
                    "deliberately broken."
                ),
            ),
            camera=frame("compute-n1", "memory-n1", "mgmt-n1", pad=3.0),
            region_ids=["compute-n1", "memory-n1", "mgmt-n1"],
            layer_reveal=_NODE,
            trace_cursor=5,
            duration_ms=40_000,
        ),
        TourStep(
            id="cluster-build",
            title="The primary builds the cluster",
            script=L(
                novice=(
                    "This is the longest wait of the whole first run. Someone "
                    "gives VxRail Manager a single settings file with names, "
                    "addresses and passwords. It checks every value, gives "
                    "each node its address, sets up vCenter, the VMware "
                    "program that manages virtual machines, and joins all "
                    "four nodes into one cluster. It also switches on "
                    "features that restart virtual machines if a node fails "
                    "and spread the work evenly. Dell says this takes roughly "
                    "25 to 40 minutes, and the clock here gives it 30. "
                    "The top node is still in charge, directing the other "
                    "three through the switches."
                ),
                standard=(
                    "The longest stage of the trace, which is why playback "
                    "dwells here; Dell quotes roughly 25 to 40 minutes, and "
                    "the twin's clock gives it 30. You hand VxRail "
                    "Manager one JSON configuration. It validates every "
                    "input, assigns management IPs, deploys or attaches "
                    "vCenter Server, and joins all four nodes into one "
                    "vSphere cluster with High Availability (HA) and the "
                    "Distributed Resource Scheduler (DRS) configured. Node 1, "
                    "the primary, orchestrates; the other nodes are driven "
                    "over the fabric."
                ),
                expert=(
                    "Longest stage (Dell: 25 to 40 min; 30 on this clock). "
                    "JSON config "
                    "validated, IPs assigned, vCenter deployed, vSphere "
                    "cluster with HA and DRS."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=(
                _every("compute") + _every("memory") + ["mgmt-n1", "tor-a", "tor-b"]
            ),
            layer_reveal=_NODE,
            trace_cursor=6,
            duration_ms=30_000,
        ),
        TourStep(
            id="vsan-fuses",
            title="Local drives become one datastore",
            script=L(
                novice=(
                    "Now the step that makes this kind of system different. "
                    "Look at the flash drives at the front of every node. "
                    "Each node's drives are claimed and pooled into one "
                    "shared store of data, called a vSAN datastore, that "
                    "stretches across the whole cluster. Every piece of data "
                    "is copied to more than one node over the switches, so a "
                    "whole node can fail without losing anything. There is "
                    "no separate storage box anywhere in this rack: the "
                    "servers themselves are the storage. The PowerFlex twin "
                    "pools servers' local drives too, but as storage "
                    "software that does not need VMware underneath it."
                ),
                standard=(
                    "The defining HCI step. Each node's local NVMe drives are "
                    "claimed and pooled into one shared vSAN datastore that "
                    "spans the cluster. On the Express Storage Architecture "
                    "(ESA) it is a single all-NVMe tier, every drive serving "
                    "both cache and capacity, with writes mirrored across "
                    "nodes over the fabric so a whole node can fail without "
                    "data loss. There is no separate array: the servers are "
                    "the storage. The PowerFlex twin pools local drives too, "
                    "as software-defined storage not tied to one hypervisor."
                ),
                expert=(
                    "vSAN ESA claims every node's NVMe into one datastore. "
                    "Single tier, cross-node mirroring, node loss tolerated. "
                    "No external array."
                ),
            ),
            # The switches carry the cross-node mirroring, so they stay in
            # shot alongside every node's NVMe.
            camera=frame(*_every("storage"), "tor-a", "tor-b", pad=1.0),
            region_ids=_every("storage") + ["tor-a", "tor-b"],
            layer_reveal=_NODE,
            trace_cursor=7,
            duration_ms=30_000,
        ),
        TourStep(
            id="cluster-online",
            title="One cluster, serving virtual machines",
            script=L(
                novice=(
                    "The lids go back on and the cluster is running. VMware's "
                    "management screen now shows one cluster of four servers "
                    "sharing one pool of storage, and virtual machines can "
                    "move between nodes while they keep running. VxRail "
                    "Manager stays on to watch the hardware and handle "
                    "future updates. To grow the cluster you add a node, "
                    "and its processor, memory and drives all join at once. That "
                    "fixed bundle is the trade the Private Cloud twin argues "
                    "against. The numbers on this timeline are illustrative."
                ),
                standard=(
                    "Reassembled and online. vCenter shows one cluster of "
                    "four hosts backed by one vSAN datastore; VxRail Manager "
                    "watches the hardware and owns lifecycle upgrades; VMs "
                    "move live between nodes with vMotion. Growth is a node "
                    "at a time, and each node brings CPU, memory and NVMe "
                    "together. That coupling is what the Private Cloud twin "
                    "argues against. Timings and wattages on this trace are "
                    "illustrative."
                ),
                expert=(
                    "Online: four hosts, one vSAN datastore, vMotion, "
                    "lifecycle via VxRail Manager. Scale by node. Figures "
                    "illustrative."
                ),
            ),
            camera=whole_map(anatomy),
            # The trace lights everything at "online"; with the lids back on,
            # the beat lights what the rack shows: every drive bay, NIC and
            # PSU, and both switches, all working as one system.
            region_ids=(
                _every("storage") + _every("network") + _every("power")
                + ["tor-a", "tor-b"]
            ),
            layer_reveal=_RACK,
            trace_cursor=8,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="vxrail-tour",
        title="A VxRail cluster's first run",
        intro=L(
            novice=(
                "A guided walk through four servers becoming one cluster, "
                "narrated beat by beat. Sit back and watch, or pause and "
                "click anything to look closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through the cluster's first run. Watch it "
                "play, or pause and explore; Resume tour brings the camera back."
            ),
            expert="Narrated first-run walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: ClusterAnatomy) -> TourResponse:
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
