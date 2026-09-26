"""The narrated tour of the Pro Max 16 Plus inference path — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
start from the closed laptop, peel it into three rooms (the host, the PCIe
strip, the inference card), pin the inference trace at the moments that carry
the story, and narrate each one. The frontend player owns the clock; nothing
here knows about time, IO or the web (AST-checked in ``tests/test_tour.py``,
the same rule as ``engine.py``).

The signature beat is ``weights-cross-once``: the 61 GB model crosses the PCIe
boundary during the load phase and during no other phase, which is
``tests/test_engine.py::test_weights_cross_the_link_exactly_once``. Every
claim the scripts make is one the engine and the anatomy already make — the
trace index named in each beat is the step whose description says the same
thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``DeviceAnatomy`` is unchanged:

    0  what the laptop is from the outside: its cooling, its power, its software
    1  the three rooms inside: host side, PCIe strip, card side
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
from .models import DeviceAnatomy

#: The step the tests pin: the twin's one idea lives here.
SIGNATURE_STEP_ID = "weights-cross-once"

_OUTSIDE = 0
_ROOMS = 1

#: Kinds a person meets without opening the machine: the fans they hear, the
#: adapter they plug in, the software they install.
_OUTSIDE_KINDS = {"thermal", "power", "runtime"}


def layer_map(anatomy: DeviceAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    return {
        r.id: _OUTSIDE if r.kind in _OUTSIDE_KINDS else _ROOMS
        for r in anatomy.regions
    }


# No tour photo. The only local image, promax-npu.svg, is this project's own
# schematic, and the player offers a step photo behind a "Show the real
# product" button, so attaching it would label a drawing as the product.


def build_tour(anatomy: DeviceAnatomy) -> Tour:
    """The Pro Max 16 Plus tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 2.0):
        return camera_around(anatomy, ids, pad=pad)

    card = ["npu-1", "npu-2", "aimem"]

    steps = [
        TourStep(
            id="laptop-exterior",
            title="A laptop with a model on its drive",
            script=L(
                novice=(
                    "This is a Dell Pro Max 16 Plus, a 16-inch laptop built for "
                    "heavy professional work. From the outside it looks like any "
                    "other: fans you can hear, a power adapter you plug in, and "
                    "software you install. It is switched off. Somewhere on its "
                    "drive sits one very large file, 61 gigabytes, which holds an "
                    "artificial-intelligence language model with 109 billion "
                    "parameters, the numbers the model learned in training. Models "
                    "that size normally live in a datacenter, behind a website. "
                    "This tour follows how that file ends up running inside the "
                    "laptop, with no server anywhere."
                ),
                standard=(
                    "This is a Dell Pro Max 16 Plus, a 16-inch mobile workstation, "
                    "switched off. From outside, all you meet is its cooling, its "
                    "adapter and battery, and its software toolchain (a laptop's "
                    "power path is the Alienware twin's subject). On its NVMe SSD, "
                    "the solid-state drive, sits a 61 GB file: a "
                    "109-billion-parameter language model, "
                    "already compiled for the inference card inside. The tour "
                    "follows that file from the left of this map to the right, "
                    "and shows why it only makes the trip once."
                ),
                expert=(
                    "Pro Max 16 Plus, powered down. 61 GB compiled container for a "
                    "109B-parameter model at rest on NVMe. Subject: its one-way "
                    "trip across PCIe."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["thermal", "power", "runtime"],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="three-rooms",
            title=L(standard="Three rooms and one narrow door", expert="Host, link, card"),
            script=L(
                novice=(
                    "With the lid off, the machine splits into three rooms. On the "
                    "left is the ordinary laptop: the main processor, its working "
                    "memory, and the SSD, the solid-state drive where files are "
                    "kept. On the right is an extra card built only for running AI "
                    "models. It carries two NPUs, short for Neural Processing "
                    "Units, chips designed to run a trained model, and 64 "
                    "gigabytes of memory that belongs to the card alone. Between "
                    "the rooms is one narrow strip, the PCIe connection (short for "
                    "Peripheral Component Interconnect Express), the only door "
                    "between them. The model file on the drive was translated for "
                    "this exact card on another machine, before the story "
                    "starts. Underneath the picture you will see that "
                    "translation as a step, called \"Translated ahead of time\". "
                    "It is listed here because it explains what happens next. "
                    "It is not happening now: it already happened, on a "
                    "different machine."
                ),
                standard=(
                    "Peeled open, the map is three rooms. Left is the host: CPU, "
                    "DDR5 system memory, and the NVMe SSD holding the model "
                    "library. Right is the Qualcomm AI 100 PC Inference Card: two "
                    "AI-100 NPUs (Neural Processing Units) and 64 GB of dedicated "
                    "AI memory. Between them is one narrow PCIe strip (PCI "
                    "Express, the card's only link to the host), drawn narrow "
                    "on purpose. The file on the SSD is a hardware-specific "
                    "container, compiled ahead of time from ONNX, an open "
                    "interchange format for neural networks, so nothing is "
                    "decided on the fly later. The trace step pinned under "
                    "this beat is that compile. It ran earlier, on a build "
                    "machine, and sits in the sequence because it produced "
                    "the container."
                ),
                expert=(
                    "Three zones: host (CPU, DDR5, NVMe), PCIe boundary, card "
                    "(2 × AI-100, 64 GB). Model is an AOT-compiled container from "
                    "ONNX, partitioned across 32 cores; the pinned trace step is "
                    "that offline compile."
                ),
            ),
            camera=frame("cpu", "ssd", "pcie", "npu-1", "npu-2", "aimem"),
            region_ids=["cpu", "dram", "ssd", "pcie", "npu-1", "npu-2", "aimem"],
            layer_reveal=_ROOMS,
            trace_cursor=1,
            duration_ms=30_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="The weights cross the strip once",
            script=L(
                novice=(
                    "This is the most important moment in the tour. The model is "
                    "loaded: all 61 gigabytes of its weights, the learned numbers, "
                    "stream from the drive, through the laptop, across the narrow "
                    "strip, and into the card's own memory. The link counter "
                    "reads 52 gigabits per second, an illustrative figure, and "
                    "this is the longest stage of the whole story. People "
                    "often worry that the connection to an add-in card "
                    "will be a bottleneck, because work would have to cross it "
                    "over and over. Here the work never crosses. The model "
                    "crosses, once, and you pay that cost once per model, not "
                    "once per question. Watch the link counter: this is the only "
                    "step where it is above zero."
                ),
                standard=(
                    "The model loads. Sixty-one gigabytes of weights stream "
                    "from the SSD, through the host CPU and memory, across PCIe "
                    "and into the card's 64 GB of AI memory. The link reads "
                    "52 Gb/s (illustrative), and this is the longest stage in "
                    "the trace. The usual objection to discrete accelerators is "
                    "that the bus becomes the bottleneck, which assumes work "
                    "crosses it continuously. Here what crosses is the model, "
                    "once per model rather than per prompt. The link counter is "
                    "nonzero in this phase and in no other."
                ),
                expert=(
                    "Load: 61 GB NVMe → host → PCIe → card memory, link at "
                    "~52 Gb/s, then never again. Longest stage; cost per "
                    "model, not per prompt or token."
                ),
            ),
            camera=frame("ssd", "cpu", "dram", "pcie", "aimem"),
            region_ids=["ssd", "cpu", "dram", "pcie", "aimem"],
            layer_reveal=_ROOMS,
            trace_cursor=2,
            duration_ms=40_000,
        ),
        TourStep(
            id="pinned-in-64gb",
            title=L(standard="Sixty-one of 64 gigabytes, pinned", expert="61 of 64 GB, pinned"),
            script=L(
                novice=(
                    "The model has arrived, and the link goes quiet for good. "
                    "The 61 gigabytes sit in the card's 64 gigabytes of memory, "
                    "which leaves a little room for the model's running notes on "
                    "the conversation, called the KV cache (key-value cache). "
                    "Nothing is ever pushed out to make room and nothing is "
                    "fetched back later, because the whole model fits. That is "
                    "why no word ever waits for part of the model to be fetched; "
                    "the only slow drift comes from the notes growing as the "
                    "conversation gets longer. The spare room, about 3 "
                    "gigabytes, limits how long a conversation can get: past "
                    "it, a request would be refused or cut short rather than "
                    "slowed down (illustrative; the trace does not model it). "
                    "The model only fits because each learned number is "
                    "squeezed into about a quarter of its usual space while it "
                    "is stored, and unpacked when it is used. Memory size, not raw speed, decides "
                    "which models this machine can run."
                ),
                standard=(
                    "Resident. The link counter drops to zero and stays there. "
                    "Sixty-one gigabytes of weights occupy 64 GB of memory that "
                    "belongs to the card alone, with about 3 GB of headroom for "
                    "the KV cache, the running record of the conversation. "
                    "Nothing is evicted and nothing is paged back in, so no "
                    "token ever waits on a page-in; the only drift is the KV "
                    "cache growing with context. That headroom caps context "
                    "length and concurrent sessions: past it, a request is "
                    "refused or truncated rather than paged (illustrative; the "
                    "trace does not model it). The fit depends on storing weights at "
                    "roughly four bits (MXINT4, the format Dell's brief names) "
                    "while computing at FP16 (16-bit floating "
                    "point): capacity, not TOPS, decides what runs."
                ),
                expert=(
                    "Resident: 61 of 64 GB, no eviction or paging. ~3 GB KV "
                    "headroom caps context and concurrency; overflow is refused, "
                    "not paged (illustrative). MXINT4 weight storage, FP16 compute. Capacity gates "
                    "model choice."
                ),
            ),
            camera=frame(*card),
            region_ids=card,
            layer_reveal=_ROOMS,
            trace_cursor=3,
            duration_ms=28_000,
        ),
        TourStep(
            id="prefill",
            title="Prefill reads the prompt at once",
            script=L(
                novice=(
                    "Now a question arrives. The laptop's main processor turns "
                    "the text into tokens, small numbered pieces of words, and "
                    "sends them across the strip. That is only a few kilobytes, "
                    "so small that the link counter still reads zero. The card "
                    "then reads the whole prompt in one go, called prefill. Every "
                    "piece can be worked on at the same time, so this is the "
                    "moment the card's raw arithmetic speed actually matters (the "
                    "maker rates it at about 450 TOPS, trillion simple "
                    "operations per second), and power use peaks here."
                ),
                standard=(
                    "A prompt arrives. The host tokenizes it and sends a few "
                    "kilobytes across the link, which is why the bandwidth "
                    "counter still honestly reads zero. The card then runs "
                    "prefill: every input token is processed in parallel, so "
                    "this is the compute-bound half of inference and arithmetic "
                    "rate is briefly what matters. The vendor rates the card at "
                    "~450 TOPS (trillion operations per second) for 8-bit "
                    "integers; at the FP16 this model computes in, throughput "
                    "is lower. Power peaks on this step."
                ),
                expert=(
                    "Prefill: host tokenizes, KB-scale transfer, link reads 0. "
                    "Parallel over the prompt, compute-bound, all 32 cores "
                    "saturated (vendor rating ~450 TOPS INT8; FP16 throughput "
                    "is lower). Power peak."
                ),
            ),
            camera=frame("cpu", "pcie", "npu-1", "npu-2", "aimem"),
            region_ids=["cpu", "pcie", "npu-1", "npu-2", "aimem"],
            layer_reveal=_ROOMS,
            trace_cursor=4,
            duration_ms=26_000,
        ),
        TourStep(
            id="decode",
            title="Decode is bounded by memory",
            script=L(
                novice=(
                    "Now the answer is written one token at a time, called "
                    "decode. For each new token the card has to read a large "
                    "share of the model's learned numbers out of its memory "
                    "again. A model this big is usually a mixture of experts, "
                    "many smaller sub-networks of which only a few are used "
                    "per token, so not every number is read every time, but "
                    "billions still are. The limit is no longer how fast the "
                    "chips can calculate but how fast they can read their own "
                    "memory. The GPU twin in this collection calls this being "
                    "memory-bound. The rate here, around 22 tokens per "
                    "second, is an illustrative number."
                ),
                standard=(
                    "Generation begins, one token at a time, and the bottleneck "
                    "moves. Each new token needs another pass over the weights "
                    "it uses (for a mixture-of-experts model, the experts it is "
                    "routed to rather than all 109 billion parameters), and "
                    "each weight read feeds only that one token's arithmetic. "
                    "So decode is bounded by how fast weights come out of the "
                    "on-card memory, not by the 450 TOPS beside it: the "
                    "memory-bound regime of the GPU twin's roofline. The "
                    "22 tokens per second shown is illustrative."
                ),
                expert=(
                    "Decode: one pass over the active weights per token, "
                    "MoE-routed; bandwidth-bound on card memory, not TOPS. The "
                    "GPU twin's memory-bound roofline regime. ~22 tok/s, "
                    "illustrative."
                ),
            ),
            camera=frame(*card),
            region_ids=card,
            layer_reveal=_ROOMS,
            trace_cursor=5,
            duration_ms=28_000,
        ),
        TourStep(
            id="host-goes-idle",
            title=L(standard="The left side goes dark", expert="Host idle, card steady"),
            script=L(
                novice=(
                    "Look at the left side of the map. The main processor, its "
                    "memory and the drive are all dark, and they stay dark for "
                    "as long as the model is writing. The whole job is happening "
                    "on the card, so the laptop stays responsive for ordinary "
                    "work. The finished tokens do come back across the strip to "
                    "be turned into text, but that is a few bytes a second, far "
                    "too little to show on the link counter or to keep the main "
                    "processor busy. Meanwhile the card's power draw holds "
                    "steady, within a few percent, because it uses little "
                    "enough power that the laptop's cooling can keep up for as "
                    "long as it takes. A hungrier graphics chip in the same "
                    "body would have to slow down once it heated up. Several "
                    "minutes in, the speed you can keep up matters more than "
                    "the top speed."
                ),
                standard=(
                    "Minutes into a long generation, the host side is dark: no "
                    "host region is lit on any generating step. Generated tokens "
                    "do return to the host to be turned back into text, but "
                    "that is bytes per second, far below the link counter's "
                    "resolution, and the host's share of the work is trivial. "
                    "The machine stays responsive for other work. The card's "
                    "wattage and token rate also hold within a few percent, "
                    "because its draw sits inside what the chassis can cool "
                    "indefinitely; a higher-power laptop GPU in the same "
                    "chassis would burst and then throttle. Sustained output "
                    "is set by how much heat you can remove, and for "
                    "interactive use the sustained rate is what counts."
                ),
                expert=(
                    "Sustained: host, DRAM, SSD idle on every generating step; "
                    "returned tokens are bytes per second, below counter "
                    "resolution. Card draw inside the chassis budget, so rate "
                    "and wattage hold within a few percent. Sustained rate "
                    "matters more than peak."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["npu-1", "npu-2", "aimem", "thermal", "power"],
            layer_reveal=_ROOMS,
            trace_cursor=6,
            duration_ms=28_000,
        ),
        TourStep(
            id="pull-the-cable",
            title="Unplug the network and nothing happens",
            script=L(
                novice=(
                    "The lid goes back on, and we pull out the network cable. "
                    "Nothing changes. The model was never being fetched from "
                    "anywhere, and no question was ever sent to a server to be "
                    "answered. After loading, everything happened inside this "
                    "laptop. That is the reason to own one: a doctor, a lawyer "
                    "or an engineer can give the model material that must not "
                    "leave the building. For models too big even for this "
                    "machine, the datacenter twins, like the XE9712 rack, show "
                    "the other answer."
                ),
                standard=(
                    "Closed up again, and the network is pulled. No counter "
                    "moves. The model was never fetched from anywhere and no "
                    "token was ever sent to a server; after load, nothing in "
                    "the trace depended on anything outside the chassis. That "
                    "non-event is the commercial case: material that cannot "
                    "leave the building can go into a 109-billion-parameter "
                    "model. The datacenter twins, such as the XE9712 rack, cover "
                    "models too large to fit on one card."
                ),
                expert=(
                    "Offline: no counter moves. Nothing after load depends on "
                    "anything outside the chassis. Data residency is the product."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=card,
            layer_reveal=_OUTSIDE,
            trace_cursor=7,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="promaxplus-tour",
        title="Inside a Pro Max 16 Plus, as a model moves in",
        intro=L(
            novice=(
                "A guided walk through the laptop as it loads a very large AI "
                "model and starts answering, narrated beat by beat. Sit back and "
                "watch, or pause and click anything to look closer; the tour "
                "waits for you."
            ),
            standard=(
                "A narrated walk from the model on disk to offline generation. "
                "Watch it play, or pause and explore; Resume tour brings the "
                "camera back."
            ),
            expert="Narrated load-to-offline walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: DeviceAnatomy) -> TourResponse:
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
