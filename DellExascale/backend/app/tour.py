"""The narrated tour of an Exascale rack feeding a training job — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
move a camera across the data-path map, peel it from the parts you can name
from the outside (the GPU racks, the fabric, the four storage engines) down to
the control path and then the data path, pin the trace cursor at the moments
that carry the story, and narrate each one. The frontend player owns the
clock; nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The storyboard follows the job's data: client racks meet the storage rack,
the mount, the one layout request, the fan-out across all four data servers,
~6 TB/s aggregate, the checkpoint burst, and tiering. The signature beat is
``metadata-leaves``: the trace step where the metadata server goes dark while
every data server lights, the fact ``test_metadata_leaves_the_data_path``
pins. Every claim the scripts make is one the engine and the anatomy already
make; the trace index named in each beat is the step whose description says
the same thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``PlatformAnatomy`` is unchanged:

    0  what you can name from outside: GPU racks, fabric, the four engines
    1  the control path: the metadata server
    2  the data path: stripe fan-out, data servers and their NVMe
"""

from __future__ import annotations

from twinkit.tour import (
    Tour,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import PlatformAnatomy

#: The step the tests pin: the twin's one idea lives here.
SIGNATURE_STEP_ID = "metadata-leaves"

_OUTSIDE = 0
_CONTROL = 1
_DATA = 2

_SERVERS = [f"data-ds{i}" for i in range(1, 5)]
_MEDIA = [f"media-ds{i}" for i in range(1, 5)]


def layer_map(anatomy: PlatformAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.kind == "metadata":
            layers[region.id] = _CONTROL
        elif region.kind in {"dataserver", "media"} or region.id == "fanout":
            layers[region.id] = _DATA
        else:
            layers[region.id] = _OUTSIDE
    return layers


def build_tour(anatomy: PlatformAnatomy) -> Tour:
    """The Exascale tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0):
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="two-racks",
            title="A rack of GPUs and a rack of storage",
            script=L(
                novice=(
                    "On the left are racks of GPUs, the graphics processors that "
                    "train AI models, the same XE9712 machines another twin in "
                    "this collection shows powering up. Everything to the right "
                    "of them is one Dell Exascale storage rack. Between the two "
                    "runs the network, called the fabric. Along the bottom sit "
                    "the ways this one rack can store data: as ordinary files "
                    "and fast parallel files, which share one box on the map, "
                    "and as objects, the way cloud storage keeps things. The "
                    "box for blocks, the kind of storage databases use, is "
                    "something Dell plans to add in 2027. Right now the rack is powered on and "
                    "idle, and no training job is attached yet."
                ),
                standard=(
                    "On the left, the readers: racks of GPUs, the XE9712 systems "
                    "from this repo's AI Factory. Everything to their right is "
                    "one Dell Exascale storage rack. Between them, the scale-out "
                    "fabric, which the SN6000 twin covers. Along the bottom are "
                    "the rack's engines in one footprint: file (PowerScale's "
                    "OneFS) and parallel file (the Lightning File System) "
                    "sharing one box, and object (ObjectScale). Block "
                    "(PowerFlex) is drawn too, though Dell targets it for the "
                    "first half of 2027. The rack is up and idle, with no job "
                    "attached."
                ),
                expert=(
                    "XE9712 GPU racks, fabric, one Exascale rack: file, "
                    "Lightning and object co-resident, block planned. Idle."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[
                "clients", "fabric", "protocol-file", "protocol-object",
                "protocol-block", "mgmt",
            ],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="mount",
            title="The mount learns who to ask",
            script=L(
                novice=(
                    "The storage engines along the bottom fade back, and the "
                    "light moves to the long block at the top: the metadata "
                    "server, the part of a file system that keeps track of where "
                    "everything is. It sits above the storage servers, not among "
                    "them. The GPU racks now connect "
                    "to the file system. This tour shows that connection using "
                    "pNFS, short for parallel NFS. It is a standard way of "
                    "reaching shared files that lets one computer talk to many "
                    "storage servers at once instead of just one. Dell also has "
                    "its own software for this, the Lightning File System, and "
                    "it does the same job. "
                    "The connection is an ordinary handshake. Nothing has been "
                    "read. The GPUs have learned who to ask, not where the data is."
                ),
                standard=(
                    "The outer layer fades back and the light moves to the "
                    "metadata server, drawn above the data servers rather than "
                    "among them. The GPU racks mount the parallel file path, "
                    "narrated here as pNFS (parallel NFS), the standard extension "
                    "that lets one client talk to many servers at once; "
                    "PowerScale's OneFS ships it, and the Lightning File System "
                    "gets the same split with Dell's own client. The mount is a "
                    "plain handshake with the metadata server: credentials and a "
                    "namespace. No data has moved. The clients know who to ask, "
                    "not yet where anything lives."
                ),
                expert=(
                    "pNFS mount against the metadata server: credentials, "
                    "namespace. No data path yet."
                ),
            ),
            camera=frame("clients", "fabric", "metadata"),
            region_ids=["clients", "fabric", "metadata"],
            layer_reveal=_CONTROL,
            trace_cursor=1,
            duration_ms=26_000,
        ),
        TourStep(
            id="one-question",
            title="One question, answered once",
            script=L(
                novice=(
                    "Big files here are cut into pieces called stripes, and the "
                    "stripes are spread across several storage servers. So the "
                    "GPUs ask the metadata server a single question: where do the "
                    "pieces of these files live? The answer is a layout, a map "
                    "that says which server holds which piece. The metadata "
                    "server hands that map over once. This is the only time it "
                    "takes part in reading this job's data."
                ),
                standard=(
                    "Large files are cut into stripes spread across the data "
                    "servers, so the client asks one question: where do this "
                    "file's stripes live? The answer is a layout. Under Flex Files, "
                    "the pNFS layout type that lets ordinary NFS servers act as "
                    "data servers, a layout is exactly that map, from stripe to "
                    "data server. The metadata server answers once and hands the "
                    "layout over. That is its only part in this job's read path."
                ),
                expert=(
                    "Flex Files layout granted once: the stripe-to-server map. "
                    "The metadata server's only touch on the read path."
                ),
            ),
            camera=frame("clients", "fabric", "metadata"),
            region_ids=["clients", "fabric", "metadata"],
            layer_reveal=_CONTROL,
            trace_cursor=2,
            duration_ms=26_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="The metadata server steps aside",
            script=L(
                novice=(
                    "This is the moment the whole design exists for. Now we can "
                    "see the data path, and something happens at once: the "
                    "metadata block at the top goes dark, and all four storage "
                    "servers light up together. Each GPU already holds the map it "
                    "was handed a moment ago — the list of which server keeps "
                    "which piece of the file — so it goes straight to every "
                    "server that has a piece and pulls all the pieces at the "
                    "same time. The metadata server is no longer "
                    "involved at all. It could even be restarted in the middle "
                    "of the read and the transfer would carry on. Compare the "
                    "PowerStore and PowerMax twins, where every byte passes "
                    "through a controller, the single box in charge of the "
                    "storage, so the controller's limit is the whole system's "
                    "limit. Here the speed is the sum of every "
                    "server streaming, not the limit of one box."
                ),
                standard=(
                    "This is the twin's one idea. With the data path revealed, "
                    "watch the map: the metadata block goes dark and all four "
                    "data servers light at once. The client is already holding "
                    "the layout it was granted a step earlier — the map of which "
                    "server holds which stripe — so it "
                    "opens a stream to every data server named in it and reads "
                    "its stripes in parallel. The metadata server is out of the "
                    "path, and could be restarted mid-read without stopping the "
                    "transfer. In the PowerStore and PowerMax twins every byte "
                    "crosses a controller; here throughput is the sum of the "
                    "servers streaming, not the ceiling of one."
                ),
                expert=(
                    "Signature: metadata leaves the data path. Layout held, "
                    "four-way parallel stripe reads, MDS dark and restartable "
                    "mid-read. Throughput sums across servers; no controller "
                    "ceiling."
                ),
            ),
            camera=frame("metadata", "clients", "fanout", *_SERVERS, *_MEDIA, pad=2.0),
            region_ids=["clients", "fabric", "fanout", *_SERVERS, *_MEDIA],
            layer_reveal=_DATA,
            trace_cursor=3,
            duration_ms=40_000,
        ),
        TourStep(
            id="six-terabytes",
            title="About six terabytes a second",
            script=L(
                novice=(
                    "Now the rack reaches full speed: about six terabytes every "
                    "second, the most Dell says one Exascale rack can read, "
                    "flowing from the flash drives called NVMe, through the four "
                    "servers, across the network and into the GPUs' own memory. "
                    "Direct memory paths, known as RDMA and GPUDirect, let the "
                    "data land there without a detour through ordinary "
                    "processors. RDMA stands for remote direct memory access. "
                    "Every server is streaming, because the speed "
                    "only exists when all of them work at once."
                ),
                standard=(
                    "Full stride: roughly 6 TB/s aggregate, about 48,000 gigabits "
                    "per second, the per-rack read ceiling Dell claims for the "
                    "Lightning File System, flowing from "
                    "NVMe flash through the data servers and across the fabric "
                    "into GPU memory. RDMA and GPUDirect put the data in GPU "
                    "memory without a detour through host CPUs. All four servers "
                    "stream, because in this design throughput exists only when "
                    "the read fans out to every one of them."
                ),
                expert=(
                    "~6 TB/s (≈48,000 Gbps), Dell's per-rack claim. NVMe to GPU "
                    "memory over RDMA/GPUDirect; full four-way fan-out."
                ),
            ),
            camera=frame("clients", "fanout", *_SERVERS, *_MEDIA),
            region_ids=["clients", "fabric", "fanout", *_SERVERS, *_MEDIA],
            layer_reveal=_DATA,
            trace_cursor=4,
            duration_ms=26_000,
        ),
        TourStep(
            id="checkpoint-burst",
            title="The checkpoint burst",
            script=L(
                novice=(
                    "This is the longest stage in the trace, so the Data path "
                    "page lingers here. "
                    "Every so often the training job saves its own progress, "
                    "called a checkpoint. For a very large model that progress "
                    "is terabytes, and it arrives all at once from every GPU "
                    "rack, spread in pieces across the same four servers. The "
                    "save makes new files, so the GPUs first ask the metadata "
                    "server for a map of them. That takes a few tiny messages, "
                    "too brief to draw, and none of the saved data goes through "
                    "it. The saving itself trains nothing. But "
                    "it decides how much work a failure can wipe out, so a "
                    "faster save means saving more often, and losing minutes "
                    "instead of hours when a GPU dies."
                ),
                standard=(
                    "The trace's longest stage, where the Data path page "
                    "dwells. The job saves "
                    "itself: a trillion-parameter model's state runs to "
                    "terabytes, and it lands all at once from every GPU rack, "
                    "across the same striped layout. A checkpoint is pure "
                    "overhead while it runs, yet it bounds how much work a "
                    "failure can destroy. Faster checkpoints allow more frequent "
                    "ones, so a failed GPU costs minutes rather than hours. The "
                    "checkpoint files are new, so the client gets their layouts "
                    "from the metadata server first: a few small messages, too "
                    "brief to draw, and no checkpoint bytes. The bulk write "
                    "bypasses it as the reads do."
                ),
                expert=(
                    "Max dwell: checkpoint burst, terabytes from every rack "
                    "across the stripes. Overhead that bounds redo on failure. "
                    "Create, rw layout and commit touch the MDS, undrawn: zero "
                    "bulk bytes."
                ),
            ),
            camera=frame("clients", "fanout", *_SERVERS, *_MEDIA),
            region_ids=["clients", "fabric", "fanout", *_SERVERS, *_MEDIA],
            layer_reveal=_DATA,
            trace_cursor=5,
            duration_ms=32_000,
        ),
        TourStep(
            id="tier-in-place",
            title="Cold data moves to object, inside the rack",
            script=L(
                novice=(
                    "Between rounds of training, data the job has finished with "
                    "moves from the fast file storage down to cheaper object "
                    "storage, ObjectScale, which speaks the S3 protocol many "
                    "cloud tools use. Both live in this same rack, so the move "
                    "never crosses the network to a separate archive, and nobody "
                    "has to reconcile two sets of names afterwards. This is why "
                    "putting several kinds of storage in one rack matters."
                ),
                standard=(
                    "Between epochs, data the job is done with ages from the "
                    "file tier to ObjectScale's S3 object tier. Tiering here is "
                    "internal because both engines share the rack: no copy over "
                    "the network to a separate archive, no second namespace to "
                    "reconcile. That is the argument for several engines in one "
                    "footprint, and Dell plans PowerFlex block beside them, for "
                    "the databases, in 2027."
                ),
                expert=(
                    "File to S3 object tiering, rack-internal: no cross-network "
                    "copy, no second namespace."
                ),
            ),
            camera=frame("protocol-file", "protocol-object", *_SERVERS, *_MEDIA),
            region_ids=["protocol-file", "protocol-object", *_SERVERS, *_MEDIA],
            layer_reveal=_DATA,
            trace_cursor=6,
            duration_ms=26_000,
        ),
        TourStep(
            id="reassemble",
            title="Read, train, checkpoint, repeat",
            script=L(
                novice=(
                    "The layers go back on. This is what the next few weeks look "
                    "like: stream a batch of data from every server at once, "
                    "train on it, save progress, and repeat, while old data "
                    "slides down to cheaper storage underneath. Almost the "
                    "whole map is lit, and the metadata server at the top is "
                    "still dark: it has nothing more to do for these files. "
                    "The GPUs never "
                    "wait for data, which is the only thing a storage system "
                    "like this is judged on. The timings in this trace are "
                    "illustrative. Watch it beside the XE9712 and SN6000 twins "
                    "to see the whole AI factory at work."
                ),
                standard=(
                    "Reassembled, and in steady state: stream a batch in "
                    "parallel, compute, checkpoint, repeat, with cold data "
                    "tiering underneath. The GPUs, the data path and the file "
                    "and object engines are lit; the metadata server stays "
                    "dark. The GPUs never wait on storage, which "
                    "is the only review an AI data platform gets. Timings on "
                    "this trace are illustrative. Run it beside the XE9712 and "
                    "SN6000 twins for the whole factory; the Data path page "
                    "walks the same trace one step at a time."
                ),
                expert=(
                    "Steady state: parallel read, train, checkpoint, tier; MDS "
                    "stays dark. GPUs never stall on I/O. Illustrative timings."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[
                "clients", "fabric", "protocol-file", "protocol-object", "mgmt",
                *_SERVERS, *_MEDIA,
            ],
            layer_reveal=_OUTSIDE,
            trace_cursor=7,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="exascale-tour",
        title="Inside an Exascale rack, feeding a training job",
        intro=L(
            novice=(
                "A guided walk through one training job's data, narrated beat by "
                "beat. Sit back and watch, or pause and click any block to look "
                "closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through a training job's data path. Watch it "
                "play, or pause and explore; Resume tour brings the camera back."
            ),
            expert="Narrated data-path walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: PlatformAnatomy) -> TourResponse:
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
