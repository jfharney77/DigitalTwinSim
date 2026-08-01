"""Worked use cases: what an SN6000 AI fabric actually gets built for.

Each use case is a narrative plus a build sheet whose category/option ids
must resolve against catalog.py (enforced in tests/test_catalog.py).
Written for a technically skilled reader new to AI networking. Quantities
count the unit named (switches, adapters, designs).
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="trainingcluster",
        title="Scale-out fabric for an eight-rack training cluster",
        summary=(
            "576 GPUs across eight NVL72 racks joined by a non-blocking "
            "leaf/spine fabric — the network that decides whether eight "
            "racks behave like eight racks or like one computer."
        ),
        narrative=[
            (
                "The workload: the eight-rack GB200 NVL72 cluster from the "
                "XE9712 twin, training one model for weeks. Inside each "
                "rack, NVLink already fuses 72 GPUs into a single domain at "
                "1.8 TB/s per GPU. The fabric's job begins at the rack "
                "wall, where available bandwidth drops by roughly an order "
                "of magnitude — and every training step ends with an "
                "all-reduce that must cross it before the next step can "
                "start. The fabric does not make the cluster fast; it "
                "determines how much of the GPUs' speed survives being "
                "spread across eight racks."
            ),
            (
                "The design: a non-blocking leaf/spine fabric of SN6000 "
                "switches — as much uplink bandwidth as endpoint bandwidth, "
                "because AI traffic is synchronized rather than bursty and "
                "any oversubscription becomes a permanent tax on every "
                "step. Spectrum-X congestion control and adaptive routing "
                "handle the incast that collectives produce, and SuperNIC "
                "adapters implement the endpoint half so senders actually "
                "respond to congestion signals. In-network reduction sums "
                "gradients inside the switches, cutting both traffic volume "
                "and synchronization rounds."
            ),
            (
                "Job placement is designed with the fabric, not after it: "
                "tensor-parallel slices — the chattiest communication — "
                "stay inside a rack's NVLink domain, and only data-parallel "
                "traffic crosses the fabric. Get that mapping wrong and no "
                "amount of switch capacity rescues the cluster's scaling "
                "efficiency."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="switch", option_id="sw-sn6000", qty=10,
                rationale="Eight leaves plus two spines: Spectrum-6 at 1.6 Tb/s per port.",
            ),
            UseCaseItem(
                category_id="topology", option_id="topo-nonblocking", qty=1,
                rationale=(
                    "Synchronized AI traffic makes any oversubscription a "
                    "tax on every training step."
                ),
            ),
            UseCaseItem(
                category_id="congestion", option_id="cong-adaptive", qty=1,
                rationale="Spreads colliding flows instead of pinning them for the job's life.",
            ),
            UseCaseItem(
                category_id="endpoint", option_id="ep-supernic", qty=8,
                rationale="Endpoints must honor congestion signals or the fabric is not lossless.",
            ),
            UseCaseItem(
                category_id="collective", option_id="col-sharp", qty=1,
                rationale="Summing gradients in the switches cuts traffic and sync rounds.",
            ),
            UseCaseItem(
                category_id="optics", option_id="opt-cpo", qty=1,
                rationale="At 1.6 Tb/s, co-packaged optics save real power and failure surface.",
            ),
            UseCaseItem(
                category_id="services", option_id="svc-validated", qty=1,
                rationale="Topology, cabling, and congestion tuning tested before delivery.",
            ),
        ],
        outcomes=[
            Stat(label="GPUs joined", value="576 across 8 NVL72 racks"),
            Stat(label="Path length", value="Two hops, any endpoint pair"),
            Stat(label="Packet loss", value="Zero, including under incast"),
            Stat(label="Oversubscription", value="1:1 — non-blocking"),
        ],
    ),
    UseCase(
        id="storagefabric",
        title="Storage fabric for a parallel file system",
        summary=(
            "The Exascale rack's fan-out reads are incast by construction — "
            "many data servers answering one client at once. This is the "
            "fabric that absorbs it."
        ),
        narrative=[
            (
                "The workload: the Lightning parallel file system from this "
                "repo's Exascale twin, feeding GPU racks at roughly 6 TB/s. "
                "The traffic pattern is unusual and unforgiving. When a "
                "client holds a layout and pulls its stripes, it opens "
                "simultaneous streams to *every* data server holding part "
                "of the file — so many senders converge on one receiver's "
                "switch port at the same instant. That is textbook incast, "
                "and it is not an edge case here; it is how every single "
                "read works."
            ),
            (
                "The design: a lossless fabric is non-negotiable because "
                "the storage path runs RDMA, whose recovery from a dropped "
                "packet is far more disruptive than TCP's. ECN marks "
                "packets as buffers fill so the data servers throttle "
                "before anything is lost, and priority flow control pauses "
                "the storage traffic class rather than discarding it. "
                "Checkpoints invert the pattern — thousands of GPUs writing "
                "simultaneously — so the fabric must absorb bursts in both "
                "directions."
            ),
            (
                "Air-cooled switches are chosen here deliberately: the "
                "storage fabric lives in networking racks at the end of the "
                "row rather than inside the liquid-cooled compute block, so "
                "there is no loop to tap. It is a small reminder that "
                "cooling design and network placement are decided together, "
                "and the storage network is often where the last air-cooled "
                "positions in a facility end up."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="switch", option_id="sw-sn6000", qty=6,
                rationale="Four leaves plus two spines serving the storage rack and clients.",
            ),
            UseCaseItem(
                category_id="congestion", option_id="cong-roce", qty=1,
                rationale="The storage path is RDMA; loss recovery here is brutal.",
            ),
            UseCaseItem(
                category_id="congestion", option_id="cong-ecnpfc", qty=1,
                rationale="Fan-out reads are incast on every request — signal, don't drop.",
            ),
            UseCaseItem(
                category_id="topology", option_id="topo-leafspine", qty=1,
                rationale="Uniform two-hop distance from any client to any data server.",
            ),
            UseCaseItem(
                category_id="optics", option_id="opt-pluggable", qty=1,
                rationale="Familiar module-swap serviceability for a mid-size fabric.",
            ),
            UseCaseItem(
                category_id="cooling", option_id="cool-air", qty=1,
                rationale="Network racks sit outside the liquid-cooled compute block.",
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-validation", qty=1,
                rationale="A miscabled uplink silently halves someone's read bandwidth.",
            ),
        ],
        outcomes=[
            Stat(label="Storage bandwidth carried", value="~6 TB/s to the GPU fleet"),
            Stat(label="Incast handling", value="ECN + PFC; zero drops"),
            Stat(label="Checkpoint bursts", value="Absorbed in both directions"),
            Stat(label="Pairs with", value="The Exascale + Lightning twin"),
        ],
    ),
    UseCase(
        id="multitenant",
        title="Multi-tenant AI cloud fabric",
        summary=(
            "A service provider rents GPU capacity by the hour: the fabric "
            "must isolate tenants from each other's traffic while keeping "
            "every tenant's collectives fast."
        ),
        narrative=[
            (
                "The workload: a provider selling GPU capacity to many "
                "customers at once, some training, some serving, some just "
                "experimenting. The fabric problem is different from a "
                "single-tenant cluster. One tenant's checkpoint burst must "
                "not slow another tenant's inference latency, tenants must "
                "not be able to observe or reach each other's traffic, and "
                "the whole thing must still deliver near-dedicated "
                "collective performance to whoever is training."
            ),
            (
                "The design: SONiC as the network OS, because the provider "
                "wants one software stack across hardware from several "
                "vendors and the ability to patch on its own schedule. "
                "BlueField DPUs at every endpoint form the tenancy boundary "
                "— isolation enforced below any tenant's operating system, "
                "where a compromised guest cannot reach it — and they carry "
                "the endpoint half of congestion control so no tenant can "
                "opt out of being well-behaved. Adaptive routing keeps one "
                "tenant's heavy flow from monopolizing an uplink that "
                "another tenant's traffic hashes onto."
            ),
            (
                "Liquid-cooled switches suit a purpose-built facility where "
                "the whole row is liquid anyway, and continuous fabric "
                "validation matters more than usual: the provider's "
                "customers cannot see the network, so the provider must be "
                "able to prove the fabric is healthy when a tenant reports "
                "that their job got slower."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="switch", option_id="sw-sn6000", qty=14,
                rationale="A larger leaf/spine fabric spanning multiple tenant pods.",
            ),
            UseCaseItem(
                category_id="endpoint", option_id="ep-supernic", qty=32,
                rationale="DPUs are the tenancy boundary, below any tenant's OS.",
            ),
            UseCaseItem(
                category_id="management", option_id="mgmt-nos", qty=1,
                rationale="SONiC gives one software stack across mixed hardware.",
            ),
            UseCaseItem(
                category_id="congestion", option_id="cong-adaptive", qty=1,
                rationale="Stops one tenant's heavy flow from owning a shared uplink.",
            ),
            UseCaseItem(
                category_id="collective", option_id="col-libs", qty=1,
                rationale="Topology-aware collectives so each tenant scales near-dedicated.",
            ),
            UseCaseItem(
                category_id="cooling", option_id="cool-liquid", qty=1,
                rationale="Purpose-built liquid row; no reason to keep air handling for switches.",
            ),
            UseCaseItem(
                category_id="services", option_id="svc-tuning", qty=1,
                rationale=(
                    "Recovering scaling efficiency is the provider's "
                    "margin, and its answer to 'why was my job slow?'"
                ),
            ),
        ],
        outcomes=[
            Stat(label="Tenant isolation", value="DPU-enforced, below the guest OS"),
            Stat(label="Noisy neighbors", value="Contained by adaptive routing"),
            Stat(label="Software stack", value="One NOS across mixed hardware"),
            Stat(label="Provable health", value="Continuous fabric validation"),
        ],
    ),
]
