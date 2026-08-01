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
# per parameter. This is the number that decides whether the machine can run
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
            label="Ahead-of-time compile — a graph becomes a hardware container",
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
            label="61 GB of weights cross PCIe — the only time they will",
            description=L(
                novice=(
                    "The slow part, and the only moment the connection between the "
                    "two halves of the machine matters. Sixty-one gigabytes travel "
                    "from the drive, through the laptop's main circuitry, across "
                    "the connector, and into the accelerator's own 64 gigabytes of "
                    "memory. That takes about a minute — the slowest thing this "
                    "machine will do all day. It is worth being precise about why "
                    "nobody minds. You pay this cost once per *model*, not once per "
                    "question, per conversation, or per day. Load it in the morning "
                    "and you are done. The usual complaint about add-in accelerator "
                    "cards is that the connection becomes the bottleneck, but that "
                    "assumes work keeps crossing it. Here what crosses is the model "
                    "itself, one time."
                ),
                plain=(
                    "The long stage, and the only moment the interconnect matters. "
                    "Sixty-one gigabytes stream from the SSD, through the host, "
                    "across the PCIe link, into the card's 64 GB of dedicated "
                    "memory. At roughly 52 Gb/s that takes about a minute, and it "
                    "is the slowest thing the machine will do all day. Why that is "
                    "acceptable: the cost is paid per *model*, not per prompt, per "
                    "token, or per session. Load in the morning and the bill is "
                    "settled. The standard objection to discrete accelerators — "
                    "that the bus becomes the bottleneck — assumes work crosses it "
                    "continuously. Here what crosses is the model, once."
                ),
                standard=(
                    "The long stage, and the only moment the interconnect "
                    "matters. Sixty-one gigabytes stream from the SSD, through "
                    "the host, across the PCIe link, and into the card's 64 GB "
                    "of dedicated AI memory. At roughly 52 Gb/s this takes on "
                    "the order of a minute, and it is the single slowest thing "
                    "the machine will do all day. It is worth being precise "
                    "about why that is acceptable: this cost is paid per "
                    "*model*, not per prompt, per token, or per session. Load "
                    "the model in the morning and the bill is settled. The "
                    "conventional objection to discrete accelerators — that the "
                    "bus becomes the bottleneck — assumes work crosses it "
                    "continuously. Here what crosses is the model itself, once."
                ),
                technical=(
                    "The long stage and the only interconnect-bound one. 61 GB from "
                    "NVMe through the host across PCIe into 64 GB of card-local "
                    "memory, ~52 Gb/s, order of a minute — the slowest operation in "
                    "the trace. The cost amortizes per model rather than per "
                    "prompt, token, or session. The standard discrete-accelerator "
                    "objection assumes continuous transfer; what transfers here is "
                    "the model, once."
                ),
                expert=(
                    "61 GB NVMe → PCIe → card memory at ~52 Gb/s. Only "
                    "interconnect-bound phase; amortized per model, not per "
                    "request. Defeats the usual bus-bottleneck objection, which "
                    "presumes continuous transfer."
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
            label="Resident — the bus goes quiet for good",
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
            label="Prefill — the prompt is read all at once",
            description=L(
                novice=(
                    "A question arrives and the accelerator reads all of it at "
                    "once. This first stage can work on every word of your input "
                    "simultaneously, so all the arithmetic units are busy together "
                    "and the chip's raw speed briefly becomes the thing that "
                    "matters. Power use peaks here. The laptop's main processor "
                    "contributes very little: it turns your text into numbers and "
                    "sends a few kilobytes across the connector — which is why the "
                    "traffic counter still reads zero at this resolution, and "
                    "honestly so."
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
                    "compute-bound half of inference. Arithmetic units saturate and "
                    "~450 TOPS is briefly the binding number; power peaks. Host "
                    "contribution is tokenization plus a few kilobytes over the "
                    "link, which is why the bandwidth counter still reads zero at "
                    "this resolution."
                ),
                expert=(
                    "Prefill — compute-bound, units saturated, ~450 TOPS binding, "
                    "power peak. Host does tokenization; link traffic negligible."
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
            label="Decode — one token at a time, bounded by memory",
            description=L(
                novice=(
                    "Now it starts producing words, and the limiting factor changes "
                    "completely. Making each new word requires reading essentially "
                    "the entire model again, so what matters is no longer how fast "
                    "the chip can calculate but how fast it can pull data out of "
                    "the memory sitting next to it. Notice what is *not* happening: "
                    "the laptop's main processor is idle, the drive is idle, and "
                    "the connector is carrying only the trickle of text coming back "
                    "to you. The entire computation is happening on one side of the "
                    "line."
                ),
                plain=(
                    "Generation begins and the bottleneck moves. Producing each "
                    "token requires reading essentially the whole model, so decode "
                    "is bounded not by the card's arithmetic rate but by how fast "
                    "weights can be pulled out of the memory beside it. This is the "
                    "memory-bound regime this repo's GPU twin names in its roofline "
                    "analysis, reached from the other direction. Note what is *not* "
                    "happening — the host CPU is idle, the SSD is idle, and the "
                    "link carries only output text."
                ),
                standard=(
                    "Generation begins, and the bottleneck moves. Producing "
                    "each new token requires reading essentially the entire "
                    "model, so decode is bounded not by the card's 450 TOPS but "
                    "by how fast weights can be pulled out of the on-card "
                    "memory beside it. This is the memory-bound regime this "
                    "repo's GPU twin's roofline analysis names, arrived at from "
                    "the opposite direction: there, a matmul becomes "
                    "memory-bound when the tile is too small to reuse what it "
                    "loaded; here, every token reuses nothing at all. Note what "
                    "is *not* happening — the host CPU is idle, the SSD is "
                    "idle, and the PCIe link is carrying a trickle of output "
                    "text. The whole computation is on one side of the line."
                ),
                technical=(
                    "Decode: the bottleneck moves from arithmetic to memory "
                    "bandwidth, since each token reads essentially the full "
                    "parameter set. This is the memory-bound regime the GPU twin's "
                    "roofline names, arrived at from the opposite side — there a "
                    "tile is too small to reuse what it loaded, here each token "
                    "reuses nothing. Host, storage, and link all idle."
                ),
                expert=(
                    "Decode — memory-bandwidth-bound; per-token working set is the "
                    "full parameter set, zero reuse. Same regime as the GPU twin's "
                    "roofline, opposite derivation. Host/storage/link idle."
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
            label="Sustained — flat wattage, no throttle",
            description=L(
                novice=(
                    "Several minutes into a long answer, and the interesting "
                    "measurement is the one that has not changed. A laptop's "
                    "graphics chip pressed into this kind of work posts an "
                    "impressive number for thirty seconds and then slows down, "
                    "because it was designed for short bursts of graphics work. "
                    "This accelerator was designed for the opposite: a steady load "
                    "for as long as it takes. So the power stays flat and the words "
                    "keep coming at the same rate. For anything you actually sit "
                    "and use, the top speed barely matters and the speed you can "
                    "hold for ten minutes matters enormously."
                ),
                plain=(
                    "Several minutes into a long generation, and the interesting "
                    "measurement is the one that does not change. A laptop GPU "
                    "pressed into inference posts a high number for thirty seconds "
                    "and then throttles, because its power and thermal design "
                    "assumes bursty graphics work. An inference accelerator is "
                    "designed for the opposite duty cycle, so the wattage holds "
                    "flat and the token rate holds with it. For interactive use, "
                    "peak throughput is close to irrelevant and the rate you can "
                    "hold for ten minutes is everything."
                ),
                standard=(
                    "Several minutes into a long generation, and the "
                    "interesting measurement is the one that does not change. A "
                    "laptop GPU pressed into inference service posts a high "
                    "number for thirty seconds and then throttles, because its "
                    "power and thermal envelope were designed for bursty "
                    "graphics work. An inference accelerator is designed for "
                    "the opposite duty cycle, so the wattage here holds flat "
                    "and the token rate holds with it. For interactive use, "
                    "peak throughput is close to irrelevant and the rate you "
                    "can hold for ten minutes is everything — which is the same "
                    "argument, at a very different scale, that forces liquid "
                    "cooling on this repo's IR7000 racks."
                ),
                technical=(
                    "Sustained generation, and the measurement of interest is the "
                    "absence of decline. A laptop GPU throttles here — its "
                    "power/thermal envelope assumes bursty graphics duty. An "
                    "inference part assumes flat duty, so wattage and token rate "
                    "hold. For interactive workloads, peak is near-irrelevant "
                    "against held rate; the same argument forces liquid cooling at "
                    "rack scale in the IR7000 twin."
                ),
                expert=(
                    "Sustained: no decline. GPU duty cycle assumes bursts and "
                    "throttles; inference silicon assumes flat load. Held rate "
                    "dominates peak for interactive use."
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
