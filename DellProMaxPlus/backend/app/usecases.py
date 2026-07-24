"""Use cases: three configurations of a Pro Max Plus, as backend data.

Each one is a build sheet whose category and option ids must resolve
against ``catalog.py`` — enforced in ``tests/test_catalog.py``. The
narratives are written for a reader who understands computers but has not
run a large model locally before.

All three turn on the same property from different directions: the model is
resident on the machine, so the data never leaves it and the network is not
in the loop. What differs is which consequence of that matters — legal
exposure, iteration speed, or the simple absence of connectivity.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="regulated-review",
        title="Case review on material that cannot leave the building",
        summary=(
            "A clinical or legal reviewer puts confidential documents "
            "through a 109-billion-parameter model that runs entirely on "
            "the laptop in front of them."
        ),
        narrative=[
            "The blocking problem in regulated work is rarely that the "
            "model is not good enough. It is that the material cannot be "
            "sent anywhere. A patient record, a sealed filing, an "
            "unannounced merger — pasting any of these into a hosted "
            "assistant is a disclosure, and no amount of contractual "
            "assurance about retention makes it stop being one. So the "
            "capability sits unused next to the people who would benefit "
            "most from it.",
            "A discrete NPU with 64 GB of its own memory removes the "
            "question rather than answering it. The model is loaded onto "
            "the card in the morning and stays there. Every token is "
            "produced on the machine, the network plays no part after "
            "load, and there is no log on anyone else's infrastructure "
            "because no request was ever made. The security review stops "
            "being about a vendor's data handling and becomes the ordinary "
            "endpoint question the organization already knows how to "
            "answer — full-disk encryption, device management, who has the "
            "laptop.",
            "The configuration follows from that single requirement. Buy "
            "the full 64 GB pool, because the whole point is to run a model "
            "good enough that people prefer it to no model at all. Size "
            "host memory and the processor for ordinary work, since neither "
            "affects what the card can hold. Then spend the remaining "
            "effort on the part that actually determines whether this "
            "succeeds: evaluating the quantized model on the real task, "
            "with real documents, before anyone relies on it.",
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="promax16plus", qty=1,
                rationale=(
                    "Portable enough to be the reviewer's only machine, "
                    "which matters — a second device that must be "
                    "collected from a locker gets used once."
                ),
            ),
            UseCaseItem(
                category_id="npu", option_id="ai100-dual", qty=1,
                rationale=(
                    "The full 64 GB pool. A model too small to be trusted "
                    "on the task is worse than none, because it will be "
                    "trusted anyway."
                ),
            ),
            UseCaseItem(
                category_id="models", option_id="large-moe", qty=1,
                rationale=(
                    "A ~109B mixture-of-experts model: frontier-class "
                    "quality, and its architecture spends memory rather "
                    "than bandwidth, which is the trade this card wins."
                ),
            ),
            UseCaseItem(
                category_id="host-cpu", option_id="cpu-balanced", qty=1,
                rationale=(
                    "The CPU is idle during generation, so size it for the "
                    "day job and not for the model."
                ),
            ),
            UseCaseItem(
                category_id="sysmem", option_id="mem-32", qty=1,
                rationale=(
                    "The model does not live in system memory, so the "
                    "usual instinct to over-buy DRAM does not apply."
                ),
            ),
            UseCaseItem(
                category_id="storage", option_id="ssd-2tb", qty=1,
                rationale=(
                    "Room for the model plus a domain-tuned variant to "
                    "compare it against."
                ),
            ),
            UseCaseItem(
                category_id="toolchain", option_id="quantization", qty=1,
                rationale=(
                    "Four-bit weights are what make 109B parameters fit — "
                    "so the accuracy cost has to be measured on the actual "
                    "task, not assumed from a benchmark."
                ),
            ),
            UseCaseItem(
                category_id="deployment", option_id="data-residency", qty=1,
                rationale=(
                    "The architectural property is the security control "
                    "here; everything else is supporting evidence."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Data leaving the device", value="None, after model load"),
            Stat(label="Model", value="~109B parameters, resident"),
            Stat(label="Sustained rate", value="~21 tokens/second"),
            Stat(label="Network required", value="No"),
        ],
    ),
    UseCase(
        id="agent-dev-loop",
        title="Building agents without a metered API in the loop",
        summary=(
            "An engineer iterates on prompts, tools, and evaluation runs "
            "against a locally resident model — no per-token cost, no rate "
            "limit, no round trip."
        ),
        narrative=[
            "Developing anything agentic means running the model an "
            "absurd number of times. Every prompt change is a re-run, "
            "every tool signature is a re-run, and any evaluation worth "
            "trusting is hundreds of runs across a fixed set of cases. "
            "Against a hosted API that loop is metered, rate-limited, and "
            "separated from the developer by a network round trip that "
            "shows up in every iteration.",
            "A resident model changes the economics of experimenting. The "
            "marginal cost of a run is electricity, so the natural "
            "instinct — try it and see — stops being something to ration. "
            "The evaluation suite can run on every commit rather than "
            "before releases. And because the compiled model is fixed, the "
            "results are reproducible in a way that a hosted endpoint, "
            "which may be silently updated beneath you, is not.",
            "This configuration favours several resident models over one "
            "very large one. Agents spend most of their time on work that "
            "does not need a frontier model — routing, classification, "
            "embedding for retrieval — and only occasionally on the hard "
            "reasoning step. Holding a generalist, a small fast model, and "
            "an embedding model in the pool simultaneously means switching "
            "between them costs nothing, which is worth more in this "
            "workload than raw capability. The production system will "
            "still call a hosted frontier model; the point is that the "
            "development loop no longer has to.",
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="promax18plus", qty=1,
                rationale=(
                    "Evaluation sweeps run for hours, so thermal headroom "
                    "is the difference between finishing and throttling."
                ),
            ),
            UseCaseItem(
                category_id="npu", option_id="ai100-dual", qty=1,
                rationale=(
                    "The 64 GB pool holds three models at once, which "
                    "matters more here than holding one enormous one."
                ),
            ),
            UseCaseItem(
                category_id="models", option_id="multi-model", qty=1,
                rationale=(
                    "Generalist, embedding model, and a small router — "
                    "resident together, so switching costs nothing."
                ),
            ),
            UseCaseItem(
                category_id="toolchain", option_id="onnx-compile", qty=1,
                rationale=(
                    "Ahead-of-time compilation fixes the model, which is "
                    "what makes an evaluation run reproducible."
                ),
            ),
            UseCaseItem(
                category_id="host-cpu", option_id="cpu-top", qty=1,
                rationale=(
                    "Chosen for the build, the container stack, and the "
                    "test harness — not for the model."
                ),
            ),
            UseCaseItem(
                category_id="sysmem", option_id="mem-64", qty=1,
                rationale=(
                    "Local services, containers, and datasets alongside "
                    "the agent under development."
                ),
            ),
            UseCaseItem(
                category_id="storage", option_id="ssd-4tb", qty=1,
                rationale=(
                    "A model library with variants adds up fast; keeping "
                    "it off the OS drive makes re-imaging survivable."
                ),
            ),
            UseCaseItem(
                category_id="thermal-power", option_id="sustained-cooling", qty=1,
                rationale=(
                    "The metric that matters is the rate held over an "
                    "hour-long sweep, not a peak figure."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Marginal cost per run", value="Electricity"),
            Stat(label="Rate limits", value="None"),
            Stat(label="Models resident together", value="3"),
            Stat(label="Reproducibility", value="Fixed compiled model"),
        ],
    ),
    UseCase(
        id="disconnected-field",
        title="A field engineer where there is no connectivity at all",
        summary=(
            "Diagnostics, manuals, and technical reasoning on a machine in "
            "a substation, a ship, or a mine — places where the network is "
            "not slow but absent."
        ),
        narrative=[
            "There is a category of work where connectivity is not a "
            "quality-of-service problem but a fact of the environment: "
            "below decks, underground, inside a substation, at a remote "
            "site whose satellite link is reserved for telemetry. The "
            "people doing that work are often the ones with the least "
            "margin for error and the least access to a specialist, which "
            "is precisely the gap an assistant would fill — and precisely "
            "where a hosted one is useless.",
            "On-device inference is not a degraded fallback here; it is "
            "the only architecture that works. Load the model and the "
            "relevant documentation before leaving, and the machine is "
            "self-contained for the duration. The final step of this "
            "twin's trace is exactly this scenario: disconnect the network "
            "and no counter moves, because nothing after model load ever "
            "depended on anything outside the chassis.",
            "This is also where the twin touches the rest of the repo's "
            "edge story. Dell's NativeEdge platform exists to manage "
            "estates of distributed machines that are rarely, briefly, or "
            "unpredictably connected — pushing a validated model out when "
            "a window opens and knowing which build landed where. The "
            "laptop is one endpoint in that estate. Fleet tooling is what "
            "keeps the model on it current without assuming someone can "
            "download sixty gigabytes over a field connection.",
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="promax16plus", qty=1,
                rationale=(
                    "It has to be carried to the site, so the 16-inch "
                    "chassis is the practical ceiling."
                ),
            ),
            UseCaseItem(
                category_id="npu", option_id="ai100-single", qty=1,
                rationale=(
                    "A mid-size model handles diagnostics and manual "
                    "lookup well; the smaller pool keeps cost and draw "
                    "down."
                ),
            ),
            UseCaseItem(
                category_id="models", option_id="dense-mid", qty=1,
                rationale=(
                    "A dense mid-size model with generous KV cache room — "
                    "long manuals matter more here than frontier reasoning."
                ),
            ),
            UseCaseItem(
                category_id="storage", option_id="ssd-2tb", qty=1,
                rationale=(
                    "The model plus the entire documentation corpus, "
                    "because neither can be fetched on site."
                ),
            ),
            UseCaseItem(
                category_id="thermal-power", option_id="adapter", qty=1,
                rationale=(
                    "On battery the model still runs, at a lower held "
                    "wattage — which is the difference between usable and "
                    "not when there is no outlet."
                ),
            ),
            UseCaseItem(
                category_id="accelerators", option_id="igpu-npu", qty=1,
                rationale=(
                    "The integrated NPU handles always-on transcription of "
                    "spoken notes at negligible power."
                ),
            ),
            UseCaseItem(
                category_id="deployment", option_id="fleet", qty=1,
                rationale=(
                    "Knowing which model build is on which field machine, "
                    "and updating it when a connection window opens."
                ),
            ),
            UseCaseItem(
                category_id="toolchain", option_id="ai-studio", qty=1,
                rationale=(
                    "Packaging one validated model for a fleet of field "
                    "laptops is a different job from compiling it once."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Connectivity required on site", value="None"),
            Stat(label="Corpus", value="Model and manuals, resident locally"),
            Stat(label="On battery", value="Runs at reduced sustained wattage"),
            Stat(label="Update path", value="Fleet push when a window opens"),
        ],
    ),
]
