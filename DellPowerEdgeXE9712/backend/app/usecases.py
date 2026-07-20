"""Worked use cases: what XE9712 racks actually get deployed for.

Each use case is a narrative plus a build sheet whose category/option ids
must resolve against catalog.py (enforced in tests/test_catalog.py).
Written for a technically skilled reader new to rack-scale AI. Quantities
are per deployment — note that unlike the single-box twins, a quantity here
is often "racks", because the rack is the unit this product is counted in.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="training",
        title="Foundation-model training",
        summary=(
            "Eight GB200 NVL72 racks joined by InfiniBand into one training "
            "computer: 576 GPUs, PowerScale streaming the corpus and "
            "swallowing checkpoints, Mission Control babysitting a job that "
            "runs for weeks."
        ),
        narrative=[
            (
                "The workload: pre-train a large language model — hundreds "
                "of billions of parameters — on trillions of tokens. The "
                "job is one enormous synchronized computation: every GPU "
                "holds a shard of the model, every training step ends with "
                "all of them exchanging gradients, and the run lasts weeks. "
                "Two things dominate the design: the model must be sliced "
                "across GPUs connected by the fastest links available, and "
                "nothing — not a failed GPU, not a slow switch port — may "
                "stall the whole fleet."
            ),
            (
                "Why the XE9712 fits: model slicing loves the NVL72 domain. "
                "The tensor-parallel slices that communicate most "
                "intensively stay inside a rack's NVLink fabric at 1.8 TB/s "
                "per GPU, and only the calmer data-parallel traffic crosses "
                "racks over InfiniBand. Eight racks give 576 Blackwell "
                "GPUs; Quantum InfiniBand with in-network reduction sums "
                "gradients inside the switches so the all-reduce that ends "
                "every step scales with the fleet. PowerScale does double "
                "duty — streaming the training corpus in and absorbing "
                "multi-terabyte checkpoints without pausing the run longer "
                "than necessary."
            ),
            (
                "Operations is the hidden half. At this scale something is "
                "always failing, so Mission Control and the BMC/OpenManage "
                "plane watch every GPU, link, and cold plate; a sick tray "
                "is drained, its work is redistributed, and the job resumes "
                "from the last checkpoint rather than dying. The racks "
                "arrive factory-integrated under IRSS because a 5,000-cable "
                "NVLink cartridge is not something anyone wants to build on "
                "a raised floor."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="plat-gb200", qty=8,
                rationale=(
                    "Eight NVL72 racks = 576 GPUs — enough tensor and data "
                    "parallelism to train a frontier-class model in weeks, "
                    "not quarters."
                ),
            ),
            UseCaseItem(
                category_id="tray", option_id="tray-gb200", qty=144,
                rationale="18 trays per rack × 8 racks; all identical, all interchangeable.",
            ),
            UseCaseItem(
                category_id="nvlink", option_id="nvl-switchtray", qty=72,
                rationale=(
                    "9 switch trays per rack keep the hottest traffic — "
                    "tensor-parallel exchange — on NVLink, off the "
                    "inter-rack network."
                ),
            ),
            UseCaseItem(
                category_id="scaleout", option_id="net-quantum", qty=8,
                rationale=(
                    "InfiniBand with in-network reduction (SHARP) so the "
                    "per-step gradient all-reduce scales across racks."
                ),
            ),
            UseCaseItem(
                category_id="storage", option_id="stor-powerscale", qty=1,
                rationale=(
                    "One namespace that streams the corpus and takes "
                    "multi-TB checkpoints; checkpoint bandwidth sets how "
                    "much work a failure can destroy."
                ),
            ),
            UseCaseItem(
                category_id="cooling", option_id="cool-rcdu", qty=8,
                rationale="One in-rack CDU per rack; ~120 kW each must leave through water.",
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-mission", qty=1,
                rationale=(
                    "Weeks-long jobs survive on automated health checks, "
                    "drain-and-replace, and checkpoint/restart."
                ),
            ),
            UseCaseItem(
                category_id="deployment", option_id="dep-irss", qty=8,
                rationale="Racks arrive built, cabled, and burn-tested — bring-up in days.",
            ),
        ],
        outcomes=[
            Stat(label="GPUs in the job", value="576 Blackwell (8 × NVL72)"),
            Stat(label="Scale-up fabric", value="NVLink · 1.8 TB/s per GPU in-rack"),
            Stat(label="Scale-out fabric", value="Quantum InfiniBand + SHARP"),
            Stat(label="Power envelope", value="~1 MW for the compute rows"),
        ],
    ),
    UseCase(
        id="inference",
        title="Real-time trillion-parameter inference",
        summary=(
            "A GB300 NVL72 rack serving a reasoning model as an API: the "
            "whole model lives inside one NVLink domain, NIM microservices "
            "make it an endpoint, and Spectrum-X Ethernet fits the rack "
            "into an ordinary data center."
        ),
        narrative=[
            (
                "The workload: serve a very large 'reasoning' model — one "
                "that thinks in long token chains before answering — to "
                "thousands of concurrent users with interactive latency. "
                "Inference at this size has a brutal constraint: if the "
                "model does not fit in fast memory on one fabric, every "
                "token pays a tax crossing between servers, and real-time "
                "service becomes impossible."
            ),
            (
                "Why the XE9712 fits: the fused domain *is* the feature. "
                "With 72 Blackwell Ultra GPUs pooling roughly 20 TB of "
                "HBM3e behind a single NVLink fabric, the entire model plus "
                "its key-value caches lives inside one rack — this is the "
                "configuration behind the '30× real-time trillion-"
                "parameter inference' claim. GB300 is chosen over GB200 "
                "precisely because reasoning workloads spend their compute "
                "at serving time. NIM microservices wrap the domain into "
                "versioned model endpoints, and Spectrum-X Ethernet — "
                "rather than InfiniBand — carries user traffic, because "
                "the enterprise already runs Ethernet everywhere else."
            ),
            (
                "The BlueField DPUs earn their place in serving: they "
                "terminate TLS, isolate tenants, and stream token "
                "telemetry, so the Grace CPUs and GPUs do nothing but run "
                "the model. Capacity grows a rack at a time — each new "
                "rack is another complete replica of the model."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="plat-gb300", qty=1,
                rationale=(
                    "Blackwell Ultra's extra HBM holds the model and its "
                    "KV-caches in one domain — the whole point of serving "
                    "from an NVL72."
                ),
            ),
            UseCaseItem(
                category_id="gpu", option_id="gpu-b300", qty=72,
                rationale="Inference-heavy refresh: more memory and low-precision throughput per GPU.",
            ),
            UseCaseItem(
                category_id="scaleout", option_id="net-spectrumx", qty=1,
                rationale=(
                    "AI-tuned Ethernet lets the rack join the enterprise "
                    "network without an InfiniBand island."
                ),
            ),
            UseCaseItem(
                category_id="scaleout", option_id="net-bluefield", qty=18,
                rationale=(
                    "DPUs terminate TLS and isolate tenants so hosts spend "
                    "zero cycles on plumbing."
                ),
            ),
            UseCaseItem(
                category_id="software", option_id="sw-nvai", qty=1,
                rationale=(
                    "NIM turns the fused domain into versioned, autoscaled "
                    "model endpoints an app team can consume."
                ),
            ),
            UseCaseItem(
                category_id="cooling", option_id="cool-erdhx", qty=1,
                rationale=(
                    "The rear-door heat exchanger catches the air-cooled "
                    "remainder, so one dense rack drops into an ordinary "
                    "room."
                ),
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-idrac", qty=1,
                rationale="OpenManage folds the rack into the existing PowerEdge fleet view.",
            ),
        ],
        outcomes=[
            Stat(label="Model residency", value="Whole model in one NVLink domain"),
            Stat(label="Claimed speedup", value="Up to 30× real-time LLM inference"),
            Stat(label="Serving surface", value="NIM endpoints over Spectrum-X"),
            Stat(label="Growth unit", value="One rack = one more model replica"),
        ],
    ),
    UseCase(
        id="sovereign",
        title="Sovereign AI factory",
        summary=(
            "A national or regulated-industry AI cloud: GB200 racks, "
            "ObjectScale holding the data estate in-country, DPU-enforced "
            "tenant isolation, and Dell delivering the whole thing as a "
            "turnkey factory."
        ),
        narrative=[
            (
                "The workload: a government, telecom, or regulated "
                "enterprise wants frontier-class AI capacity that never "
                "leaves its jurisdiction — training on national data, "
                "serving public services, renting spare capacity to local "
                "industry. The constraints are less about peak FLOPS and "
                "more about custody: data residency, tenant isolation, "
                "auditable operations, and independence from any public "
                "cloud."
            ),
            (
                "Why the XE9712 fits: sovereignty needs a vendor who can "
                "deliver the *whole* factory — compute, fabric, storage, "
                "power, liquid cooling, and the operating model — inside "
                "the border, which is precisely what the Dell AI Factory "
                "program packages. GB200 NVL72 racks provide the capacity; "
                "ObjectScale keeps the multi-petabyte national data estate "
                "on S3 inside the facility; BlueField DPUs enforce "
                "isolation between ministries or tenant companies at the "
                "network line rate, below the host operating system where "
                "a compromised tenant cannot reach."
            ),
            (
                "Dell's services matter most here: few sovereign operators "
                "have ever run 120 kW liquid-cooled racks, so facility "
                "readiness, bring-up, and residencies transfer the skills "
                "along with the hardware. Mission Control gives the "
                "operator one pane for fleet health and power steering — "
                "and the whole estate, being an AI factory rather than a "
                "cloud region, is inventoried, powered, and audited as "
                "national infrastructure."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="platform", option_id="plat-gb200", qty=4,
                rationale=(
                    "A starter sovereign pod: enough for national-language "
                    "model training and public-sector serving, growable "
                    "rack by rack."
                ),
            ),
            UseCaseItem(
                category_id="storage", option_id="stor-objectscale", qty=1,
                rationale=(
                    "The data estate stays in-country on S3 — the corpus, "
                    "models, and logs never touch a foreign cloud."
                ),
            ),
            UseCaseItem(
                category_id="scaleout", option_id="net-spectrumx", qty=1,
                rationale="Ethernet end to end keeps the national operator's skills relevant.",
            ),
            UseCaseItem(
                category_id="scaleout", option_id="net-bluefield", qty=72,
                rationale=(
                    "Per-tray DPUs are the tenancy boundary — isolation "
                    "enforced below any tenant's OS."
                ),
            ),
            UseCaseItem(
                category_id="software", option_id="sw-aifactory", qty=1,
                rationale=(
                    "Validated designs mean the pod is an audited, "
                    "supportable configuration, not a bespoke science "
                    "project."
                ),
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-mission", qty=1,
                rationale="One operational pane for fleet health, capacity, and power steering.",
            ),
            UseCaseItem(
                category_id="deployment", option_id="dep-services", qty=1,
                rationale=(
                    "Facility readiness and residencies transfer AI-factory "
                    "operating skills to the sovereign operator."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Data custody", value="Corpus, models, logs all in-country"),
            Stat(label="Tenant isolation", value="DPU-enforced, below the host OS"),
            Stat(label="Capacity", value="288 GPUs, growable rack by rack"),
            Stat(label="Operating model", value="Turnkey AI factory + skills transfer"),
        ],
    ),
]
