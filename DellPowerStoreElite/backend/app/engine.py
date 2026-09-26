"""Pure cluster-join engine for the PowerStore Elite twin.

``simulate()`` returns the deterministic trace of a modernization: an
existing prior-generation PowerStore serving I/O, a new PowerStore Elite
appliance waking beside it, the two fusing into one mixed-generation
cluster over the cluster's Ethernet network, volumes rebalancing live, and
the old array taking a second role instead of a skip. Same purity rule as
every twin: no FastAPI, no IO, no timers — the frontend owns the playback
clock, and each ``JoinState`` is plain data the renderer consumes.

The storytelling beat that makes Elite different from the original
PowerStore twin: that one's drama is a box coming to life; this one's
drama is that *nothing dramatic is allowed to happen*. Hosts keep reading
and writing through every step, ``downtime_seconds`` is pinned at zero,
and the performance headline (3x) is only realized after cutover — the
claim is earned by the sequence, not asserted at the start. Timing,
IOPS and capacity figures are illustrative but shaped by Dell's launch
materials (3x performance, 6:1 data reduction, 5.8 PB effective per 3U). One
correction from the 2026-09 fact-check is load-bearing: Elite's 200 Gb RDMA
"node interconnect" joins the two controller nodes *inside* one appliance
(cable-free, across the midplane — StorageReview's Gen 3 review); it is not
the wire between appliances. Appliances in a cluster talk over the Ethernet
cluster network, so the ``cluster-mesh`` region and the ``mesh`` phase model
that network, and its speed is illustrative. Favor a correct mental model over measured numbers (project scope
guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import JoinState

# The prior array's serving set: what "the estate keeps working" looks like.
_PRIOR_SERVE = [
    "prior-bay",
    "prior-cpu-a", "prior-cpu-b",
    "prior-io-a", "prior-io-b",
]
_PRIOR_BOARDS = ["prior-board-a", "prior-board-b"]
_ELITE_PSUS = ["elite-psu-a", "elite-psu-b"]
_ELITE_FANS = ["elite-fans-a", "elite-fans-b"]
_ELITE_BOOT = [
    "elite-cpu-a", "elite-cpu-b",
    "elite-dimm-a", "elite-dimm-b",
    "elite-board-a", "elite-board-b",
]
_ELITE_BBUS = ["elite-bbu-a", "elite-bbu-b"]
_ELITE_MGMT = ["elite-mgmt-a", "elite-mgmt-b"]
_ELITE_IO = ["elite-io-a", "elite-io-b"]
_ELITE_CPUS = ["elite-cpu-a", "elite-cpu-b"]
_ELITE_SERVE = ["elite-bay", "elite-nvram", *_ELITE_IO, *_ELITE_CPUS]

# Baseline the whole trace is measured against: what the prior array serves
# alone. The floor (service never dips below 85% of this) and the ceiling
# (3x after cutover) are both expressed relative to it in the tests.
_BASE_IOPS = 250


def simulate() -> list[JoinState]:
    """A live modernization, from lone prior-gen array to mixed-generation
    cluster serving 3x — with the downtime counter never leaving zero."""
    return [
        JoinState(
            step=0,
            phase="steady",
            label="The estate before — one array, serving",
            description=L(
                novice=(
                    "This is an ordinary Tuesday. A PowerStore array a company "
                    "bought a few years ago is doing its job: databases, "
                    "virtual machines and file shares are all reading and "
                    "writing to it right now. It is also getting full, and "
                    "newer, faster hardware exists. The traditional next move "
                    "is painful — buy a new box, copy everything over, and "
                    "pick a weekend to switch, hoping nothing goes wrong. "
                    "Watch the downtime counter through this whole story: the "
                    "new way means it never moves off zero."
                ),
                plain=(
                    "A prior-generation PowerStore is serving the estate "
                    "alone: block, file and VM workloads all live here. It is "
                    "filling up, and faster hardware now exists. The classic "
                    "answer is a forklift refresh — new array, bulk copy, a "
                    "cutover weekend. The whole point of what follows is that "
                    "none of that happens; keep an eye on the downtime "
                    "counter, which never leaves zero."
                ),
                standard=(
                    "A prior-generation PowerStore serves the whole estate — "
                    "block, file and virtual-machine workloads at a steady "
                    "quarter-million IOPS. It is nearing capacity and two "
                    "hardware generations behind. The traditional remedy is a "
                    "forklift refresh: buy, migrate, cut over, decommission. "
                    "Everything that follows exists to make that remedy "
                    "obsolete — the downtime counter on the right is the "
                    "score being kept."
                ),
                technical=(
                    "Baseline: prior-generation PowerStore serving ~250K IOPS "
                    "of mixed block/file/VM load, near capacity. The trace "
                    "measures everything against this state — the service "
                    "floor during rebalance and the 3x post-cutover ceiling "
                    "are both defined relative to it. downtime_seconds "
                    "starts at zero and is asserted zero on every step."
                ),
                expert=(
                    "Baseline 250K IOPS, prior gen, near capacity. All floors "
                    "and multipliers are relative to this step. downtime ≡ 0 "
                    "asserted trace-wide."
                ),
            ),
            active_regions=[*_PRIOR_SERVE],
            iops_thousands=_BASE_IOPS,
            downtime_seconds=0,
            generations_in_cluster=1,
            effective_tb=1200,
            elapsed_seconds=0,
        ),
        JoinState(
            step=1,
            phase="power",
            label="Elite racked — PSUs energize, no power button",
            description=L(
                novice=(
                    "The new PowerStore Elite is bolted into the rack below "
                    "the old array and its power cords go in. Like every "
                    "storage array, it has no power button — the moment "
                    "electricity arrives, it starts waking up on its own. "
                    "Both halves of the machine (there are two independent "
                    "controllers inside, just like the old one) begin at the "
                    "same time. Meanwhile the old array above carries on "
                    "serving everyone as if nothing were happening — because "
                    "for its users, nothing is."
                ),
                plain=(
                    "The Elite is racked and cabled and AC is applied. There "
                    "is no power button — applying mains *is* the power-on, "
                    "and both controller nodes wake in parallel, the "
                    "dual-canister habit of every PowerStore generation. The "
                    "prior array keeps serving throughout; its users see "
                    "nothing."
                ),
                standard=(
                    "The 3U Elite appliance is racked beneath the prior array "
                    "and AC is applied — no power button, both node canisters "
                    "waking in parallel, exactly the bring-up contract the "
                    "PowerStore twin walks through step by step. The "
                    "difference in *this* trace is the top band: the prior "
                    "array keeps serving its quarter-million IOPS while the "
                    "new hardware comes up beside it."
                ),
                technical=(
                    "AC applied to the Elite; PSUs detect line voltage and "
                    "bring rails up on both canisters simultaneously "
                    "(lockstep `-a`/`-b` bring-up, asserted). Prior array "
                    "unaffected — serving state and IOPS unchanged. The "
                    "power-on mechanics are the DellPowerStore twin's; this "
                    "trace compresses them to two steps."
                ),
                expert=(
                    "AC = power-on; dual-canister lockstep wake. Prior array "
                    "serving, unchanged. See the PowerStore twin for the "
                    "uncompressed bring-up."
                ),
            ),
            active_regions=[*_PRIOR_SERVE, *_ELITE_PSUS, *_ELITE_FANS],
            iops_thousands=_BASE_IOPS,
            downtime_seconds=0,
            generations_in_cluster=1,
            effective_tb=1200,
            elapsed_seconds=120,
        ),
        JoinState(
            step=2,
            phase="power",
            label="Elite nodes boot PowerStoreOS",
            description=L(
                novice=(
                    "Each of the Elite's two controllers is a complete "
                    "computer, and each now boots its operating system — the "
                    "same PowerStoreOS family the old array runs, which is "
                    "the secret to everything that follows: two machines that "
                    "speak the same language can share a cluster even though "
                    "their hardware is generations apart. The new processors "
                    "have up to half again as many cores as the old ones, and "
                    "the memory is a generation newer. This boot is the "
                    "longest part of the new box's own story."
                ),
                plain=(
                    "Both Elite nodes boot PowerStoreOS — the same operating "
                    "system lineage as the prior array, which is what will "
                    "let two hardware generations share one cluster. Under it "
                    "sits the new platform: Xeon Scalable CPUs with up to 50% "
                    "more cores, DDR5 memory, and a PCIe Gen 5 fabric."
                ),
                standard=(
                    "Both Elite nodes boot PowerStoreOS. Same OS lineage as "
                    "the prior array — the compatibility that makes "
                    "mixed-generation clustering possible — on a new "
                    "platform: Intel Xeon Scalable with up to 50% more cores "
                    "(Dell's comparison: the new 5500 against the 3200T), "
                    "DDR5 memory, PCIe Gen 5 lanes. The dwell here is real: a container-based storage "
                    "OS coming up on two nodes is the slowest thing the new "
                    "box itself does."
                ),
                technical=(
                    "PowerStoreOS boots on both canisters (parallel, "
                    "lockstep). Platform: Xeon Scalable +50% cores (5500 vs "
                    "3200T, Dell), DDR5, Gen 5 fabric. OS-lineage continuity "
                    "is the enabling fact for the mixed-generation join two "
                    "steps from now. Longest dwell of the *power* "
                    "phase; the trace-wide maximum belongs to the rebalance."
                ),
                expert=(
                    "PowerStoreOS up, both nodes. Xeon Scalable +50% cores, "
                    "DDR5, Gen 5. OS continuity enables the join. Phase-max "
                    "dwell only — rebalance holds the trace max."
                ),
            ),
            active_regions=[
                *_PRIOR_SERVE, *_ELITE_PSUS, *_ELITE_FANS, *_ELITE_BOOT,
            ],
            iops_thousands=_BASE_IOPS,
            downtime_seconds=0,
            generations_in_cluster=1,
            effective_tb=1200,
            elapsed_seconds=420,
            cycle_cost=3,
        ),
        JoinState(
            step=3,
            phase="power",
            label="E3 drives and write cache online, batteries checked",
            description=L(
                novice=(
                    "The Elite finds its own storage: forty slim flash drives "
                    "in a new, denser shape called E3. It also sets aside part "
                    "of its memory as an ultra-fast notepad for incoming "
                    "writes, and checks its batteries — not to survive a "
                    "blackout, but to buy just enough seconds during one to "
                    "copy that notepad safely to flash so no write is ever "
                    "lost. The old array above keeps the same promise with "
                    "special notepad drives in its front bay; the promise is "
                    "a family trait, and only the way of keeping it is new."
                ),
                plain=(
                    "The Elite discovers its 40 low-profile E3 NVMe drives, "
                    "arms its battery-backed write cache, and self-tests the "
                    "battery backup units that vault that cache to flash on "
                    "power loss. The vaulting contract is inherited from "
                    "every PowerStore generation. Two things changed: the "
                    "cache now lives in battery-backed DDR5 rather than in "
                    "NVRAM drives, and the bay holds 40 E3 slots in 3U "
                    "instead of 25 2.5″ slots in 2U."
                ),
                standard=(
                    "Drive discovery on the Elite: 40 dual-ported low-profile "
                    "E3 NVMe slots (QLC or TLC), the battery-backed DDR5 "
                    "write cache that replaces the prior generation's NVRAM "
                    "drives (as StorageReview describes the design), and a "
                    "BBU self-test — the vault-to-flash insurance carried "
                    "over from the prior generation. E3 density is the quiet "
                    "headline: Dell claims up to 3x the density, which is "
                    "how 5.8 PB effective fits in 3U."
                ),
                technical=(
                    "Enumeration of 40× dual-ported E3 NVMe (QLC/TLC); "
                    "software-defined persistent memory armed (DDR5 "
                    "presented as NVDIMM, vaulted to M.2 on AC loss — per "
                    "StorageReview; no NVRAM drives in the bay); BBU "
                    "self-test. Dell's 3x density figure compares a 9500 at "
                    "6:1 with a 9200T at 5:1. "
                    "Both nodes see all drives — the dual-ported invariant "
                    "is generation-independent."
                ),
                expert=(
                    "40× E3 NVMe enumerated, SDPM write cache + BBUs armed. "
                    "Dual-ported throughout. 3x density (Dell, 9500 vs "
                    "9200T)."
                ),
            ),
            active_regions=[
                *_PRIOR_SERVE, "elite-bay", "elite-nvram",
                *_ELITE_BBUS, "elite-board-a", "elite-board-b",
            ],
            iops_thousands=_BASE_IOPS,
            downtime_seconds=0,
            generations_in_cluster=1,
            effective_tb=1200,
            elapsed_seconds=540,
        ),
        JoinState(
            step=4,
            phase="join",
            label="The Elite joins the existing cluster",
            description=L(
                novice=(
                    "Here is the moment the whole product exists for. Instead "
                    "of standing up the new box as a separate island and "
                    "planning a great migration to it, the administrator "
                    "clicks once: the Elite *joins the old array's cluster*. "
                    "From this moment there is one storage system with two "
                    "generations of hardware inside it, managed from one "
                    "screen. Nobody's applications stopped. Nobody scheduled "
                    "a weekend. The capacity counter jumps because the new "
                    "box's enormous space is now part of the shared pool."
                ),
                plain=(
                    "The signature move: the Elite joins the prior array's "
                    "cluster rather than replacing it. One cluster now spans "
                    "two hardware generations, under one PowerStore Manager "
                    "pane. No host path closed, no application paused — the "
                    "generations counter goes to two and the downtime counter "
                    "stays at zero. Effective capacity jumps as the Elite's "
                    "pool comes in behind the 6:1 data reduction guarantee."
                ),
                standard=(
                    "Mixed-generation clustering, the launch's signature "
                    "capability: the Elite joins the existing cluster live. "
                    "One cluster, two hardware generations, one management "
                    "plane — and no service interruption, because a join is a "
                    "membership operation, not a data operation. Effective "
                    "capacity leaps to seven petabytes as the Elite's 40-slot "
                    "E3 pool arrives behind the 6:1 data reduction guarantee "
                    "(raised from the prior generation's 5:1)."
                ),
                technical=(
                    "Cluster join: membership + metadata only, no data "
                    "movement yet. generations_in_cluster 1→2 exactly here "
                    "(asserted); downtime remains 0 — the join closes no "
                    "host path. Effective pool jumps ~1.2→7.0 PB (Elite: "
                    "5.8 PB effective per 3U at 6:1 guaranteed DRR, up from "
                    "5:1). Single PowerStore Manager instance spans both."
                ),
                expert=(
                    "Join = membership op. gens 1→2, downtime 0, eff. pool "
                    "+5.8 PB @ 6:1 DRR. One mgmt plane."
                ),
            ),
            active_regions=[
                *_PRIOR_SERVE, *_ELITE_MGMT, *_ELITE_CPUS, "elite-bay",
            ],
            iops_thousands=_BASE_IOPS,
            downtime_seconds=0,
            generations_in_cluster=2,
            effective_tb=7000,
            elapsed_seconds=660,
            cycle_cost=2,
        ),
        JoinState(
            step=5,
            phase="mesh",
            label="The cluster network links the generations",
            description=L(
                novice=(
                    "The two generations now open a working connection to "
                    "each other over the cluster's own network — ordinary "
                    "fast Ethernet, running through the switches at the top "
                    "of the rack, on a network of its own beside the traffic of the "
                    "people using the storage. Think of two neighboring "
                    "workshops knocking a door through their shared wall "
                    "instead of walking deliveries around the block. Every "
                    "byte of the move that follows will go through this "
                    "door. (The Elite also has a much faster link of its own "
                    "inside its case, between its two controllers, but "
                    "that one never leaves the box.)"
                ),
                plain=(
                    "The appliances link over the cluster network: Ethernet "
                    "between the two boxes, through the top-of-rack "
                    "switches, on its own internal network. It is the "
                    "corridor the live rebalance will run on. Elite's "
                    "headline 200 Gb RDMA (remote direct memory access) "
                    "interconnect is a different wire — it joins the two "
                    "controller nodes inside the Elite and never leaves the "
                    "chassis."
                ),
                standard=(
                    "The cluster network comes up between the generations: "
                    "an Ethernet path through the top-of-rack switches, "
                    "on its own internal network, which the coming rebalance "
                    "will run on. It is worth keeping apart from Elite's "
                    "headline 200 Gb RDMA (remote direct memory access) node "
                    "interconnect, which joins the two controllers inside "
                    "one Elite appliance across the midplane — up from 2× "
                    "10 GbE in the prior generation, by StorageReview's "
                    "account — and carries mirrored writes, not "
                    "migrations. The link speed drawn between the "
                    "appliances here is illustrative."
                ),
                technical=(
                    "Intra-cluster data network established between the "
                    "appliances (Ethernet via the ToR pair; speed "
                    "illustrative). Not the 200 GbE RDMA node interconnect: "
                    "that is intra-appliance, midplane-routed, dedicated to "
                    "write ingest (100 GbE on the 1500; 2× 10 GbE in Gen 2, "
                    "per StorageReview). Migration is background-throttled, "
                    "which is what the service-floor invariant models. "
                    "First `cluster-mesh` activation in the trace; asserted "
                    "inactive before this phase."
                ),
                expert=(
                    "Intra-cluster Ethernet up between appliances (200G RDMA "
                    "is intra-appliance only). Mesh first lights here "
                    "(asserted)."
                ),
            ),
            active_regions=[
                *_PRIOR_SERVE, *_PRIOR_BOARDS, "cluster-mesh",
                "elite-board-a", "elite-board-b",
            ],
            iops_thousands=_BASE_IOPS,
            downtime_seconds=0,
            generations_in_cluster=2,
            effective_tb=7000,
            elapsed_seconds=720,
        ),
        JoinState(
            step=6,
            phase="rebalance",
            label="Volumes rebalance live across the cluster network",
            description=L(
                novice=(
                    "Now the actual move — and it happens while everyone "
                    "keeps working. Volume by volume (a volume is the chunk "
                    "of storage one application sees as its disk), the cluster "
                    "copies data from the old array's drives to the Elite's, "
                    "over the cluster network, in the background, while the old "
                    "array keeps answering everyone. Users notice nothing; "
                    "at worst the system is a few percent slower during the "
                    "busiest copying, which is the honest price of never "
                    "having to stop. This is by far the longest stage — "
                    "moving petabytes takes hours no matter how clever you "
                    "are — so the picture lingers here. The old way spent "
                    "this same time too, but spent it on a weekend with the "
                    "business offline."
                ),
                plain=(
                    "Volumes migrate from the prior array's drives to the "
                    "Elite's, live, over the cluster network. Hosts keep reading "
                    "and writing throughout, still through the prior array's "
                    "ports; served IOPS dips a few percent "
                    "at the peak of the copy — the honest price of never "
                    "stopping — and the downtime counter does not move. It "
                    "is the longest stage of the trace by far, because "
                    "moving petabytes takes hours; the difference from a "
                    "forklift refresh is *when* those hours happen: during "
                    "business as usual, not during an outage window."
                ),
                standard=(
                    "The live rebalance: the cluster drains volumes from the "
                    "prior generation's bay to the Elite's E3 pool across "
                    "the cluster network, while the prior array keeps serving "
                    "hosts through its own ports (the Elite's front end stays "
                    "dark until cutover). Hosts are mapped and multipathed to "
                    "the Elite before the first volume moves; that prerequisite "
                    "is what makes the later cutover a path change. "
                    "IOPS sags slightly under the copy load and recovers — "
                    "the trace's service floor holds — and downtime stays at "
                    "zero. This step carries the largest dwell in the trace, "
                    "deliberately: the hours a migration takes did not "
                    "disappear, they just stopped requiring an outage to "
                    "spend."
                ),
                technical=(
                    "Background volume migration prior→Elite over the "
                    "intra-cluster network (PowerStore's internal, "
                    "appliance-to-appliance migration); hosts stay on the prior "
                    "front end, with paths to the Elite mapped beforehand. Served "
                    "IOPS dips within the asserted floor (≥85% of baseline) "
                    "and downtime remains 0. The single longest stage of the "
                    "trace — the honest location of the cost of 'no host-side "
                    "migration project' is this stage's duration, and the "
                    "tests pin it as the unique maximum."
                ),
                expert=(
                    "Live drain prior→Elite over the cluster net. IOPS ≥85% of "
                    "baseline, downtime 0. Longest stage of the join — the cost "
                    "is duration, never availability."
                ),
            ),
            active_regions=[
                "cluster-mesh", "prior-bay", "elite-bay",
                *_PRIOR_SERVE[1:], *_ELITE_CPUS,
                "elite-board-a", "elite-board-b",
            ],
            iops_thousands=230,
            downtime_seconds=0,
            generations_in_cluster=2,
            effective_tb=7000,
            elapsed_seconds=14400,
            cycle_cost=6,
        ),
        JoinState(
            step=7,
            phase="rebalance",
            label="Rebalance completes — placement verified",
            description=L(
                novice=(
                    "The background move finishes. The cluster double-checks "
                    "its bookkeeping: every volume now lives on the Elite's "
                    "drives, every copy matches, and the map of what-is-where "
                    "is consistent on both machines. Service has already "
                    "drifted most of the way back to full speed. Nothing has "
                    "switched over yet — that is the next step — but the "
                    "data itself is home."
                ),
                plain=(
                    "The drain completes and the cluster verifies placement: "
                    "volumes now live on the Elite's E3 pool, checksums and "
                    "metadata agree on both appliances, and served IOPS has "
                    "climbed back toward baseline. The data is home; the "
                    "front-end cutover is still to come."
                ),
                standard=(
                    "Migration complete, placement verified — every volume "
                    "resident on the Elite's pool with metadata consistent "
                    "across both generations, service back within a few "
                    "percent of baseline. The distinction between this step "
                    "and the next matters: the data has moved, but the hosts "
                    "are still being served through the paths they always "
                    "used."
                ),
                technical=(
                    "Drain complete; placement and metadata verified across "
                    "both appliances. IOPS recovering toward baseline "
                    "(still under the pre-cutover ceiling — the 3x claim is "
                    "deliberately not realized until cutover). Data "
                    "residency and host pathing are now independent facts."
                ),
                expert=(
                    "Drain done, placement verified. IOPS ≈ baseline; 3x "
                    "withheld until cutover. Residency ≠ pathing."
                ),
            ),
            active_regions=[
                "cluster-mesh", "elite-bay", "elite-nvram", *_ELITE_CPUS,
                *_PRIOR_SERVE[1:],
            ],
            iops_thousands=245,
            downtime_seconds=0,
            generations_in_cluster=2,
            effective_tb=7000,
            elapsed_seconds=21600,
            cycle_cost=2,
        ),
        JoinState(
            step=8,
            phase="cutover",
            label="Cutover — the Elite serves, performance triples",
            description=L(
                novice=(
                    "The hosts' traffic now flows to the new machine — and "
                    "because modern storage networks give every host several "
                    "paths and switch between them automatically, this "
                    "handover is invisible too. Suddenly the speed triples: "
                    "the new processors, the faster memory, the denser flash "
                    "and the doubled network ports all engage at once. "
                    "Notice that the tripling happens *here*, at the end of "
                    "the sequence — the new box earned it by first joining, "
                    "linking and moving in, not by being unboxed."
                ),
                plain=(
                    "Host paths cut over to the Elite — transparently, via "
                    "standard multipathing, so the downtime counter still "
                    "reads zero — and performance triples: Dell claims up to "
                    "3x the IOPS and 3x the throughput of the prior "
                    "generation on a 70/30 read/write mix, and credits "
                    "PowerStoreOS 5.0's Metadata Acceleration with reads up "
                    "to 70% faster. The claim lands here, after the move, not "
                    "at the unboxing."
                ),
                standard=(
                    "Cutover: multipathing shifts host I/O to the Elite's "
                    "40-port front end with no interruption, and the "
                    "platform's headline numbers finally engage. All are "
                    "Dell's preliminary internal figures: up to 3x IOPS "
                    "(1500 against 1200T, 70/30 read/write, 8K blocks), 3x "
                    "throughput (9500 against 9200T, 1 MB blocks), and reads "
                    "up to 70% faster from Metadata Acceleration, a "
                    "PowerStoreOS 5.0 feature Dell measured on a 500T. The "
                    "ports are 64 Gb FC and 100 GbE, at what Dell calls "
                    "twice the port count. The trace holds "
                    "the tripling back until this step on purpose: it is a "
                    "property of the modernized estate, not of the box in "
                    "the crate."
                ),
                technical=(
                    "ALUA/multipath cutover to the Elite front end; no path "
                    "loss, downtime 0. Post-cutover IOPS ≥3x baseline "
                    "(asserted; pre-cutover steps are asserted ≤1.2x — the "
                    "multiplier is earned by the sequence). Basis per Dell "
                    "(preliminary internal): 3x IOPS 1500 vs 1200T, 70/30, "
                    "8K over FC; 3x throughput 9500 vs 9200T, 1 MB; Metadata "
                    "Acceleration reads +70% (OS 5.0 vs 4.3 on a 500T); up "
                    "to 40 ports, 64 Gb FC / 100 GbE."
                ),
                expert=(
                    "Multipath cutover, downtime 0. IOPS ≥3x baseline here, "
                    "≤1.2x before (both asserted). 40 ports, 64G FC, "
                    "100 GbE, metadata reads +70% (Dell figures)."
                ),
            ),
            active_regions=[*_ELITE_SERVE, "cluster-mesh"],
            iops_thousands=760,
            downtime_seconds=0,
            generations_in_cluster=2,
            effective_tb=7000,
            elapsed_seconds=21900,
            cycle_cost=2,
        ),
        JoinState(
            step=9,
            phase="repurpose",
            label="The prior generation takes a second job",
            description=L(
                novice=(
                    "And the old array? It does not go in a skip. Still a "
                    "member of the cluster, it takes a lighter job: hosting "
                    "snapshots (saved earlier versions of the data) and "
                    "serving the test environment. Hardware that was too slow to be the star "
                    "is still plenty good as the understudy — and because it "
                    "never left the cluster, giving it that job is a "
                    "settings change, not a project."
                ),
                plain=(
                    "The prior array is repurposed, not retired: still a "
                    "cluster member, now carrying snapshots "
                    "and test workloads. Assigning it that role is a policy "
                    "change inside the cluster it never left — the second "
                    "half of the no-forklift argument."
                ),
                standard=(
                    "The prior generation is repurposed in place: snapshot "
                    "retention, test and development estate — lighter roles its "
                    "hardware still serves well. Because it never left the "
                    "cluster, the reassignment is policy, not a project. "
                    "(A replication target is the exception: PowerStore "
                    "replicates between clusters, so that role means removing "
                    "the appliance and redeploying it as a remote system.) "
                    "This is the half of the modernization story a spec "
                    "sheet can't show: the refresh cycle stops producing "
                    "decommissioned arrays and starts producing second "
                    "roles."
                ),
                technical=(
                    "Prior appliance reassigned within the cluster: snapshot "
                    "retention / non-prod serving. Not a replication target — "
                    "native replication is cluster-to-cluster, and an in-cluster "
                    "copy would share the failure domain. No data egress, no "
                    "decommission event. "
                    "Mixed-generation membership persists to the end of the "
                    "trace — the tests assert the prior array is never "
                    "evicted."
                ),
                expert=(
                    "Prior gen → snapshot/non-prod, in place (replication "
                    "needs a separate cluster). No "
                    "egress, no decommission; membership persists "
                    "(asserted)."
                ),
            ),
            active_regions=[
                *_PRIOR_SERVE, *_PRIOR_BOARDS, "cluster-mesh",
            ],
            iops_thousands=760,
            downtime_seconds=0,
            generations_in_cluster=2,
            effective_tb=7000,
            elapsed_seconds=22500,
        ),
        JoinState(
            step=10,
            phase="elite",
            label="Steady on Elite — the modernization that wasn't a project",
            description=L(
                novice=(
                    "The end state: the Elite serves everyone at triple the "
                    "old speed, the old array keeps the snapshots and test "
                    "systems, and the "
                    "two run as one system under one screen. Now read the "
                    "counters one last time. Speed: tripled. Capacity: "
                    "nearly six times larger. Downtime: zero seconds, ever. "
                    "The company modernized its storage the way you'd hope "
                    "to renovate a house — while living in it, without "
                    "moving out, and the old furniture found a use in the "
                    "spare room."
                ),
                plain=(
                    "Steady state: the Elite serves ~3x the baseline with "
                    "built-in AI balancing load and tuning placement "
                    "continuously (Dell claims up to 95% less manual "
                    "effort); the prior array holds snapshots and test "
                    "workloads; one cluster, "
                    "two generations, one management pane. Total downtime "
                    "across the entire modernization: zero seconds."
                ),
                standard=(
                    "Steady state on the Elite: ~3x baseline IOPS, 7 PB "
                    "effective behind the 6:1 guarantee, built-in AI "
                    "balancing workloads and placement continuously — the "
                    "launch's 'up to 95% less manual effort' claim describes "
                    "this ongoing state, not the join. The mixed-generation "
                    "cluster is the *end* state, not a transition: when the "
                    "next generation ships, it will join this cluster the "
                    "same way, and the Elite will inherit the second job. "
                    "The downtime counter ends where it began — zero."
                ),
                technical=(
                    "End state: Elite primary at ~3.1x baseline, 7 PB "
                    "effective @ 6:1 DRR, autonomous balancing active (the "
                    "95%-less-manual-effort claim attaches here). "
                    "Mixed-generation membership is terminal, not "
                    "transitional — next-gen hardware repeats the same join "
                    "against this cluster. Trace ends with downtime_seconds "
                    "== 0, the twin's defining assertion."
                ),
                expert=(
                    "Elite primary, ~3.1x, 7 PB @ 6:1, autonomous balancing "
                    "on. Mixed-gen membership terminal; next gen repeats the "
                    "join. downtime == 0, QED."
                ),
            ),
            active_regions=[
                *_ELITE_SERVE, "cluster-mesh", "prior-bay",
            ],
            iops_thousands=780,
            downtime_seconds=0,
            generations_in_cluster=2,
            effective_tb=7000,
            elapsed_seconds=23100,
        ),
    ]
