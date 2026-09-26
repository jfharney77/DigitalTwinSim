"""Device anatomy data: the inference path through a Dell Pro Max 16 Plus.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over millimetre accuracy (project
scope guardrail). This is not a service manual's view of the chassis; it is
a map of where a model's weights actually sit.

The drawing is organized around one boundary. Everything on the left is the
host: the CPU, system DRAM, and the NVMe SSD where the compiled model file
lives at rest. Everything on the right is the inference card: two AI-100
NPUs and the 64 GB of dedicated AI memory they read from (physically two
32 GB LPDDR4x banks, one per NPU; drawn as one block because a large model
is sharded across both). Between them, a
single narrow PCIe strip.

The geometry is the lesson, so ``tests/test_anatomy.py`` pins it: every
host-side region lies strictly left of that strip and every card-side region
strictly right of it. Weights cross it once, during load, and then never
again — which is why the strip is drawn narrow and the AI memory is drawn
large.
"""

from __future__ import annotations

from .leveling import L
from .models import DeviceAnatomy, DeviceRegion, Photo, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell or Qualcomm product image — with an honest credit.
NPU_ILLO = Photo(
    url="/promax-npu.svg",
    caption=(
        "The inference path: a compiled model crosses the PCIe boundary "
        "once, into 64 GB of on-card AI memory, and stays there. Every "
        "token generated afterwards is read from the right-hand side of "
        "that line — which is why the bus is idle during inference and the "
        "network can be unplugged entirely."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)

_NPU_DESC = (
    "One of the two Qualcomm AI-100 inference processors on the card. Each "
    "is built for one job — running a trained network forward — and its "
    "internal design says so: separate tensor, vector, and scalar units per "
    "AI core, with the tensor unit doing the heavy matrix work. Each NPU "
    "has 16 AI cores and its own 32 GB bank of LPDDR4x memory, and the host "
    "sees the two as separate devices. Across the card that is 32 AI cores "
    "and, as widely reported, roughly 450 TOPS (trillions of 8-bit "
    "operations per second). The comparison that matters is not against a "
    "datacenter GPU but against the integrated NPU in the host processor: "
    "Intel rates the one in this machine's Core Ultra 200HX at 13 TOPS, "
    "and, more decisively, it has no memory of its own. This is why "
    "'discrete' is the word in the product name: the accelerator brought "
    "its own memory with it."
)


ANATOMY = DeviceAnatomy(
    id="promax16plus",
    name="Dell Pro Max 16 Plus — discrete NPU inference path",
    vendor="Dell Technologies + Qualcomm",
    form_factor="16-inch mobile workstation with Qualcomm AI 100 PC Inference Card",
    generation="First mobile workstation with an enterprise-grade discrete NPU",
    year=2025,
    width=100,
    height=54,
    overview=L(
        novice=(
            "This is a laptop that can run a very large "
            "artificial-intelligence "
            "model entirely by itself, with no internet connection. Normally "
            "that kind of model is far too big for a personal computer, so you "
            "send your question to a company's servers and they send an answer "
            "back. This machine does not need to. It has an extra chip inside "
            "— "
            "an accelerator built only for running AI models — and, crucially, "
            "that chip has 64 gigabytes of memory reserved for itself. Memory "
            "is what decides whether a model fits at all, the way a "
            "bookshelf's "
            "size decides how many books you can keep to hand. The diagram is "
            "arranged around one narrow strip in the middle, which is the "
            "connection between the laptop's ordinary parts on the left and "
            "the "
            "accelerator on the right. The model is copied across that strip "
            "once, when you load it. After that it simply lives on the right "
            "side and never moves again. That is why you can unplug the "
            "network "
            "entirely and nothing changes."
        ),
        plain=(
            "The Dell Pro Max 16 Plus is the first mobile workstation with a "
            "separate, dedicated AI accelerator rather than a small one built "
            "into the main processor. The card carries two AI-100 chips and 64 "
            "GB of memory that belongs to the card alone — and that memory "
            "figure, not the raw speed, is what decides which models will run. "
            "Dell demonstrated a 109-billion-parameter model generating text "
            "on "
            "this machine with no internet connection. The map is drawn around "
            "the connection in the middle: the model file starts on the left, "
            "on the drive, crosses that connection once while loading, and is "
            "then read in place on the right for every word it produces. That "
            "is why the connection goes quiet, the main processor has little "
            "to "
            "do, and unplugging the network changes nothing."
        ),
        standard=(
            "The Dell Pro Max 16 Plus is the first mobile workstation to ship "
            "an "
            "enterprise-grade discrete Neural Processing Unit: a Qualcomm AI "
            "100 "
            "PC Inference Card carrying two AI-100 NPUs, 32 AI cores, roughly "
            "450 TOPS of 8-bit compute, and — the number that actually decides "
            "what you can run — 64 GB of dedicated on-card AI memory. Dell "
            "demonstrated a 109-billion-parameter Llama 4 model generating "
            "text "
            "on this machine with no internet connection and no server behind "
            "it. This map is drawn around the one boundary that explains how: "
            "the PCIe strip in the middle. The model file starts on the left, "
            "on the NVMe SSD. It crosses the strip exactly once, during load. "
            "Every token generated after that is computed entirely on the "
            "right "
            "— which is why the bus goes quiet, why the host CPU has almost "
            "nothing to do, and why pulling the network cable changes nothing "
            "at all. Layout is a stylized mental model, not a service diagram."
        ),
        technical=(
            "The first mobile workstation with an enterprise-grade discrete "
            "NPU: a Qualcomm AI 100 PC Inference Card with two AI-100 NPUs, 32 "
            "AI cores, ~450 TOPS INT8, and 64 GB of dedicated on-card memory — "
            "the capacity figure being what actually gates model selection. "
            "Dell demonstrated a 109B-parameter Llama 4 running fully offline. "
            "The map is organized around the PCIe boundary: the container is "
            "staged on NVMe, crosses once at load, and every subsequent token "
            "is computed card-side. Hence an idle bus, a host CPU doing "
            "tokenization and little else, and complete indifference to "
            "network "
            "state. Stylized layout, not a service diagram."
        ),
        expert=(
            "Discrete NPU in a mobile workstation: 2 × AI-100, 32 cores, ~450 "
            "TOPS INT8, 64 GB dedicated. Capacity gates model selection, not "
            "throughput. Weights cross PCIe once at load and are resident "
            "thereafter; decode is card-local and bandwidth-bound against "
            "on-card memory. Bus idle post-load, host idle during generation, "
            "network irrelevant."
        ),
    ),
    regions=[
        DeviceRegion(
            id="cpu", kind="host", label="Host CPU",
            x=2, y=4, w=36, h=11,
            description=L(
                novice=(
                    "The laptop's main processor — the chip that runs the "
                    "operating system and everything you normally open. Here "
                    "it does the setting-up: it opens the model file, tells "
                    "the accelerator card what to do, and hands over your "
                    "question. Then, surprisingly, it mostly waits. On the "
                    "way in it chops your text into the small pieces the "
                    "model reads, and on the way out it turns the model's "
                    "answer back into words, but the thinking itself all "
                    "happens on the other side of the narrow strip in the "
                    "middle of the picture. That idleness is deliberate. It "
                    "means the laptop stays responsive for ordinary work "
                    "while a very large model is running, which is not true "
                    "of a laptop that borrows its graphics chip to do the "
                    "same job. The processor also has a small AI chip built "
                    "into it, which is still useful for little always-on "
                    "jobs like blurring your background on a video call — "
                    "but not for a model this size."
                ),
                standard=(
                "The host processor. It does the setup work — opening the "
                "model container, programming the card, handing over the "
                "prompt — and then, strikingly, very little. During "
                "generation the CPU is mostly waiting: it tokenizes text on "
                "the way in, detokenizes on the way out, and the entire "
                "forward pass happens on the other side of the PCIe strip. "
                "That idleness is a feature. It means the machine stays "
                "responsive for ordinary work while a 109-billion-parameter "
                "model is running, which is not true of a laptop that "
                "borrows its GPU for inference. Its own integrated NPU is "
                "still there and still useful, but for small always-on "
                "tasks — background blur, transcription — not for this."
                ),
            ),
        ),
        DeviceRegion(
            id="dram", kind="memory",
            label=L(
                novice="System memory (the laptop's own working memory)",
                standard="System memory (DDR5 CAMM2)",
            ),
            x=2, y=17, w=36, h=10,
            description=L(
                novice=(
                    "The laptop's ordinary working memory — the scratch space "
                    "the processor keeps whatever it is busy with in. It sits "
                    "on the laptop's side of the narrow strip. The label calls "
                    "it DDR5 CAMM2, which is just the type of memory module "
                    "Dell fits here; the name matters to whoever orders spare "
                    "parts, not to this story. What matters is who it belongs "
                    "to: everyone. On a laptop with no accelerator card, a "
                    "large model would have to live in this shared space, "
                    "competing with the operating system and every open "
                    "application, and it could only be as large as the memory "
                    "someone happened to buy. The card having its own memory "
                    "removes that argument: the model is not queuing behind "
                    "your web browser. While the model is answering, this "
                    "block is quiet — it holds your question, the answer being "
                    "written, and some housekeeping, and nothing more."
                ),
                standard=(
                "System DRAM, on the host side of the boundary. On a laptop "
                "without a discrete NPU this is where a large model would "
                "have to live, shared with the operating system and every "
                "application — and shared memory means contention, "
                "unpredictable latency, and a hard ceiling set by whatever "
                "the machine was configured with. The card's own memory "
                "removes that argument entirely: the model does not compete "
                "with the browser. During inference this region is quiet, "
                "holding only the prompt, the generated text, and the "
                "runtime's bookkeeping."
                ),
            ),
        ),
        DeviceRegion(
            id="ssd", kind="storage",
            label=L(
                novice="Solid-state drive — where the model files are kept",
                standard="NVMe SSD — model library at rest",
            ),
            x=2, y=29, w=36, h=10,
            description=L(
                novice=(
                    "The laptop's drive, where model files sit when nothing is "
                    "running. A file here is not a plain bag of the numbers a "
                    "model learned. It has already been translated for this "
                    "exact card: the work divided up across the card's 32 "
                    "processing cores, the numbers compressed so they take "
                    "less room. Several models can sit side by side, and "
                    "swapping to another one means copying it across, not "
                    "translating it again. This is the only point in the "
                    "model's life where its sheer size is a problem — 61 "
                    "gigabytes has to travel across the strip, once. After "
                    "that the drive has nothing to do with answering "
                    "questions, which is why it goes dark for the rest of the "
                    "sequence."
                ),
                standard=(
                "Where compiled models live between runs. A model here is "
                "not a checkpoint of raw weights but a container built for "
                "this specific hardware — the graph already partitioned "
                "across the card's 32 AI cores, the weights already "
                "quantized. Several such models can sit side by side, and "
                "switching between them is a load, not a recompile. This is "
                "the only moment in the model's life when its size is a "
                "throughput problem: 61 GB has to move across the bus once. "
                "Afterwards the SSD is irrelevant to inference, which is "
                "why it goes dark for the rest of the trace."
                ),
            ),
        ),
        DeviceRegion(
            id="pcie", kind="link", label="PCIe",
            x=43, y=4, w=8, h=35,
            description=L(
                novice=(
                    "The narrow strip in the middle: the one connection "
                    "between the laptop and the accelerator card. PCIe is its "
                    "name, short for Peripheral Component Interconnect "
                    "Express, and it is the standard way an add-in card plugs "
                    "into a computer. It is also this whole diagram's subject. "
                    "People expect a connection like this to be the weak "
                    "link, because work has to be shipped across it and "
                    "results shipped back, over and over. That is true when "
                    "data keeps moving. It is not true here, because what "
                    "crosses is the model, not the work. The model makes the "
                    "trip once, while loading, and then stays put. Afterwards "
                    "the only things crossing are your question going right "
                    "and words coming back left, which is a few kilobytes "
                    "against 61 gigabytes. Watch the link counter while the "
                    "sequence plays: it is busy during loading and reads zero "
                    "for every step where the model is actually answering. "
                    "The strip is drawn narrow on purpose."
                ),
                standard=(
                "The boundary — and this twin's whole subject. Conventional "
                "wisdom about discrete accelerators is that the bus is the "
                "bottleneck: every batch has to be shipped across, results "
                "shipped back, and the interconnect sets the ceiling. That "
                "is true when data moves continuously. It is not true here, "
                "because what crosses is the model, not the work. The "
                "weights make the trip once during load and then stay put; "
                "afterwards the only traffic is a prompt going right and "
                "generated tokens coming left, which is a few kilobytes "
                "against 61 gigabytes. Watch the link counter during the "
                "trace: it peaks during load and reads zero for every step "
                "of actual inference. The strip is drawn narrow on purpose."
                ),
            ),
        ),
        DeviceRegion(
            id="npu-1", kind="npu", label="AI-100 NPU 1",
            x=56, y=4, w=20, h=13,
            description=_NPU_DESC,
        ),
        DeviceRegion(
            id="npu-2", kind="npu", label="AI-100 NPU 2",
            x=78, y=4, w=20, h=13,
            description=_NPU_DESC,
        ),
        DeviceRegion(
            id="aimem", kind="aimemory",
            label=L(
                novice="64 GB of memory belonging to the card alone",
                standard="64 GB dedicated AI memory (LPDDR4x)",
            ),
            x=56, y=19, w=42, h=20,
            description=L(
                novice=(
                    "The reason this machine can do what it does, and drawn "
                    "large because it deserves to be. Sixty-four gigabytes of "
                    "memory that belongs to the card and to nothing else, "
                    "holding the model's learned numbers from the moment it "
                    "loads until you close it. The label calls it LPDDR4x, "
                    "which is the type of memory chip used; the name matters "
                    "to the people who build the card, not to this story. "
                    "Physically it is two 32-gigabyte banks, one wired to each "
                    "of the two AI chips, drawn as a single block because a "
                    "model this large is split across both. Dell says the card "
                    "can hold a model of roughly 120 billion parameters when "
                    "the numbers are squeezed down to four bits each. By that "
                    "arithmetic a 109-billion-parameter model takes about 61 "
                    "gigabytes, this twin's illustrative figure — it fits, "
                    "with a little room left for the notes the model keeps as "
                    "a conversation gets longer. One distinction is worth "
                    "keeping straight: the numbers are stored squeezed, but "
                    "the arithmetic is done at fuller precision. Compressing "
                    "what you store and computing carefully are separate "
                    "decisions, and only the first is what makes the model "
                    "fit. Producing each word means reading nearly all of "
                    "this memory, so the speed of answering is set by how "
                    "fast this block can be read, not by how fast the chips "
                    "next door can calculate."
                ),
                standard=(
                "The reason this machine can do what it does, drawn large "
                "because it deserves to be. Sixty-four gigabytes of memory "
                "belonging to the card and to nothing else, holding the "
                "model's weights from load until the process ends. "
                "Physically it is two 32 GB banks, one wired to each NPU; "
                "it is drawn as one block because a model this large is "
                "split across both. Dell's product brief puts the ceiling "
                "at about 120 billion parameters with four-bit (MXINT4) "
                "weights. By that arithmetic a 109-billion-parameter model "
                "occupies about 61 GB (this twin's illustrative figure) — "
                "it fits, with a little room for the KV cache that grows "
                "as the conversation gets longer. Note the distinction the "
                "specifications invite you to blur: the weights are stored "
                "quantized, while the arithmetic runs at FP16 (16-bit "
                "floating point). Compressing what you store and computing "
                "at full precision are different decisions, and only the "
                "first one is what makes the model fit. During generation "
                "every single token requires reading essentially all of "
                "this, which is why decode is bounded by memory bandwidth "
                "rather than by the 450 TOPS next door — the same "
                "memory-bound regime this repo's GPU twin's roofline "
                "analysis names."
                ),
            ),
        ),
        DeviceRegion(
            id="runtime", kind="runtime", label="Toolchain & runtime",
            x=2, y=42, w=30, h=10,
            description=(
                "The software that turns a trained model into something "
                "this card can execute. A model is exported to ONNX (an "
                "open interchange format for neural networks), then "
                "compiled ahead of time into a hardware-specific container "
                "— a step that partitions the graph across AI cores, picks "
                "the quantization for each tensor, and fixes the execution "
                "schedule. That compile is slow, and it is also the reason "
                "runtime behaviour is so predictable: the hard decisions "
                "were made offline, on a build machine, once. Nothing is "
                "being chosen dynamically while tokens are being generated."
            ),
        ),
        DeviceRegion(
            id="thermal", kind="thermal", label="Vapor chamber & fans",
            x=35, y=42, w=30, h=10,
            description=(
                "Cooling, and the quiet half of the discrete-NPU argument. "
                "A laptop GPU asked to run inference will hit a high number "
                "briefly and then throttle, because its power and thermal "
                "envelope were designed for bursty graphics work. An "
                "inference accelerator is designed for the opposite duty "
                "cycle: a flat, sustained load for as long as the "
                "generation lasts. So the interesting metric on this "
                "machine is not peak throughput but the absence of a "
                "decline — watch the wattage during the sustained phase and "
                "note that it does not sag. The same trade appears at rack "
                "scale in this repo's IR7000 twin, where sustained AI load "
                "is what forces liquid cooling."
            ),
        ),
        DeviceRegion(
            id="power", kind="power", label="Adapter & battery rail",
            x=68, y=42, w=30, h=10,
            description=(
                "The power path feeding the card, modelled in detail by "
                "this repo's Alienware twin: an adapter negotiating its "
                "capability with the embedded controller, a system power "
                "budget divided between the CPU and the inference card, "
                "and a battery that can supplement the adapter under peak "
                "demand. The card takes the slot and the power budget a "
                "discrete GPU would otherwise have — the machine is "
                "ordered with one or the other, not both. Its appetite is "
                "modest by accelerator standards — a reported 75 W "
                "envelope, against well over 100 W for a high-end laptop "
                "GPU — which is what makes it possible in a 16-inch "
                "chassis at all. Behaviour on battery is not documented by "
                "Dell; this twin assumes the model still runs at a lower "
                "sustained wattage."
            ),
        ),
    ],
    stats=[
        Stat(label="Accelerator", value="Qualcomm AI 100 PC Inference Card"),
        Stat(label="NPUs", value="2 × AI-100 — 32 AI cores"),
        Stat(label="AI memory", value="64 GB LPDDR4x on the card (2 × 32 GB, one bank per NPU)"),
        Stat(label="Compute", value="~450 TOPS INT8 (reported); FP16 arithmetic"),
        Stat(label="Model size", value="Up to ~120 billion parameters with MXINT4 weights (Dell)"),
        Stat(label="Demonstrated", value="109B-parameter Llama 4 Scout, no network (DTW 2025)"),
        Stat(label="Card power", value="75 W envelope (reported); takes the place of a discrete GPU"),
        Stat(label="Operating systems", value="Ubuntu 24.04 LTS since November 2025; Windows 11 announced for 2026"),
        Stat(label="Form factor", value="16-inch mobile workstation"),
    ],
    photo=NPU_ILLO,
    sources=[
        SourceLink(
            label="Dell — Reimagining AI: discrete NPU power with Dell Pro Max",
            url="https://www.dell.com/en-us/blog/reimagining-ai-discrete-npu-power-with-dell-pro-max/",
        ),
        SourceLink(
            label="Dell Pro Max Plus 16 with Qualcomm AI 100 — product brief (PDF)",
            url="https://www.delltechnologies.com/asset/en-us/products/workstations/briefs-summaries/dell-pro-max-plus-workstation-with-qualcomm-npu-brief.pdf",
        ),
        SourceLink(
            label="Dell Pro Max 16 Plus — product page",
            url="https://www.dell.com/en-us/shop/dell-laptops/dell-pro-max-16-plus-laptop/spd/dell-pro-max-mb16250-laptop",
        ),
        SourceLink(
            label="StorageReview — Dell Pro Max 16 Plus with Qualcomm AIC100 review (2 × 32 GB, ~450 TOPS, replaces the GPU)",
            url="https://www.storagereview.com/review/dell-pro-max-16-plus-with-qualcomm-aic100-review-excellent-workstation-experimental-accelerator",
        ),
        SourceLink(
            label="Laptop Mag — Dell's new laptop ditches the GPU for a discrete NPU (75 W, Llama 4 demo)",
            url="https://www.laptopmag.com/laptops/dells-new-laptop-ditches-gpu-for-npu",
        ),
        SourceLink(
            label="Phoronix — shipping on Ubuntu 24.04 ahead of Windows 11 (20 November 2025)",
            url="https://www.phoronix.com/news/Dell-Pro-Max-With-Qualcomm-NPU",
        ),
        SourceLink(
            label="Intel — Core Ultra 9 285HX specifications (13 TOPS integrated NPU)",
            url="https://www.intel.com/content/www/us/en/products/sku/242297/intel-core-ultra-9-processor-285hx-36m-cache-up-to-5-50-ghz/specifications.html",
        ),
        SourceLink(
            label="Qualcomm Cloud AI SDK — architecture",
            url="https://quic.github.io/cloud-ai-sdk-pages/latest/Getting-Started/Architecture/",
        ),
        SourceLink(
            label="Serving LLMs on Cloud AI 100 Ultra vs NVIDIA GPUs (arXiv 2507.00418)",
            url="https://arxiv.org/abs/2507.00418",
        ),
    ],
)
