"""Pure power-on sequence engine for the PowerStore appliance.

``simulate()`` returns the deterministic trace of what happens inside the
array from the moment AC arrives until it is serving I/O. Same purity rule
as the GPU and R760 engines: no FastAPI, no IO, no timers — the frontend
owns the playback clock, and each ``PowerOnState`` is plain data the
renderer consumes. ``cycle_cost`` marks the long stages (PowerStoreOS boot,
pool assembly) so the UI dwells on them.

The storytelling beat that makes an array different from a server: there is
no power button — applying AC *is* the power-on — and everything happens
twice, once per controller node, before the two converge into one
active/active system. Timing and wattage are illustrative but plausible for
a dual-node 2U all-NVMe appliance; favor a correct mental model over
measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import PowerOnState

_PSUS = ["psu-a", "psu-b"]
_BBUS = ["bbu-a", "bbu-b"]
_FANS = ["fans-a", "fans-b"]
_CPUS = ["cpu-a", "cpu-b"]
_BOARDS = ["board-a", "board-b"]
_DIMMS = ["dimm-a", "dimm-b"]
_EMBEDDED = ["embedded-a", "embedded-b"]
_MGMT = ["mgmt-a", "mgmt-b"]
_IOMODS = ["iomod-a1", "iomod-a2", "iomod-b1", "iomod-b2"]


def simulate() -> list[PowerOnState]:
    """The PowerStore's journey from AC plug-in to serving I/O, as pure data."""
    return [
        PowerOnState(
            step=0,
            phase="off",
            label="AC connected",
            description=L(
                novice=(
                    "Both power cords go in — ideally to two separate electrical "
                    "feeds, one for each half of the box. The enclosure is dark: no "
                    "fans, no lights, no power drawn. Unlike a server, nothing "
                    "further is asked of you. A storage array has no power button "
                    "at all, and everything from here happens by itself."
                ),
                plain=(
                    "Two power cords go in, ideally into two different electrical "
                    "feeds so each node has its own. The enclosure sits dark — no "
                    "fans, no lights, nothing drawing power. Nothing further is "
                    "asked of you, because a storage appliance has no power button "
                    "at all. Everything from here happens without anyone touching "
                    "it."
                ),
                standard=(
                    "Both power cords are plugged in — ideally to separate "
                    "feeds, one per node. The enclosure is dark: no fans, no "
                    "LEDs, no draw. Unlike a server, nothing more is required "
                    "of you; a storage appliance has no power button, and what "
                    "happens next is entirely automatic."
                ),
                technical=(
                    "AC present at both cords, ideally from independent feeds, one "
                    "per node. Enclosure dark. No power button exists — the "
                    "appliance model assumes unattended return to service, so the "
                    "sequence from here is fully automatic."
                ),
                expert=(
                    "AC present, independent feeds per node. No power button — "
                    "unattended return to service by design."
                ),
            ),
            active_regions=[],
            power_watts=0,
            fan_percent=0,
            elapsed_seconds=0,
        ),
        PowerOnState(
            step=1,
            phase="power",
            label="PSUs energize — no power button",
            description=L(
                novice=(
                    "Each half's power supply notices there is voltage and brings "
                    "its power up. Applying mains power *is* the switch-on: an "
                    "array is expected to come back into service by itself after "
                    "any outage, with nobody at the rack to press anything. Both "
                    "halves start waking at the same time — and from here on, "
                    "everything in this story happens twice."
                ),
                plain=(
                    "Each node's power supply detects line voltage and brings its "
                    "rails up. Applying AC *is* the power-on: an array is expected "
                    "to return to service by itself after any outage, with no human "
                    "at the rack. Both node canisters begin waking in parallel — "
                    "from here on, everything happens twice."
                ),
                standard=(
                    "Each node's power supply detects line voltage and brings "
                    "its rails up. Applying AC *is* the power-on: an array is "
                    "expected to return to service by itself after any outage, "
                    "with no human at the rack to press anything. Both node "
                    "canisters begin waking in parallel — from here on, "
                    "everything happens twice."
                ),
                technical=(
                    "PSUs detect line voltage and bring rails up. AC application is "
                    "the power-on event — unattended recovery after an outage is a "
                    "requirement, not a convenience. Both canisters wake in "
                    "parallel; every subsequent step is duplicated per node."
                ),
                expert=(
                    "PSUs up on AC detect. AC application is power-on — unattended "
                    "recovery required. Both canisters, in parallel, from here."
                ),
            ),
            active_regions=_PSUS,
            power_watts=60,
            fan_percent=10,
            elapsed_seconds=3,
        ),
        PowerOnState(
            step=2,
            phase="power",
            label="Battery backup self-test",
            description=L(
                novice=(
                    "Each half tests its battery before anything else matters. This "
                    "battery is not there to keep the array running — it cannot. "
                    "Its only job is to keep the write-cache drives powered for the "
                    "short time they need to copy what they hold into their own "
                    "built-in flash if the mains fails. Until both halves know that a power cut is survivable, "
                    "the array will not accept a single write."
                ),
                plain=(
                    "Each node tests its battery backup unit before anything else "
                    "matters. The BBU is not a UPS — it cannot keep the array "
                    "running. Its only job is vaulting: on AC loss it powers the "
                    "NVRAM write-cache drives for the short time they need to copy "
                    "their contents into their own flash. Until both nodes know a power loss is "
                    "survivable, the array will not accept a single write."
                ),
                standard=(
                    "Each node tests its battery backup unit (BBU) before "
                    "anything else matters. The BBU is not a UPS — it cannot "
                    "keep the array running. Its only job is 'vaulting': on AC "
                    "loss it powers the NVRAM write-cache drive slots and the "
                    "node's management controller for the short time the NVRAM "
                    "drives need to copy their volatile contents into their own "
                    "flash. Until both "
                    "nodes know a power loss is survivable, the array will not "
                    "accept a single write."
                ),
                technical=(
                    "Per-node BBU self-test gates everything downstream. The BBU is "
                    "not a UPS and cannot sustain service; its sole function is "
                    "vaulting — powering the NVRAM drive slots and the BMC long "
                    "enough for the NVRAM drives to persist their volatile contents "
                    "to on-drive flash on AC loss. No write is accepted "
                    "until both nodes confirm survivability."
                ),
                expert=(
                    "BBU self-test gates write acceptance. Not a UPS — vault-only: "
                    "holds up NVRAM slots + BMC while NVRAM self-persists on AC loss. No writes until both nodes "
                    "confirm."
                ),
            ),
            active_regions=_BBUS,
            power_watts=90,
            fan_percent=15,
            elapsed_seconds=10,
        ),
        PowerOnState(
            step=3,
            phase="power",
            label="Fan packs spin up",
            description=L(
                novice=(
                    "Both halves' fan packs run up hard, then settle once the "
                    "temperature sensors report in — the same cautious "
                    "maximum-airflow-first approach servers take. Air moves front "
                    "to back: in across the twenty-five drives, through each half, "
                    "and out past its power supply. Each half cools itself, so a "
                    "fan failure on one side never threatens the other."
                ),
                plain=(
                    "The fans in both nodes run up hard and then settle back once "
                    "the temperature sensors have reported in — the same cautious "
                    "assume-the-worst approach the server twins take. Air travels "
                    "front to rear: in across the 25 drives, through each node, and "
                    "out past its power supply. Each node cools only itself, so a "
                    "fan failing on one side is never a problem for the other."
                ),
                standard=(
                    "Both nodes' fan packs run up hard, then settle once "
                    "thermal sensors report in — the same conservative "
                    "max-airflow-first policy servers use. Airflow is front to "
                    "rear: in across the 25 NVMe drives, through each node "
                    "canister, out past its PSU. Each node cools itself; a fan "
                    "failure in one canister never threatens the other."
                ),
                technical=(
                    "Fan packs to full, settling on sensor report — the same "
                    "conservative default the server twins use. Front-to-rear "
                    "airflow across the 25-slot bay, through each canister, "
                    "exhausting past its PSU. Cooling domains are per-node, so a "
                    "fan failure is contained to one canister."
                ),
                expert=(
                    "Fans to full, settle on sensor report. Front-to-rear, per-node "
                    "cooling domains — fan failure contained to one canister."
                ),
            ),
            active_regions=_FANS,
            power_watts=220,
            fan_percent=100,
            elapsed_seconds=15,
        ),
        PowerOnState(
            step=4,
            phase="boot",
            label="Node firmware starts — twice",
            description=L(
                novice=(
                    "Each controller half is a complete computer in its own right, and "
                    "each runs its own start-up firmware from its own flash, powers up "
                    "its own processor, and tests its own memory. The two halves start "
                    "independently and know nothing of each other yet — redundancy "
                    "begins from the assumption that your partner may simply not be "
                    "there. Independently does not mean out of step, though: both "
                    "halves run the same start-up on the same schedule, which is why "
                    "the same part lights on both halves at every step so far."
                ),
                plain=(
                    "Each controller node is a complete x86 computer, and each runs its "
                    "own UEFI firmware from its own flash, sequences power to its own "
                    "Xeon, and tests its own DRAM. The two nodes boot independently and "
                    "know nothing of each other yet — redundancy starts with the "
                    "assumption that the partner may not be there. Independent is not "
                    "the same as out of step: both nodes run the same sequence on the "
                    "same schedule, so the same part lights on both at each step."
                ),
                standard=(
                    "Each controller node is a complete x86 computer, and each runs its "
                    "own BIOS/UEFI firmware from its own flash, sequences power to its "
                    "own Xeon, and tests its own DRAM. The two nodes boot independently "
                    "and know nothing of each other yet — redundancy starts with the "
                    "assumption that the partner may not be there. Independent is not "
                    "out of step: both nodes run the same sequence on the same "
                    "schedule, so the same region lights on both at each step."
                ),
                technical=(
                    "Each node is a complete x86 system: own firmware from own flash, "
                    "own CPU power sequencing, own DRAM test. Independent boots with no "
                    "inter-node state — the redundancy model assumes partner absence "
                    "from the outset. Same sequence, same schedule: the -a and -b "
                    "regions light together."
                ),
                expert=(
                    "Independent x86 boots per node: own firmware, own sequencing, own "
                    "DRAM test. No inter-node state; partner assumed absent. Same "
                    "schedule, so -a/-b light together."
                ),
            ),
            active_regions=_CPUS + _BOARDS,
            power_watts=350,
            fan_percent=60,
            elapsed_seconds=40,
            cycle_cost=2,
        ),
        PowerOnState(
            step=5,
            phase="boot",
            label="PowerStoreOS loads on both nodes",
            description=L(
                novice=(
                    "Each half loads the array's operating system, PowerStoreOS, from a "
                    "small drive of its own. PowerStoreOS runs each storage feature as "
                    "a separate container, a small packaged program: one serves disks "
                    "to other computers, one serves shared folders, one runs the "
                    "management console, one copies data between arrays. This is the "
                    "longest single stage. An operating system for storage checks "
                    "itself thoroughly as it starts, and that takes minutes rather than "
                    "seconds. A screen would show nothing, because arrays start up "
                    "without one."
                ),
                plain=(
                    "Each node boots PowerStoreOS from its internal M.2 device — an "
                    "embedded Linux running the entire storage stack as containers: "
                    "block services, file services, management, data mobility. This is "
                    "the longest single stage; booting a storage operating system with "
                    "its integrity checks is minutes, not seconds. The console would "
                    "show nothing — arrays boot headless."
                ),
                standard=(
                    "Each node boots PowerStoreOS from its internal M.2 device — an "
                    "embedded Linux that runs the entire storage stack as containers: "
                    "block services, file services, management, data mobility. This is "
                    "the longest single stage; booting a storage operating system with "
                    "its integrity checks is minutes, not seconds. The console would "
                    "show nothing — arrays boot headless."
                ),
                technical=(
                    "Max-dwell stage. PowerStoreOS boots per node from internal M.2 — "
                    "embedded Linux running the storage stack as containers: block, "
                    "file, management, data mobility. Integrity-checked OS boot is "
                    "minutes rather than seconds, and headless throughout."
                ),
                expert=(
                    "Max dwell: PowerStoreOS per node from M.2 — containerized block, "
                    "file, management, mobility. Integrity-checked, headless, minutes."
                ),
            ),
            active_regions=_CPUS + _DIMMS,
            power_watts=420,
            fan_percent=50,
            elapsed_seconds=150,
            cycle_cost=4,
        ),
        PowerOnState(
            step=6,
            phase="drives",
            label="NVMe discovery — both nodes see every drive",
            description=L(
                novice=(
                    "Each half now looks for the drives, and each finds all twenty-five "
                    "slots. Every drive is dual-ported: it has two separate "
                    "connections, like two doors, one wired to each half, with nothing "
                    "in between. This is why losing one half is not a crisis. Switching "
                    "to the surviving half is called failover, and it needs no handover "
                    "of the drives, because that half was connected to every one of "
                    "them all along. The few seconds a failover does take are spent by "
                    "the other computers switching to their second route into the "
                    "array."
                ),
                plain=(
                    "Each node enumerates the drive bay over PCIe. Every drive is "
                    "dual-ported: two independent PCIe connections, one to each node, "
                    "with no SAS expanders or protocol bridges between. Both "
                    "controllers reach all 25 slots directly — the physical reason "
                    "failover needs no drive takeover. The surviving node doesn't take "
                    "over the drives; it already owns a path to them. The seconds a "
                    "failover does take are hosts retrying on their other paths."
                ),
                standard=(
                    "Each node enumerates the drive bay over PCIe. Every drive is "
                    "dual-ported: it has two independent PCIe connections, one to each "
                    "node, with no SAS expanders or protocol bridges between. Both "
                    "controllers therefore reach all 25 slots directly — the physical "
                    "reason failover needs no drive takeover: the surviving node "
                    "doesn't take over the drives, it already owns a path to them. The "
                    "seconds a failover does take are hosts retrying on their paths to "
                    "the other node."
                ),
                technical=(
                    "Per-node PCIe enumeration of the bay. Dual-ported drives present "
                    "an independent path to each node with no expander or bridge in "
                    "between, so both controllers address all 25 slots directly. "
                    "Failover requires no drive-path acquisition — the surviving node "
                    "already owns one — so its duration is host path retry, measured in "
                    "seconds."
                ),
                expert=(
                    "Dual-ported NVMe, direct PCIe path per node, no expanders. No "
                    "drive-path acquisition at failover; its seconds are host path "
                    "retry."
                ),
            ),
            active_regions=["drive-bay"] + _EMBEDDED,
            power_watts=520,
            fan_percent=45,
            elapsed_seconds=170,
        ),
        PowerOnState(
            step=7,
            phase="drives",
            label="NVRAM write cache initializes",
            description=L(
                novice=(
                    "The four fast drives at the front wake up as the write cache, "
                    "called NVRAM: storage that keeps its contents without power. They "
                    "work as mirrored pairs, two drives that always hold the same "
                    "thing, and they sit in the shared front bay, where both halves "
                    "reach them directly. Once the array is serving, every write a "
                    "computer sends is saved onto both drives of a pair, and only then "
                    "does the array answer 'done'. The slower move to the main drives "
                    "happens later, while nobody is waiting. Both copies sit outside "
                    "the two halves, so a write the array has answered for survives one "
                    "half failing. The drives keep their contents without power, so it "
                    "survives a power cut too."
                ),
                plain=(
                    "The four NVMe NVRAM drives come up as the write cache. They are "
                    "installed as mirrored pairs in the shared front bay, and both "
                    "nodes reach them directly. Once the array is serving, a host write "
                    "is committed to both drives of a pair and only then acknowledged; "
                    "the destage to capacity SSDs happens later, off the latency path. "
                    "The protected copy is on those drives, not in either node's "
                    "memory, so an acknowledged write survives a node failure. NVRAM is "
                    "non-volatile, so it survives a power loss too."
                ),
                standard=(
                    "The four NVMe NVRAM drives come up as the write cache: mirrored "
                    "pairs in the shared, dual-ported front bay, which both nodes reach "
                    "directly. Once the array is serving, a host write is committed to "
                    "both drives of a pair and only then acknowledged; the destage to "
                    "capacity SSDs happens later, off the latency path. The protected "
                    "copy lives on those drives, outside either node, so an "
                    "acknowledged write survives a node failure, and NVRAM is "
                    "non-volatile, so it survives a power loss too. The node-failure "
                    "scenario puts exactly this to the test."
                ),
                technical=(
                    "NVRAM write cache initializes across four NVMe devices, installed "
                    "as mirrored pairs in the shared dual-ported bay and addressed "
                    "directly by both nodes. In service, the receiving node commits a "
                    "host write to both drives of a pair and then acknowledges; destage "
                    "to the capacity tier is asynchronous and off the latency path. The "
                    "protected copy sits outside either node's failure domain, so an "
                    "acknowledged write survives node loss, and non-volatility covers "
                    "power loss."
                ),
                expert=(
                    "NVRAM write cache up: mirrored drive pairs in the shared "
                    "dual-ported bay, outside either node's failure domain. Commit to "
                    "both drives, then ack; async destage. Acknowledged writes survive "
                    "node loss and power loss."
                ),
            ),
            # The cache is drives in the shared bay that both nodes reach; the
            # interconnect is not the mirror, so it stays dark here.
            active_regions=["nvram"] + _BOARDS,
            power_watts=540,
            fan_percent=42,
            elapsed_seconds=185,
            cycle_cost=2,
        ),
        PowerOnState(
            step=8,
            phase="cluster",
            label="Nodes find each other",
            description=L(
                novice=(
                    "The two halves have run the same start-up side by side without "
                    "talking to each other. Here they finally meet. Over an internal "
                    "link they start sending each other a regular I-am-alive signal, "
                    "called a heartbeat, and agree to run active/active: both own "
                    "volumes and serve traffic at once, rather than one sitting idle as "
                    "a spare. The link carries this coordination. It does not carry the "
                    "safe copy of a write, which is on the mirrored cache drives in the "
                    "front bay. Each half also begins watching the other: if one ever "
                    "stops answering, its partner takes over all of its connections "
                    "within seconds."
                ),
                plain=(
                    "The two boots converge. Over the internal interconnect the nodes "
                    "exchange heartbeats and negotiate active/active operation — both "
                    "will own volumes and serve I/O at once, rather than one idling as "
                    "a spare. The interconnect carries that coordination, not the "
                    "protected copy of a write, which is on the NVRAM drives in the "
                    "shared bay. Each also starts watching the other: if a node stops "
                    "answering, its partner takes over all host paths in seconds."
                ),
                standard=(
                    "The two boots converge. Over the internal interconnect the nodes "
                    "exchange heartbeats and negotiate active/active operation — both "
                    "nodes will own volumes and serve I/O at once, rather than one "
                    "idling as a spare. The interconnect carries this coordination; it "
                    "is not the write mirror, which is the NVRAM drive pair in the "
                    "shared bay. Each also starts watching the other: if a node ever "
                    "stops answering, its partner takes over all host paths in seconds."
                ),
                technical=(
                    "The independent boots converge over the internal interconnect: "
                    "heartbeat exchange and active/active negotiation — both nodes own "
                    "volumes and serve concurrently rather than one holding as a "
                    "passive spare. The interconnect is a coordination path, not the "
                    "write mirror; the protected copy is the NVRAM pair in the shared "
                    "bay. Mutual monitoring begins; path takeover on partner loss is "
                    "seconds."
                ),
                expert=(
                    "Boots converge: heartbeat, active/active negotiated. Interconnect "
                    "is coordination, not the write mirror. Mutual monitoring; seconds "
                    "to path takeover."
                ),
            ),
            active_regions=["interconnect"] + _BOARDS,
            power_watts=560,
            fan_percent=40,
            elapsed_seconds=200,
        ),
        PowerOnState(
            step=9,
            phase="cluster",
            label="Storage pool assembles",
            description=L(
                novice=(
                    "The array now builds its storage pool, the one large space that "
                    "all data goes into. Older arrays tie drives into fixed groups and "
                    "keep one spare drive standing by. Here, software Dell calls the "
                    "dynamic resiliency engine cuts every drive into slices and spreads "
                    "the redundancy information across all of them. Redundancy "
                    "information is extra data that lets a lost drive's contents be "
                    "worked out again. The spare space is spread out the same way. When "
                    "a drive fails, every remaining drive helps rebuild it at once, "
                    "instead of one spare drive becoming the bottleneck. The PowerFlex "
                    "twin takes the same idea further, across whole servers."
                ),
                plain=(
                    "The dynamic resiliency engine — PowerStore's replacement for fixed "
                    "RAID groups — assembles the pool. Every drive is carved into "
                    "slices, and redundancy is spread across all drives with spare "
                    "capacity distributed the same way. When a drive fails, every "
                    "remaining drive contributes to the rebuild in parallel, instead of "
                    "one hot spare becoming the bottleneck."
                ),
                standard=(
                    "The dynamic resiliency engine — PowerStore's replacement for fixed "
                    "RAID groups — assembles the pool. Every drive is carved into "
                    "slices, and redundancy (parity) is spread across all drives with "
                    "spare capacity distributed the same way. When a drive fails, every "
                    "remaining drive contributes to the rebuild in parallel, instead of "
                    "one hot-spare becoming the bottleneck."
                ),
                technical=(
                    "Dynamic resiliency engine assembles the pool in place of fixed "
                    "RAID groups: drives are sliced, parity is distributed across all "
                    "of them, and spare capacity is distributed rather than dedicated. "
                    "Rebuild is many-to-many — every surviving drive contributes — "
                    "which is the same instinct the PowerFlex twin applies at node "
                    "granularity."
                ),
                expert=(
                    "Distributed-parity pool, no fixed RAID groups, distributed spare. "
                    "Many-to-many rebuild — PowerFlex's instinct at drive rather than "
                    "node granularity."
                ),
            ),
            active_regions=["drive-bay"] + _CPUS,
            power_watts=600,
            fan_percent=40,
            elapsed_seconds=240,
            cycle_cost=3,
        ),
        PowerOnState(
            step=10,
            phase="services",
            label="Data services start",
            description=L(
                novice=(
                    "The data features start on both halves. The main one is data "
                    "reduction: deduplication finds identical blocks of data and stores "
                    "them once, and compression shrinks what is left. Two words matter "
                    "here — 'inline' and 'always on'. Every write is reduced before it "
                    "touches the drives, there is no cleanup pass afterwards, and there "
                    "is no switch anyone can forget to turn on. Two more features start "
                    "alongside. A snapshot is a frozen picture of a volume at one "
                    "moment that you can go back to. Thin provisioning means space is "
                    "used up only as data is written, not when a volume is created."
                ),
                plain=(
                    "The data-service containers come up on both nodes: inline "
                    "deduplication and compression, snapshots, and thin provisioning. "
                    "'Inline' and 'always on' matter — every write is reduced before it "
                    "touches flash, there is no post-process pass and no switch to "
                    "forget. Dedupe finds identical blocks and stores them once; "
                    "compression shrinks what remains."
                ),
                standard=(
                    "The data-service containers come up on both nodes: inline "
                    "deduplication and compression, snapshots, and thin provisioning. "
                    "'Inline' and 'always on' matter — every write is reduced before it "
                    "touches flash, there is no post-process pass and no switch to "
                    "forget. Dedup finds identical blocks and stores them once; "
                    "compression shrinks what remains."
                ),
                technical=(
                    "Data-service containers start on both nodes: inline deduplication "
                    "and compression, snapshots, thin provisioning. Inline and "
                    "non-optional — reduction precedes the flash write, with no "
                    "post-process pass and no configuration switch, which removes an "
                    "entire class of operational mistake."
                ),
                expert=(
                    "Data services up both nodes: inline dedupe and compression, "
                    "snapshots, thin provisioning. Pre-flash, non-optional, no "
                    "post-process pass."
                ),
            ),
            active_regions=_CPUS + _DIMMS,
            power_watts=620,
            fan_percent=38,
            elapsed_seconds=260,
        ),
        PowerOnState(
            step=11,
            phase="services",
            label="Front-end ports online",
            description=L(
                novice=(
                    "The built-in ports and the swappable input/output modules "
                    "present the array to the hosts that will use it: several "
                    "block-storage protocols including a newer one that carries the "
                    "drive protocol directly over the network without translation, "
                    "and file-sharing protocols. Matching modules in both halves "
                    "mean every host connection exists twice, once per half."
                ),
                plain=(
                    "The embedded mezzanine ports and hot-swap I/O modules present "
                    "the array to hosts: Fibre Channel and iSCSI block targets, "
                    "NVMe-oF — the NVMe protocol carried over Fibre Channel or TCP, "
                    "skipping SCSI translation entirely — and NFS/SMB file shares. "
                    "Matching modules in both nodes mean every host path exists "
                    "twice, once per node."
                ),
                standard=(
                    "The embedded mezzanine ports and the hot-swap I/O modules "
                    "present the array to hosts: Fibre Channel and iSCSI block "
                    "targets, NVMe-oF (NVMe-over-Fabrics — the NVMe protocol "
                    "carried over FC or TCP, skipping SCSI translation "
                    "entirely), and NFS/SMB file shares. Matching modules in "
                    "both nodes mean every host path exists twice, once per "
                    "node."
                ),
                technical=(
                    "Embedded mezzanine and hot-swap I/O modules present block and "
                    "file targets: FC, iSCSI, NVMe-oF over FC or TCP eliminating "
                    "SCSI translation, plus NFS and SMB. Module symmetry across "
                    "nodes means every host path is duplicated, so a node reboot "
                    "never removes a path a host depends on."
                ),
                expert=(
                    "Front-end up: FC, iSCSI, NVMe-oF (FC/TCP, no SCSI "
                    "translation), NFS/SMB. Symmetric modules — every path "
                    "duplicated per node."
                ),
            ),
            active_regions=_EMBEDDED + _IOMODS,
            power_watts=650,
            fan_percent=36,
            elapsed_seconds=280,
        ),
        PowerOnState(
            step=12,
            phase="services",
            label="Management stack up",
            description=L(
                novice=(
                    "The management interface — its web console and programming "
                    "interface — comes up on a cluster address that floats between "
                    "the two halves' management ports, so the address you bookmark "
                    "keeps working even through a controller failure. Management "
                    "traffic stays on its own dedicated ports, completely off the "
                    "path that carries data."
                ),
                plain=(
                    "The management interface comes up — a web console and a "
                    "programming interface — on a cluster address that moves "
                    "between the two nodes' management ports as needed. That means "
                    "the address you bookmark keeps working even if a node fails "
                    "underneath it. This traffic runs on its own dedicated 1 GbE "
                    "ports and never touches the ports carrying data."
                ),
                standard=(
                    "PowerStore Manager — the web UI and REST API — comes up "
                    "on a cluster IP that floats between the nodes' management "
                    "ports, so the address you bookmark keeps working through "
                    "a node failure. Management traffic stays on its own 1 GbE "
                    "ports, completely off the data path."
                ),
                technical=(
                    "Management stack up: web UI and REST API on a floating cluster "
                    "IP that migrates between node management ports, so the "
                    "bookmarked address survives node loss. Management traffic is "
                    "confined to dedicated 1 GbE ports and never shares the data "
                    "path."
                ),
                expert=(
                    "Management up on a floating cluster IP across node mgmt ports. "
                    "Dedicated 1 GbE, off the data path."
                ),
            ),
            active_regions=_MGMT,
            power_watts=655,
            fan_percent=35,
            elapsed_seconds=300,
        ),
        PowerOnState(
            step=13,
            phase="online",
            label="Serving I/O — active/active",
            description=L(
                novice=(
                    "The array is online. Both halves serve traffic and share the load. "
                    "Every write is saved on a mirrored pair of cache drives before it "
                    "is confirmed, reads come off the main pool, and data reduction "
                    "runs on every write as it arrives. A two-controller all-flash box "
                    "of this size (2U, about 9 cm of rack height) idles at several "
                    "hundred watts with fans under thermal control. That figure is "
                    "illustrative; Dell's spec sheet lists up to about 1.4 kW for a "
                    "fully loaded PowerStore 5200T, one of the larger models, working "
                    "hard. From plugging in the cords to serving traffic: minutes, with "
                    "nobody touching the box."
                ),
                plain=(
                    "The array is serving. Both nodes handle host traffic and split the "
                    "work between them; writes are committed to a mirrored pair of "
                    "NVRAM drives before they are acknowledged, reads come from the "
                    "drive pool, and every write is deduplicated and compressed as it "
                    "arrives. A two-node all-flash 2U appliance idles at a few hundred "
                    "watts with the fans under thermal control (illustrative; Dell's "
                    "spec sheet lists up to about 1.4 kW for a fully populated 5200T). "
                    "Cords in to serving traffic takes minutes, and nobody had to touch "
                    "the box."
                ),
                standard=(
                    "The array is online. Both nodes serve host I/O and share the load; "
                    "writes commit to a mirrored NVRAM drive pair before the "
                    "acknowledgement, reads come off the NVMe pool, and data reduction "
                    "runs inline on every write. Steady-state draw for a dual-node "
                    "all-NVMe 2U appliance idles in the several-hundred-watt range with "
                    "fans on thermal control — an illustrative figure; Dell's spec "
                    "sheet lists up to about 1.4 kW for a fully populated 5200T under "
                    "typical operating conditions. From cords-in to serving I/O: "
                    "minutes, with no one touching the box."
                ),
                technical=(
                    "Online and active/active: both nodes serving and load-sharing, "
                    "writes committed to the shared mirrored NVRAM pair, reads from the "
                    "NVMe pool, reduction inline on every write. Several-hundred-watt "
                    "idle for a dual-node 2U all-NVMe appliance under thermal control "
                    "(illustrative; spec-sheet maximum for a full 5200T is about 1.4 kW "
                    "at 26 °C). Cords-in to serving in minutes, unattended."
                ),
                expert=(
                    "Online, active/active. Writes to the shared mirrored NVRAM pair, "
                    "NVMe reads, inline reduction. Several-hundred-watt idle "
                    "(illustrative; spec max ~1.4 kW). Cords-in to serving in minutes, "
                    "unattended."
                ),
            ),
            active_regions=(
                ["drive-bay", "nvram", "interconnect"]
                + _CPUS + _DIMMS + _EMBEDDED + _IOMODS + _MGMT + _FANS
            ),
            power_watts=680,
            fan_percent=30,
            elapsed_seconds=330,
        ),
    ]
