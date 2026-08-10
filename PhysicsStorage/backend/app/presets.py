"""Presets and the teaching layer for the storage simulator — config
presets (one per product), workload presets (spec 02's generator
presets), guided scenarios covering every product, and Explain entries.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    Explain,
    GuidedScenario,
    Scenario,
    SimEvent,
    StorageConfig,
    Workload,
    WorkloadPreset,
)

# --- Config presets --------------------------------------------------------

POWERSTORE_2 = StorageConfig(
    product="powerstore", units=2, drives_per_unit=12, drive_tb=15.36,
    drive_class="nvme", protection="raid6",
)
POWERMAX_4 = StorageConfig(
    product="powermax", units=4, drives_per_unit=24, drive_tb=15.36,
    drive_class="nvme", protection="raid6", srdf="off",
)
POWERSCALE_20 = StorageConfig(
    product="powerscale", units=20, drives_per_unit=15, drive_tb=15.36,
    drive_class="nvme", protection="ec8+2",
)
OBJECTSCALE_12 = StorageConfig(
    product="objectscale", units=12, drives_per_unit=24, drive_tb=20.0,
    drive_class="hdd", protection="ec16+4", immutable=True,
)
POWERFLEX_20 = StorageConfig(
    product="powerflex", units=20, drives_per_unit=10, drive_tb=7.68,
    drive_class="nvme", protection="mirror", nic_gbps=100,
)
EXASCALE_32 = StorageConfig(
    product="exascale", units=32, drives_per_unit=12, drive_tb=15.36,
    drive_class="nvme", protection="ec8+2",
    lightning_units=16, file_units=6, object_units=6, block_units=4,
)

CONFIG_PRESETS = [
    ConfigPreset(id="powerstore", compare_preset_id="powerflex", name="PowerStore ×2", config=POWERSTORE_2,
                 blurb="Dual-controller mid-range — the knee's natural habitat."),
    ConfigPreset(id="powermax", compare_preset_id="powerscale", name="PowerMax ×4 bricks", config=POWERMAX_4,
                 blurb="Six-nines personality; add SRDF and a distance."),
    ConfigPreset(id="powerscale", name="PowerScale ×20", config=POWERSCALE_20,
                 blurb="Scale-out NAS — rebuilds get faster as it grows."),
    ConfigPreset(id="objectscale", name="ObjectScale ×12", config=OBJECTSCALE_12,
                 blurb="HDD-dense S3 with object lock on."),
    ConfigPreset(id="powerflex", name="PowerFlex ×20 @100G", config=POWERFLEX_20,
                 blurb="SDS block — the network is the array."),
    ConfigPreset(id="exascale", name="Exascale rack ×32", config=EXASCALE_32,
                 blurb="The meta-sim: partition the pool, feed the GPUs."),
]

# --- Workload presets (spec 02's generator) --------------------------------

OLTP = Workload(iops_demand_k=300, block_kb=8, read_pct=70, sequential_pct=5,
                working_set_fit_pct=80, ingest_tb_day=1, reduction_ratio=3)
VDI = Workload(iops_demand_k=200, block_kb=16, read_pct=60, sequential_pct=10,
               working_set_fit_pct=70, ingest_tb_day=0.5, reduction_ratio=6)
BACKUP = Workload(iops_demand_k=40, block_kb=512, read_pct=5, sequential_pct=95,
                  working_set_fit_pct=5, ingest_tb_day=40, reduction_ratio=8)
STREAMING = Workload(iops_demand_k=60, block_kb=1024, read_pct=98,
                     sequential_pct=98, working_set_fit_pct=10,
                     ingest_tb_day=2, reduction_ratio=1.2)
AI_READ = Workload(iops_demand_k=2000, block_kb=1024, read_pct=95,
                   sequential_pct=90, working_set_fit_pct=15,
                   ingest_tb_day=5, reduction_ratio=1.5)
ANALYTICS = Workload(iops_demand_k=500, block_kb=128, read_pct=90,
                     sequential_pct=70, working_set_fit_pct=30,
                     ingest_tb_day=8, reduction_ratio=2.5)

WORKLOAD_PRESETS = [
    WorkloadPreset(id="oltp", name="OLTP database", workload=OLTP),
    WorkloadPreset(id="vdi", name="VDI", workload=VDI),
    WorkloadPreset(id="backup", name="Backup target", workload=BACKUP),
    WorkloadPreset(id="streaming", name="Media streaming", workload=STREAMING),
    WorkloadPreset(id="ai", name="AI training read", workload=AI_READ),
    WorkloadPreset(id="analytics", name="Analytics scan", workload=ANALYTICS),
]

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="find-the-knee",
        title="Find the knee",
        narration=[
            L(
                novice=(
                    "A database asks this two-controller array for more "
                    "and more work: the demand doubles twice during the "
                    "run. Watch the response-time chart. For a long "
                    "while, more work costs almost nothing — then, past "
                    "a point, the same small increase in demand doubles "
                    "and redoubles the wait. That bend is the knee, and "
                    "it is the single most important shape in storage: "
                    "every sizing argument is an argument about where "
                    "the knee sits."
                ),
                standard=(
                    "OLTP demand steps 300k → 600k → 780k IOPS against "
                    "a two-appliance PowerStore (ceiling ≈ 800k). "
                    "Latency = service × 1/(1−ρ): flat through ρ=0.5, "
                    "×2 by ρ=0.75, vertical past 0.9 — the knee. Note "
                    "the delivered-vs-demanded gap opening only after "
                    "saturation: the array protects itself by queueing, "
                    "and the queue is the latency. Same curve, every "
                    "product in this app; only the ceiling moves."
                ),
                expert=(
                    "ρ steps 0.37/0.75/0.97 on 1/(1−ρ). Flat, ×2, "
                    "vertical. The ceiling varies by product; the "
                    "curve never does."
                ),
            ),
        ],
        question="At what fraction of the ceiling did latency double from its floor?",
        scenario=Scenario(
            config=POWERSTORE_2, workload=OLTP, duration_h=72,
            events=[
                SimEvent(at_h=24, action="set-workload",
                         workload=OLTP.model_copy(update={"iops_demand_k": 600})),
                SimEvent(at_h=48, action="set-workload",
                         workload=OLTP.model_copy(update={"iops_demand_k": 780})),
            ],
        ),
    ),
    GuidedScenario(
        id="controller-failover",
        title="Controller failover under load",
        narration=[
            L(
                novice=(
                    "Halfway through a busy day, one of the array's two "
                    "controller computers dies. Nothing goes offline — "
                    "that is the design working — but the survivor now "
                    "does both jobs, and the response-time curve bends "
                    "at half the old demand. The array didn't get "
                    "slower; its ceiling got lower. Watch the same "
                    "workload land on the other side of the knee."
                ),
                standard=(
                    "VDI at ~50% of the pair's ceiling; at hour 24 one "
                    "controller fails. Front-end capability halves, the "
                    "same demand becomes ρ≈1, and latency jumps from "
                    "the flat part of the curve to the wall — availability "
                    "preserved, headroom spent. This is why arrays are "
                    "sized to run each controller below 50%: the spare "
                    "half is the failover plan."
                ),
                expert=(
                    "ρ 0.5 → ~1.0 on failover. Uptime kept, knee "
                    "crossed. The 50%-per-controller sizing rule, "
                    "demonstrated."
                ),
            ),
        ],
        question="What did latency do at the failover instant, and what would it have done at 40% load?",
        scenario=Scenario(
            config=POWERSTORE_2, workload=VDI.model_copy(update={"iops_demand_k": 400}),
            duration_h=72,
            events=[SimEvent(at_h=24, action="fail-controller")],
        ),
    ),
    GuidedScenario(
        id="snapshot-bill",
        title="The snapshot bill",
        narration=[
            L(
                novice=(
                    "This run lasts ninety simulated days. The array "
                    "ingests data steadily, and every half hour it "
                    "takes a snapshot — a frozen copy that quietly "
                    "keeps old blocks alive. Watch the capacity gauge: "
                    "the data grows linearly, but the snapshot share "
                    "compounds, and the 80/90/95% alarms arrive months "
                    "before anyone planned. Snapshots are not free; "
                    "they are a mortgage on change."
                ),
                standard=(
                    "90 sim-days, steady ingest, 48 snapshots/day: "
                    "used = ingest/reduction + snapshot overhead, and "
                    "the snapshot term compounds with the change rate "
                    "until the 80/90/95% alerts fire in sequence. The "
                    "fix is policy, not hardware — retention and "
                    "schedule are capacity decisions. Check the "
                    "final-used figure against the same run with 4 "
                    "snapshots/day."
                ),
                expert=(
                    "used = ingest/DRR + Σsnap(change); aggressive "
                    "schedule compounds → alert ladder. Retention "
                    "policy is a capacity dial."
                ),
            ),
        ],
        question="On which sim-day does the 90% alert fire, and what fraction of used capacity is snapshots by then?",
        scenario=Scenario(
            config=POWERSTORE_2,
            workload=OLTP.model_copy(update={
                "ingest_tb_day": 8.0, "snapshots_per_day": 48,
            }),
            duration_h=2160,
        ),
    ),
    GuidedScenario(
        id="sync-distance",
        title="Why sync replication has a distance limit",
        narration=[
            L(
                novice=(
                    "This array refuses to acknowledge a write until a "
                    "second array — hundreds of kilometers away — also "
                    "has it. Light in glass fiber travels about two "
                    "hundred kilometers per millisecond, and the "
                    "confirmation must come back, so every kilometer "
                    "of distance taxes every single write, forever. "
                    "The run moves the partner site from next door to "
                    "800 km away: watch write latency climb with "
                    "nothing but geography changing. This is why "
                    "'zero data loss' protection has a radius."
                ),
                standard=(
                    "Sync SRDF at 0, then 300, then 800 km (workload "
                    "events swap the config's distance via demand — "
                    "here, three runs in one: watch the srdf-latency "
                    "instrument). The penalty is distance × 0.01 ms/km "
                    "× 2 on the write fraction — speed of light in "
                    "fiber, the one constant in this app that is not "
                    "an estimate. Past ~100–200 km the tax dominates "
                    "flash latency entirely, which is why metro sync "
                    "pairs are metro."
                ),
                expert=(
                    "+d×0.02 ms on writes. 800 km = +16 ms against a "
                    "0.1 ms medium. c is the vendor nobody negotiates "
                    "with."
                ),
            ),
        ],
        question="At what distance does the light tax exceed 10× the media latency?",
        scenario=Scenario(
            config=POWERMAX_4.model_copy(update={"srdf": "sync", "distance_km": 800}),
            workload=OLTP, duration_h=48,
        ),
    ),
    GuidedScenario(
        id="async-rpo",
        title="Async RPO under a write burst",
        narration=[
            L(
                novice=(
                    "The faraway copy is now updated in the background "
                    "— writes acknowledge locally and replicate when "
                    "the link allows. The cost is honesty about loss: "
                    "the RPO gauge shows how many seconds of recent "
                    "data would vanish if the site died right now. "
                    "Watch a six-hour write burst outrun the "
                    "replication link: the backlog grows, the RPO "
                    "climbs, and it takes hours after the burst for "
                    "the gauge to fall back to near zero."
                ),
                standard=(
                    "Async SRDF: RPO = backlog ÷ link rate. At hour 12 "
                    "a ×5 write burst outruns the 1 GB/s link for six "
                    "hours; the backlog integrates the excess and the "
                    "RPO gauge climbs, then drains after the burst. "
                    "Sync mode's distance tax bought zero RPO; async "
                    "buys back latency and pays in this gauge. There "
                    "is no third option — only this trade at different "
                    "prices."
                ),
                expert=(
                    "RPO = ∫max(0, W−link)/link. Burst ×5 for 6 h → "
                    "climb, then drain. Sync vs async is one trade, "
                    "priced two ways."
                ),
            ),
        ],
        question="What peak RPO did the burst buy, and how long did the drain take?",
        scenario=Scenario(
            config=POWERMAX_4.model_copy(update={"srdf": "async"}),
            workload=OLTP.model_copy(update={"read_pct": 40, "iops_demand_k": 150}),
            duration_h=72,
            events=[SimEvent(at_h=12, action="write-burst", value=5)],
        ),
    ),
    GuidedScenario(
        id="scale-out-rebuild",
        title="Scale-up vs scale-out rebuild",
        narration=[
            L(
                novice=(
                    "A fifteen-terabyte drive dies in a twenty-node "
                    "cluster. Instead of one controller grinding "
                    "through the rebuild for hours, every surviving "
                    "node rebuilds a small slice at once — done in "
                    "under an hour, and a bigger cluster would be "
                    "faster still. Run the same failure on the "
                    "PowerStore preset and compare: same drive, same "
                    "data, opposite arithmetic. Growth making recovery "
                    "faster is the deepest argument for scale-out."
                ),
                standard=(
                    "A 15.36 TB drive fails at hour 6 in a 20-node "
                    "PowerScale: rebuild rate = per-node contribution "
                    "× 19 survivors ≈ 9.5 GB/s → well under an hour, "
                    "with the exposure flag barely lit. The identical "
                    "event on PowerStore runs at the controller's "
                    "1.2 GB/s ≈ 3.5 h. The rebuild-window risk gauge "
                    "is the real product here: it is exposure time, "
                    "and scale-out shrinks it with every node added."
                ),
                expert=(
                    "rate ∝ survivors: 19×0.5 ≈ 9.5 GB/s vs 1.2 fixed "
                    "→ ~25 min vs ~3.5 h. Exposure window is the "
                    "metric that matters."
                ),
            ),
        ],
        question="How long was the exposure window here versus on the PowerStore preset?",
        scenario=Scenario(
            config=POWERSCALE_20, workload=ANALYTICS, duration_h=24,
            events=[SimEvent(at_h=6, action="fail-drive")],
        ),
    ),
    GuidedScenario(
        id="network-is-the-array",
        title="The network IS the array",
        narration=[
            L(
                novice=(
                    "Twenty fast servers full of fast drives — "
                    "connected, in this run, by modest 10-gigabit "
                    "network cards. Watch the ceiling: the pool "
                    "delivers a fraction of what its drives could, "
                    "because every byte must cross the network and "
                    "the network is full. Re-run with the 100-gigabit "
                    "preset and the same drives go seven times "
                    "faster. In software-defined storage, the network "
                    "card is the component that decides what you "
                    "bought."
                ),
                standard=(
                    "PowerFlex at 10 GbE: aggregate = min(node "
                    "ceilings ≈ 3000k, NIC term ≈ 1500k at 8K after "
                    "the mirror-write share) — network-bound, and the "
                    "fabric block on the map saturates first. The "
                    "100 GbE preset moves the min() back to the "
                    "nodes. The validation panel says it before the "
                    "run does: buy bandwidth before drives."
                ),
                expert=(
                    "cap = min(Σnode, ΣNIC/2/blk): 10G binds at ~½ "
                    "node ceiling; 100G frees it. The NIC is the "
                    "array."
                ),
            ),
        ],
        question="Where did the ceiling move when the NICs went from 10 to 100 GbE?",
        scenario=Scenario(
            config=POWERFLEX_20.model_copy(update={"nic_gbps": 10}),
            workload=OLTP.model_copy(update={"iops_demand_k": 2500}),
            duration_h=48,
        ),
    ),
    GuidedScenario(
        id="immutable-bucket",
        title="The immutable bucket",
        narration=[
            L(
                novice=(
                    "Twice during this run, something tries to delete "
                    "the archive — once politely, once at the worst "
                    "moment. The bucket refuses both times: it is "
                    "write-once storage, locked by policy that even "
                    "an administrator cannot lift early. The event "
                    "log records the bounces; the capacity line "
                    "doesn't flinch. This is the property backup "
                    "vaults are built on, and the resilience "
                    "simulator (PhysicsResilience) picks the story up "
                    "from here."
                ),
                standard=(
                    "ObjectScale with object lock: attempt-delete "
                    "events at hours 12 and 30 bounce with WORM log "
                    "lines and used capacity unchanged — the negative "
                    "result is the demonstration. Note the object "
                    "personality around it: ms-class latency floor "
                    "nobody minds, HDD-dense EC 16+4, and the "
                    "small-object toggle available to show the "
                    "metadata tax. The vault half of this story is "
                    "PhysicsResilience's."
                ),
                expert=(
                    "WORM: deletes bounce, capacity flat, log tells "
                    "it. 16+4 on HDD, ms floor by design. The vault "
                    "substrate."
                ),
            ),
        ],
        question="What does the log show at hours 12 and 30, and what does the used-capacity line show?",
        scenario=Scenario(
            config=OBJECTSCALE_12, workload=BACKUP, duration_h=48,
            events=[
                SimEvent(at_h=12, action="attempt-delete"),
                SimEvent(at_h=30, action="attempt-delete"),
            ],
        ),
    ),
    GuidedScenario(
        id="right-size-the-mix",
        title="Right-size the mix",
        narration=[
            L(
                novice=(
                    "One rack of storage servers feeds a training "
                    "cluster, and you decide how many servers play "
                    "which role. In this starting split, the "
                    "fast-feed pool is too small: watch the "
                    "GPU-idle gauge — the percentage of time the "
                    "expensive computers wait for data — sit "
                    "stubbornly above zero, and spike when the "
                    "periodic checkpoint bursts land. Repartition in "
                    "the build panel until the gauge sleeps. That "
                    "gauge is the only score that counts here."
                ),
                standard=(
                    "The Exascale meta-sim with a deliberately "
                    "lopsided partition (8 Lightning nodes carrying "
                    "60% of an AI-read-heavy profile): the Lightning "
                    "pool runs past saturation, GPU-idle-due-to-data "
                    "sits above zero, and the 6-hourly checkpoint "
                    "stampedes (writes ×6) spike it. Rebalance toward "
                    "the preset's 16/6/6/4 and the gauge falls to "
                    "~0 — the compute app's data-feed slider, solved "
                    "from the supply side. Build last, the spec says: "
                    "this is why."
                ),
                expert=(
                    "Lopsided partition → Lightning ρ>1 → GPU idle >0, "
                    "checkpoint spikes ×6. Repartition to 16/6/6/4 → "
                    "idle ≈ 0. The capstone dial."
                ),
            ),
        ],
        question="Which pool saturates, and what partition puts the GPU-idle gauge to sleep?",
        scenario=Scenario(
            config=EXASCALE_32.model_copy(update={
                "lightning_units": 8, "file_units": 10,
                "object_units": 10, "block_units": 4,
            }),
            workload=AI_READ, duration_h=48,
        ),
    ),
]

# --- Explain-mode entries --------------------------------------------------

EXPLAINS = [
    Explain(
        id="queueing",
        title="The queueing knee",
        equation="latency = service_time × 1 / (1 − ρ),  ρ = demand / capacity",
        inputs=["demand", "capacity", "utilization ρ", "latency", "p99"],
        explanation=L(
            novice=(
                "Response time has two parts: the work itself, and the "
                "waiting in line. The line is the interesting part — "
                "nearly empty until the system approaches full, then "
                "growing without bound. Halve the load on a struggling "
                "system and it usually becomes instant; that is the "
                "knee working in reverse."
            ),
            standard=(
                "The M/M/1-shaped multiplier 1/(1−ρ) on the "
                "cache-weighted service time: ×2 at ρ=0.5, ×10 at "
                "ρ=0.9, clamped at 0.98 to keep the sim finite. The "
                "same curve prices the fabric app's links — spec 03 "
                "points at this equation deliberately. Every product "
                "here changes only the denominator."
            ),
            expert=(
                "service/(1−min(ρ,0.98)); p99 ≈ ×3. Products move "
                "capacity; the curve is universal (see PhysicsFabric's "
                "links)."
            ),
        ),
    ),
    Explain(
        id="capacity",
        title="Capacity arithmetic",
        equation="usable = raw × (1 − protection);  effective = usable × reduction",
        inputs=["raw TB", "protection", "usable TB", "reduction ratio", "effective TB"],
        explanation=L(
            novice=(
                "Three numbers get called 'capacity'. Raw is the sum "
                "of the drives. Usable subtracts the redundancy that "
                "survives failures. Effective multiplies by how well "
                "your data squeezes — a hopeful number, workload-"
                "dependent, and the one on the brochure. Buy usable; "
                "hope for effective."
            ),
            standard=(
                "Raw → usable via the protection scheme's arithmetic "
                "(mirror 50%, RAID 6 25%, EC 8+2 20%) → effective via "
                "the reduction ratio, which is a property of the data, "
                "not the array (the workload presets carry honest "
                "ones: OLTP 3:1, media 1.2:1). Used fills at "
                "ingest/reduction plus the snapshot term, and the "
                "80/90/95 ladder fires on usable — the number that "
                "cannot be negotiated with."
            ),
            expert=(
                "raw·(1−ovh)·DRR; DRR is the workload's property. "
                "Alerts ladder on usable. Snapshots compound with "
                "change rate."
            ),
        ),
    ),
    Explain(
        id="rebuild",
        title="Rebuild time & the exposure window",
        equation="hours = drive_TB × 1000 / (rate_GB/s × 3600);  rate ∝ survivors (scale-out)",
        inputs=["drive size", "rebuild rate", "survivors", "hours", "exposure"],
        explanation=L(
            novice=(
                "After a drive dies, the system is racing: it must "
                "recreate that drive's data before a second failure "
                "lands. A traditional array rebuilds through one "
                "controller — hours, growing with every drive-size "
                "generation. A cluster rebuilds everywhere at once, "
                "so bigger clusters finish faster. The time spent "
                "racing is the exposure window, and it is the number "
                "that should keep planners honest."
            ),
            standard=(
                "Controller arrays rebuild at a fixed ~1.2 GB/s "
                "budget (host I/O competing, the ×1.6 latency "
                "penalty); scale-out rebuilds at per-node rate × "
                "survivors — PowerScale ~0.5 GB/s/node, PowerFlex "
                "~2 GB/s/node, which is how 'the 60-second rebuild' "
                "happens. The exposure flag marks when failures-in-"
                "window equal what the protection survives: that "
                "duration, not IOPS, is the resilience spec."
            ),
            expert=(
                "Fixed-budget vs ∝survivors; PFlex ~4× NAS/node. "
                "Exposure = window at survives-limit. Drive growth "
                "made R5 obsolete; this is the same clock."
            ),
        ),
    ),
    Explain(
        id="srdf",
        title="Replication: light and backlog",
        equation="sync: +d × 0.01 × 2 ms per write;  async: RPO = backlog / link",
        inputs=["distance", "write fraction", "latency tax", "backlog", "RPO"],
        explanation=L(
            novice=(
                "Keeping a second copy far away costs one of two "
                "currencies. Wait for the far copy on every write and "
                "you pay in speed — light needs a millisecond per "
                "hundred kilometers of round trip. Copy in the "
                "background and you pay in honesty: some seconds of "
                "recent work would be lost in a disaster, and the RPO "
                "gauge says how many. Pick a currency; there is no "
                "free one."
            ),
            standard=(
                "Sync: distance × 0.01 ms/km each way on the write "
                "fraction — fiber-optic light speed, this app's only "
                "non-estimate performance constant. Async: the "
                "backlog integrates writes minus link and RPO = "
                "backlog/link, growing under bursts and draining "
                "after. The two modes are one trade priced in "
                "latency or in loss; the distance slider and the "
                "write-burst event let you shop both."
            ),
            expert=(
                "c/1.5 ≈ 200 km/ms → 0.02 ms/km RT. RPO = ∫(W−L)/L. "
                "Latency or loss; geography sets the exchange rate."
            ),
        ),
    ),
    Explain(
        id="gpu-idle",
        title="GPU idle due to data",
        equation="idle % = 1 − delivered_reads / demanded_reads",
        inputs=["read demand", "pool capacity", "delivered", "GPU idle %"],
        explanation=L(
            novice=(
                "The Exascale scoreboard: what fraction of the time "
                "the training computers sit waiting because this "
                "rack couldn't feed them. Storage people watch IOPS; "
                "the people paying for GPUs watch this. When it is "
                "zero, the storage is invisible — which is the only "
                "compliment storage gets."
            ),
            standard=(
                "The supply-side view of PhysicsCompute's data-feed "
                "slider: undelivered read demand, as a percentage. "
                "Each partitioned pool serves its share; the "
                "Lightning pool carries the training feed, so its "
                "saturation shows up here first. The checkpoint "
                "stampede (writes ×6, every 6 h) tests whether the "
                "mix survives its own success."
            ),
            expert=(
                "1 − min(D,C)/D on the read stream, pool-shared. "
                "Compute app's feed slider, inverted. Lightning "
                "binds first; checkpoints stress-test the split."
            ),
        ),
    ),
]
