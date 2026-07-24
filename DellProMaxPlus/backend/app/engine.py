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
            description=(
                "A 16-inch mobile workstation, closed. Somewhere on its NVMe "
                "SSD sits a 61 GB file: a 109-billion-parameter language "
                "model, already compiled for the inference card inside. "
                "Nothing about that file is remarkable except where it is — "
                "on a laptop, not in a datacenter, and not behind an API. "
                "Everything that follows is the story of how it gets from "
                "the left-hand side of this diagram to the right-hand side, "
                "and why it only has to make that trip once."
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            description=(
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
            active_regions=[*_CARD, "thermal", "power"],
            weights_resident_gb=MODEL_GB,
            link_gbps=0,
            tokens_per_second=21,
            npu_watts=67,
            elapsed_seconds=240,
        ),
    ]
