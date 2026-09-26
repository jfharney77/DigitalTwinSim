"""Pure data-path engine for Exascale Storage + Lightning File System.

``simulate()`` returns the deterministic trace of an AI training job's data
— mounting a parallel filesystem, fetching a layout, streaming stripes from
many data servers at once, saturating the GPUs, checkpointing, and tiering
cold data to object. Same purity rule as every other twin in this repo: no
FastAPI, no IO, no timers — the frontend owns the playback clock, and each
``DataState`` is plain data the renderer consumes. ``cycle_cost`` marks the
long stages (the checkpoint burst) so the UI dwells on them.

The one idea this twin exists to teach: **the metadata server is not in the
data path.** Every block-storage twin in this repo (PowerStore, PowerMax)
funnels bytes through a controller, and the controller's ceiling is the
system's ceiling. A parallel file system refuses that bargain. The client
asks the metadata server one question — where do this file's stripes live?
— receives a layout, and from then on talks straight to the data servers,
in parallel, with the metadata server out of the conversation entirely.
Throughput becomes the *sum* of the data servers rather than the maximum of
one controller, which is how a rack reaches multiple terabytes per second
and keeps thousands of GPUs fed.

``tests/test_engine.py`` holds the engine to exactly that: the metadata
region may not be active during any bulk-data phase. Sizes and timings are
illustrative but plausible for an Exascale-class rack; favor a correct
mental model over measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import DataState

# Four data servers drawn; a real Exascale rack holds many more. Their
# count is the point — throughput scales with them, not with a controller.
DATA_SERVERS = ["ds1", "ds2", "ds3", "ds4"]
MEDIA = [f"media-{d}" for d in DATA_SERVERS]

# Phases where bulk data is moving. The metadata server must be absent from
# every one of them — see test_metadata_leaves_the_data_path.
BULK_PHASES = {"stripe", "feed", "checkpoint", "tier", "steady"}


def _servers() -> list[str]:
    return [f"data-{d}" for d in DATA_SERVERS]


def simulate() -> list[DataState]:
    """The job's data journey, from mount to steady-state training loop."""
    return [
        DataState(
            step=0,
            phase="idle",
            label="Exascale rack online, no job attached",
            description=L(
                novice=(
                    "The storage rack is powered up and idle. Inside one footprint "
                    "sit the ways of accessing data that an AI system needs: "
                    "ordinary files, high-speed parallel files, and object "
                    "storage, with block storage for databases planned by Dell "
                    "for 2027. Putting them together is not tidiness. A training "
                    "dataset typically arrives as objects, gets prepared as files, "
                    "and must then be read very fast indeed — and shuttling "
                    "petabytes between separate systems for each of those steps "
                    "would waste more time than the training itself."
                ),
                plain=(
                    "The storage rack is up and idle. Inside one footprint sit the "
                    "access patterns an AI factory needs: file (OneFS), parallel "
                    "file (Lightning), and object (ObjectScale), with block "
                    "(PowerFlex) planned by Dell for 2027. Consolidating them is "
                    "not tidiness — a training "
                    "corpus arrives as objects, is prepared as files, and must be "
                    "read at parallel-filesystem speed, and moving petabytes "
                    "between separate systems for each stage costs more than the "
                    "training."
                ),
                standard=(
                    "The storage rack is up and idle. Inside one footprint sit "
                    "the access patterns an AI factory needs, each a software "
                    "personality on the same servers: file (PowerScale's "
                    "OneFS), parallel file (Lightning), and object "
                    "(ObjectScale). Dell targets block (PowerFlex) for the "
                    "first half of 2027, so that box stays dark. Consolidating "
                    "them is not tidiness — a training corpus arrives as objects, is "
                    "prepared as files, and must be read at parallel-filesystem "
                    "speed, and moving petabytes between separate systems for "
                    "each step wastes more time than the training itself."
                ),
                technical=(
                    "Rack up, idle. Three personalities co-resident on common "
                    "nodes: file (OneFS), parallel file (Lightning), object "
                    "(ObjectScale); block (PowerFlex) targeted 1H CY2027. "
                    "Consolidation is a "
                    "data-movement argument, not an aesthetic one — the corpus "
                    "transits object → file → parallel-file, and inter-system "
                    "copies at petabyte scale dominate the pipeline."
                ),
                expert=(
                    "File, parallel file, object co-resident; block planned 2027. "
                    "Consolidation avoids petabyte-scale inter-system "
                    "copies across the object → file → parallel-file transit."
                ),
            ),
            active_regions=["mgmt", "protocol-file", "protocol-object"],
            throughput_gbps=0,
            data_servers_streaming=0,
            layout_held=False,
            elapsed_seconds=0,
        ),
        DataState(
            step=1,
            phase="mount",
            label="GPU clients mount the parallel filesystem",
            description=L(
                novice=(
                    "The compute racks connect to the file system using a standard "
                    "protocol that lets a client talk to many servers at once "
                    "rather than just one. The connection itself is ordinary: a "
                    "handshake, credentials, a name for the storage. Nothing has "
                    "been read yet. Note carefully what the client has just learned "
                    "— not where any data is, only who to ask."
                ),
                plain=(
                    "The compute racks connect to the rack's parallel file path. "
                    "This twin tells it as pNFS — parallel NFS, the open standard "
                    "PowerScale ships, which lets one client talk to many servers "
                    "at once; the Lightning File System does the same job with "
                    "Dell's own client software. The "
                    "connection itself is unremarkable: a handshake with the "
                    "metadata server, credentials, a namespace. Nothing has been "
                    "read yet. Notice what the client has actually learned — not "
                    "where any data is, only who to ask for it."
                ),
                standard=(
                    "The compute racks mount the parallel file path. The twin "
                    "narrates it as pNFS — parallel NFS, the standardized "
                    "extension of NFS that lets a client talk to many servers "
                    "at once instead of one, which PowerScale's OneFS ships and "
                    "ordinary Linux clients speak. The Lightning File System "
                    "reaches the same split with Dell's own client software. "
                    "The mount itself is ordinary: a handshake with the "
                    "metadata server, credentials, a namespace. Nothing has "
                    "been read yet. Note what the client has just learned — not "
                    "where any data is, only who to ask."
                ),
                technical=(
                    "Clients mount over pNFS — the standardized NFS extension "
                    "permitting many-server access from one client, as OneFS "
                    "ships it; Lightning FS substitutes its own client. "
                    "Ordinary mount semantics: metadata server handshake, "
                    "credentials, namespace. No data path established. The client "
                    "has learned who to ask, not where anything is."
                ),
                expert=(
                    "pNFS mount: MDS handshake, credentials, namespace. No data "
                    "path yet — the client knows who to ask, not where."
                ),
            ),
            active_regions=["clients", "fabric", "metadata"],
            throughput_gbps=0,
            data_servers_streaming=0,
            layout_held=False,
            elapsed_seconds=2,
        ),
        DataState(
            step=2,
            phase="layout",
            label="The client asks where the stripes live",
            description=L(
                novice=(
                    "The pivotal exchange. The client asks for a layout — a map "
                    "saying which servers hold which pieces of which files — and "
                    "the metadata server answers once and hands it over. This is "
                    "the only moment the metadata server touches this job's read "
                    "path. Everything after it is a direct conversation between the "
                    "client and the servers holding the data, which is precisely "
                    "why that one server does not become the bottleneck."
                ),
                plain=(
                    "The pivotal exchange. The client requests a layout for the "
                    "files it wants. Under Flex Files (the pNFS layout type that "
                    "lets ordinary NFS servers act as data servers), a layout is a "
                    "map saying which data servers hold which stripes of which "
                    "file. The metadata server answers once and hands over the "
                    "layout. This is the only "
                    "moment the metadata server touches this job's read path. "
                    "Everything after is a direct conversation between the client "
                    "and the data servers, which is why it never becomes the "
                    "ceiling."
                ),
                standard=(
                    "The pivotal exchange. The client requests a layout for "
                    "the files it wants. Under Flex Files (the pNFS layout type "
                    "that lets ordinary NFS servers act as data servers), the "
                    "layout is a map saying which data servers hold which "
                    "stripes of which file. The metadata server answers once "
                    "and hands over the layout. This is the only moment the "
                    "metadata server "
                    "touches this job's read path. Everything after it is a "
                    "direct conversation between the client and the data "
                    "servers, which is precisely why the metadata server never "
                    "becomes the bottleneck no matter how many GPUs pile on."
                ),
                technical=(
                    "The pivotal exchange: the client requests a Flex Files layout "
                    "— the stripe-to-data-server map — and the MDS answers once "
                    "with the layout (LAYOUTGET, not a delegation). This is the "
                    "only MDS touch on the read path; in this trace the metadata "
                    "region is active in exactly {mount, layout} and absent from "
                    "every bulk phase, and the twin's tests enforce that."
                ),
                expert=(
                    "Flex Files layout requested; MDS answers once with the "
                    "layout. Only MDS touch on the read path — active in "
                    "exactly {mount, layout} (test-enforced)."
                ),
            ),
            active_regions=["clients", "fabric", "metadata"],
            throughput_gbps=0,
            data_servers_streaming=0,
            layout_held=True,
            elapsed_seconds=3,
        ),
        DataState(
            step=3,
            phase="stripe",
            label="Parallel read fans out — the metadata server steps aside",
            description=L(
                novice=(
                    "Holding the map, the client opens connections to every server "
                    "named in it and pulls its pieces simultaneously. The metadata "
                    "server is now completely out of the way — it could be "
                    "restarted mid-read without interrupting the transfer. Watch "
                    "the picture: the metadata block goes dark while all four data "
                    "servers light up at once. That single visual is the difference "
                    "between this design and a conventional storage system."
                ),
                plain=(
                    "Holding the layout, the client opens connections to every data "
                    "server named in it and pulls its stripes simultaneously. The "
                    "metadata server is now entirely out of the path — it could be "
                    "rebooted mid-read without interrupting the transfer. Watch the "
                    "map: the metadata block goes dark while all four data servers "
                    "light at once. That single visual is the difference between a "
                    "parallel file system and everything else."
                ),
                standard=(
                    "Holding the layout, the client opens connections to every "
                    "data server named in it and pulls its stripes "
                    "simultaneously. The metadata server is now entirely out of "
                    "the path — it could be rebooted mid-read without "
                    "interrupting this transfer. Watch the map: the metadata "
                    "block goes dark while all four data servers light at once. "
                    "That single visual is the difference between a parallel "
                    "file system and everything else in this repo — throughput "
                    "is now the sum of the servers streaming, not the "
                    "maximum of one controller."
                ),
                technical=(
                    "With the layout held, the client opens connections to every "
                    "named data server and reads stripes concurrently. The MDS is "
                    "out of the path entirely — restartable mid-transfer without "
                    "interruption. The map shows it: metadata dark, all four data "
                    "servers lit. In this trace nonzero throughput always means "
                    "full four-way fan-out."
                ),
                expert=(
                    "Layout held; concurrent reads from all named data servers. MDS "
                    "out of path — restartable mid-transfer. Throughput implies "
                    "full fan-out."
                ),
            ),
            active_regions=["clients", "fabric"] + _servers() + MEDIA,
            throughput_gbps=12000,
            data_servers_streaming=4,
            layout_held=True,
            elapsed_seconds=8,
            cycle_cost=2,
        ),
        DataState(
            step=4,
            phase="feed",
            label="GPUs saturated — full read throughput",
            description=L(
                novice=(
                    "The rack reaches its stride: roughly six terabytes every "
                    "second, the most Dell says one rack can read, flowing from "
                    "flash storage, through the servers, across "
                    "the network and into the memory of the graphics processors. "
                    "The gauge above says 48 Tb/s, which is terabits; eight bits "
                    "make a byte, so 48 terabits a second is the same speed as "
                    "about six terabytes a second. "
                    "Special data paths let the information land directly in that "
                    "memory without a detour through the ordinary processors, so "
                    "the chips that matter spend their time on mathematics rather "
                    "than on copying data around."
                ),
                plain=(
                    "The rack reaches its stride: roughly 6 TB/s aggregate — about "
                    "48,000 gigabits per second, Dell's claimed per-rack read "
                    "ceiling — flowing from NVMe flash through "
                    "the data servers and across the fabric into GPU memory. RDMA "
                    "and GPUDirect paths let the data land in GPU memory without a "
                    "detour through host CPUs, so the processors that matter spend "
                    "their cycles on mathematics rather than copying."
                ),
                standard=(
                    "The rack reaches its stride: roughly 6 TB/s aggregate — "
                    "about 48,000 gigabits per second — flowing from NVMe flash "
                    "through the data servers and across the fabric into GPU "
                    "memory. RDMA and GPUDirect paths let the data land in GPU "
                    "memory without a detour through host CPUs, so the "
                    "processors that matter spend their cycles on mathematics "
                    "rather than on copying. The 6 TB/s is Dell's own figure "
                    "for a rack running the Lightning File System, used here "
                    "as an illustrative peak; for PowerScale's pNFS Dell "
                    "claims up to 6× NFSv3 on large files. The reason for both "
                    "is on screen: four servers streaming, none of them "
                    "waiting on a metadata lookup."
                ),
                technical=(
                    "~6 TB/s aggregate (≈48,000 Gbps; Dell's per-rack read claim "
                    "for the Lightning personality) from NVMe through the data "
                    "servers across the fabric into GPU memory. RDMA and GPUDirect "
                    "eliminate the host-CPU bounce, so host cycles are not spent on "
                    "data movement. The trace peaks at 48,000 Gbps, illustrative."
                ),
                expert=(
                    "~6 TB/s (≈48,000 Gbps, vendor claim) NVMe → data servers → fabric → GPU "
                    "memory. RDMA/GPUDirect, no host bounce."
                ),
            ),
            active_regions=["clients", "fabric"] + _servers() + MEDIA,
            throughput_gbps=48000,
            data_servers_streaming=4,
            layout_held=True,
            elapsed_seconds=30,
            cycle_cost=3,
        ),
        DataState(
            step=5,
            phase="checkpoint",
            label="Checkpoint burst — new files, written across the same servers",
            description=L(
                novice=(
                    "The long stage. Every so often the training job must save its "
                    "own state, and for a very large model that state is terabytes "
                    "— landing all at once, across the same spread-out arrangement, "
                    "from every compute rack at the same instant. Saving state is "
                    "the least glamorous number in this field and one of the most "
                    "consequential: it is pure overhead while it happens, and yet "
                    "it decides how much work a failure can destroy. Saving makes "
                    "new files, so the job first asks the metadata server for "
                    "their maps. That is a few tiny messages, too brief to draw "
                    "here, and none of the saved data passes through it: the "
                    "terabytes go straight to the storage servers, as the reads did."
                ),
                plain=(
                    "The long stage. Every so often the training job must save "
                    "itself: a trillion-parameter model's state is terabytes, and "
                    "it lands all at once across the same striped layout, in "
                    "parallel, from every GPU rack simultaneously. Checkpointing is "
                    "the least glamorous number in AI infrastructure and one of the "
                    "most consequential — pure overhead while it runs, yet it "
                    "bounds how much work a failure can destroy. A checkpoint "
                    "writes new files, so the client first gets their layouts from "
                    "the metadata server: a few small messages, too brief to draw "
                    "here, carrying none of the checkpoint. The bulk write goes "
                    "straight to the data servers, as the reads did."
                ),
                standard=(
                    "The long stage. Every so often the training job must save "
                    "itself: a trillion-parameter model's state is terabytes, "
                    "and it lands all at once across the same striped layout, "
                    "in parallel, from every GPU rack at the same instant. "
                    "Checkpointing is the least glamorous number in AI "
                    "infrastructure and one of the most consequential — it is "
                    "pure overhead while it runs, yet it bounds how much work a "
                    "failure can destroy. Faster checkpoints mean more frequent "
                    "ones, which means a dead GPU costs minutes instead of "
                    "hours. A checkpoint writes new files, so the client first "
                    "gets their layouts from the metadata server and commits "
                    "them afterwards: a few small messages, too brief to draw "
                    "here, carrying none of the checkpoint's bytes. The bulk "
                    "write bypasses the metadata server exactly as the reads do."
                ),
                technical=(
                    "Max-dwell stage. Checkpoint writes a trillion-parameter "
                    "model's state — terabytes — across the same striped layout, in "
                    "parallel, from every rack simultaneously. Pure overhead while "
                    "it runs and the bound on failure-recoverable work; checkpoint "
                    "interval is the trade between overhead and redo cost. New "
                    "files mean real MDS traffic — CREATE/OPEN, a read-write "
                    "LAYOUTGET, then LAYOUTCOMMIT — but those are control messages "
                    "too small to draw at this scale; zero bulk bytes cross the "
                    "MDS, which is the claim the dark metadata block makes."
                ),
                expert=(
                    "Max dwell: checkpoint burst, terabytes across the striped "
                    "layout from all racks at once. Pure overhead; bounds redo on "
                    "failure. CREATE, rw LAYOUTGET and LAYOUTCOMMIT hit the MDS "
                    "but are not drawn: control only, zero bulk bytes."
                ),
            ),
            active_regions=["clients", "fabric"] + _servers() + MEDIA,
            throughput_gbps=36000,
            data_servers_streaming=4,
            layout_held=True,
            elapsed_seconds=90,
            cycle_cost=5,
        ),
        DataState(
            step=6,
            phase="tier",
            label="Cold data ages from file to object, in place",
            description=L(
                novice=(
                    "Between rounds of training, data the job has finished with "
                    "moves from the fast file tier to the cheaper object tier — and "
                    "because both live in this same rack, the move is internal. No "
                    "copying across a network to a separate archive system, and no "
                    "second naming scheme to reconcile. This is the argument for "
                    "putting several storage types in one footprint."
                ),
                plain=(
                    "Between epochs, data the job has finished with ages from the "
                    "file tier to ObjectScale's S3 object tier — and because both "
                    "engines live in this rack, the move is internal: no copy "
                    "across a network to a separate archive, no second namespace to "
                    "reconcile. This is the argument for consolidating storage "
                    "types in one footprint."
                ),
                standard=(
                    "Between epochs, data the job has finished with ages from "
                    "the file tier to ObjectScale's S3 object tier — and "
                    "because both engines live in this rack, the move is "
                    "internal: no copy across a network to a separate archive "
                    "system, no second namespace to reconcile. This is the "
                    "argument for consolidating storage types in one "
                    "footprint. The corpus that arrives as objects, gets "
                    "prepared as files, and is read in parallel never has to "
                    "leave the building to change its clothes."
                ),
                technical=(
                    "Inter-epoch tiering from the file tier to the S3 object tier, "
                    "internal to the rack because both engines are co-resident: no "
                    "cross-network archive copy, no second namespace. The "
                    "consolidation argument made concrete — the key does not change "
                    "and no reconciliation is required."
                ),
                expert=(
                    "File → object tiering, rack-internal. No cross-network copy, "
                    "no second namespace, key unchanged."
                ),
            ),
            active_regions=(
                ["protocol-object", "protocol-file"] + _servers() + MEDIA
            ),
            throughput_gbps=8000,
            data_servers_streaming=4,
            layout_held=True,
            elapsed_seconds=150,
            cycle_cost=2,
        ),
        DataState(
            step=7,
            phase="steady",
            label="The training loop runs: read, train, checkpoint, repeat",
            description=L(
                novice=(
                    "Steady state, and the shape of the next several weeks: stream "
                    "a batch in parallel, compute, save state, repeat, with cold "
                    "data moving to cheaper storage underneath. The storage rack "
                    "has become invisible in the good way — the processors never "
                    "wait, which is the only review a system like this ever gets."
                ),
                plain=(
                    "Steady state, and the shape of the next several weeks: stream "
                    "a batch in parallel, compute, checkpoint, repeat, with cold "
                    "data tiering underneath. The storage rack has become invisible "
                    "in the good way — the GPUs never wait, which is the only "
                    "review an AI data platform ever gets. Read this beside the "
                    "XE9712 and SN6000 twins for the whole factory."
                ),
                standard=(
                    "Steady state, and the shape of the next several weeks: "
                    "stream a batch in parallel, compute, checkpoint, repeat, "
                    "with cold data tiering underneath. The storage rack has "
                    "become invisible in the good way — the GPUs never wait, "
                    "which is the only review an AI data platform ever gets. "
                    "Run this twin beside the XE9712 and SN6000 twins for the "
                    "whole factory: this is where the bytes live, the fabric "
                    "carries them, and the racks burn them into weights."
                ),
                technical=(
                    "Steady state: parallel stream, compute, checkpoint, repeat, "
                    "with tiering underneath. Success condition is that the GPUs "
                    "never stall on I/O — the only metric an AI data platform is "
                    "judged on. This is the data pillar of the repo's four AI-factory "
                    "twins, beside XE9712 (compute), IR7000 (cooling) and SN6000 "
                    "(fabric)."
                ),
                expert=(
                    "Steady: stream, compute, checkpoint, tier. Success = GPUs "
                    "never stall on I/O. Data pillar of the AI-factory four "
                    "(compute, cooling, fabric, data)."
                ),
            ),
            active_regions=(
                ["clients", "fabric", "protocol-file", "protocol-object", "mgmt"]
                + _servers() + MEDIA
            ),
            throughput_gbps=48000,
            data_servers_streaming=4,
            layout_held=True,
            elapsed_seconds=300,
        ),
    ]
