"""Component catalog: what you actually choose when you configure a Dell Pro
Max Plus for on-device inference, as backend data.

Written for a technically skilled reader who is new to running models
locally: NPU, TOPS, quantization, ONNX, prefill/decode, KV cache, and
mixture-of-experts are all spelled out on first use. Categories map to the
inference-path regions in ``anatomy.py`` via ``region_ids``, and
``tests/test_catalog.py`` enforces that every id resolves.

The ordering is deliberate. The first category is the machine, but the
second is the accelerator card, and every category after it is downstream
of one question the card decides: how big a model fits in memory. That is a
different buying question from the one a workstation usually poses, where
the processor comes first and memory is sized to suit it.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="platform",
        name="Mobile workstation platform",
        blurb=(
            "The chassis, and with it the thermal and power envelope that "
            "decides how long a sustained inference run can hold its rate."
        ),
        limits="16-inch and 18-inch chassis; ISV-certified mobile workstations",
        region_ids=[],
        options=[
            CatalogOption(
                id="promax16plus",
                name="Dell Pro Max 16 Plus",
                summary=(
                    "The 16-inch mobile workstation that introduced the "
                    "enterprise discrete NPU."
                ),
                details=(
                    "The machine this twin models: the first mobile "
                    "workstation to ship an enterprise-grade discrete "
                    "Neural Processing Unit — a dedicated inference "
                    "accelerator with its own memory, rather than a share "
                    "of the CPU's. It is a full workstation in every other "
                    "respect, so it is a reasonable primary machine that "
                    "happens to be able to run a 109-billion-parameter "
                    "model on a plane. Linux first, with Windows support "
                    "arriving in early 2026."
                ),
            ),
            CatalogOption(
                id="promax18plus",
                name="Dell Pro Max 18 Plus",
                summary=(
                    "The 18-inch sibling — more chassis volume, so more "
                    "sustained thermal headroom."
                ),
                details=(
                    "The same discrete-NPU architecture in a larger body. "
                    "For inference the extra size buys exactly one thing, "
                    "and it is the right one: the ability to hold a given "
                    "wattage for longer without the fans becoming the "
                    "limiting factor. If the workload is a handful of short "
                    "prompts a day the difference is invisible; if it is an "
                    "agent grinding through documents for an hour, it is "
                    "the whole difference."
                ),
            ),
            CatalogOption(
                id="promax16",
                name="Dell Pro Max 16 (no discrete NPU)",
                summary=(
                    "The conventional configuration — integrated NPU and an "
                    "optional workstation GPU."
                ),
                details=(
                    "Worth listing because it is the honest baseline. This "
                    "machine still has an integrated NPU in its processor, "
                    "good for perhaps 50 TOPS, and can carry a workstation "
                    "GPU. It will run small models comfortably. What it "
                    "cannot do is hold a hundred-billion-parameter model "
                    "resident, because both of those accelerators draw on "
                    "system memory shared with everything else. The gap is "
                    "not about speed; it is about capacity."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="npu",
        name="Discrete NPU card",
        blurb=(
            "The accelerator and, more importantly, the memory it brings "
            "with it — the single decision that sets which models will run."
        ),
        limits="Up to 2 × AI-100, 32 AI cores, 64 GB dedicated AI memory",
        region_ids=["npu-1", "npu-2", "aimem"],
        options=[
            CatalogOption(
                id="ai100-dual",
                name="Qualcomm AI 100 PC Inference Card — dual NPU, 64 GB",
                summary=(
                    "Two AI-100 NPUs, 32 AI cores, ~450 TOPS, and 64 GB of "
                    "dedicated AI memory."
                ),
                details=(
                    "The configuration in this twin. Two inference "
                    "processors share one 64 GB pool of LPDDR4x memory that "
                    "belongs to the card and to nothing else. TOPS "
                    "(trillions of operations per second) is the headline "
                    "number at roughly 450 for 8-bit arithmetic, but the "
                    "64 GB is the number that decides what is possible: a "
                    "109-billion-parameter model with weights quantized to "
                    "about four bits fits in roughly 61 GB, leaving room "
                    "for the KV cache — the running record of the "
                    "conversation, which grows with context length. Compute "
                    "runs at FP16 (16-bit floating point) even though the "
                    "weights are stored compressed; those are separate "
                    "decisions and only the storage one makes the model fit."
                ),
            ),
            CatalogOption(
                id="ai100-single",
                name="Single AI-100 configuration",
                summary=(
                    "One inference processor and a smaller memory pool — "
                    "sized for models in the tens of billions."
                ),
                details=(
                    "Half the card, and therefore half the ceiling. This is "
                    "the right choice when the target models are in the 7 "
                    "to 30 billion parameter range, which covers most "
                    "coding assistants, summarizers, and domain-tuned "
                    "models in practice. The reasoning to apply is "
                    "unglamorous: work out the resident size of the largest "
                    "model you actually intend to run, add the KV cache for "
                    "your longest realistic context, and buy the pool that "
                    "holds it. Nothing else about the card matters as much."
                ),
            ),
            CatalogOption(
                id="integrated-only",
                name="Integrated NPU only",
                summary=(
                    "The NPU already inside the host processor — no card, "
                    "no dedicated memory."
                ),
                details=(
                    "Every current business laptop processor includes a "
                    "modest NPU, typically around 50 TOPS, and it is "
                    "genuinely useful: background blur, live captioning, "
                    "local transcription, small classifiers running "
                    "continuously at very low power. It shares system "
                    "memory with the operating system, so a large model "
                    "would contend with everything else on the machine and "
                    "hit a ceiling set by however much DRAM was ordered. "
                    "The two accelerators are complements, not rivals — the "
                    "integrated one for always-on background work, the "
                    "discrete one for the model you sat down to use."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="host-cpu",
        name="Host processor",
        blurb=(
            "Runs the workstation and orchestrates the card — then, during "
            "generation, does almost nothing."
        ),
        limits="Mobile workstation-class processors with an integrated NPU",
        region_ids=["cpu"],
        options=[
            CatalogOption(
                id="cpu-balanced",
                name="Balanced workstation processor",
                summary=(
                    "Enough cores for the workstation's day job; inference "
                    "does not need more."
                ),
                details=(
                    "During generation the CPU tokenizes input, "
                    "detokenizes output, and waits. That is the entire "
                    "contribution, because the forward pass happens on the "
                    "other side of the PCIe boundary. So the processor "
                    "should be sized for whatever else the machine does — "
                    "compiling, CAD, simulation, a browser with too many "
                    "tabs — and not for the model. The pleasant consequence "
                    "is that the workstation stays fully responsive while a "
                    "very large model is running, which is emphatically not "
                    "true when inference borrows the GPU."
                ),
            ),
            CatalogOption(
                id="cpu-top",
                name="Top-bin workstation processor",
                summary=(
                    "For machines whose non-AI workload is the demanding "
                    "part."
                ),
                details=(
                    "Choose this on the merits of the other work. A faster "
                    "host will shave a little off model load time, since "
                    "reading 61 GB off the SSD and pushing it across PCIe "
                    "is partly a host-driven operation, but that cost is "
                    "paid once per model rather than per prompt. It will "
                    "not make a single token arrive faster."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="sysmem",
        name="System memory",
        blurb=(
            "Host DRAM — for the operating system and applications, not for "
            "the model."
        ),
        limits="LPDDR5X, on the host side of the PCIe boundary",
        region_ids=["dram"],
        options=[
            CatalogOption(
                id="mem-32",
                name="32 GB",
                summary="Adequate, because the model is not living here.",
                details=(
                    "This is the configuration decision that changes most "
                    "when a discrete NPU is present. On a machine without "
                    "one, system memory is the model's ceiling, and buyers "
                    "over-specify it for exactly that reason. With 64 GB on "
                    "the card, host memory returns to being sized for "
                    "ordinary work. The model never touches it after load."
                ),
            ),
            CatalogOption(
                id="mem-64",
                name="64 GB or more",
                summary=(
                    "For workstation workloads that genuinely need it, "
                    "alongside inference."
                ),
                details=(
                    "Worth buying for simulation, large datasets, virtual "
                    "machines, or heavy container work — the things a "
                    "workstation was always bought for. It will not raise "
                    "the size of the model you can run, since that is set "
                    "entirely by the card's own pool."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="storage",
        name="Storage — the model library",
        blurb=(
            "Where compiled models sit between runs, and the only stage "
            "where their size costs time."
        ),
        limits="NVMe SSD; a 109B model occupies roughly 61 GB at rest",
        region_ids=["ssd"],
        options=[
            CatalogOption(
                id="ssd-2tb",
                name="2 TB NVMe",
                summary="Room for a working set of several large models.",
                details=(
                    "A compiled container for a large model runs to tens of "
                    "gigabytes, so a model library is a real storage "
                    "consideration in a way that ordinary applications are "
                    "not. Read speed matters for exactly one operation — "
                    "load — and load happens once per model, not per "
                    "prompt. Switching between two already-compiled models "
                    "is a load, not a recompile, so keeping several on disk "
                    "is the normal working pattern."
                ),
            ),
            CatalogOption(
                id="ssd-4tb",
                name="4 TB NVMe or dual drives",
                summary=(
                    "For teams keeping many model variants, or model files "
                    "alongside large datasets."
                ),
                details=(
                    "Fine-tuned variants multiply quickly: one base model "
                    "plus a handful of domain adaptations is already "
                    "several hundred gigabytes. A second drive also lets "
                    "the model library live separately from the operating "
                    "system, which makes re-imaging a machine considerably "
                    "less painful."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="accelerators",
        name="Other accelerators on board",
        blurb=(
            "What else in the machine can run a model, and why it is not "
            "the same thing."
        ),
        limits="Integrated NPU ~50 TOPS; optional workstation GPU",
        region_ids=["cpu", "pcie"],
        options=[
            CatalogOption(
                id="igpu-npu",
                name="Integrated NPU — always-on background work",
                summary=(
                    "Low power, always available, sharing system memory."
                ),
                details=(
                    "The processor's own NPU is the right home for small "
                    "models that run continuously and must cost almost "
                    "nothing: noise suppression, background blur, "
                    "transcription, on-device search indexing. It is not "
                    "competing with the card, and treating it as a smaller "
                    "version of the card is the wrong mental model — the "
                    "difference is that it has no memory of its own."
                ),
            ),
            CatalogOption(
                id="rtx-gpu",
                name="Workstation GPU",
                summary=(
                    "Excellent at training, rendering, and bursty compute; "
                    "an awkward fit for sustained inference."
                ),
                details=(
                    "A mobile workstation GPU has more raw floating-point "
                    "throughput than the inference card and is the right "
                    "tool for rendering, simulation, and fine-tuning a "
                    "small model locally. For serving a large model it runs "
                    "into two problems: its memory is measured in tens of "
                    "gigabytes shared with graphics, and its power and "
                    "thermal design assumes bursts, so a long generation "
                    "hits a high rate and then throttles. Sustained token "
                    "rate, not peak, is what an interactive assistant is "
                    "judged on."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="toolchain",
        name="Model toolchain",
        blurb=(
            "How a trained model becomes something this specific silicon "
            "can execute."
        ),
        limits="Ahead-of-time compilation; ONNX in, hardware container out",
        region_ids=["runtime"],
        options=[
            CatalogOption(
                id="onnx-compile",
                name="ONNX export and ahead-of-time compilation",
                summary=(
                    "Export to an open interchange format, then compile "
                    "once for the card."
                ),
                details=(
                    "The standard path. A trained model is exported to ONNX "
                    "— an open format for describing neural networks — and "
                    "compiled into a container built for this hardware: the "
                    "graph partitioned across the card's 32 AI cores, "
                    "quantization chosen per tensor, execution schedule "
                    "fixed. Compilation is slow and happens on a build "
                    "machine, and that is precisely why runtime behaviour "
                    "is so steady. Nothing is being decided dynamically "
                    "while tokens are being produced."
                ),
            ),
            CatalogOption(
                id="quantization",
                name="Quantization strategy",
                summary=(
                    "How aggressively weights are compressed — the lever "
                    "that decides whether a model fits."
                ),
                details=(
                    "Quantization stores each weight in fewer bits than the "
                    "16 or 32 it was trained with. Four-bit weights are "
                    "what let 109 billion parameters occupy about 61 GB "
                    "rather than 218 GB. The cost is a small, measurable "
                    "loss of accuracy that varies by model and by task, so "
                    "the honest engineering step is to evaluate the "
                    "quantized model on your own task rather than trusting "
                    "a benchmark. Note that compressing storage is separate "
                    "from computing at reduced precision: this card does "
                    "the arithmetic at FP16 regardless."
                ),
            ),
            CatalogOption(
                id="ai-studio",
                name="Dell Pro AI Studio",
                summary=(
                    "Dell's tooling for packaging and deploying models to a "
                    "fleet of AI PCs."
                ),
                details=(
                    "Compiling a model once is a development task; getting "
                    "the same validated model onto four hundred laptops is "
                    "an IT task, and a different one. Dell's AI PC "
                    "enablement tooling covers the second: packaging "
                    "models, targeting the right accelerator on each "
                    "machine, and versioning what is deployed. This is the "
                    "unglamorous half of on-device AI and usually the half "
                    "that decides whether a pilot becomes a rollout."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="models",
        name="Models that fit",
        blurb=(
            "What 64 GB of dedicated memory actually buys, in models you "
            "would want to run."
        ),
        limits="Up to ~120 billion parameters resident, quantized",
        region_ids=["aimem"],
        options=[
            CatalogOption(
                id="large-moe",
                name="Large mixture-of-experts model (~109B parameters)",
                summary=(
                    "The demonstrated case — a frontier-class open model "
                    "running with no network."
                ),
                details=(
                    "Dell demonstrated a 109-billion-parameter Llama 4 "
                    "model generating text on this machine offline. Models "
                    "of this size are typically mixture-of-experts designs: "
                    "all the parameters must be held in memory, but only a "
                    "fraction of them are used for any given token, so the "
                    "arithmetic per token is far lower than the parameter "
                    "count suggests. That architecture is unusually kind to "
                    "this hardware, because it trades exactly what the card "
                    "has plenty of — memory capacity — against what it has "
                    "less of than a datacenter GPU, which is bandwidth."
                ),
            ),
            CatalogOption(
                id="dense-mid",
                name="Dense mid-size model (7B–70B)",
                summary=(
                    "The everyday case: fast, comfortable, plenty of "
                    "headroom for long context."
                ),
                details=(
                    "A dense model uses every parameter for every token, so "
                    "the token rate is set fairly directly by how fast the "
                    "weights can be read from on-card memory. At these "
                    "sizes there is generous room left for the KV cache, "
                    "which means long documents and long conversations "
                    "without the context window becoming the binding "
                    "constraint — often the more practical limitation in "
                    "real work than model quality."
                ),
            ),
            CatalogOption(
                id="multi-model",
                name="Several models resident at once",
                summary=(
                    "Split the pool: a generalist plus specialists, no "
                    "reload between them."
                ),
                details=(
                    "Sixty-four gigabytes can hold one very large model or "
                    "several smaller ones simultaneously — a mid-size "
                    "general model, an embedding model for retrieval, and a "
                    "small fast model for classification and routing. For "
                    "agent workloads that switch between roles constantly, "
                    "this is usually worth more than one larger model, "
                    "because switching costs nothing when both are already "
                    "resident."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="thermal-power",
        name="Thermal and power",
        blurb=(
            "What decides the token rate you can hold for an hour, as "
            "opposed to for thirty seconds."
        ),
        limits="Vapor chamber cooling; adapter and battery rail shared with CPU/GPU",
        region_ids=["thermal", "power"],
        options=[
            CatalogOption(
                id="sustained-cooling",
                name="Sustained-load cooling",
                summary=(
                    "Designed for a flat duty cycle rather than bursts."
                ),
                details=(
                    "Inference is an unusual laptop workload: constant, "
                    "moderate, and long. That is easier to cool than a "
                    "gaming spike, but only if the design expects it. The "
                    "measurement worth watching is not a peak figure but "
                    "the absence of decline — a wattage that holds for the "
                    "length of a generation. This repo's IR7000 twin is the "
                    "same argument at 200 kW, where sustained AI load is "
                    "what forces liquid cooling on an entire rack."
                ),
            ),
            CatalogOption(
                id="adapter",
                name="Adapter and battery operation",
                summary=(
                    "The card runs on battery too — at a lower sustained "
                    "wattage."
                ),
                details=(
                    "The power path here is the one this repo's Alienware "
                    "twin models in detail: an adapter negotiating its "
                    "capability with the embedded controller, a system "
                    "budget divided between CPU, GPU, and now the "
                    "inference card, and a battery able to supplement the "
                    "adapter under peak demand. The card's draw is modest "
                    "by accelerator standards, which is what makes it "
                    "viable in a laptop; on battery the model still runs, "
                    "just at a lower held wattage and a correspondingly "
                    "lower token rate."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="deployment",
        name="Deployment, security, and support",
        blurb=(
            "Turning one impressive laptop into a fleet an IT organization "
            "will actually approve."
        ),
        limits="Commercial-grade manageability and support programs",
        region_ids=[],
        options=[
            CatalogOption(
                id="data-residency",
                name="Data residency by construction",
                summary=(
                    "The strongest security property here is architectural, "
                    "not a feature."
                ),
                details=(
                    "Nothing leaves the machine because nothing needs to. "
                    "There is no prompt in a hosted log, no retention "
                    "policy to negotiate, and no vendor to trust with the "
                    "contents of a document. For regulated work this "
                    "reframes the approval conversation entirely: the "
                    "question stops being 'what does the provider do with "
                    "our data' and becomes the ordinary endpoint-security "
                    "question the organization already knows how to answer."
                ),
            ),
            CatalogOption(
                id="fleet",
                name="Fleet management and model versioning",
                summary=(
                    "Knowing which model version is on which machine, and "
                    "being able to change it."
                ),
                details=(
                    "An on-device model is a deployed artifact like any "
                    "other, with the awkward property that it is large and "
                    "changes meaning subtly between versions. Fleet tooling "
                    "has to answer which build is where, push a replacement "
                    "without a sixty-gigabyte download over a hotel "
                    "connection, and roll back when a new version behaves "
                    "worse on the task that matters. This repo's CloudIQ "
                    "twin covers the same discipline for infrastructure."
                ),
            ),
            CatalogOption(
                id="support",
                name="ProSupport and deployment services",
                summary=(
                    "Commercial support programs covering the workstation "
                    "and its accelerator."
                ),
                details=(
                    "Standard commercial workstation support, extended to a "
                    "component category that is new enough that the useful "
                    "part is often advisory rather than break-fix: sizing "
                    "the memory pool against the models a team actually "
                    "intends to run, and validating that a quantized model "
                    "still performs on the task it was chosen for."
                ),
            ),
        ],
    ),
]
