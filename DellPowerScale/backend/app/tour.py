"""The narrated tour of a PowerScale cluster — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: nine beats that
move a camera across the cluster map, peel it from the protocols clients see
down to the drives and the back-end network, pin the namespace trace at the
moments that carry the story, and narrate each one. The frontend player owns
the clock; nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The storyboard follows the twin's one idea — there are no volumes: the
protocol band over six identical nodes, the namespace as the only shape that
spans every node, a file striped across the nodes, the cluster filling, two
nodes joining with no migration, and the live rebalance. The signature beat
is ``onefs-stripe``, pinned to the trace step that lays one file system
across every node. Every claim the scripts make is one the engine, the
anatomy, or ``tests/test_engine.py`` already makes.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``ClusterAnatomy`` is unchanged:

    0  what clients and administrators touch: the protocols, management
    1  the cluster itself: the namespace and the nodes
    2  inside and beneath the nodes: the drives and the back-end network
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
SIGNATURE_STEP_ID = "onefs-stripe"

_FACE = 0
_CLUSTER = 1
_BENEATH = 2

_PROTOCOLS = ["proto-nfs", "proto-smb", "proto-s3", "proto-hdfs"]
_FIRST_NODES = [f"node-{i}" for i in range(1, 5)]
_ALL_NODES = [f"node-{i}" for i in range(1, 7)]
_FIRST_MEDIA = [f"media-{i}" for i in range(1, 5)]
_ALL_MEDIA = [f"media-{i}" for i in range(1, 7)]


def layer_map(anatomy: ClusterAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    by_kind = {
        "protocol": _FACE,
        "management": _FACE,
        "namespace": _CLUSTER,
        "node": _CLUSTER,
        "media": _BENEATH,
        "interconnect": _BENEATH,
    }
    return {r.id: by_kind.get(r.kind, _CLUSTER) for r in anatomy.regions}


def build_tour(anatomy: ClusterAnatomy) -> Tour:
    """The PowerScale tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 2.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="cluster-exterior",
            title="Four protocols over six identical nodes",
            script=L(
                novice=(
                    "This is a Dell PowerScale, a group of storage computers "
                    "that together act as one giant shared drive for a whole "
                    "organisation. Across the top are the four languages it "
                    "speaks: NFS for Linux and Unix computers, SMB for Windows, "
                    "S3 for web-style apps, and HDFS for big data tools. "
                    "Below them sits a row of six identical boxes called "
                    "nodes, each with its own processor, memory, network and "
                    "drives. Right now only four are racked, and they are not "
                    "yet joined to each other; nodes five and six arrive later "
                    "in the story. Notice what is missing: nobody is about "
                    "to divide the space into walled-off sections called "
                    "volumes."
                ),
                standard=(
                    "This is Dell PowerScale, scale-out network-attached "
                    "storage (NAS): a cluster of nodes presenting one file "
                    "system. Across the top are the four protocols it serves "
                    "— NFS for Unix and Linux, SMB for Windows, S3 for object "
                    "access over HTTP, HDFS for analytics platforms. Below "
                    "runs a band of six identical nodes, each carrying its "
                    "own compute, memory, networking and drives. Four are "
                    "racked and unjoined; five and six join later in the "
                    "story. Watch for the step that never comes: nobody "
                    "carves this capacity into volumes."
                ),
                expert=(
                    "PowerScale scale-out NAS. NFS, SMB, S3, HDFS over a band "
                    "of six identical nodes; four racked, two pending. No "
                    "volume provisioning, ever."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=list(_PROTOCOLS),
            layer_reveal=_FACE,
            trace_cursor=0,
            duration_ms=28_000,
        ),
        TourStep(
            id="nodes-form",
            title="No controller, no head",
            script=L(
                novice=(
                    "The protocol labels fade back so we can look at the "
                    "machines. The four nodes find each other over a private "
                    "network only they use, called the back-end interconnect. "
                    "Every node runs the same software, OneFS, and OneFS joins "
                    "them into one team, called a cluster. There is no boss "
                    "machine: no controller, no head unit. Each node does the "
                    "same work and can answer requests by itself, so from now "
                    "on space, speed and safety belong to the whole cluster, "
                    "not to any one box."
                ),
                standard=(
                    "Peeling back the protocol band: the four nodes find each "
                    "other over the back-end interconnect, a private network "
                    "for node-to-node traffic, and OneFS — the operating "
                    "system every PowerScale node runs — joins them into one "
                    "cluster. There is no controller among them and no head "
                    "unit. Every node runs the same software and will answer "
                    "clients directly, so capacity, performance and "
                    "protection belong to the cluster as a whole. This took "
                    "about 45 seconds on the illustrative clock."
                ),
                expert=(
                    "Cluster formation over the back-end network. Symmetric "
                    "membership: no controller, no head node."
                ),
            ),
            # A close-up on the four nodes forming and the network joining
            # them; management is not part of this beat's story, so it is not
            # lit off-camera.
            camera=frame(*_FIRST_NODES, "interconnect"),
            region_ids=[*_FIRST_NODES, "interconnect"],
            layer_reveal=_CLUSTER,
            trace_cursor=1,
            duration_ms=26_000,
        ),
        TourStep(
            id="namespace-band",
            title="The one shape that spans every node",
            script=L(
                novice=(
                    "Look at the long bar between the protocols and the "
                    "nodes. It is the namespace: the single shared file "
                    "system, which lives at a folder called /ifs. It is drawn "
                    "as one unbroken shape, and it is the only thing in the "
                    "whole picture that stretches across every node, "
                    "including the two that have not arrived yet. Everything "
                    "else belongs to one node or sits in its own strip. The "
                    "namespace has no walls inside it, so there is nothing "
                    "smaller than the cluster that could ever fill up."
                ),
                standard=(
                    "Now the band between the protocols and the nodes comes "
                    "alive. It is the namespace — the single file system, "
                    "rooted at /ifs — and it is drawn as one continuous shape "
                    "for a reason: it is the only region on this map whose "
                    "extent crosses every node boundary, including the two "
                    "nodes still to come. Everything else belongs to a node "
                    "or sits in a band. There are no volumes underneath it "
                    "and no internal boundaries for data to be migrated "
                    "across."
                ),
                expert=(
                    "The namespace, /ifs: the only region spanning every "
                    "node. No volumes beneath it, no internal boundaries."
                ),
            ),
            camera=frame("namespace", *_ALL_NODES, pad=1.5),
            region_ids=["namespace"],
            layer_reveal=_CLUSTER,
            trace_cursor=2,
            duration_ms=26_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Every node holds part of every file",
            script=L(
                novice=(
                    "This is the most important moment in the tour. OneFS "
                    "lays that one file system across all four nodes at "
                    "once. Every file is cut into pieces called stripes, and "
                    "the stripes are spread over every node. Alongside them "
                    "OneFS stores extra maths called parity, a technique "
                    "known as erasure coding, so any lost piece can be "
                    "worked out again from the others. No node holds a whole "
                    "file, and every node holds a slice of every file. So "
                    "the edge of the file system is the edge of the cluster. "
                    "That is what no volumes really means: there is no "
                    "smaller container anywhere that could run out of room, "
                    "and no container to move data between."
                ),
                standard=(
                    "This is the idea the whole system is built around. "
                    "OneFS lays the single file system across all four nodes "
                    "at once: every file is cut into stripes and spread over "
                    "the cluster with erasure coding, mathematical parity "
                    "stored alongside the data from which any lost stripe "
                    "can be recomputed. Protection belongs to the file, not "
                    "to a RAID group inside one box. No node holds a whole "
                    "file; every node holds part of every file. The file "
                    "system's boundary is the cluster's boundary, so nothing "
                    "smaller than the cluster exists to fill up or to "
                    "migrate out of."
                ),
                expert=(
                    "Per-file striping across all nodes with "
                    "erasure coding. File-system boundary equals cluster "
                    "boundary; no sub-cluster container exists."
                ),
            ),
            camera=frame(
                "namespace", *_FIRST_NODES, *_FIRST_MEDIA, "interconnect",
                pad=1.5,
            ),
            region_ids=["namespace", *_FIRST_NODES, *_FIRST_MEDIA, "interconnect"],
            layer_reveal=_BENEATH,
            trace_cursor=2,
            duration_ms=40_000,
        ),
        TourStep(
            id="every-node-every-protocol",
            title="Any node, any protocol, same files",
            script=L(
                novice=(
                    "Now the cluster opens its doors. All four languages "
                    "switch on, and they all reach the very same files: a "
                    "picture saved from a Windows laptop can be read by a "
                    "Linux server or a web app without being copied. Just as "
                    "important, every node speaks all four. There is no "
                    "special Windows node and no special Linux node, so a "
                    "computer can connect through any node and see exactly "
                    "the same single file system. People start saving work, "
                    "and the cluster is about 18% full in this illustrative "
                    "run."
                ),
                standard=(
                    "The access layer comes up. NFS, SMB, S3 and HDFS all "
                    "reach the same files, and every node serves all four: "
                    "there is no NFS node and no SMB head, so a client can "
                    "mount the namespace through any node and see the same "
                    "single file system. That symmetry is what makes one "
                    "namespace usable rather than merely true. For the "
                    "object-only version of this trade, see the ObjectScale "
                    "spec in this repo. Clients begin writing; usage reaches "
                    "an illustrative 18%."
                ),
                expert=(
                    "NFS, SMB, S3, HDFS up on every node against one /ifs "
                    "tree. Symmetric multiprotocol service; 18% used."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[*_PROTOCOLS, "namespace", *_FIRST_NODES],
            layer_reveal=_BENEATH,
            trace_cursor=3,
            duration_ms=26_000,
        ),
        TourStep(
            id="namespace-fills",
            title="Full, but no volume is full",
            script=L(
                novice=(
                    "Months pass in one step, and the shared space climbs "
                    "past 80% full. On most file storage this is where the "
                    "trouble starts. Not because everything is full, but "
                    "because one walled-off section, one volume, is nearly "
                    "full while another sits half empty, and fixing that means "
                    "copying data around during planned downtime. Here there "
                    "are no volumes. The whole cluster fills evenly, so the "
                    "only choice coming is a simple one: add hardware. The "
                    "migrations counter still reads zero."
                ),
                standard=(
                    "Months compressed into a step: the one namespace climbs "
                    "to an illustrative 81% used. On a conventional NAS this "
                    "is where the pathology starts — one volume at 95% while "
                    "another sits half empty, and every correction a "
                    "migration and a maintenance window. Here there is no "
                    "container to hit 95%. The four nodes fill evenly, and "
                    "the only decision approaching is the simple one: add "
                    "hardware. Migrations required is zero, and it stays "
                    "there."
                ),
                expert=(
                    "81% used, uniform across the namespace. No per-volume "
                    "exhaustion possible; migrationsRequired = 0."
                ),
            ),
            # The namespace is what is filling, and it spans the full width,
            # so the frame does too: nodes five and six stay dark on the right.
            camera=frame("namespace", *_FIRST_NODES, *_FIRST_MEDIA, pad=1.5),
            region_ids=["namespace", *_FIRST_NODES, *_FIRST_MEDIA],
            layer_reveal=_BENEATH,
            trace_cursor=4,
            duration_ms=26_000,
        ),
        TourStep(
            id="add-a-node",
            title="Two nodes join, still one namespace",
            script=L(
                novice=(
                    "Here is the moment other storage turns into a project. "
                    "Nodes five and six are plugged into the private network "
                    "and join the cluster in about a minute. Watch the "
                    "numbers: total space jumps from 400 to 600 terabytes, "
                    "and the used share falls from 81% to 54%, both "
                    "illustrative. But the count of namespaces stays at one, "
                    "because the existing file system simply became larger. "
                    "Nothing was set up, nothing was divided, and no data "
                    "had to be moved by hand. Growing was a purchase and two "
                    "cables."
                ),
                standard=(
                    "Nodes five and six are cabled to the interconnect and "
                    "OneFS absorbs them in about a minute. The counters make "
                    "the argument: capacity jumps from 400 TB to 600 TB and "
                    "used falls from 81% to 54% (illustrative figures), while "
                    "namespaces stays at one — the file system became larger "
                    "rather than gaining a sibling. Nothing was provisioned "
                    "and migrations required is still zero. On a conventional "
                    "NAS this is a planning exercise; here it is a purchase "
                    "and two cables."
                ),
                expert=(
                    "Node-join: 400 to 600 TB, 81% to 54% used. namespaces = "
                    "1, migrationsRequired = 0. No provisioning."
                ),
            ),
            # Everything the join lights, down to the interconnect the new
            # nodes are cabled to and the management surface that admits them.
            camera=frame(
                "namespace", *_ALL_NODES, *_ALL_MEDIA, "interconnect", "mgmt",
                pad=1.5,
            ),
            region_ids=["namespace", *_ALL_NODES, *_ALL_MEDIA, "interconnect", "mgmt"],
            layer_reveal=_BENEATH,
            trace_cursor=5,
            duration_ms=30_000,
        ),
        TourStep(
            id="live-rebalance",
            title="The slow part, while clients keep working",
            script=L(
                novice=(
                    "Now the cluster spreads some of everything onto the two "
                    "new nodes, so all six share the work evenly. A "
                    "background job called AutoBalance does this, and it is "
                    "the slowest stage in the whole timeline, on purpose. "
                    "Moving a share of every file is real work, and it is "
                    "the price of never having to plan a migration. The key "
                    "word is background: all four languages stay on, on "
                    "every node, and people keep opening and saving the same "
                    "files the whole time. Growing is a chore the cluster "
                    "does quietly, not a shutdown."
                ),
                standard=(
                    "AutoBalance, the OneFS job that keeps data spread "
                    "evenly, restripes files onto the new nodes — the arcs "
                    "across the node row. It is deliberately the longest "
                    "stage in the trace: moving a share of everything onto "
                    "new hardware is genuinely slow, and it is the price of "
                    "never migrating. Every protocol stays up on every node "
                    "throughout, and clients keep reading and writing the "
                    "same paths. Expansion is a background task, not an "
                    "outage."
                ),
                expert=(
                    "AutoBalance restripe onto nodes 5–6; longest stage. All "
                    "protocols up on all nodes throughout. No outage."
                ),
            ),
            # The protocols are part of the claim (service continues), so the
            # frame keeps them in view along with the arcs on the node row.
            camera=frame(
                *_PROTOCOLS, "namespace", *_ALL_NODES, *_ALL_MEDIA, "interconnect",
                pad=1.5,
            ),
            region_ids=[
                "namespace", *_PROTOCOLS, *_ALL_NODES, *_ALL_MEDIA, "interconnect",
            ],
            layer_reveal=_BENEATH,
            trace_cursor=6,
            duration_ms=34_000,
        ),
        TourStep(
            id="served-at-six",
            title="Bigger, and still one file system",
            script=L(
                novice=(
                    "The layers come back together. Six nodes now share the "
                    "one file system evenly, and the two newcomers carry "
                    "their full share of the work. Add up what growing cost: "
                    "no volume was created, no data was moved by hand, and "
                    "nobody had to reconnect anything. The PowerFlex twin in "
                    "this collection does the same trick for block storage, "
                    "the raw disk-like kind that databases use, by removing "
                    "the controller. The Exascale twin covers Dell's separate "
                    "Lightning file system, a faster, temporary work area "
                    "that sits beside a cluster like this one, and CloudIQ "
                    "watches the cluster's health."
                ),
                standard=(
                    "Reassembled at larger scale. Six nodes serve the one "
                    "file system, every stripe balanced across them. The "
                    "expansion cost no provisioned volume, no hand migration "
                    "and no client remount. The PowerFlex twin next door is "
                    "the sibling refusal, deleting the controller from block "
                    "storage where OneFS deleted the volume. The Exascale "
                    "twin's Lightning file system is a separate product, not "
                    "OneFS: Dell positions it as the scratch tier beside "
                    "PowerScale, which serves the rest of the data's life. "
                    "CloudIQ is where this cluster's telemetry goes."
                ),
                expert=(
                    "Six nodes, one namespace, balanced. Sibling refusals: "
                    "PowerFlex (controller), OneFS (volume)."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_FACE,
            trace_cursor=7,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="powerscale-tour",
        title="Inside a PowerScale, as it grows",
        intro=L(
            novice=(
                "A guided walk through the cluster as it forms, fills up and "
                "grows, narrated beat by beat. Sit back and watch, or pause "
                "and click anything to look closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through the cluster as it forms, fills and "
                "grows. Watch it play, or pause and explore; Resume tour "
                "brings the camera back."
            ),
            expert="Narrated form-fill-grow walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
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
