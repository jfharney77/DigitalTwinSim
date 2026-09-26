"""Use-case build sheets for the PowerStore Elite twin.

Each use case is a concrete estate story assembled from catalog options —
category and option ids must resolve against catalog.py (enforced in
tests/test_catalog.py). Narratives are written for a technically skilled
reader new to storage; capacities and timings are illustrative.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="hospital-modernization",
        title="A hospital modernizes without a maintenance window",
        summary=(
            "A regional hospital replaces the performance tier under its "
            "electronic health records without scheduling a single minute "
            "of downtime — the twin's trace as a purchase order."
        ),
        narrative=[
            (
                "The hospital's PowerStore 5000T holds the electronic health "
                "record database, imaging metadata, and the VM farm behind "
                "registration and pharmacy. It is at 87% capacity and two "
                "generations old — but an EHR system has no good weekend "
                "for a migration, because the emergency department does not "
                "close. Every refresh plan the team drafted began with a "
                "risk-review meeting about the cutover window."
            ),
            (
                "The Elite path deletes the window instead of arguing about "
                "it. A new PowerStore 5500 racks in below the existing "
                "array, joins its cluster live, and drains the volumes "
                "over the cluster network while clinicians keep charting. "
                "Cutover is a multipathing event no application notices. "
                "The old 5000T stays in the cluster as the snapshot-retention "
                "and test tier — a lighter job on hardware the hospital "
                "already owns and trusts. Off-site replication still goes to "
                "a separate cluster, as it must."
            ),
            (
                "The numbers the CIO reports upward: reads up to 70% "
                "faster by Dell's own test figure, which a metadata-heavy "
                "EHR profile is well placed to approach; six years "
                "of imaging growth absorbed by the 6:1-guaranteed E3 pool, "
                "and a modernization whose total service interruption was "
                "zero seconds."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="model", option_id="elite-5500", qty=1,
                rationale=(
                    "The midrange model matches the 5000T-class array it "
                    "relieves — like for like, two generations up."
                ),
            ),
            UseCaseItem(
                category_id="modernization", option_id="mixed-gen-cluster", qty=1,
                rationale=(
                    "The whole point: join, rebalance and cut over with the "
                    "EHR online throughout."
                ),
            ),
            UseCaseItem(
                category_id="modernization", option_id="repurpose", qty=1,
                rationale=(
                    "The old 5000T becomes the snapshot and test tier "
                    "instead of a decommissioning line item."
                ),
            ),
            UseCaseItem(
                category_id="drives", option_id="e3-tlc", qty=24,
                rationale=(
                    "TLC endurance for a write-heavy transactional EHR "
                    "database."
                ),
            ),
            UseCaseItem(
                category_id="memory", option_id="metadata-acceleration", qty=1,
                rationale=(
                    "EHR reads are metadata-bound, which is the workload "
                    "Dell's 70%-faster-reads claim describes."
                ),
            ),
            UseCaseItem(
                category_id="resilience", option_id="cyber-detect", qty=1,
                rationale=(
                    "Healthcare is ransomware's favorite target; byte-level "
                    "snapshot scanning names the last clean copy."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Cutover downtime", value="0 seconds"),
            Stat(label="Reads", value="Up to 70% faster (Dell claim)"),
            Stat(label="Old array's fate", value="Snapshot & test tier"),
        ],
    ),
    UseCase(
        id="consolidation-3u",
        title="Nine arrays become one 3U appliance",
        summary=(
            "A manufacturer collapses a sprawl of aging midrange arrays "
            "into a single PowerStore 9500 — 5.8 PB effective in three rack "
            "units, serving block, file, VMs and containers at once."
        ),
        narrative=[
            (
                "Fifteen years of plant acquisitions left the manufacturer "
                "with nine midrange arrays from three vendors across two "
                "rooms — each with its own management tool, support "
                "contract, spares shelf and administrator muscle memory. "
                "The estate's real workload would fit comfortably in one "
                "modern box; the sprawl exists because migrating off any "
                "single array was never worth the outage."
            ),
            (
                "One PowerStore 9500 takes the whole estate: block LUNs for the "
                "ERP database, NFS and SMB shares for engineering, vVols "
                "for the VMware farm, and container volumes for the new "
                "MES services — four workload classes that historically "
                "justified four separate purchases. Forty QLC E3 drives "
                "behind the 6:1 guarantee present Dell's 5.8 PB effective, which "
                "swallows the nine arrays' combined contents with room for "
                "a decade of growth."
            ),
            (
                "The consolidation itself is nine small migrations rather "
                "than one giant one — and the two arrays that were "
                "PowerStores join the Elite's cluster and drain live, their "
                "hosts given paths to the Elite first and no outage taken. Dynamic core allocation keeps the "
                "ERP's latency flat while the file and container loads "
                "come aboard; the 40-port front end means no workload "
                "queues behind another for connectivity."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="model", option_id="elite-9500", qty=1,
                rationale=(
                    "Nine arrays' worth of mixed workloads need the top "
                    "model's cores, memory and port count."
                ),
            ),
            UseCaseItem(
                category_id="drives", option_id="e3-qlc", qty=40,
                rationale=(
                    "Capacity-first economics: a full QLC bay behind 6:1 "
                    "reaches the 5.8 PB-effective headline."
                ),
            ),
            UseCaseItem(
                category_id="reduction", option_id="drr-guarantee", qty=1,
                rationale=(
                    "The guarantee is what makes sizing nine estates into "
                    "one bay a contract instead of a hope."
                ),
            ),
            UseCaseItem(
                category_id="frontend", option_id="fc64", qty=16,
                rationale="The ERP SAN keeps its Fibre Channel personality.",
            ),
            UseCaseItem(
                category_id="frontend", option_id="eth100", qty=16,
                rationale=(
                    "File, NVMe/TCP and container traffic ride 100 GbE "
                    "beside the FC estate."
                ),
            ),
            UseCaseItem(
                category_id="processors", option_id="dynamic-cores", qty=1,
                rationale=(
                    "Four workload classes on one box only works if cores "
                    "follow the load automatically."
                ),
            ),
            UseCaseItem(
                category_id="modernization", option_id="mixed-gen-cluster", qty=1,
                rationale=(
                    "The two existing PowerStores join and drain live "
                    "rather than being migrated by hand."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Footprint", value="9 arrays · 2 rooms → 1× 3U"),
            Stat(label="Effective capacity", value="5.8 PB in one appliance"),
            Stat(label="Workloads", value="Block · file · vVols · containers"),
        ],
    ),
    UseCase(
        id="rolling-refresh",
        title="The estate that never gets migrated again",
        summary=(
            "A SaaS company adopts Elite for the architecture, not the "
            "speed: controller swaps and cluster joins turn every future "
            "refresh into a background task, permanently."
        ),
        narrative=[
            (
                "The platform team runs customer databases on storage that "
                "must grow every quarter and get faster every second year — "
                "and their postmortem archive says every past storage "
                "migration slipped its window and paged someone at 3 a.m. "
                "Their buying criterion this cycle was blunt: whatever we "
                "buy, we are never doing a data migration again."
            ),
            (
                "Elite's modular architecture is the answer to that "
                "criterion rather than to a benchmark. Capacity refresh: "
                "new E3 drives slot into the live bay. Performance "
                "refresh: next-generation controllers swap into the same "
                "chassis, keeping the drives and the data in place. "
                "Platform refresh: the next Elite generation joins the "
                "cluster over the cluster network and volumes rebalance "
                "to it live — the same sequence this twin's trace plays, "
                "repeated on whatever hardware 2028 ships."
            ),
            (
                "The prior-generation array from this cycle's refresh "
                "stays in the cluster serving the staging environment — "
                "the team's rule is that hardware leaves the rack when it "
                "dies, not when marketing renames its successor. Autonomous "
                "balancing plus AIOps telemetry means the quarterly growth "
                "is absorbed by the array's own placement decisions, and "
                "the 3 a.m. migration page has no failure mode left to "
                "fire on."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="model", option_id="elite-1500", qty=2,
                rationale=(
                    "Two smaller appliances in one cluster beat one big "
                    "one when the goal is rolling, incremental refresh."
                ),
            ),
            UseCaseItem(
                category_id="modernization", option_id="controller-swap", qty=1,
                rationale=(
                    "The two-year performance refresh becomes a canister "
                    "swap, not an array replacement."
                ),
            ),
            UseCaseItem(
                category_id="modernization", option_id="mixed-gen-cluster", qty=1,
                rationale=(
                    "The generational refresh becomes a cluster join — "
                    "this trace, replayed every cycle."
                ),
            ),
            UseCaseItem(
                category_id="interconnect", option_id="cluster-network", qty=1,
                rationale=(
                    "Every future rebalance rides the cluster network "
                    "between appliances, in the background."
                ),
            ),
            UseCaseItem(
                category_id="autonomous", option_id="ai-balancing", qty=1,
                rationale=(
                    "Quarterly growth is placed by the cluster itself, not "
                    "by a change ticket."
                ),
            ),
            UseCaseItem(
                category_id="autonomous", option_id="aiops", qty=1,
                rationale=(
                    "Fleet telemetry gives the team forecasts instead of "
                    "surprises."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Future migrations planned", value="0"),
            Stat(label="Refresh unit", value="Drive · controller · appliance"),
            Stat(label="3 a.m. pages", value="Retired with the forklift"),
        ],
    ),
]
