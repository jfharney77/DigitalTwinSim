"""Pure inference engine for the Dell Pro Max 16 Plus discrete-NPU twin.

``simulate()`` returns the deterministic trace of a large language model's
life on this machine: compiled ahead of time, loaded across the PCIe
boundary once, and then generating tokens with the bus idle and the network
unplugged. Same purity rule as every other twin in this repo: no FastAPI, no
IO, no timers — the frontend owns the playback clock, and each
``InferenceState`` is plain data the renderer consumes. ``cycle_cost`` marks
the long stages (moving 61 GB of weights) so the UI dwells on them.

The idea this twin exists to teach: **the weights never move.**

Every other accelerator twin in this repo is a story about transfer. The
XE9712 fuses 72 GPUs precisely so gradients can cross between them at
1.8 TB/s. The SN6000 exists to carry traffic between racks without dropping
it. The Exascale rack answers a read from four data servers at once. All of
them are fighting the same fight: the data is somewhere else, and getting it
here is the problem.

A discrete NPU with its own memory declines the fight. The model is
compiled offline into a container built for this specific silicon, streamed
across PCIe exactly once, and from then on it is simply *there* — 61 GB
resident in 64 GB of memory that belongs to the card and to nothing else.
Generation reads it in place. The bus goes quiet. The host CPU has nothing
to do. And because nothing is being fetched from anywhere, the network can
be disconnected without changing a single number in the trace, which is the
last step here and the entire commercial argument: the data never leaves
the machine, because it never had to.

The counters that carry this are ``link_gbps`` — nonzero during exactly one
phase — and ``weights_resident_gb``, which is monotonic and never partially
evicted. ``tests/test_engine.py`` asserts both.

Capacities, rates, and timings are illustrative but plausible for an AI 100
PC Inference Card; favor a correct mental model over measured numbers
(project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import InferenceState

# A 109-billion-parameter model with weights quantized to roughly four bits
# per parameter (Dell's brief: "up to 120B (with MXINT4)"). 61 GB is this
# twin's arithmetic, not a published file size. This is the number that
# decides whether the machine can run
# the model at all, and it is a memory-capacity number, not a speed one.
MODEL_GB = 61

# Phases in which tokens are actually being generated. During these, the
# entire computation lives on the card: no host region lights up, and the
# PCIe link carries nothing but the trickle of output text.
GENERATION_PHASES = {"decode", "sustained", "offline"}

# Region kinds on the host side of the PCIe boundary. Absent from the active
# set during generation — see test_host_is_idle_during_generation.
HOST_KINDS = {"host", "memory", "storage"}

_CARD = ["npu-1", "npu-2", "aimem"]


def simulate() -> list[InferenceState]:
    """The life of a model on this machine, from file on disk to generating
    text with the network unplugged."""
    return [
        InferenceState(
            step=0,
            phase="off",
            label="Powered down — the model is a file on disk",
            description=L(
                novice=(
                    "A 16-inch laptop, closed and switched off. Somewhere on its "
                    "internal drive is a 61-gigabyte file: a language model with "
                    "109 billion adjustable numbers in it, already converted into "
                    "the exact form the accelerator chip inside wants. There is "
                    "nothing unusual about the file itself. What is unusual is "
                    "where it is — on a laptop, rather than in a data centre behind "
                    "a website. Everything that follows is the story of how it gets "
                    "from the left-hand side of this picture to the right-hand "
                    "side, and why it only has to make that journey once."
                ),
                plain=(
                    "A 16-inch mobile workstation, closed. On its drive sits a 61 "
                    "GB file: a 109-billion-parameter language model, already "
                    "compiled for the inference card inside. Nothing about the file "
                    "is remarkable except its location — on a laptop, not in a "
                    "datacenter and not behind an API. What follows is how it gets "
                    "from the left of this diagram to the right, and why it only "
                    "makes that trip once."
                ),
                standard=(
                    "A 16-inch mobile workstation, closed. Somewhere on its NVMe "
                    "SSD sits a 61 GB file: a 109-billion-parameter language "
                    "model, already compiled for the inference card inside. "
                    "Nothing about that file is remarkable except where it is — "
                    "on a laptop, not in a datacenter, and not behind an API. "
                    "Everything that follows is the story of how it gets from "
                    "the left-hand side of this diagram to the right-hand side, "
                    "and why it only has to make that trip once."
                ),
                technical=(
                    "A 16-inch mobile workstation at rest. 61 GB on NVMe: a "
                    "109B-parameter model, precompiled for the on-board "
                    "accelerator. The only remarkable property is location — local, "
                    "not hosted. The rest of the trace is how it crosses the "
                    "boundary, and why exactly once."
                ),
                expert=(
                    "Cold. 61 GB precompiled container staged on NVMe; 109B "
                    "parameters, local rather than hosted."
                ),
            ),
            active_regions=[],
            weights_resident_gb=0,
            link_gbps=0,
            tokens_per_second=0,
            npu_watts=0,
            elapsed_seconds=0,
        ),
        InferenceState(
            step=1,
            phase="compile",
            label=L(
                novice="Translated ahead of time — the model is rewritten for this exact chip",
                standard="Ahead-of-time compile — a graph becomes a hardware container",
            ),
            description=L(
                novice=(
                    "This step already happened, on a different machine, possibly "
                    "weeks ago — but it belongs in the story because it explains "
                    "why everything later is so predictable. The trained model is "
                    "converted into a standard interchange format, then compiled "
                    "specifically for this chip: the work is divided across the "
                    "card's 32 processing cores, the numbers are compressed to take "
                    "up less space, and the order of operations is fixed in "
                    "advance. Compiling is slow and you do it once. The reward is "
                    "that nothing has to be figured out later while the model is "
                    "actually answering you — which is why the thousandth word "
                    "arrives just as quickly as the first."
                ),
                plain=(
                    "This step already happened, on a build machine, perhaps weeks "
                    "ago — but it explains everything predictable about what "
                    "follows. The model is exported to ONNX, an open format for "
                    "describing neural networks, and compiled into a container "
                    "built for this silicon: the graph partitioned across the "
                    "card's 32 AI cores, a compression level chosen per tensor, the "
                    "execution schedule fixed. Compilation is slow and happens "
                    "once. The payoff is that nothing is decided on the fly while "
                    "tokens are being generated, so the thousandth token takes as "
                    "long as the first."
                ),
                standard=(
                    "This step already happened, on a build machine, possibly "
                    "weeks ago — but it belongs in the story because it explains "
                    "everything predictable about what comes after. The trained "
                    "model is exported to ONNX, an open interchange format for "
                    "neural networks, and then compiled into a container built "
                    "for this exact silicon: the graph partitioned across the "
                    "card's 32 AI cores, a quantization chosen per tensor, the "
                    "execution schedule fixed. Compilation is slow and it is "
                    "done once. The payoff is that nothing is decided "
                    "dynamically while tokens are being generated later, which "
                    "is why the latency of the thousandth token looks like the "
                    "latency of the first."
                ),
                technical=(
                    "Already done, offline, on a build machine — but it belongs in "
                    "the trace because it explains the runtime's determinism. "
                    "Export to ONNX, then ahead-of-time compilation into a "
                    "hardware-specific container: graph partitioned across 32 AI "
                    "cores, per-tensor quantization selected, execution schedule "
                    "fixed. Slow, and paid once. Nothing is scheduled dynamically "
                    "during generation, hence flat per-token latency."
                ),
                expert=(
                    "Offline AOT compile: ONNX → hardware container. Graph "
                    "partitioned across 32 cores, per-tensor quantization, static "
                    "schedule. Paid once; the source of flat per-token latency."
                ),
            ),
            active_regions=["ssd", "runtime"],
            weights_resident_gb=0,
            link_gbps=0,
            tokens_per_second=0,
            npu_watts=0,
            elapsed_seconds=12,
            cycle_cost=2,
        ),
        InferenceState(
            step=2,
            phase="load",
            label=L(
                novice=(
                    "The model's 61 GB of learned numbers, called weights, cross "
                    "the connector, called PCIe — the only time they will"
                ),
                standard="61 GB of weights cross PCIe — the only time they will",
            ),
            description=L(
                novice=(
                    "The slow part, and the only stage where the time is spent simply "
                    "moving bytes. All 61 gigabytes of the "
                    "model's learned numbers, called weights, travel from the "
                    "drive, through the laptop's main circuitry, across the "
                    "connector (a link called PCIe), and into the accelerator's "
                    "own 64 gigabytes of memory. That takes about a minute — the slowest thing this "
                    "machine will do all day. It is worth being precise about why "
                    "nobody minds. You pay this cost once per model, not once per "
                    "question, per conversation, or per day. Load it in the morning "
                    "and you are done. The usual complaint about add-in accelerator "
                    "cards is that the connection becomes the bottleneck, but that "
                    "assumes work keeps crossing it. Here what crosses is the model "
                    "itself, one time."
                ),
                plain=(
                    "The long stage, and the only one where moving bytes sets the pace. "
                    "Sixty-one gigabytes stream from the SSD, through the host, "
                    "across the PCIe link, into the card's 64 GB of dedicated "
                    "memory. The link peaks at roughly 52 Gb/s (an illustrative "
                    "figure — around 6.5 GB/s, which is drive-read speed rather "
                    "than the limit of the link), and with reading and placing "
                    "the file the whole "
                    "stage takes about a minute, the slowest thing the machine "
                    "will do all day. Why that is "
                    "acceptable: the cost is paid per model, not per prompt, per "
                    "token, or per session. Load in the morning and the bill is "
                    "settled. The standard objection to discrete accelerators — "
                    "that the bus becomes the bottleneck — assumes work crosses it "
                    "continuously. Here what crosses is the model, once."
                ),
                standard=(
                    "The long stage, and the only one where moving bytes sets "
                    "the pace. Sixty-one gigabytes stream from the SSD, through "
                    "the host, across the PCIe link, and into the card's 64 GB "
                    "of dedicated AI memory. The link peaks at roughly 52 Gb/s "
                    "(illustrative) — about 6.5 GB/s, which is the shape of an "
                    "SSD read rather than a PCIe ceiling, so what is modelled "
                    "here is the drive feeding the link, not the link itself. "
                    "With reading the container and placing it "
                    "across the two NPUs' memory banks, the whole stage takes "
                    "on the order of a minute, and it is the single slowest "
                    "thing the machine will do all day. It is worth being precise "
                    "about why that is acceptable: this cost is paid per "
                    "model, not per prompt, per token, or per session. Load "
                    "the model in the morning and the bill is settled. The "
                    "conventional objection to discrete accelerators — that the "
                    "bus becomes the bottleneck — assumes work crosses it "
                    "continuously. Here what crosses is the model itself, once."
                ),
                technical=(
                    "The long stage, and the only one bounded by moving bytes. 61 GB from "
                    "NVMe through the host across PCIe into 64 GB of card-local "
                    "memory (2 × 32 GB), link peaking ~52 Gb/s (illustrative), "
                    "order of a minute end to end — the slowest operation in "
                    "the trace. Note the shape of that figure: ~6.5 GB/s is an "
                    "NVMe sequential read, not a PCIe ceiling, so what is "
                    "modelled here is the drive feeding the link rather than "
                    "the link itself. The cost amortizes per model rather than per "
                    "prompt, token, or session. The standard discrete-accelerator "
                    "objection assumes continuous transfer; what transfers here is "
                    "the model, once."
                ),
                expert=(
                    "61 GB NVMe → PCIe → card memory, ~52 Gb/s peak "
                    "(illustrative — ~6.5 GB/s, i.e. NVMe-shaped rather than "
                    "link-shaped: the modelled bound is the read, not the PCIe "
                    "width). The only phase bounded by moving bytes at all; "
                    "amortized per model, not per request. Defeats the usual "
                    "bus-bottleneck objection, which presumes continuous "
                    "transfer."
                ),
            ),
            active_regions=[
                "ssd", "cpu", "dram", "pcie", "runtime", "power", *_CARD,
            ],
            weights_resident_gb=MODEL_GB,
            link_gbps=52,
            tokens_per_second=0,
            npu_watts=34,
            elapsed_seconds=70,
            cycle_cost=6,
        ),
        InferenceState(
            step=3,
            phase="resident",
            label=L(
                novice="In place — the connector goes quiet for good",
                standard="Resident — the bus goes quiet for good",
            ),
            description=L(
                novice=(
                    "The model is in place and the traffic counter drops to zero, "
                    "where it stays for the rest of the story. Sixty-one gigabytes "
                    "now sit inside 64 gigabytes of memory that belongs to the "
                    "accelerator and nothing else, leaving a little room for the "
                    "running record of your conversation, which grows as you keep "
                    "talking. Nothing will be pushed out and nothing will be "
                    "fetched back in, because the whole model is present at once. "
                    "That absence of shuffling is what makes each word arrive at a "
                    "steady, predictable pace — and it is the difference between a "
                    "model that fits and one that almost fits, which in practice is "
                    "the difference between usable and not."
                ),
                plain=(
                    "The model is in place and the link counter drops to zero, "
                    "where it stays. Sixty-one gigabytes occupy 64 GB of memory "
                    "belonging to the card alone, leaving headroom for the KV cache "
                    "— the running record of the conversation, which grows as "
                    "context lengthens. Nothing is evicted and nothing is swapped "
                    "in: the whole model is present, so there are no layers to "
                    "page. That absence is what makes token latency predictable, "
                    "and it is the difference between 'this fits' and 'this almost "
                    "fits' — in practice, between usable and not."
                ),
                standard=(
                    "The model is in place and the link counter drops to zero, "
                    "where it stays for the rest of the trace. Sixty-one "
                    "gigabytes of weights occupy 64 GB of memory that belongs "
                    "to the card alone, leaving headroom for the KV cache — the "
                    "running record of the conversation so far, which grows as "
                    "context lengthens. Nothing will be evicted and nothing "
                    "will be swapped in: the whole model is present, so there "
                    "are no layers to page. That absence is what makes token "
                    "latency predictable, and it is the difference between "
                    "'this model fits' and 'this model almost fits', which in "
                    "practice is the difference between usable and not."
                ),
                technical=(
                    "Resident; link counter to zero for the remainder. 61 GB in 64 "
                    "GB of card-local memory, headroom left for a growing KV cache. "
                    "No eviction, no paging — the full parameter set is present, "
                    "which is what makes token latency predictable. The gap between "
                    "fits and almost-fits is the gap between usable and not."
                ),
                expert=(
                    "Resident: 61/64 GB, KV headroom remaining. No paging, so "
                    "latency is deterministic. Fits vs almost-fits is the usability "
                    "boundary."
                ),
            ),
            active_regions=[*_CARD, "power"],
            weights_resident_gb=MODEL_GB,
            link_gbps=0,
            tokens_per_second=0,
            npu_watts=18,
            elapsed_seconds=78,
        ),
        InferenceState(
            step=4,
            phase="prefill",
            label=L(
                novice="The question is read all at once, a stage called prefill",
                standard="Prefill — the prompt is read all at once",
            ),
            description=L(
                novice=(
                    "A question arrives and the accelerator reads all of it at "
                    "once. This first stage can work on every word of your input "
                    "simultaneously, so all the arithmetic units are busy together "
                    "and the chip's raw speed briefly becomes the thing that "
                    "matters. Power use peaks here. The laptop's main processor "
                    "contributes very little: it turns your text into numbers and "
                    "sends a few kilobytes across the connector. That is far too "
                    "little to register on the traffic counter, which counts in "
                    "whole gigabits per second, so it still reads zero, and at "
                    "the scale it measures that zero is accurate."
                ),
                plain=(
                    "A prompt arrives and the card processes all of it in parallel. "
                    "Prefill is the compute-bound half of inference: every input "
                    "token can be attended to at once, so the arithmetic units "
                    "saturate and the card's ~450 TOPS is briefly the number that "
                    "matters. Power peaks here. The host's contribution is turning "
                    "text into token ids and sending a few kilobytes across the "
                    "link — which is why the bandwidth counter still reads zero at "
                    "this resolution, and honestly so."
                ),
                standard=(
                    "A prompt arrives and the card processes all of it in "
                    "parallel. Prefill is the compute-bound half of language "
                    "model inference: every token of the input can be attended "
                    "to simultaneously, so the arithmetic units are saturated "
                    "and the card's ~450 TOPS is briefly the number that "
                    "matters. Power peaks here. The host's contribution to this "
                    "step is turning text into token ids and sending a few "
                    "kilobytes across the link — which is why the bandwidth "
                    "counter still reads zero at this resolution, and honestly "
                    "so."
                ),
                technical=(
                    "Prefill: the whole prompt processed in parallel, the "
                    "compute-bound half of inference. All 32 cores saturate, so "
                    "arithmetic rate is briefly the binding limit (the vendor "
                    "rates the card at ~450 TOPS INT8; FP16 throughput is "
                    "lower); power peaks. Host "
                    "contribution is tokenization plus a few kilobytes over the "
                    "link, which is why the bandwidth counter still reads zero at "
                    "this resolution."
                ),
                expert=(
                    "Prefill — compute-bound, all 32 cores saturated (vendor "
                    "rating ~450 TOPS INT8; FP16 throughput is lower), power "
                    "peak. Host does tokenization; link traffic negligible."
                ),
            ),
            active_regions=["cpu", "pcie", *_CARD, "thermal", "power"],
            weights_resident_gb=MODEL_GB,
            link_gbps=0,
            tokens_per_second=0,
            npu_watts=71,
            elapsed_seconds=80,
            cycle_cost=2,
        ),
        InferenceState(
            step=5,
            phase="decode",
            label=L(
                novice=(
                    "The answer is written one small piece (a token) at a time, "
                    "a stage called decode, limited by memory speed"
                ),
                standard="Decode — one token at a time, bounded by memory",
            ),
            description=L(
                novice=(
                    "Now it starts producing words, and the limiting factor changes "
                    "completely. The answer is built from tokens, small pieces of "
                    "words, one at a time, and making each one requires reading "
                    "a large part of the model's learned numbers again. A model "
                    "this big is a mixture of experts, many smaller sub-networks "
                    "of which only a few are used per token, so not every number "
                    "is read every time, but billions still are. So what matters is no longer how fast "
                    "the chip can calculate but how fast it can pull data out of "
                    "the memory sitting next to it. Notice what is not happening: "
                    "the laptop's main processor is idle, the drive is idle, and "
                    "the connector is carrying only the trickle of text coming back "
                    "to you. The entire computation is happening on one side of the "
                    "line."
                ),
                plain=(
                    "Generation begins and the bottleneck moves. Producing each "
                    "token requires reading a large part of the model again: in a "
                    "mixture-of-experts model like this one, the experts that "
                    "token is sent to rather than all 109 billion parameters. "
                    "So decode is bounded not by the card's arithmetic rate but by how fast "
                    "weights can be pulled out of the memory beside it. This is the "
                    "memory-bound regime this repo's GPU twin names in its roofline "
                    "analysis, reached from the other direction. Note what is not "
                    "happening — the host CPU is idle, the SSD is idle, and the "
                    "link carries only output text."
                ),
                standard=(
                    "Generation begins, and the bottleneck moves. Producing "
                    "each new token requires another pass over the weights it "
                    "uses (in a mixture-of-experts model like this one, the "
                    "experts the token is routed to rather than all 109 billion "
                    "parameters), so decode is bounded not by the card's 450 TOPS but "
                    "by how fast weights can be pulled out of the on-card "
                    "memory beside it. This is the memory-bound regime this "
                    "repo's GPU twin's roofline analysis names, arrived at from "
                    "the opposite direction: there, a matmul becomes "
                    "memory-bound when the tile is too small to reuse what it "
                    "loaded; here, every token reuses nothing at all. Note what "
                    "is not happening — the host CPU is idle, the SSD is "
                    "idle, and the PCIe link is carrying a trickle of output "
                    "text. The whole computation is on one side of the line."
                ),
                technical=(
                    "Decode: the bottleneck moves from arithmetic to memory "
                    "bandwidth, since each token reads its active expert set "
                    "(roughly a sixth of the weights for this mixture-of-experts "
                    "model, illustrative) and reuses none of it for the next. "
                    "This is the memory-bound regime the GPU twin's "
                    "roofline names, arrived at from the opposite side — there a "
                    "tile is too small to reuse what it loaded, here each token "
                    "reuses nothing. Host, storage, and link all idle."
                ),
                expert=(
                    "Decode — memory-bandwidth-bound; per-token working set is the "
                    "active expert set (~1/6 of the weights, illustrative), zero "
                    "reuse across tokens. Same memory-bound regime as the GPU "
                    "twin: there a tile is too small to amortize its load, here "
                    "a token amortizes nothing. Host/storage/link idle."
                ),
            ),
            active_regions=[*_CARD, "thermal", "power"],
            weights_resident_gb=MODEL_GB,
            link_gbps=0,
            tokens_per_second=22,
            npu_watts=68,
            elapsed_seconds=86,
            cycle_cost=2,
        ),
        InferenceState(
            step=6,
            phase="sustained",
            label=L(
                novice="Minutes later — steady power, no slowing down",
                standard="Sustained — flat wattage, no throttle",
            ),
            description=L(
                novice=(
                    "Several minutes into a long answer, and the interesting "
                    "measurement is the one that has barely changed. A laptop's "
                    "graphics chip pressed into this kind of work can post an "
                    "impressive number for thirty seconds and then slow down, "
                    "because it is allowed to draw more power than the laptop's "
                    "body can get rid of as heat for long. This card draws about "
                    "70 watts here (an illustrative figure), which the cooling "
                    "can carry away for as long as it takes. So the power and the "
                    "rate of words stay within a few percent of where they "
                    "started. For anything you actually sit "
                    "and use, the top speed barely matters and the speed you can "
                    "hold for ten minutes matters enormously."
                ),
                plain=(
                    "Several minutes into a long generation, and the interesting "
                    "measurement is the one that barely changes. A laptop GPU "
                    "pressed into inference can post a high number for thirty "
                    "seconds and then throttle, because its power limit sits above "
                    "what the chassis can shed as heat indefinitely. This card's "
                    "draw, about 70 W here (illustrative), sits inside that "
                    "budget, so the wattage and the token rate hold within a few "
                    "percent. For interactive use, "
                    "peak throughput is close to irrelevant and the rate you can "
                    "hold for ten minutes is everything."
                ),
                standard=(
                    "Several minutes into a long generation, and the "
                    "interesting measurement is the one that barely changes. A "
                    "laptop GPU pressed into inference service can post a high "
                    "number for thirty seconds and then throttle, because its "
                    "power limit sits above what the chassis can dissipate "
                    "indefinitely. This card's draw, about 70 W here "
                    "(illustrative), sits inside the chassis budget, so the "
                    "wattage and the token rate hold within a few percent of "
                    "the first decode step. For interactive use, peak "
                    "throughput is close to irrelevant and the rate you can "
                    "hold for ten minutes is everything. Sustained output is "
                    "set by how much heat you can remove, which is the same "
                    "argument, at a very different scale, that forces liquid "
                    "cooling on this repo's IR7000 racks."
                ),
                technical=(
                    "Sustained generation, and the measurement of interest is the "
                    "near-absence of decline: wattage and token rate stay within "
                    "a few percent of first decode. The card's draw sits inside "
                    "the chassis thermal budget, so nothing forces a throttle; a "
                    "higher-power GPU in the same chassis is budget- and "
                    "skin-limited instead. For interactive workloads, peak is "
                    "near-irrelevant against held rate. Sustained output is set "
                    "by heat removal, the argument that forces liquid cooling at "
                    "rack scale in the IR7000 twin."
                ),
                expert=(
                    "Sustained: rate and wattage within a few percent of first "
                    "decode. Card draw sits inside the chassis budget; a "
                    "higher-TGP GPU in the same chassis is budget- and "
                    "skin-limited. Held rate dominates peak for interactive use."
                ),
            ),
            active_regions=[*_CARD, "thermal", "power"],
            weights_resident_gb=MODEL_GB,
            link_gbps=0,
            tokens_per_second=21,
            npu_watts=67,
            elapsed_seconds=180,
            cycle_cost=3,
        ),
        InferenceState(
            step=7,
            phase="offline",
            label="Network disconnected — nothing changes",
            description=L(
                novice=(
                    "The last step is a non-event, and that is exactly the point. "
                    "Disconnect the network and nothing changes. The model was "
                    "never being fetched from anywhere, no word was ever sent to a "
                    "company's server to be completed, and nothing after the "
                    "loading step depended on anything outside this laptop. What "
                    "follows from that is the whole reason to buy the machine: a "
                    "doctor, a lawyer, or an engineer can put material into a very "
                    "capable model that could not lawfully or sensibly be pasted "
                    "into an online one, because the material does not go anywhere."
                ),
                plain=(
                    "The last step is a non-event, which is the point. Pull the "
                    "network: no counter moves. The model was never being fetched "
                    "from anywhere, no token was ever sent to a server to be "
                    "completed, and nothing after load depended on anything outside "
                    "the chassis. That is the commercial case — a clinician, a "
                    "lawyer, or an engineer can put material into a "
                    "109-billion-parameter model that could not lawfully or "
                    "sensibly be pasted into a hosted one, because the data does "
                    "not leave."
                ),
                standard=(
                    "The last step is a non-event, and that is the point. Pull "
                    "the network: no counter moves. The model was never being "
                    "fetched from anywhere, no token was ever sent to a server "
                    "to be completed, and nothing in this trace after the load "
                    "phase depended on anything outside the chassis. What "
                    "follows from that is the whole commercial case for the "
                    "machine — a clinician, a lawyer, or an engineer can put "
                    "material into a 109-billion-parameter model that could not "
                    "lawfully or sensibly be pasted into a hosted one, because "
                    "the data does not leave. This repo's other twins answer "
                    "the same question at datacenter scale, where the model is "
                    "too large to do anything else. This one is the answer for "
                    "when it isn't."
                ),
                technical=(
                    "A deliberate non-event: disconnect the network and no counter "
                    "moves. Nothing after load depended on anything off-chassis. "
                    "That is the commercial argument — regulated material can go "
                    "into a frontier-class model because it never leaves the "
                    "device, which reframes the approval question as endpoint "
                    "security rather than vendor data handling."
                ),
                expert=(
                    "Network disconnected; no counter moves. Nothing post-load is "
                    "off-chassis. Data residency by construction — the approval "
                    "question becomes endpoint security, not vendor handling."
                ),
            ),
            active_regions=[*_CARD, "thermal", "power"],
            weights_resident_gb=MODEL_GB,
            link_gbps=0,
            tokens_per_second=21,
            npu_watts=67,
            elapsed_seconds=240,
        ),
    ]
