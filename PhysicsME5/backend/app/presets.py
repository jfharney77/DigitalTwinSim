"""Presets and the teaching layer — backend data.

Config presets, workload presets, guided scenarios (scripted walkthroughs
that set the scenario and narrate what to watch), and Explain-mode
entries (the equation behind each key readout, with placeholders the
frontend substitutes with live values). Explain and scenario prose
carries reading levels.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    ArrayConfig,
    ConfigPreset,
    Explain,
    GuidedScenario,
    Scenario,
    SimEvent,
    Workload,
    WorkloadPreset,
)

# --- Config presets --------------------------------------------------------

ENTRY = ArrayConfig(
    model="ME5012", drive_type="hdd-10k", drive_count=6, drive_tb=4,
    raid_level="5", spares=1, controllers=2, host_interface="iSCSI",
)

R10_PERF = ArrayConfig(
    model="ME5024", drive_type="hdd-10k", drive_count=24, drive_tb=4,
    raid_level="10", spares=0, controllers=2, host_interface="FC",
)

R6_CAPACITY = ArrayConfig(
    model="ME5012", drive_type="hdd-7.2k", drive_count=12, drive_tb=20,
    raid_level="6", spares=1, controllers=2, host_interface="iSCSI",
)

ALL_FLASH = ArrayConfig(
    model="ME5024", drive_type="ssd", drive_count=24, drive_tb=8,
    raid_level="6", spares=1, controllers=2, host_interface="FC",
)

CONFIG_PRESETS = [
    ConfigPreset(id="entry", name="Entry", config=ENTRY,
                 blurb="6× 10k HDD, RAID 5 + spare — the small-office baseline."),
    ConfigPreset(id="r10-perf", name="RAID 10 performance", config=R10_PERF,
                 blurb="24× 10k HDD mirrored — write penalty ×2, half the capacity."),
    ConfigPreset(id="r6-capacity", name="RAID 6 capacity", config=R6_CAPACITY,
                 blurb="12× 20 TB NL-SAS, dual parity — big, slow, rebuilds in days."),
    ConfigPreset(id="all-flash", name="All-flash", config=ALL_FLASH,
                 blurb="24 SSDs — the drives stop being the bottleneck; the controllers start."),
]

# --- Workload presets ------------------------------------------------------

IDLE = Workload(offered_kiops=0.2, read_pct=70, block_kb=8)
OLTP = Workload(offered_kiops=3.0, read_pct=70, block_kb=8)
VDI = Workload(offered_kiops=2.0, read_pct=40, block_kb=4)
BACKUP = Workload(offered_kiops=1.5, read_pct=5, block_kb=256)
ANALYTICS = Workload(offered_kiops=4.0, read_pct=95, block_kb=64)
FLASH_OLTP = Workload(offered_kiops=400.0, read_pct=70, block_kb=8)

WORKLOAD_PRESETS = [
    WorkloadPreset(id="idle", name="Idle", workload=IDLE),
    WorkloadPreset(id="oltp", name="OLTP database", workload=OLTP),
    WorkloadPreset(id="vdi", name="VDI (write-heavy)", workload=VDI),
    WorkloadPreset(id="backup", name="Backup target", workload=BACKUP),
    WorkloadPreset(id="analytics", name="Analytics (read)", workload=ANALYTICS),
    WorkloadPreset(id="flash-oltp", name="All-flash OLTP", workload=FLASH_OLTP),
]

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="write-penalty",
        title="RAID write penalty",
        narration=[
            L(
                novice=(
                    "Twenty-four identical drives, mirrored (RAID 10), "
                    "under a write-heavy load. Note the number of disk "
                    "operations the array performs for every write the "
                    "servers send — two, because a mirror keeps two "
                    "copies. Now switch the build to RAID 6 in the panel "
                    "and run again: the same drives suddenly serve far "
                    "fewer writes, because each write now costs six disk "
                    "operations — the array must read the old data and "
                    "both parity blocks, then write all three back. Same "
                    "hardware, three times less write performance: that "
                    "is the price of the extra safety."
                ),
                standard=(
                    "The same 24 spindles under a write-heavy mix, RAID "
                    "10 first. Watch the backend-ops readout: each host "
                    "write becomes 2 disk I/Os. Flip the build to RAID 6 "
                    "and the multiplier becomes 6 (read data + two "
                    "parities, write all three) — served write IOPS "
                    "drops by exactly the 6:2 penalty ratio while the "
                    "drives work just as hard. Explain mode shows the "
                    "live arithmetic; the ledger is asserted per tick, "
                    "not merely charted."
                ),
                expert=(
                    "24 spindles, 30/70 mix. R10: wp=2. Re-run R6: wp=6, "
                    "served writes ÷3 at identical disk budget. Ledger "
                    "asserted per tick."
                ),
            ),
        ],
        question="At the same disk budget, what ratio of write IOPS do you measure between RAID 10 and RAID 6?",
        scenario=Scenario(
            config=R10_PERF,
            workload=Workload(offered_kiops=6.0, read_pct=30, block_kb=8),
            duration_min=240, tick_minutes=1,
        ),
    ),
    GuidedScenario(
        id="rebuild-20tb",
        title="Rebuild a 20 TB drive",
        narration=[
            L(
                novice=(
                    "A 20-terabyte drive dies at minute 60. The hot "
                    "spare jumps in and the array starts copying the "
                    "missing data onto it — but copying twenty terabytes "
                    "through a busy array takes days, not minutes. The "
                    "whole time, the risk gauge stays lit: with RAID 6 "
                    "the array can still survive one more failure, which "
                    "is exactly why RAID 6 exists. Try the same run with "
                    "RAID 5 and watch the gauge go red — one more "
                    "failure during those days would lose everything."
                ),
                standard=(
                    "One 20 TB NL-SAS member fails at t+60 min under a "
                    "steady load; the spare takes over and the rebuild "
                    "window opens. At ~50 MB/s effective (host load "
                    "slows it further), the window is measured in days — "
                    "the ticks are hours here for that reason. RAID 6 "
                    "holds a second parity through the window, so the "
                    "risk index stays low; rerun as RAID 5 and the same "
                    "window is one failure from loss. Drives grew into "
                    "this arithmetic; that is why RAID 6 displaced "
                    "RAID 5."
                ),
                expert=(
                    "20 TB member out at t+60. Window ≈ TB/(50 MB/s × "
                    "load derate) ≈ days. R6 risk low; R5 same window, "
                    "red. QED dual parity."
                ),
            ),
        ],
        question="How many hours does this rebuild take, and what happens to that number when you double the offered load?",
        scenario=Scenario(
            config=R6_CAPACITY,
            workload=Workload(offered_kiops=0.4, read_pct=60, block_kb=64),
            duration_min=10080, tick_minutes=60,
            events=[SimEvent(at_min=60, action="fail-drive", index=3)],
        ),
    ),
    GuidedScenario(
        id="second-failure",
        title="Second failure, mid-rebuild",
        narration=[
            L(
                novice=(
                    "The nightmare scenario, run twice by you: a drive "
                    "dies, the rebuild begins, and days before it "
                    "finishes a second drive dies. This build is RAID 6, "
                    "so the array shrugs — dual parity means it can lose "
                    "two members and keep serving, degraded but alive. "
                    "Switch the build to RAID 5 and repeat: the second "
                    "failure is the end. The array goes offline and the "
                    "data is gone. Every backup-and-restore story you "
                    "have heard starts at this moment."
                ),
                standard=(
                    "A member fails at t+60 and a second at t+1500, deep "
                    "inside the first rebuild window. RAID 6 tolerates "
                    "two concurrent losses: service continues, reads pay "
                    "the reconstruct tax, the rebuilds queue. Flip to "
                    "RAID 5 and the second failure exceeds tolerance — "
                    "the array goes offline with data loss, which is "
                    "precisely what the risk gauge was pricing during "
                    "the window."
                ),
                expert=(
                    "Failures at t+60 and t+1500 inside the window. R6: "
                    "degraded ×2, serving. R5: over tolerance, offline, "
                    "loss. The gauge was the point."
                ),
            ),
        ],
        question="Run this on RAID 5 — at what point exactly does the array die, and what did the risk gauge read just before?",
        scenario=Scenario(
            config=R6_CAPACITY,
            workload=Workload(offered_kiops=0.4, read_pct=60, block_kb=64),
            duration_min=10080, tick_minutes=60,
            events=[
                SimEvent(at_min=60, action="fail-drive", index=3),
                SimEvent(at_min=1500, action="fail-drive", index=7),
            ],
        ),
    ),
    GuidedScenario(
        id="controller-failover",
        title="Lose a controller",
        narration=[
            L(
                novice=(
                    "Storage arrays have two controller computers so "
                    "that one can fail without the servers noticing. At "
                    "minute 120 one of them dies. Service continues — "
                    "that is the headline — but look closer: the "
                    "survivor now answers for everything, and the write "
                    "cache can no longer keep a safety copy on its dead "
                    "partner, so every write must wait for the actual "
                    "drives. Latency rises. Redundancy works, and it is "
                    "never free."
                ),
                standard=(
                    "Controller A drops at t+120 under an OLTP load. "
                    "Service survives — the active-active pair is why — "
                    "but the survivor owns all volumes (front-end "
                    "ceiling halves) and, with no partner to mirror "
                    "into, write cache falls to write-through: the RAID "
                    "write penalty stops hiding behind the cache and "
                    "walks straight into host latency."
                ),
                expert=(
                    "Ctrl A out at t+120. Service holds; FE cap halves; "
                    "cache → write-through; latency shows the penalty "
                    "raw."
                ),
            ),
        ],
        question="What did latency do at the failover — and which part of the rise is the cache mode, not the ceiling?",
        scenario=Scenario(
            config=R10_PERF,
            workload=Workload(offered_kiops=5.0, read_pct=70, block_kb=8),
            duration_min=480, tick_minutes=1,
            events=[SimEvent(at_min=120, action="fail-controller")],
        ),
    ),
    GuidedScenario(
        id="flash-ceiling",
        title="Where all-flash hits the ceiling",
        narration=[
            L(
                novice=(
                    "Fill the shelf with SSDs and the drives stop being "
                    "the slow part — twenty-four of them could serve "
                    "hundreds of thousands of operations per second. So "
                    "why does the array level off? Because now the "
                    "controllers are the bottleneck: the two computers "
                    "at the back can only push so much traffic no "
                    "matter how fast the drives behind them are. Every "
                    "storage system has a next bottleneck waiting; "
                    "flash just moves the queue."
                ),
                standard=(
                    "24 SSDs at a 70/30 mix with the offered load "
                    "climbing mid-run. The disk budget is enormous — "
                    "spindle arithmetic no longer binds — and the array "
                    "saturates anyway, flat against the per-controller "
                    "front-end ceiling. Kill a controller at t+300 and "
                    "the ceiling halves on the spot. On spindles you "
                    "never see this line; on flash it is the first "
                    "thing you hit."
                ),
                expert=(
                    "24× SSD, offered ramps past FE cap: disk_scale=1, "
                    "fe_scale binds. Ctrl loss at t+300 halves the "
                    "ceiling. Flash relocates the bottleneck."
                ),
            ),
        ],
        question="What served-IOPS ceiling do you hit with both controllers, and where does it move when one fails?",
        scenario=Scenario(
            config=ALL_FLASH,
            workload=Workload(offered_kiops=250.0, read_pct=70, block_kb=8),
            duration_min=600, tick_minutes=1,
            events=[
                SimEvent(at_min=150, action="set-offered", value=500),
                SimEvent(at_min=300, action="fail-controller"),
            ],
        ),
    ),
]

# --- Explain-mode entries ---------------------------------------------------

EXPLAINS = [
    Explain(
        id="write-penalty",
        title="RAID write penalty",
        equation="disk I/Os = reads × read_cost + writes × penalty  (R1/10: ×2 · R5: ×4 · R6: ×6)",
        inputs=["host writes", "RAID level", "backend disk I/O", "disk utilization", "served IOPS"],
        explanation=L(
            novice=(
                "Protecting data means writing it more than once. A "
                "mirror simply writes two copies. The parity schemes "
                "are cleverer with space but costlier in motion: to "
                "update one small block, RAID 5 must read the old data "
                "and the old parity, compute, and write both back — "
                "four operations for one write. RAID 6 keeps two "
                "parities, so six. This multiplication happens on every "
                "single write, forever, and is the main reason the "
                "same drives feel fast under one layout and slow under "
                "another."
            ),
            standard=(
                "Every host write is multiplied before it reaches a "
                "drive: ×2 mirrored (two copies), ×4 RAID 5 "
                "(read-modify-write against one parity), ×6 RAID 6 "
                "(against two). Reads cost 1 healthy, ~2 while a "
                "parity group is degraded (stripe reconstruct). The "
                "backend ledger is exact arithmetic, asserted per tick "
                "— the sim's conservation identity."
            ),
            expert=(
                "wp ∈ {2,4,6} by level; RMW cycle is the ×4/×6. "
                "Degraded read_cost ≈ 2. Ledger asserted per tick."
            ),
        ),
    ),
    Explain(
        id="usable-capacity",
        title="Usable capacity",
        equation="raw = usable + protection overhead + spares  (exact)",
        inputs=["drive count", "drive size", "RAID level", "spares", "usable TB"],
        explanation=L(
            novice=(
                "You never get to use everything you bought. Mirroring "
                "keeps a full second copy, so half the space is "
                "protection. RAID 5 gives one drive's worth to parity; "
                "RAID 6 gives two. Hot spares sit empty on purpose, "
                "waiting for a failure. The bar in the instruments "
                "shows exactly where every terabyte went — nothing is "
                "lost, it is all accounted for."
            ),
            standard=(
                "The capacity ledger closes exactly: raw drive TB "
                "splits into usable (what hosts see), protection "
                "overhead (the mirror half, or 1–2 members' worth of "
                "parity), and idle spares. R10 usable = n/2; R5 = n−1 "
                "members; R6 = n−2. Asserted per tick as this sim's "
                "capacity-conservation identity."
            ),
            expert=(
                "usable: R10 n/2 · R5 n−1 · R6 n−2 (×TB); raw − usable "
                "− spare = overhead, exact, asserted."
            ),
        ),
    ),
    Explain(
        id="rebuild-time",
        title="Rebuild window",
        equation="hours = TB × 1000 ÷ (rate × (1 − 0.5 × load) × 3.6)",
        inputs=["drive size", "rebuild rate", "host load", "hours remaining", "risk index"],
        explanation=L(
            novice=(
                "After a drive dies, the array must recreate everything "
                "that was on it, onto the spare, while still serving "
                "the servers. Big modern drives make this slow: twenty "
                "terabytes at a realistic fifty megabytes per second is "
                "the better part of a week. The busier the array, the "
                "slower the rebuild — and the entire time, another "
                "failure is more dangerous than usual. That danger "
                "window is why double-parity RAID 6 took over from "
                "RAID 5 as drives grew."
            ),
            standard=(
                "The rebuild window is drive capacity over an effective "
                "rate — ~50 MB/s for spindles once host I/O and "
                "verification are paid, further derated as utilization "
                "rises. 20 TB ≈ 111 h unloaded, longer in practice. "
                "During the window RAID 5 has no parity left and "
                "RAID 6 has one; the risk index prices exactly that "
                "difference against the hours remaining."
            ),
            expert=(
                "window = TB/(rate·(1−0.5u)); 20 TB @50 MB/s ≈ 4.6 d. "
                "R5 in-window tolerance 0, R6 1 — the gauge is that "
                "times the clock."
            ),
        ),
    ),
    Explain(
        id="latency-knee",
        title="Latency and the queue knee",
        equation="latency ≈ service_time ÷ (1 − utilization) + overheads",
        inputs=["offered load", "disk utilization", "latency", "saturation"],
        explanation=L(
            novice=(
                "A drive that is half busy answers almost as fast as an "
                "idle one. A drive that is nearly always busy makes "
                "every request wait in line behind others, and the line "
                "grows explosively as you approach fully busy — the "
                "same reason a highway at 95% capacity is a parking "
                "lot. Storage people live at the base of this curve "
                "and size systems to never climb it."
            ),
            standard=(
                "Service time is the drive's mechanical constant (~6 ms "
                "for a 10k spindle, ~0.25 ms for an SSD); queueing "
                "divides it by (1 − utilization), so latency is flat "
                "until roughly 70% busy and vertical past 90%. Degraded "
                "mode and failover add their own terms. The knee, not "
                "the average, is what capacity planning is actually "
                "about."
            ),
            expert=(
                "M/M/1 shape: R = S/(1−ρ), capped at ρ=0.95. Add "
                "degraded + failover terms. Plan for the knee."
            ),
        ),
    ),
]
