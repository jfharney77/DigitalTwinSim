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
                    "Its only job is to power that half for the few seconds needed "
                    "to flush cached writes to permanent storage if the mains "
                    "fails. Until both halves know that a power cut is survivable, "
                    "the array will not accept a single write."
                ),
                plain=(
                    "Each node tests its battery backup unit before anything else "
                    "matters. The BBU is not a UPS — it cannot keep the array "
                    "running. Its only job is vaulting: on AC loss it powers the "
                    "node for the few seconds needed to flush cached writes to "
                    "non-volatile media. Until both nodes know a power loss is "
                    "survivable, the array will not accept a single write."
                ),
                standard=(
                    "Each node tests its battery backup unit (BBU) before "
                    "anything else matters. The BBU is not a UPS — it cannot "
                    "keep the array running. Its only job is 'vaulting': on AC "
                    "loss it powers the node for the few seconds needed to "
                    "flush cached writes to non-volatile media. Until both "
                    "nodes know a power loss is survivable, the array will not "
                    "accept a single write."
                ),
                technical=(
                    "Per-node BBU self-test gates everything downstream. The BBU is "
                    "not a UPS and cannot sustain service; its sole function is "
                    "vaulting — powering the node long enough to flush cached "
                    "writes to non-volatile media on AC loss. No write is accepted "
                    "until both nodes confirm survivability."
                ),
                expert=(
                    "BBU self-test gates write acceptance. Not a UPS — vault-only: "
                    "flush cache to NVM on AC loss. No writes until both nodes "
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
                    "Each controller half is a complete computer in its own right, "
                    "and each runs its own start-up firmware from its own flash, "
                    "powers up its own processor, and tests its own memory. The two "
                    "halves start independently and know nothing of each other yet "
                    "— redundancy begins from the assumption that your partner may "
                    "simply not be there."
                ),
                plain=(
                    "Each controller node is a complete x86 computer, and each runs "
                    "its own UEFI firmware from its own flash, sequences power to "
                    "its own Xeon, and tests its own DRAM. The two nodes boot "
                    "independently and know nothing of each other yet — redundancy "
                    "starts with the assumption that the partner may not be there."
                ),
                standard=(
                    "Each controller node is a complete x86 computer, and each "
                    "runs its own BIOS/UEFI firmware from its own flash, "
                    "sequences power to its own Xeon, and tests its own DRAM. "
                    "The two nodes boot independently and know nothing of each "
                    "other yet — redundancy starts with the assumption that "
                    "the partner may not be there."
                ),
                technical=(
                    "Each node is a complete x86 system: own firmware from own "
                    "flash, own CPU power sequencing, own DRAM test. Independent "
                    "boots with no inter-node state — the redundancy model assumes "
                    "partner absence from the outset."
                ),
                expert=(
                    "Independent x86 boots per node: own firmware, own sequencing, "
                    "own DRAM test. No inter-node state; partner assumed absent."
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
                    "Each half loads the storage operating system from its own "
                    "internal drive — an embedded Linux that runs the entire "
                    "storage stack as containers: block services, file services, "
                    "management, data movement. This is the longest single stage; "
                    "booting a storage operating system with all its integrity "
                    "checks takes minutes rather than seconds. A screen would show "
                    "nothing, because arrays boot without one."
                ),
                plain=(
                    "Each node boots PowerStoreOS from its internal M.2 device — an "
                    "embedded Linux running the entire storage stack as containers: "
                    "block services, file services, management, data mobility. This "
                    "is the longest single stage; booting a storage operating "
                    "system with its integrity checks is minutes, not seconds. The "
                    "console would show nothing — arrays boot headless."
                ),
                standard=(
                    "Each node boots PowerStoreOS from its internal M.2 device "
                    "— an embedded Linux that runs the entire storage stack as "
                    "containers: block services, file services, management, "
                    "data mobility. This is the longest single stage; booting "
                    "a storage operating system with its integrity checks is "
                    "minutes, not seconds. The console would show nothing — "
                    "arrays boot headless."
                ),
                technical=(
                    "Max-dwell stage. PowerStoreOS boots per node from internal M.2 "
                    "— embedded Linux running the storage stack as containers: "
                    "block, file, management, data mobility. Integrity-checked OS "
                    "boot is minutes rather than seconds, and headless throughout."
                ),
                expert=(
                    "Max dwell: PowerStoreOS per node from M.2 — containerized "
                    "block, file, management, mobility. Integrity-checked, "
                    "headless, minutes."
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
                    "Each half enumerates the drive bay. Every drive is dual-ported "
                    "— it has two independent connections, one to each half, with "
                    "no intermediate hardware in between. Both controllers "
                    "therefore reach all twenty-five slots directly. This is the "
                    "physical reason failover is instant: the surviving half does "
                    "not have to take over the drives, because it already owns a "
                    "path to every one of them."
                ),
                plain=(
                    "Each node enumerates the drive bay over PCIe. Every drive is "
                    "dual-ported: two independent PCIe connections, one to each "
                    "node, with no SAS expanders or protocol bridges between. Both "
                    "controllers reach all 25 slots directly — the physical reason "
                    "failover is instant. The surviving node doesn't take over the "
                    "drives; it already owns a path to them."
                ),
                standard=(
                    "Each node enumerates the drive bay over PCIe. Every drive "
                    "is dual-ported: it has two independent PCIe connections, "
                    "one to each node, with no SAS expanders or protocol "
                    "bridges between. Both controllers therefore reach all 25 "
                    "slots directly — the physical reason failover is instant: "
                    "the surviving node doesn't take over the drives, it "
                    "already owns a path to them."
                ),
                technical=(
                    "Per-node PCIe enumeration of the bay. Dual-ported drives "
                    "present an independent path to each node with no expander or "
                    "bridge in between, so both controllers address all 25 slots "
                    "directly. Failover is instantaneous because no path "
                    "acquisition is required — the surviving node already owns one."
                ),
                expert=(
                    "Dual-ported NVMe, direct PCIe path per node, no expanders. "
                    "Failover is instant because no path acquisition occurs."
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
                    "The four fast non-volatile drives come up as the write cache. "
                    "From now on, a write from a host lands in that cache, mirrored "
                    "across both halves, and is acknowledged straight away; the "
                    "slower move to the main capacity drives happens later, off the "
                    "path the host is waiting on. Because that cache keeps its "
                    "contents without power and exists on both halves, an "
                    "acknowledged write survives both a controller failure and a "
                    "power cut."
                ),
                plain=(
                    "The four NVMe NVRAM drives come up as the write cache. From "
                    "now on a host write lands in NVRAM mirrored across both nodes "
                    "and is acknowledged immediately; the destage to capacity SSDs "
                    "happens later, off the latency path. Because NVRAM is "
                    "non-volatile and mirrored, an acknowledged write survives a "
                    "node failure and a power loss both."
                ),
                standard=(
                    "The four NVMe NVRAM drives come up as the write cache. "
                    "From now on, a host write lands in NVRAM mirrored across "
                    "both nodes' views and is acknowledged immediately; the "
                    "destage to capacity SSDs happens later, off the latency "
                    "path. Because NVRAM is non-volatile and mirrored, an "
                    "acknowledged write survives a node failure and a power "
                    "loss both."
                ),
                technical=(
                    "NVRAM write cache initializes across four NVMe devices. Host "
                    "writes land mirrored across both nodes and acknowledge "
                    "immediately; destage to the capacity tier is asynchronous and "
                    "off the latency path. Non-volatility plus mirroring means an "
                    "acknowledged write survives both node loss and power loss."
                ),
                expert=(
                    "NVRAM write cache up, mirrored cross-node. Immediate ack, "
                    "async destage. Acknowledged writes survive node loss and power "
                    "loss."
                ),
            ),
            active_regions=["nvram", "interconnect"],
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
                    "The two independent starts finally converge. Over an internal "
                    "link the halves exchange heartbeats, establish the path they "
                    "will use to mirror cached writes to each other, and agree to "
                    "run active/active — both owning volumes and serving traffic at "
                    "once, rather than one sitting idle as a spare. Each also "
                    "begins watching the other: if one ever stops answering, its "
                    "partner takes over all host connections within seconds."
                ),
                plain=(
                    "The two boots converge. Over the internal interconnect the "
                    "nodes exchange heartbeats, establish the cache mirroring path, "
                    "and negotiate active/active operation — both will own volumes "
                    "and serve I/O at once, rather than one idling as a spare. Each "
                    "also starts watching the other: if a node stops answering, its "
                    "partner takes over all host paths in seconds."
                ),
                standard=(
                    "The two boots converge. Over the internal interconnect "
                    "the nodes exchange heartbeats, establish the cache "
                    "mirroring path, and negotiate active/active operation — "
                    "both nodes will own volumes and serve I/O at once, rather "
                    "than one idling as a spare. Each also starts watching the "
                    "other: if a node ever stops answering, its partner takes "
                    "over all host paths in seconds."
                ),
                technical=(
                    "The independent boots converge over the internal interconnect: "
                    "heartbeat exchange, cache-mirroring path establishment, and "
                    "active/active negotiation — both nodes own volumes and serve "
                    "concurrently rather than one holding as a passive spare. "
                    "Mutual monitoring begins; path takeover on partner loss is "
                    "seconds."
                ),
                expert=(
                    "Boots converge: heartbeat, cache-mirror path, active/active "
                    "negotiated. Mutual monitoring; seconds to path takeover."
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
                    "The resiliency engine — which replaces traditional fixed disk "
                    "groups — assembles the pool. Every drive is divided into "
                    "slices, and the redundancy information is spread across all of "
                    "them, with spare capacity distributed the same way. When a "
                    "drive fails, every remaining drive contributes to rebuilding "
                    "it in parallel, instead of one designated spare becoming the "
                    "bottleneck. This is the same instinct the PowerFlex twin takes "
                    "further."
                ),
                plain=(
                    "The dynamic resiliency engine — PowerStore's replacement for "
                    "fixed RAID groups — assembles the pool. Every drive is carved "
                    "into slices, and redundancy is spread across all drives with "
                    "spare capacity distributed the same way. When a drive fails, "
                    "every remaining drive contributes to the rebuild in parallel, "
                    "instead of one hot spare becoming the bottleneck."
                ),
                standard=(
                    "The dynamic resiliency engine — PowerStore's replacement "
                    "for fixed RAID groups — assembles the pool. Every drive "
                    "is carved into slices, and redundancy (parity) is spread "
                    "across all drives with spare capacity distributed the "
                    "same way. When a drive fails, every remaining drive "
                    "contributes to the rebuild in parallel, instead of one "
                    "hot-spare becoming the bottleneck."
                ),
                technical=(
                    "Dynamic resiliency engine assembles the pool in place of fixed "
                    "RAID groups: drives are sliced, parity is distributed across "
                    "all of them, and spare capacity is distributed rather than "
                    "dedicated. Rebuild is many-to-many — every surviving drive "
                    "contributes — which is the same instinct the PowerFlex twin "
                    "applies at node granularity."
                ),
                expert=(
                    "Distributed-parity pool, no fixed RAID groups, distributed "
                    "spare. Many-to-many rebuild — PowerFlex's instinct at drive "
                    "rather than node granularity."
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
                    "The data-service components come up on both halves: "
                    "deduplication and compression, snapshots, and thin "
                    "provisioning. Two words matter here — 'inline' and 'always "
                    "on'. Every write is reduced before it ever touches flash, "
                    "there is no separate cleanup pass afterwards, and there is no "
                    "switch anyone can forget to turn on. Deduplication finds "
                    "identical blocks and stores them once; compression shrinks "
                    "what is left."
                ),
                plain=(
                    "The data-service containers come up on both nodes: inline "
                    "deduplication and compression, snapshots, and thin "
                    "provisioning. 'Inline' and 'always on' matter — every write is "
                    "reduced before it touches flash, there is no post-process pass "
                    "and no switch to forget. Dedupe finds identical blocks and "
                    "stores them once; compression shrinks what remains."
                ),
                standard=(
                    "The data-service containers come up on both nodes: inline "
                    "deduplication and compression, snapshots, and thin "
                    "provisioning. 'Inline' and 'always on' matter — every "
                    "write is reduced before it touches flash, there is no "
                    "post-process pass and no switch to forget. Dedup finds "
                    "identical blocks and stores them once; compression "
                    "shrinks what remains."
                ),
                technical=(
                    "Data-service containers start on both nodes: inline "
                    "deduplication and compression, snapshots, thin provisioning. "
                    "Inline and non-optional — reduction precedes the flash write, "
                    "with no post-process pass and no configuration switch, which "
                    "removes an entire class of operational mistake."
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
                    "The array is online. Both halves serve host traffic and share "
                    "the load; writes are mirrored through the non-volatile cache, "
                    "reads come off the main pool, and data reduction runs on every "
                    "write as it arrives. A dual-controller all-flash 2U appliance "
                    "idles in the several-hundred-watt range with fans under "
                    "thermal control. From plugging in the cords to serving "
                    "traffic: minutes, with nobody touching the box."
                ),
                plain=(
                    "The array is serving. Both nodes handle host traffic and split "
                    "the work between them; writes are mirrored through the "
                    "non-volatile cache, reads come from the drive pool, and every "
                    "write is deduplicated and compressed as it arrives. A two-node "
                    "all-flash 2U appliance idles at a few hundred watts with the "
                    "fans under thermal control. Cords in to serving traffic takes "
                    "minutes, and nobody had to touch the box."
                ),
                standard=(
                    "The array is online. Both nodes serve host I/O and share "
                    "the load; writes mirror through NVRAM, reads come off the "
                    "NVMe pool, and data reduction runs inline on every write. "
                    "Steady-state draw for a dual-node all-NVMe 2U appliance "
                    "idles in the several-hundred-watt range with fans on "
                    "thermal control. From cords-in to serving I/O: minutes, "
                    "with no one touching the box."
                ),
                technical=(
                    "Online and active/active: both nodes serving and load-sharing, "
                    "writes mirrored through NVRAM, reads from the NVMe pool, "
                    "reduction inline on every write. Several-hundred-watt idle for "
                    "a dual-node 2U all-NVMe appliance under thermal control. "
                    "Cords-in to serving in minutes, unattended."
                ),
                expert=(
                    "Online, active/active. NVRAM-mirrored writes, NVMe reads, "
                    "inline reduction. Several-hundred-watt idle. Cords-in to "
                    "serving in minutes, unattended."
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
