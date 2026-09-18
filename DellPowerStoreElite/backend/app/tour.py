"""The narrated tour of a PowerStore Elite cluster join — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
move a camera across the two stacked appliances, peel them from the
serviceable outside to the RDMA mesh between the generations, pin the join
trace at the moments that carry the story, and narrate each one. The frontend
player owns the clock; nothing here knows about time, IO or the web
(AST-checked in ``tests/test_tour.py``, the same rule as ``engine.py``).

The signature beat is ``zero-downtime-join``: a second hardware generation
becomes a member of the cluster while the first keeps serving, and the
downtime counter does not move. Every claim the scripts make is one the
engine and the anatomy already make — the trace index each beat pins is the
step whose description says the same thing, and ``tests/test_tour.py``
checks the pairing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``ChassisAnatomy`` is unchanged:

    0  what you can see and touch: drive bays, NVRAM, ports, PSUs, mgmt
    1  inside each node canister: fans, batteries, CPUs, DDR5, node boards
    2  the 200 Gb RDMA mesh between the generations
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
from .models import ChassisAnatomy

#: The step the tests pin: the twin's one idea lives here.
SIGNATURE_STEP_ID = "zero-downtime-join"

_OUTSIDE = 0
_CANISTER = 1
_MESH = 2

# The prior array's serving set, lit on every beat where it is still the
# thing hosts talk to.
_PRIOR_SERVING = [
    "prior-bay",
    "prior-cpu-a", "prior-cpu-b",
    "prior-io-a", "prior-io-b",
]


def layer_map(anatomy: ChassisAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    inside = {"cooling", "battery", "cpu", "memory", "board"}
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.id == "cluster-mesh":
            layers[region.id] = _MESH
        elif region.kind in inside:
            layers[region.id] = _CANISTER
        else:
            layers[region.id] = _OUTSIDE
    return layers


def build_tour(anatomy: ChassisAnatomy) -> Tour:
    """The PowerStore Elite tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="two-generations",
            title="Two appliances, one rack",
            script=L(
                novice=(
                    "These are two Dell PowerStore storage arrays, boxes whose "
                    "whole job is to hold data for other computers, drawn from "
                    "above. The top band is the array this company already owns, "
                    "an older generation with 25 flash drives, and it is busy "
                    "serving every application in the building, about a quarter "
                    "of a million reads and writes a second in this illustrative "
                    "run. The bottom band is where the new one, PowerStore Elite, "
                    "is about to go; for now it is dark. The thin strip between "
                    "them is the link that will join them. Watch the downtime counter: "
                    "the usual way to replace an array is to stop everything and "
                    "move the data, and this tour is about not doing that."
                ),
                standard=(
                    "Two appliances, seen from above. The top band is the "
                    "prior-generation PowerStore a company already owns: 25 NVMe "
                    "slots, serving the whole estate at a steady 250K IOPS "
                    "(input/output operations per second; illustrative). The "
                    "bottom band is the new PowerStore Elite, a 3U appliance "
                    "about to be racked beneath it, still dark. The strip between "
                    "them is the cluster mesh, a 200 Gb RDMA (Remote Direct "
                    "Memory Access) interconnect. The traditional refresh is a forklift: "
                    "buy, migrate, cut over, decommission. The downtime counter "
                    "keeps score against that."
                ),
                expert=(
                    "Prior-gen PowerStore (25 NVMe) on top serving ~250K IOPS "
                    "(illustrative); Elite 3U below, not yet racked; RDMA mesh between. "
                    "Baseline for a no-forklift refresh."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=list(_PRIOR_SERVING),
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=28_000,
        ),
        TourStep(
            id="elite-wakes",
            title="The Elite wakes beside a working array",
            script=L(
                novice=(
                    "We have lifted the lid on the new box. It has no power "
                    "button: plugging it in is how it starts, and its two halves, "
                    "called nodes, each a complete computer, wake up at the same "
                    "time and in the same way, like mirror images. Each loads the "
                    "array's operating system, PowerStoreOS, on newer parts: "
                    "Intel Xeon processors with up to half again as many cores "
                    "as the older models, by Dell's count, and faster DDR5 memory. "
                    "This is the slowest thing the new box does by itself. Just "
                    "above the picture, the old array has not noticed anything "
                    "and keeps serving. The PowerStore twin walks "
                    "this start-up in detail; read it first if you have not."
                ),
                standard=(
                    "Lid off the Elite. There is no power button: AC is the "
                    "power-on, and nodes A and B wake in lockstep, whatever lights "
                    "on one lighting on the other. Both boot PowerStoreOS, the same "
                    "OS lineage as the prior array (the compatibility that makes "
                    "mixed-generation clustering possible), on Xeon Scalable with "
                    "up to 50% more cores than the 3200T/5500 class (Dell's "
                    "figure), DDR5 and PCIe Gen 5. It is the slowest "
                    "thing the new box does on its own. The bring-up is the one "
                    "the PowerStore twin walks step by step; here the top band, "
                    "just out of frame, keeps serving throughout."
                ),
                expert=(
                    "AC-on, no button. Elite nodes A/B boot PowerStoreOS in "
                    "lockstep: Xeon (+50% cores, Dell figure), DDR5, Gen 5. Same OS lineage as "
                    "prior gen. Prior array serving, unaffected."
                ),
            ),
            # Close on the Elite's two canisters. The prior band sits just
            # above the frame (the narration says so), still serving.
            camera=CameraTarget(x=12, y=20, w=72, h=50),
            region_ids=[
                "elite-cpu-a", "elite-cpu-b",
                "elite-dimm-a", "elite-dimm-b",
                "elite-board-a", "elite-board-b",
                "elite-fans-a", "elite-fans-b",
            ],
            layer_reveal=_CANISTER,
            trace_cursor=2,
            duration_ms=28_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Joining without stopping",
            script=L(
                novice=(
                    "This is the most important moment in the tour. The new Elite "
                    "joins the old array's cluster, the group of arrays that are "
                    "managed and used as one. From now on there is one cluster "
                    "with two generations of hardware in it and one place to "
                    "manage them. Nothing stops for this, and it happens once. "
                    "Joining only changes the list of members; it does not move "
                    "any data, so the old array keeps serving every application "
                    "exactly as before. The downtime counter still reads zero. "
                    "The usable space jumps from about 1.2 to about 7 petabytes "
                    "in this illustrative run, because the new box's 40 drive slots "
                    "arrive behind Dell's promise that data will shrink six to one."
                ),
                standard=(
                    "The idea the whole twin is built around: the Elite joins the "
                    "existing cluster live, exactly once. One cluster, two "
                    "hardware generations, one management plane. Nothing pauses, "
                    "because a join is a membership operation, not a data "
                    "operation: the prior array keeps serving hosts through the "
                    "same paths, and downtime stays at zero. Effective capacity "
                    "jumps from about 1.2 PB to about 7 PB (illustrative) as the "
                    "Elite's 40-slot E3 pool arrives behind Dell's 6:1 data "
                    "reduction guarantee. It is the only capacity jump in the trace."
                ),
                expert=(
                    "Live mixed-generation join, once. Membership, not "
                    "data movement; prior gen keeps serving; downtime 0. Effective "
                    "~1.2 to ~7 PB (illustrative), 6:1 guarantee."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[
                *_PRIOR_SERVING,
                "elite-bay",
                "elite-cpu-a", "elite-cpu-b",
                "elite-mgmt-a", "elite-mgmt-b",
            ],
            layer_reveal=_CANISTER,
            trace_cursor=4,
            duration_ms=40_000,
        ),
        TourStep(
            id="rdma-mesh",
            title="The only new plumbing",
            script=L(
                novice=(
                    "Now the strip between the two boxes comes alive. It is a "
                    "very fast network link, 200 gigabits per second, that uses "
                    "RDMA, short for Remote Direct Memory Access: one box can copy "
                    "data straight into the other's memory without asking either "
                    "processor to do the work. That matters for what comes next, "
                    "because the processors stay free to keep answering the "
                    "applications. This link is the only new wiring the whole "
                    "upgrade needs, and nothing uses it before this moment."
                ),
                standard=(
                    "The 200 Gb RDMA (Remote Direct Memory Access) node "
                    "interconnect comes up between the generations. RDMA moves "
                    "bulk data memory to memory without either CPU doing the "
                    "copying, so the coming rebalance taxes neither array's "
                    "ability to serve hosts. The mesh never lights before this "
                    "step, and it is the only new plumbing the modernization "
                    "requires."
                ),
                expert=(
                    "200 Gb RDMA mesh up between generations; CPU-bypass bulk "
                    "transfer. First lit here. Only new plumbing required."
                ),
            ),
            # Close on the strip, with the node boards it joins on either
            # side; only the mesh is lit, because the beat is about it alone
            # (the engine also lights all four boards at this step).
            camera=frame("cluster-mesh", "prior-board-b", "elite-board-a", pad=2.0),
            region_ids=["cluster-mesh"],
            layer_reveal=_MESH,
            trace_cursor=5,
            duration_ms=26_000,
        ),
        TourStep(
            id="live-rebalance",
            title="Moving everything while serving everything",
            script=L(
                novice=(
                    "Here is the slow part, and the timeline lingers on it on "
                    "purpose. The cluster copies every stored volume from the old "
                    "box's drives to the new box's drives across the fast link, "
                    "while both boxes keep answering the applications. The work "
                    "rate dips a little, to about 230 thousand operations a "
                    "second in this illustrative run, but never below 85 percent "
                    "of normal, and the downtime counter stays at zero. Moving a "
                    "lot of data still takes hours. What changed is that those "
                    "hours no longer need an outage to spend."
                ),
                standard=(
                    "The live rebalance, and the longest stage in the trace. The "
                    "cluster drains volumes from the prior bay to the Elite's E3 "
                    "pool across the RDMA mesh while both arrays keep serving "
                    "hosts. IOPS sags under the copy load, to about 230K "
                    "(illustrative), but the service floor of 85% of baseline "
                    "holds and downtime stays at zero. The hours a migration "
                    "takes did not disappear; they stopped requiring an outage."
                ),
                expert=(
                    "Live rebalance, longest stage: volumes drain prior bay to E3 "
                    "pool over RDMA. IOPS ~230K (illustrative), floor >=85% of "
                    "baseline, downtime 0. Cost is duration, not availability."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[
                "cluster-mesh",
                *_PRIOR_SERVING,
                "elite-bay",
                "elite-cpu-a", "elite-cpu-b",
                "elite-board-a", "elite-board-b",
            ],
            layer_reveal=_MESH,
            trace_cursor=6,
            duration_ms=32_000,
        ),
        TourStep(
            id="cutover",
            title="Three times, and only now",
            script=L(
                novice=(
                    "The data has moved. Now the applications' traffic shifts "
                    "over to the new box's connections, and they notice nothing, "
                    "because each application already had more than one path to "
                    "its storage and simply starts using the new one. Only now "
                    "does the speed jump: about three times the old rate, around "
                    "760 thousand operations a second in this illustrative run. "
                    "The threefold figure is Dell's own claim for the new platform, "
                    "and this story deliberately holds it back until this step, "
                    "because it belongs to the finished upgrade, not to the box "
                    "still in its crate."
                ),
                standard=(
                    "Cutover. Multipathing (each host holding several paths to "
                    "its storage) shifts host I/O to the Elite's front end with "
                    "no interruption, and only now does the headline engage: up "
                    "to 3x IOPS versus the prior generation, Dell's claim on a "
                    "70/30 read/write, 8K basis, about 760K here (illustrative). "
                    "Before this step the cluster never served above its 250K "
                    "baseline. The tripling is a property of the modernized "
                    "estate, not of the box in the crate."
                ),
                expert=(
                    "Cutover via multipathing, no interruption. 3x IOPS engages "
                    "only here (Dell claim, 70/30 8K; ~760K illustrative). "
                    "Pre-cutover: never above the 250K baseline."
                ),
            ),
            # The Elite band and the mesh above it; hosts now land here.
            camera=frame(
                "cluster-mesh", "elite-bay", "elite-nvram", "elite-io-a", "elite-io-b",
                pad=2.0,
            ),
            region_ids=[
                "cluster-mesh",
                "elite-bay", "elite-nvram",
                "elite-cpu-a", "elite-cpu-b",
                "elite-io-a", "elite-io-b",
            ],
            layer_reveal=_MESH,
            trace_cursor=8,
            duration_ms=28_000,
        ),
        TourStep(
            id="second-job",
            title="A second job, not a skip",
            script=L(
                novice=(
                    "In the old way, the old array would now be unplugged and "
                    "thrown out. Here it stays. It never left the cluster, so "
                    "giving it a new, lighter job, such as keeping copies of data "
                    "for safety or hosting a test setup, is just a change of "
                    "settings, not another move. Upgrades stop producing scrap "
                    "and start producing second roles."
                ),
                standard=(
                    "The prior generation is repurposed in place: replication "
                    "target, snapshot host, test estate, lighter roles its "
                    "hardware still serves well. Because it never left the "
                    "cluster, the reassignment is policy, not migration. The "
                    "refresh cycle stops producing decommissioned arrays and "
                    "starts producing second roles."
                ),
                expert=(
                    "Prior gen repurposed in place (replication target, "
                    "snapshots, test). Never left the cluster: policy change, "
                    "no migration."
                ),
            ),
            camera=frame(
                "prior-bay", "prior-board-a", "prior-board-b", "cluster-mesh",
                pad=2.0,
            ),
            region_ids=[
                "cluster-mesh",
                *_PRIOR_SERVING,
                "prior-board-a", "prior-board-b",
            ],
            layer_reveal=_MESH,
            trace_cursor=9,
            duration_ms=24_000,
        ),
        TourStep(
            id="mixed-generation-end",
            title="Mixed generations is the end state",
            script=L(
                novice=(
                    "The lids go back on. The new box does most of the work at "
                    "about three times the old speed, the old box has its second "
                    "job, and both are still members of one cluster. That mix is "
                    "where the story ends, not a halfway point: when the next "
                    "generation ships, it will join this cluster the same way, "
                    "and the Elite will be the one that takes the second job. "
                    "The downtime counter ends where it began, at zero. The "
                    "PowerScale and PowerFlex twins make the same argument, "
                    "growing without moving data, in their own ways."
                ),
                standard=(
                    "Reassembled. The Elite serves at about 3x baseline, 7 PB "
                    "effective behind the 6:1 guarantee (illustrative), and the "
                    "prior array is still a member. The mixed-generation cluster "
                    "is the end state, not a transition: the next generation "
                    "will join the same way, and the Elite will inherit the "
                    "second job. Downtime ends where it began, at zero. The "
                    "PowerScale and PowerFlex twins make the sibling argument for "
                    "growth without migration."
                ),
                expert=(
                    "End state: two generations, one cluster; Elite ~3x, 7 PB "
                    "effective (illustrative). Next gen joins the same way. "
                    "Downtime 0 throughout."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[
                "cluster-mesh",
                "prior-bay",
                "elite-bay", "elite-nvram",
                "elite-cpu-a", "elite-cpu-b",
                "elite-io-a", "elite-io-b",
            ],
            layer_reveal=_OUTSIDE,
            trace_cursor=10,
            duration_ms=28_000,
        ),
    ]

    return Tour(
        id="powerstore-elite-tour",
        title="A PowerStore Elite joins a working cluster",
        intro=L(
            novice=(
                "A guided walk through a storage upgrade that never stops the "
                "applications, narrated beat by beat. Watch it play, or pause "
                "and click anything to look closer; the tour waits for you. It "
                "reads best after the PowerStore tour."
            ),
            standard=(
                "A narrated walk through a live mixed-generation cluster join. "
                "Watch it play, or pause and explore; Resume tour brings the "
                "camera back. Best read after the PowerStore twin."
            ),
            expert="Narrated cluster-join walk-through. Pause to explore; read after PowerStore.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: ChassisAnatomy) -> TourResponse:
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
