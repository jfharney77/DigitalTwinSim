"""Component catalog: what you actually choose when you build a PowerFlex
pool, as backend data.

Written for a technically skilled reader new to software-defined storage:
SDS, SDC, metadata manager, mesh mirroring, erasure coding, fault sets, and
two-layer versus hyperconverged are all spelled out on first use.
Categories map to the pool regions in ``anatomy.py`` via ``region_ids``, and
``tests/test_catalog.py`` enforces that every id resolves.

The ordering says something. There is no "controller" category, because
there is no controller — the second category is the *deployment topology*,
which is the decision a traditional array never lets you make: whether the
servers holding the storage are also the servers using it.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="nodes",
        name="Storage nodes",
        blurb=(
            "The servers that make up the pool. Every one is identical in "
            "role, which is what makes the scaling arithmetic simple."
        ),
        limits="3 to 2,000+ nodes; up to 240 million IOPS",
        region_ids=["node-1", "node-2", "node-3", "node-4", "node-5", "node-6"],
        options=[
            CatalogOption(
                id="pflex-appliance",
                name="PowerFlex appliance nodes",
                summary=(
                    "Dell-built, Dell-validated nodes with the lifecycle "
                    "managed as one system."
                ),
                details=(
                    "PowerEdge servers assembled and validated as pool "
                    "members, with firmware, drivers, and PowerFlex "
                    "software versioned together. The reason this matters "
                    "more here than in a normal server purchase is that "
                    "the storage system is now made of servers, so a "
                    "firmware mismatch on one node is a storage problem "
                    "rather than a server problem. Buying the validated "
                    "combination is buying somebody else's compatibility "
                    "matrix."
                ),
            ),
            CatalogOption(
                id="pflex-rack",
                name="PowerFlex rack",
                summary=(
                    "The whole rack — nodes, switches, and cabling — "
                    "delivered integrated."
                ),
                details=(
                    "For deployments large enough that the network is a "
                    "serious design exercise in its own right. Because the "
                    "pool runs over IP, the switching is part of the "
                    "storage system's performance envelope, and having it "
                    "designed and cabled at the factory removes the most "
                    "common way a first PowerFlex deployment disappoints "
                    "people — an under-provisioned fabric being blamed on "
                    "the storage."
                ),
            ),
            CatalogOption(
                id="pflex-software",
                name="Software on your own servers",
                summary=(
                    "Bring your own hardware; the pool is software all the "
                    "way down."
                ),
                details=(
                    "The purest expression of the idea: the product is the "
                    "software, and any suitable x86 servers with local "
                    "NVMe can be pool members. This is the right choice "
                    "when there is an existing standard server platform "
                    "worth staying on, and the wrong one when nobody wants "
                    "to own the compatibility matrix. Mixed node sizes are "
                    "supported — the software balances chunks by capacity "
                    "— but wildly uneven nodes make the balancing less "
                    "even."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="topology",
        name="Deployment topology",
        blurb=(
            "Whether the servers holding the storage are also the servers "
            "using it — a choice a traditional array cannot offer."
        ),
        limits="Two-layer, hyperconverged, or mixed within one pool",
        region_ids=["node-1", "clients"],
        options=[
            CatalogOption(
                id="two-layer",
                name="Two-layer",
                summary=(
                    "Storage nodes and compute nodes are separate, so each "
                    "scales on its own."
                ),
                details=(
                    "Storage servers do nothing but storage; application "
                    "servers run the client and consume volumes. The "
                    "advantage is independent scaling — add capacity "
                    "without buying application licences, add compute "
                    "without buying drives — and predictable performance, "
                    "since no application can steal cycles from the "
                    "storage path. This is the configuration most large "
                    "deployments settle on, and it is what this twin's "
                    "trace depicts."
                ),
            ),
            CatalogOption(
                id="hci",
                name="Hyperconverged",
                summary=(
                    "Every server both stores and computes — the densest "
                    "option."
                ),
                details=(
                    "Each node runs applications and contributes storage. "
                    "Fewer boxes, less rack space, lower entry cost. The "
                    "trade is contention: a noisy application affects the "
                    "storage its neighbours are reading. This repo's "
                    "VxRail twin is a full treatment of the "
                    "hyperconverged model with VMware's vSAN; PowerFlex "
                    "differs in that it can be hyperconverged *and* "
                    "two-layer in the same pool, which vSAN cannot."
                ),
            ),
            CatalogOption(
                id="mixed",
                name="Mixed in one pool",
                summary=(
                    "Some nodes converged, some dedicated — one pool "
                    "either way."
                ),
                details=(
                    "The option that quietly justifies the architecture. "
                    "Because there is no controller defining the system's "
                    "shape, the shape is free to be inconsistent: a few "
                    "hyperconverged nodes for one workload, a block of "
                    "dedicated storage nodes for another, one namespace "
                    "across both. Estates arrive at this by evolution far "
                    "more often than by design, and an architecture that "
                    "tolerates it saves a migration."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="protection",
        name="Data protection",
        blurb=(
            "How the pool survives losing hardware, and what that costs in "
            "capacity."
        ),
        limits="Mesh mirroring or erasure coding; fault sets for failure domains",
        region_ids=["protection"],
        options=[
            CatalogOption(
                id="mesh-mirror",
                name="Mesh mirroring",
                summary=(
                    "Two copies of every chunk, scattered so that every "
                    "node is a rebuild partner."
                ),
                details=(
                    "The classic PowerFlex protection scheme. Each chunk "
                    "exists twice, on different nodes, and the placement "
                    "is deliberately spread rather than paired — node 1 is "
                    "not the mirror of node 2. That distinction is what "
                    "produces the many-to-many rebuild: when a node dies, "
                    "its data is recoverable from *all* the survivors "
                    "rather than from one partner, so all of them rebuild "
                    "simultaneously. The cost is half the raw capacity, "
                    "which is the price of the fastest recovery."
                ),
            ),
            CatalogOption(
                id="erasure-coding",
                name="Erasure coding",
                summary=(
                    "Parity instead of a second copy — far less capacity "
                    "overhead for comparable protection."
                ),
                details=(
                    "Rather than storing a whole duplicate, the software "
                    "stores mathematical parity from which a lost fragment "
                    "can be reconstructed. Capacity overhead falls "
                    "dramatically compared with mirroring. The trade is "
                    "computation: a rebuild has to calculate the missing "
                    "data rather than copy it, and writes incur parity "
                    "work. The 5.0 Ultra release pairs this with a "
                    "scalable availability engine, which is the part that "
                    "keeps the many-to-many rebuild property intact rather "
                    "than trading it away for the capacity saving."
                ),
            ),
            CatalogOption(
                id="fault-sets",
                name="Fault sets",
                summary=(
                    "Telling the software which nodes share a rack, a "
                    "switch, or a power feed."
                ),
                details=(
                    "Scattering copies across nodes is only protection if "
                    "the nodes fail independently, and they often do not — "
                    "a rack loses power, a switch dies, a whole row goes "
                    "down. A fault set declares that a group of nodes "
                    "shares a fate, and the software then refuses to place "
                    "both copies of anything inside one. This is the "
                    "single most commonly skipped configuration step, and "
                    "the one whose absence is discovered at the worst "
                    "possible moment."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="fabric",
        name="Network fabric",
        blurb=(
            "The pool runs over ordinary IP — which makes the network part "
            "of the storage design."
        ),
        limits="25/100 GbE typical; no dedicated storage-area network required",
        region_ids=["fabric"],
        options=[
            CatalogOption(
                id="eth-25",
                name="25 GbE",
                summary=(
                    "The practical baseline for a general-purpose pool."
                ),
                details=(
                    "Every read that a client issues crosses the fabric, "
                    "and so does every fragment moved during a rebuild. "
                    "Undersize the network and the storage will be blamed "
                    "for it. Redundant links matter as much as raw speed: "
                    "a node that is alive but unreachable looks exactly "
                    "like a dead one to the metadata manager, and will be "
                    "treated as such."
                ),
            ),
            CatalogOption(
                id="eth-100",
                name="100 GbE and above",
                summary=(
                    "For dense all-NVMe nodes, where the drives can "
                    "outrun a smaller pipe."
                ),
                details=(
                    "Modern NVMe nodes are quite capable of saturating "
                    "25 GbE from a handful of drives, at which point the "
                    "network is the pool's ceiling rather than the media. "
                    "The other reason to go faster is rebuild: recovery "
                    "speed is bounded by how quickly survivors can shuttle "
                    "fragments to each other, so the fabric is a "
                    "resilience decision as much as a performance one."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="clients",
        name="Client access",
        blurb=(
            "How consuming servers see pool volumes — as ordinary block "
            "devices, addressed directly."
        ),
        limits="Block volumes; the client holds the chunk map",
        region_ids=["clients"],
        options=[
            CatalogOption(
                id="sdc",
                name="Storage data client",
                summary=(
                    "A lightweight driver that turns pool volumes into "
                    "local block devices."
                ),
                details=(
                    "The client holds the map of which nodes hold which "
                    "chunks, so it sends each request straight to a server "
                    "that can answer it. Nothing is forwarded, and there "
                    "is no target device whose queue everyone shares. This "
                    "is the mechanical reason the architecture has no "
                    "controller bottleneck — not that the controller is "
                    "fast, but that the client never talks to one."
                ),
            ),
            CatalogOption(
                id="nvme-tcp",
                name="Standards-based access (NVMe/TCP)",
                summary=(
                    "For hosts that cannot or should not run a vendor "
                    "driver."
                ),
                details=(
                    "Standard protocol access lets hosts consume volumes "
                    "without installing anything PowerFlex-specific, which "
                    "matters for appliances, locked-down platforms, and "
                    "anything whose support contract forbids third-party "
                    "kernel modules. The trade is that a standards-based "
                    "client does not hold the full chunk map, so it "
                    "reaches the pool through a gateway rather than "
                    "addressing every node directly — some of the "
                    "architecture's directness is given back in exchange "
                    "for compatibility."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="coordinator",
        name="Metadata management",
        blurb=(
            "The referee: chunk placement, cluster membership, and failure "
            "decisions. Not a data path."
        ),
        limits="Redundant metadata managers; no client data traverses them",
        region_ids=["mdm"],
        options=[
            CatalogOption(
                id="mdm-cluster",
                name="Redundant metadata managers",
                summary=(
                    "Several managers with a quorum, so the referee is "
                    "never a single point of failure."
                ),
                details=(
                    "The metadata manager decides where chunks live and "
                    "what to do when a node stops answering. It is "
                    "deployed redundantly with a voting quorum, for the "
                    "familiar reason that a referee who disappears leaves "
                    "the cluster unable to agree on who is alive. What it "
                    "is not is a controller: no read passes through it, no "
                    "write waits on it, and its throughput appears in "
                    "nobody's sizing calculation. Keeping those two roles "
                    "distinct in your head is most of understanding this "
                    "architecture."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="services",
        name="Data services",
        blurb=(
            "Snapshots, replication, and reduction — included rather than "
            "licensed separately."
        ),
        limits="All-inclusive licensing; massive snapshot capacity in 5.0 Ultra",
        region_ids=["protection", "mgmt"],
        options=[
            CatalogOption(
                id="snapshots",
                name="Snapshots",
                summary=(
                    "Point-in-time copies, at a scale that makes them a "
                    "routine tool rather than a rationed one."
                ),
                details=(
                    "Snapshot capacity in the 5.0 Ultra release is large "
                    "enough that snapshots stop being something to budget "
                    "for and become something to take casually — before "
                    "every deployment, on every test database, hourly on "
                    "anything that matters. The behavioural change that "
                    "unlocks is worth more than the feature: teams take "
                    "risks they would otherwise avoid when rolling back is "
                    "free and instant."
                ),
            ),
            CatalogOption(
                id="replication",
                name="Native replication",
                summary=(
                    "Asynchronous replication between pools for disaster "
                    "recovery."
                ),
                details=(
                    "Volume-level replication to a second pool, typically "
                    "at another site. Pair it with this repo's "
                    "PowerProtect twin for the distinction that matters: "
                    "replication protects against a site being destroyed, "
                    "and an immutable vault protects against a site being "
                    "*corrupted*. Replication faithfully copies ransomware "
                    "to your disaster-recovery site, which is why it is "
                    "not a backup."
                ),
            ),
            CatalogOption(
                id="reduction",
                name="Data reduction and encryption",
                summary=(
                    "Inline reduction and hardware-based encryption at "
                    "rest."
                ),
                details=(
                    "Compression reduces what is stored; hardware-based "
                    "encryption protects it at rest without a measurable "
                    "performance cost, since the work happens in the drive "
                    "controller. Both are included in the licensing rather "
                    "than sold as tiers, which removes the usual awkward "
                    "conversation about whether encryption is worth paying "
                    "extra for."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="lifecycle",
        name="Lifecycle and operations",
        blurb=(
            "Growing, shrinking, and refreshing a pool without an outage — "
            "the operation this architecture is unusually good at."
        ),
        limits="Non-disruptive add, rebalance, and remove",
        region_ids=["mgmt"],
        options=[
            CatalogOption(
                id="rebalance",
                name="Non-disruptive expansion and refresh",
                summary=(
                    "Add nodes, let the pool rebalance, remove the old "
                    "ones — hosts never notice."
                ),
                details=(
                    "Because capacity is chunks distributed over "
                    "interchangeable servers, growing the pool is adding "
                    "servers and letting the software redistribute onto "
                    "them. The same mechanism runs in reverse, which makes "
                    "a hardware refresh into a background task rather than "
                    "a migration project: add the new generation, "
                    "rebalance, retire the old, without hosts seeing so "
                    "much as a dropped path. On a controller array the "
                    "equivalent is a data migration with a maintenance "
                    "window."
                ),
            ),
            CatalogOption(
                id="observability",
                name="Telemetry and AIOps",
                summary=(
                    "Watching a system made of two thousand "
                    "interchangeable parts."
                ),
                details=(
                    "The flip side of uniformity is that no single node's "
                    "health is dramatic enough to notice by hand. A "
                    "slowly-failing drive in one node of two thousand "
                    "shows up as a faint statistical anomaly, which is "
                    "exactly the shape of problem this repo's CloudIQ twin "
                    "exists to catch. Fleet-scale observability is not an "
                    "add-on to this architecture; it is how you have any "
                    "idea what is happening in it."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="integration",
        name="Platform integration",
        blurb=(
            "What consumes the pool: hypervisors, container platforms, "
            "databases, and the AI rack."
        ),
        limits="Block storage for virtualized, containerized, and bare-metal hosts",
        region_ids=["clients"],
        options=[
            CatalogOption(
                id="virt",
                name="Virtualization and containers",
                summary=(
                    "Persistent volumes for hypervisors and Kubernetes."
                ),
                details=(
                    "The mainstream case: shared block storage for virtual "
                    "machines and container persistent volumes, with the "
                    "advantage over hyperconverged alternatives that "
                    "storage and compute scale separately. For platform "
                    "teams the practical draw is that adding storage does "
                    "not mean adding hypervisor licences."
                ),
            ),
            CatalogOption(
                id="databases",
                name="Databases and latency-sensitive workloads",
                summary=(
                    "Consistent low latency, including while the pool is "
                    "rebuilding."
                ),
                details=(
                    "Databases care less about peak throughput than about "
                    "the shape of the tail — the slowest one percent of "
                    "operations. The relevant property here is that "
                    "failure and rebuild produce a proportional dip rather "
                    "than a failover pause, so the worst case during a "
                    "hardware loss is a somewhat slower system rather than "
                    "a briefly frozen one."
                ),
            ),
            CatalogOption(
                id="ai-rack",
                name="Block tier of the Exascale rack",
                summary=(
                    "PowerFlex is the block layer in Dell's unified AI "
                    "storage rack."
                ),
                details=(
                    "Dell's Exascale rack architecture — twinned "
                    "separately in this repo — unifies block, file, and "
                    "object in one system: PowerFlex for block, "
                    "PowerScale with the Lightning file system for file, "
                    "ObjectScale for object. The reason a parallel file "
                    "system and a distributed block pool end up in the "
                    "same rack is that they are the same instinct applied "
                    "to different access patterns: refuse the controller, "
                    "spread the data, and let the client talk to "
                    "everything at once."
                ),
            ),
        ],
    ),
]
