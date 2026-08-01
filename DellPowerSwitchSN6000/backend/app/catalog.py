"""Component catalog: what an SN6000 AI fabric is built from, as data.

Same pattern as the other twins: categories map onto fabric regions via
``region_ids`` (ids from anatomy.py; an empty list means the item is not a
drawn part of the topology — validated designs, services). Written for a
technically skilled reader new to AI networking; jargon (leaf/spine,
incast, RoCE, ECN/PFC, adaptive routing, CPO, SHARP, ...) is spelled out on
first use. Figures come from Dell's SN6000 material and the 2026 AI Factory
announcements, not benchmarks.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

_LEAF_REGIONS = [f"leaf-l{i}" for i in (1, 2, 3, 4)]
_SPINE_REGIONS = [f"spine-s{i}" for i in (1, 2)]
_ENDPOINT_REGIONS = [f"endpoint-e{i}" for i in (1, 2, 3, 4)]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="switch",
        name="Switch platform",
        blurb=(
            "The box itself. In a leaf/spine fabric the same model often "
            "serves both roles — what differs is which ports face down to "
            "endpoints and which face up to spines."
        ),
        limits="Up to 409.6 Tb/s switching capacity; 1.6 Tb/s ports",
        region_ids=_SPINE_REGIONS + _LEAF_REGIONS,
        options=[
            CatalogOption(
                id="sw-sn6000",
                name="Dell PowerSwitch SN6000",
                summary="Spectrum-6 silicon: 1.6 Tb/s ports, up to 2,048 breakout connections.",
                details=(
                    "The SN6000 series is Dell's Spectrum-6-based Ethernet "
                    "switch for AI, announced with the March 2026 AI "
                    "Factory expansion and globally available from July. It "
                    "delivers up to 409.6 Tb/s of switching capacity with "
                    "1.6 Tb/s ports and up to 2,048 breakout connections, "
                    "sized for GPU-cluster scale-out in middle-of-row and "
                    "end-of-row designs, with liquid cooling and "
                    "co-packaged optics as options."
                ),
            ),
            CatalogOption(
                id="sw-quantum",
                name="NVIDIA Quantum-X800 InfiniBand",
                summary="The InfiniBand alternative for sites with HPC heritage.",
                details=(
                    "Dell also offers Quantum-X800 InfiniBand switches for "
                    "clusters that prefer InfiniBand's lossless-by-"
                    "construction fabric and in-network reduction. The "
                    "practical choice is usually cultural as much as "
                    "technical: HPC centres have run InfiniBand for "
                    "decades, while enterprises would rather not staff a "
                    "second network technology alongside the Ethernet they "
                    "already operate everywhere else."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="topology",
        name="Fabric topology",
        blurb=(
            "The shape of the network — which matters more than any single "
            "link, because a collective finishes only when its slowest "
            "participant does."
        ),
        limits="Leaf/spine at or near 1:1 oversubscription for AI",
        region_ids=_SPINE_REGIONS + _LEAF_REGIONS,
        options=[
            CatalogOption(
                id="topo-leafspine",
                name="Leaf/spine (two-tier)",
                summary="Every leaf to every spine: uniform two-hop distance, many equal paths.",
                details=(
                    "The standard AI cluster shape. Leaves hold the "
                    "endpoint ports, spines connect only to leaves, and "
                    "every leaf uplinks to every spine — so any endpoint "
                    "reaches any other in two hops and no pair of ranks is "
                    "structurally disadvantaged. The redundant paths this "
                    "creates are not just failover; they are what adaptive "
                    "routing spreads congested flows onto. Adding a spine "
                    "adds both bandwidth and another path."
                ),
            ),
            CatalogOption(
                id="topo-nonblocking",
                name="Non-blocking (1:1) uplink ratio",
                summary="As much uplink bandwidth as endpoint bandwidth — no built-in choke point.",
                details=(
                    "Oversubscription is the ratio of endpoint bandwidth to "
                    "uplink bandwidth on a leaf. Enterprise networks "
                    "happily run 3:1 or worse because ordinary traffic is "
                    "bursty and uncorrelated. AI traffic is the opposite — "
                    "synchronized and all-to-all — so the design target is "
                    "at or near 1:1. Getting this wrong is expensive and "
                    "quiet: the cluster works, and simply never reaches the "
                    "scaling efficiency it was bought for."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="congestion",
        name="Lossless & congestion control",
        blurb=(
            "The fabric's defining property: it does not drop. Everything "
            "in this category exists to make a full buffer someone's "
            "problem other than the training job's."
        ),
        limits="ECN + PFC + adaptive routing; zero packet loss under incast",
        region_ids=["telemetry"],
        options=[
            CatalogOption(
                id="cong-roce",
                name="RoCE (RDMA over Converged Ethernet)",
                summary="Remote direct memory access on Ethernet — and why loss is intolerable.",
                details=(
                    "RoCE lets one machine read and write another's memory "
                    "directly over Ethernet, bypassing both operating "
                    "systems. It is what makes Ethernet viable for AI — and "
                    "also what makes packet loss so costly, because RDMA's "
                    "recovery from a dropped packet is far more disruptive "
                    "than TCP's. A fabric carrying RoCE must be engineered "
                    "lossless; that requirement drives everything else in "
                    "this category."
                ),
            ),
            CatalogOption(
                id="cong-ecnpfc",
                name="ECN + priority flow control",
                summary="Signal congestion before buffers overflow; pause a class, never drop.",
                details=(
                    "Explicit congestion notification (ECN) marks packets "
                    "as buffers begin to fill so senders slow down "
                    "*before* anything is lost. Priority flow control (PFC) "
                    "is the harder backstop: it pauses one traffic class on "
                    "a link rather than discarding its frames. Tuned "
                    "together they hold the fabric at high utilization "
                    "without loss — the state this twin's congestion step "
                    "shows at 98% on the hot link with the drop counter "
                    "still reading zero."
                ),
            ),
            CatalogOption(
                id="cong-adaptive",
                name="Adaptive routing",
                summary="Spread flows across equal-cost paths using live load, not a static hash.",
                details=(
                    "Conventional Ethernet picks a path per flow by hashing "
                    "header fields, so two heavy flows that hash to the "
                    "same uplink collide for their entire lifetime — and in "
                    "training, a flow's lifetime is the job's. Adaptive "
                    "routing uses live congestion telemetry to move traffic "
                    "onto the alternate paths leaf/spine provides. In this "
                    "twin's reroute step, the hot link falls from 98% to "
                    "71% while total throughput *rises*: the work did not "
                    "shrink, it spread."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="optics",
        name="Optics & cabling",
        blurb=(
            "At 1.6 Tb/s per port, optics become a leading share of the "
            "fabric's power draw and failure rate."
        ),
        limits="Pluggable transceivers or co-packaged optics",
        region_ids=["optics"],
        options=[
            CatalogOption(
                id="opt-cpo",
                name="Co-packaged optics (CPO)",
                summary="Optical engines on the switch package: less power, less signal loss.",
                details=(
                    "CPO moves the optical engine from a pluggable module "
                    "at the faceplate onto the switch package beside the "
                    "silicon, shortening the electrical path the signal "
                    "must survive. The payoff at 1.6 Tb/s is substantial "
                    "power and signal-integrity savings, plus thousands "
                    "fewer pluggable modules to fail across a large "
                    "cluster. The trade is serviceability: an optical fault "
                    "is no longer a module swap."
                ),
            ),
            CatalogOption(
                id="opt-pluggable",
                name="Pluggable transceivers",
                summary="The familiar model: swap a module, keep the switch.",
                details=(
                    "Conventional pluggable optics remain the default where "
                    "operational familiarity matters more than the last "
                    "increment of power efficiency. Failures are repaired "
                    "by walking to the rack with a spare, and the estate is "
                    "not tied to one optical generation. For clusters that "
                    "are large but not enormous, this is still usually the "
                    "right answer."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="endpoint",
        name="Endpoints & adapters",
        blurb=(
            "What the fabric actually serves — and the smart adapters that "
            "make each rack a well-behaved participant."
        ),
        limits="400–800 Gb/s class per endpoint; SuperNIC or DPU",
        region_ids=_ENDPOINT_REGIONS,
        options=[
            CatalogOption(
                id="ep-gpurack",
                name="GPU rack (XE9712 / NVL72)",
                summary="Inside: NVLink at 1.8 TB/s per GPU. Outside: this fabric.",
                details=(
                    "The endpoints are the rack-scale systems from this "
                    "repo's XE9712 twin. The bandwidth cliff at the rack "
                    "wall is the fact that shapes every job placement "
                    "decision: NVLink gives each GPU 1.8 TB/s inside the "
                    "rack, while the scale-out fabric offers roughly an "
                    "order of magnitude less. So tensor-parallel slices "
                    "stay inside a rack and only the calmer data-parallel "
                    "traffic crosses this fabric."
                ),
            ),
            CatalogOption(
                id="ep-supernic",
                name="BlueField / SuperNIC adapters",
                summary="Endpoint-side congestion control, RDMA offload, and telemetry.",
                details=(
                    "Spectrum-X is a system, not just switches: the "
                    "adapters participate. BlueField DPUs and SuperNICs "
                    "implement the endpoint half of congestion control, "
                    "terminate RDMA, and feed the telemetry adaptive "
                    "routing depends on. A fabric whose switches are "
                    "brilliant and whose endpoints ignore congestion "
                    "signals is not a lossless fabric."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="collective",
        name="Collective acceleration",
        blurb=(
            "The traffic pattern that dominates training — and the trick of "
            "doing some of the arithmetic inside the network."
        ),
        limits="In-network reduction where the fabric supports it",
        region_ids=_SPINE_REGIONS,
        options=[
            CatalogOption(
                id="col-sharp",
                name="In-network reduction (SHARP)",
                summary="Switches sum gradients in flight instead of shipping them all.",
                details=(
                    "SHARP performs part of a collective's arithmetic "
                    "inside the switch: rather than every rank sending its "
                    "gradients to every other, the switches sum "
                    "contributions as they pass and distribute the result. "
                    "That cuts both the traffic volume and the number of "
                    "synchronization rounds — an unusually direct case of a "
                    "network doing computation because moving the data is "
                    "more expensive than the arithmetic itself."
                ),
            ),
            CatalogOption(
                id="col-libs",
                name="Collective libraries (NCCL) tuning",
                summary="Topology-aware collectives that keep chatty ranks inside a rack.",
                details=(
                    "The collective library decides which ranks talk to "
                    "which and over what path. Tuned against the actual "
                    "topology, it keeps the heaviest exchanges inside the "
                    "NVLink domain and shapes cross-rack traffic to suit "
                    "the leaf/spine fabric. Much of a cluster's real-world "
                    "scaling efficiency is won or lost here rather than in "
                    "the hardware."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cooling",
        name="Switch cooling",
        blurb=(
            "A reminder that at this capacity the network is another "
            "kilowatt-class heat source, not a quiet accessory."
        ),
        limits="Air or liquid, matched to the row's cooling design",
        region_ids=["cooling"],
        options=[
            CatalogOption(
                id="cool-liquid",
                name="Liquid-cooled SN6000",
                summary="Cold plates on the switch silicon, served by the rack's loop.",
                details=(
                    "Spectrum-6 at full capacity is dense enough to justify "
                    "the same cold-plate treatment the GPUs get, fed by the "
                    "facility loop this repo's IR7000 twin models. Beyond "
                    "the thermal argument, liquid cooling removes the "
                    "switch's fans from the row's acoustic and airflow "
                    "budget — in a fully liquid row, adding an air-cooled "
                    "switch means keeping air handling alive for one box."
                ),
            ),
            CatalogOption(
                id="cool-air",
                name="Air-cooled SN6000",
                summary="Conventional front-to-back airflow for rows that are not liquid-ready.",
                details=(
                    "The conventional option, appropriate where the row is "
                    "air-cooled anyway or where the switch sits in a "
                    "networking rack outside the liquid-cooled compute "
                    "block. Middle-of-row and end-of-row designs often land "
                    "here, since the network racks may be the only "
                    "air-cooled positions left in an otherwise liquid "
                    "facility."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="management",
        name="Fabric management",
        blurb=(
            "At thousands of ports something is always degraded; the goal "
            "is that the job never notices."
        ),
        limits="NOS per switch + fabric-wide validation",
        region_ids=["mgmt"],
        options=[
            CatalogOption(
                id="mgmt-nos",
                name="Network OS (SmartFabric OS10 / SONiC)",
                summary="Disaggregated network operating system on open hardware.",
                details=(
                    "As with the E3200 twin, the switch hardware and its "
                    "operating system are chosen separately: Dell "
                    "SmartFabric OS10 or Enterprise SONiC, the open-source "
                    "NOS that hyperscalers standardized on. For AI fabrics "
                    "SONiC is common, partly because operators want the "
                    "same software across a fleet from multiple hardware "
                    "vendors."
                ),
            ),
            CatalogOption(
                id="mgmt-validation",
                name="Fabric validation & telemetry",
                summary="Continuous topology checks and link health across the cluster.",
                details=(
                    "Fabric-wide management validates that the topology "
                    "matches the design — a miscabled uplink is invisible "
                    "until it silently halves someone's bandwidth — and "
                    "watches per-link error counters to catch a degrading "
                    "optic before it starts corrupting a job. This is where "
                    "'the fabric is fine' becomes a claim someone can "
                    "actually check."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="services",
        name="Design & services",
        blurb=(
            "Fabric design for AI is sized against collective patterns, not "
            "user counts — an unfamiliar exercise for most network teams."
        ),
        limits="Validated designs; deployment and tuning services",
        region_ids=[],
        options=[
            CatalogOption(
                id="svc-validated",
                name="AI Factory validated network designs",
                summary="Pre-tested topology, cabling, and congestion tuning per cluster size.",
                details=(
                    "Dell's AI Factory designs specify the fabric alongside "
                    "the compute and storage: how many spines for a given "
                    "GPU count, cable plans, congestion-control settings, "
                    "and the tuning that keeps collectives efficient. "
                    "Because the components are tested together, the "
                    "cluster's first training run is a configuration "
                    "exercise rather than a networking research project."
                ),
            ),
            CatalogOption(
                id="svc-tuning",
                name="Fabric tuning & scaling services",
                summary="Wringing scaling efficiency out of a cluster that already works.",
                details=(
                    "The characteristic AI-cluster problem is not an outage "
                    "but disappointing scaling — doubling the GPUs yields "
                    "1.6× the throughput, and nobody can say why. Tuning "
                    "engagements profile the collectives, hunt the "
                    "congestion hot spots and rank-placement mistakes, and "
                    "recover the missing efficiency. On a fleet this "
                    "expensive, a few percent pays for the engagement many "
                    "times over."
                ),
            ),
        ],
    ),
]
