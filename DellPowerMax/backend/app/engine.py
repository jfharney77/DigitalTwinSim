"""Pure power-on sequence engine for a PowerMax node-pair engine.

``simulate()`` returns the deterministic trace of what happens inside a
PowerMax array from the moment AC arrives until it is serving I/O. Same
purity rule as the GPU, R760, PowerStore, and Alienware engines: no FastAPI,
no IO, no timers — the frontend owns the playback clock, and each
``PowerOnState`` is plain data the renderer consumes. ``cycle_cost`` marks the
long stages (PowerMaxOS boot, pool assembly) so the UI dwells on them.

The storytelling beats that make PowerMax different from the smaller arrays:
there is no power button (applying AC *is* the power-on); everything happens
twice, once per director node, before the pair converges; the write cache is
DRAM protected by *vault to flash* rather than by dedicated NVRAM drives; and
the drives are not on either node's bus — they hang off the InfiniBand
Dynamic Fabric, which is why the fabric gets a bring-up phase of its own.
Timing and wattage are illustrative but plausible for a single node pair plus
one DME (~2 kVA per the spec sheet); favor a correct mental model over
measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import PowerOnState

_PSUS = ["psu-a", "psu-b"]
_SPS = ["sps-a", "sps-b"]
_FANS = ["fans-a", "fans-b"]
_VAULT = ["vault-a", "vault-b"]
_CACHE = ["cache-a", "cache-b"]
_CPUS = ["cpu-a", "cpu-b"]
_BOARDS = ["board-a", "board-b"]
_FABRIC = ["fabric-a", "fabric-b"]
_IOMODS = ["iomod-a1", "iomod-a2", "iomod-b1", "iomod-b2"]
_MGMT = ["mgmt-a", "mgmt-b"]


def simulate() -> list[PowerOnState]:
    """PowerMax's journey from AC plug-in to serving I/O, as pure data."""
    return [
        PowerOnState(
            step=0,
            phase="off",
            label="AC connected at the PDUs",
            description=L(
                novice=(
                    "The power cords are connected to the cabinet's managed power "
                    "strips — two separate power zones, fed from different "
                    "supplies. The array is dark. As with any storage array there "
                    "is no power button: it is expected to come back into service "
                    "by itself after an outage, so everything that follows happens "
                    "automatically."
                ),
                plain=(
                    "Line cords are connected to the cabinet's intelligent power "
                    "distribution units — two power zones, fed from separate "
                    "supplies. The array is dark. As with any storage array there "
                    "is no power button: an array is expected to return to service "
                    "by itself after an outage, so what happens next is entirely "
                    "automatic."
                ),
                standard=(
                    "Line cords are connected to the cabinet's intelligent power "
                    "distribution units — two power zones, fed from separate "
                    "feeds. The array is dark. As with any storage array there is "
                    "no power button: an array is expected to return to service by "
                    "itself after an outage, so what happens next is entirely "
                    "automatic."
                ),
                technical=(
                    "Cords connected to the cabinet's intelligent PDUs across two "
                    "independently fed power zones. Array dark. No power button — "
                    "unattended return to service is the requirement, so the "
                    "sequence is fully automatic."
                ),
                expert=(
                    "Intelligent PDUs energized across two independent power zones. "
                    "No power button; unattended recovery by design."
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
            label="Power supplies energize",
            description=L(
                novice=(
                    "Each processing unit's power supplies notice the voltage and "
                    "bring their power up. The managed power strips start reporting "
                    "telemetry — power, voltage, current, temperature, humidity. "
                    "Both halves of the pair wake at once: from here on everything "
                    "happens twice, once per unit, because redundancy starts from "
                    "the assumption that your partner might not be there."
                ),
                plain=(
                    "Each director's power supplies detect line voltage and bring "
                    "their rails up. The intelligent PDUs begin streaming telemetry "
                    "— power, voltage, current, temperature, humidity. Both nodes "
                    "of the pair wake in parallel: from here on everything happens "
                    "twice, once per director, because redundancy starts with the "
                    "assumption that the partner might not be there."
                ),
                standard=(
                    "Each director's power supplies detect line voltage and bring "
                    "their rails up. The intelligent PDUs begin streaming "
                    "telemetry — power, voltage, current, temperature, humidity. "
                    "Both nodes of the pair wake in parallel: from here on, "
                    "everything happens twice, once per director, because "
                    "redundancy starts with the assumption that the partner might "
                    "not be there."
                ),
                technical=(
                    "Director PSUs bring rails up on line-voltage detect; the "
                    "intelligent PDUs begin streaming power, voltage, current, "
                    "temperature, and humidity telemetry. Both nodes of the pair "
                    "wake in parallel — every subsequent step is duplicated per "
                    "director, on the assumption of partner absence."
                ),
                expert=(
                    "Director PSUs up; PDUs streaming power/environmental "
                    "telemetry. Parallel wake, duplicated per director, partner "
                    "assumed absent."
                ),
            ),
            active_regions=_PSUS,
            power_watts=150,
            fan_percent=10,
            elapsed_seconds=3,
        ),
        PowerOnState(
            step=2,
            phase="power",
            label="Standby power supply self-test",
            description=L(
                novice=(
                    "Each unit tests its standby power supply — the battery behind "
                    "the emergency flush to flash. It is not a general backup "
                    "supply and cannot keep the array serving; its only job is to "
                    "power the unit through the few seconds it takes to write the "
                    "memory cache out to flash if the mains fails. Until both units "
                    "know a power loss is survivable, the array will not accept a "
                    "single write."
                ),
                plain=(
                    "Each node tests its standby power supply — the battery behind "
                    "vault-to-flash. The SPS is not a UPS and cannot keep the array "
                    "serving; its only job is to power the director through the "
                    "seconds it takes to flush DRAM cache to flash if line power is "
                    "lost. Until both nodes know a power loss is survivable, the "
                    "array will not accept a single write."
                ),
                standard=(
                    "Each node tests its standby power supply (SPS) — the battery "
                    "behind vault-to-flash. The SPS is not a UPS and cannot keep "
                    "the array serving; its only job is to power the director "
                    "through the seconds it takes to flush DRAM cache to flash if "
                    "line power is lost. Until both nodes know a power loss is "
                    "survivable, the array will not accept a single write."
                ),
                technical=(
                    "Per-node SPS self-test gates write acceptance. Not a UPS — its "
                    "sole function is powering the director through a DRAM-cache "
                    "flush to flash on line loss. No write is accepted until both "
                    "nodes confirm survivability, exactly as PowerStore gates on "
                    "its BBU."
                ),
                expert=(
                    "SPS self-test gates writes. Vault-only, not a UPS: powers the "
                    "DRAM flush to flash on line loss."
                ),
            ),
            active_regions=_SPS,
            power_watts=220,
            fan_percent=15,
            elapsed_seconds=10,
        ),
        PowerOnState(
            step=3,
            phase="power",
            label="Fan packs spin up",
            description=L(
                novice=(
                    "Both units' fans run up hard, then settle once temperature "
                    "sensors report in. This array runs its processors continuously "
                    "at their boosted speed, so cooling is deliberately aggressive "
                    "— the adaptive cooling logic and the fans work harder when the "
                    "room is warm, which is why the specification quotes a higher "
                    "power figure above 35 °C than below 26 °C."
                ),
                plain=(
                    "The fans on both nodes run up hard, then settle once the "
                    "temperature sensors report in. PowerMax keeps its processors "
                    "running at boosted speed continuously, so the cooling is "
                    "deliberately aggressive: the adaptive cooling logic pushes the "
                    "fans harder as the room gets warmer. That is why the "
                    "specification quotes one power figure above 35 °C and a lower "
                    "one below 26 °C."
                ),
                standard=(
                    "Both nodes' fans run up hard, then settle once thermal "
                    "sensors report in. PowerMax runs its Xeons continuously in "
                    "turbo, so cooling is deliberately aggressive — the Adaptive "
                    "Cooling algorithm and the fans work harder at high ambient "
                    "temperature, which is why the spec sheet quotes a higher "
                    "power figure above 35 °C than below 26 °C."
                ),
                technical=(
                    "Fans to full, settling on sensor report. Sustained turbo "
                    "operation on the Xeons makes cooling deliberately aggressive; "
                    "Adaptive Cooling scales with ambient, which is why the "
                    "published power figure differs above 35 °C and below 26 °C. "
                    "Ambient is a specification input here, not an afterthought."
                ),
                expert=(
                    "Fans full, settle on sensor report. Sustained turbo forces "
                    "aggressive cooling; Adaptive Cooling scales with ambient — "
                    "hence the banded power figures."
                ),
            ),
            active_regions=_FANS,
            power_watts=520,
            fan_percent=100,
            elapsed_seconds=16,
        ),
        PowerOnState(
            step=4,
            phase="vault",
            label="Validate the vault",
            description=L(
                novice=(
                    "Before loading the storage software, each unit checks its "
                    "flash vault modules. This array's write cache lives in "
                    "volatile memory; on a power loss the standby supply powered a "
                    "flush of that cache into these flash modules. On this start-up "
                    "the array validates the vault — and if the last shutdown was "
                    "unclean, restores the cache from flash before doing anything "
                    "else — so no acknowledged write is ever lost across a power "
                    "event."
                ),
                plain=(
                    "Before booting the storage stack, each node checks its "
                    "vault-to-flash modules. PowerMax's write cache lives in "
                    "volatile DRAM; on a power loss the SPS powered a flush of that "
                    "cache to these NVMe self-encrypting flash modules. On this "
                    "boot the array validates the vault — and if the last shutdown "
                    "was dirty, restores cache from flash before anything else — so "
                    "no acknowledged write is ever lost across a power event."
                ),
                standard=(
                    "Before booting the storage stack, each node checks its "
                    "vault-to-flash modules. PowerMax's write cache lives in "
                    "volatile DRAM; on a power loss the SPS powered a flush of "
                    "that cache to these NVMe SED flash modules. On this boot the "
                    "array validates the vault — and if the last shutdown was "
                    "dirty, restores cache from flash before anything else — so no "
                    "acknowledged write is ever lost across a power event."
                ),
                technical=(
                    "Vault validation precedes the storage stack. Write cache is "
                    "volatile DRAM, flushed to NVMe SED vault modules under SPS "
                    "power on line loss. This boot validates the vault and, on a "
                    "dirty prior shutdown, restores cache from flash before "
                    "proceeding — the mechanism by which no acknowledged write is "
                    "lost across a power event."
                ),
                expert=(
                    "Vault validated pre-stack. DRAM cache, SPS-powered flush to "
                    "NVMe SED modules; dirty-shutdown restore precedes everything. "
                    "No acknowledged write lost."
                ),
            ),
            active_regions=_VAULT + _CACHE,
            power_watts=620,
            fan_percent=60,
            elapsed_seconds=32,
            cycle_cost=2,
        ),
        PowerOnState(
            step=5,
            phase="boot",
            label="Directors power on — twice",
            description=L(
                novice=(
                    "Each processing unit is a complete multi-processor computer. "
                    "Each brings up power to its own processors in sequence, tests "
                    "its own memory cache, and runs its own firmware from its own "
                    "flash. The two start independently and know nothing of each "
                    "other yet — the network that joins them comes up in a later "
                    "stage."
                ),
                plain=(
                    "Each director is a full computer in its own right, with "
                    "several processors. Each brings up power to its own processors "
                    "in the correct order, tests its own memory cache, and runs "
                    "firmware from its own flash chip. The two start up "
                    "independently and have no knowledge of one another yet — the "
                    "fabric that will join them comes up several steps later, which "
                    "is itself the architectural point."
                ),
                standard=(
                    "Each director is a complete multi-socket x86 compute complex. "
                    "Each sequences power to its own Intel Xeon processors, tests "
                    "its own DRAM cache, and runs its own firmware from its own "
                    "flash. The two directors boot independently and know nothing "
                    "of each other yet — the fabric that joins them comes up in a "
                    "later stage."
                ),
                technical=(
                    "Each director is a full multi-socket x86 complex: own CPU "
                    "power sequencing, own DRAM cache test, own firmware from own "
                    "flash. Independent boots with no inter-director state — the "
                    "joining fabric initializes later, which is itself the "
                    "architectural point."
                ),
                expert=(
                    "Independent multi-socket director boots: own sequencing, own "
                    "DRAM test, own firmware. Joining fabric comes later."
                ),
            ),
            active_regions=_CPUS + _BOARDS,
            power_watts=900,
            fan_percent=55,
            elapsed_seconds=58,
            cycle_cost=2,
        ),
        PowerOnState(
            step=6,
            phase="boot",
            label="PowerMaxOS 10 loads on both directors",
            description=L(
                novice=(
                    "Each unit loads the storage operating environment — the "
                    "software that runs the whole stack: memory management, data "
                    "reduction, snapshots, replication, and the emulation layers "
                    "that let one array speak several different host protocols at "
                    "once, including the mainframe ones. This is the longest single "
                    "stage; a mission-critical storage operating system with its "
                    "integrity checks takes minutes rather than seconds, and it "
                    "boots without a screen."
                ),
                plain=(
                    "Each director boots PowerMaxOS 10 — the operating environment "
                    "running the entire storage stack: global memory management, "
                    "data reduction, SnapVX, SRDF, and the front-end emulations "
                    "that let one array speak Fibre Channel, iSCSI, NVMe, and "
                    "mainframe FICON at once. This is the longest single stage; a "
                    "mission-critical storage OS with its integrity checks is "
                    "minutes, not seconds, and it boots headless."
                ),
                standard=(
                    "Each director boots PowerMaxOS 10 — the operating environment "
                    "that runs the entire storage stack: global memory management, "
                    "data reduction, SnapVX, SRDF, and the front-end emulations "
                    "that make one array speak Fibre Channel, iSCSI, NVMe, and "
                    "mainframe FICON at once. This is the longest single stage; a "
                    "mission-critical storage OS with its integrity checks is "
                    "minutes, not seconds, and the array boots headless."
                ),
                technical=(
                    "Max-dwell stage. PowerMaxOS 10 boots per director: global "
                    "memory management, data reduction, SnapVX, SRDF, and the "
                    "front-end emulations presenting FC, iSCSI, NVMe, and FICON "
                    "concurrently from one array. Integrity-checked boot is "
                    "minutes, headless throughout."
                ),
                expert=(
                    "Max dwell: PowerMaxOS 10 per director — global memory, "
                    "reduction, SnapVX, SRDF, concurrent FC/iSCSI/NVMe/FICON "
                    "emulations. Integrity-checked, headless."
                ),
            ),
            active_regions=_CPUS + _CACHE,
            power_watts=1250,
            fan_percent=50,
            elapsed_seconds=200,
            cycle_cost=4,
        ),
        PowerOnState(
            step=7,
            phase="fabric",
            label="Dynamic Fabric comes up",
            description=L(
                novice=(
                    "The high-speed internal network initializes and the two units "
                    "find each other over it. Cache mirroring and heartbeats now "
                    "cross that network — every dirty write is copied to the "
                    "partner before it is acknowledged, and each unit watches the "
                    "other for instant failover. On the larger model this same "
                    "network is a redundant mesh joining every pair to every other; "
                    "on the smaller one it is a direct connection between the two."
                ),
                plain=(
                    "The InfiniBand Dynamic Fabric initializes at 100 Gb/s per port "
                    "and the two directors find each other over it. Cache mirroring "
                    "and heartbeat now cross the fabric — every dirty write is "
                    "copied to the partner before it is acknowledged, and each node "
                    "watches the other for instant failover. On a PowerMax 8500 "
                    "this fabric is a dual redundant mesh connecting every node "
                    "pair to every other; on the 2500 it is a direct connection "
                    "between the pair."
                ),
                standard=(
                    "The InfiniBand Dynamic Fabric initializes at 100 Gb/s per "
                    "port and the two directors find each other over it. Cache "
                    "mirroring and heartbeat now cross the fabric — every dirty "
                    "write is copied to the partner before it is acknowledged, and "
                    "each node watches the other for instant failover. On a "
                    "PowerMax 8500 this same fabric is a dual redundant mesh that "
                    "connects every node pair to every other; on the 2500 it is a "
                    "direct connection between the pair."
                ),
                technical=(
                    "InfiniBand Dynamic Fabric initializes at 100 Gb/s per port; "
                    "directors discover each other across it. Cache mirroring and "
                    "heartbeat now traverse the fabric — dirty writes are "
                    "partner-copied before acknowledgement. On the 8500 the fabric "
                    "is a dual redundant mesh across all node pairs; on the 2500 it "
                    "is a direct pair interconnect."
                ),
                expert=(
                    "Dynamic Fabric up at 100 Gb/s/port; directors discover across "
                    "it. Cache mirror and heartbeat on-fabric; partner copy "
                    "precedes ack. Mesh on 8500, direct on 2500."
                ),
            ),
            active_regions=_FABRIC + ["fabric-bus"],
            power_watts=1450,
            fan_percent=48,
            elapsed_seconds=225,
            cycle_cost=2,
        ),
        PowerOnState(
            step=8,
            phase="drives",
            label="DME discovery — drives on the fabric",
            description=L(
                novice=(
                    "The units enumerate the separate drive enclosure across that "
                    "network. Every drive is dual-ported and reached over the "
                    "fabric rather than off one unit's local bus — so any "
                    "processing unit in the array, in any pair, has a path to any "
                    "drive. That is the physical reason this design scales outward: "
                    "computing power and capacity are separate modules joined by a "
                    "network, and either can grow without the other."
                ),
                plain=(
                    "The directors discover the separate drive enclosure across the "
                    "fabric. Every drive is dual-ported and reached over that "
                    "fabric rather than off one director's local bus, so any "
                    "director anywhere in the array has a path to any drive. This "
                    "is the physical reason PowerMax scales outward: compute and "
                    "capacity are separate modules joined by a network, and either "
                    "can grow without the other."
                ),
                standard=(
                    "The directors enumerate the Dynamic Media Enclosure over the "
                    "fabric. Every NVMe drive is dual-ported and reached across "
                    "the InfiniBand fabric rather than off one node's PCIe bus — "
                    "so any director in the array, in any node pair, has a path to "
                    "any drive. That is the physical reason PowerMax scales out: "
                    "compute and capacity are separate modules joined by the "
                    "fabric, and either can grow without the other."
                ),
                technical=(
                    "DME enumeration across the fabric. Dual-ported NVMe reached "
                    "over InfiniBand rather than a node-local PCIe bus, so any "
                    "director in any node pair holds a path to any drive. This is "
                    "the mechanism behind independent scaling of compute and "
                    "capacity, and why the engine asserts fabric initialization "
                    "strictly precedes drive discovery."
                ),
                expert=(
                    "DME enumerated over fabric, not node-local PCIe. Any director, "
                    "any pair, any drive. Fabric-before-drives asserted — "
                    "independent compute/capacity scaling."
                ),
            ),
            active_regions=["dme"] + _FABRIC,
            power_watts=1650,
            fan_percent=46,
            elapsed_seconds=245,
        ),
        PowerOnState(
            step=9,
            phase="pool",
            label="Flexible RAID pool assembles",
            description=L(
                novice=(
                    "The storage pool is assembled with a flexible redundancy "
                    "scheme spread across the enclosure's drives, with spare "
                    "capacity distributed among them rather than sitting in one "
                    "dedicated drive. When a drive fails, every remaining drive "
                    "contributes to the rebuild at once instead of a single spare "
                    "becoming the bottleneck. The array is entirely "
                    "thin-provisioned from the factory, so usable capacity is a "
                    "policy decision over this pool rather than a fixed carve-up."
                ),
                plain=(
                    "The storage pool is assembled using Flexible RAID — a choice "
                    "of redundancy layouts spread across the enclosure's drives, "
                    "with spare capacity distributed among all of them rather than "
                    "sitting idle in one dedicated drive. When a drive fails, every "
                    "surviving drive helps rebuild it at once. The array is fully "
                    "thin-provisioned from the factory, so usable capacity is a "
                    "policy over the pool rather than a fixed division of it."
                ),
                standard=(
                    "PowerMaxOS assembles the storage resource pool with Flexible "
                    "RAID — RAID 1, 5, or 6 layouts spread across the DME's drives "
                    "with distributed spare capacity. When a drive fails, every "
                    "remaining drive contributes to the rebuild at once instead of "
                    "a single hot spare becoming the bottleneck. The array is 100% "
                    "thin-provisioned from the factory, so usable capacity is a "
                    "policy over this pool, not a fixed carve-up."
                ),
                technical=(
                    "Storage resource pool assembled under Flexible RAID — RAID 1, "
                    "5, or 6 across the DME with distributed spare capacity rather "
                    "than dedicated hot spares, so rebuild is many-to-many. The "
                    "array ships 100% thin-provisioned, making usable capacity a "
                    "policy expressed over the pool rather than a static "
                    "allocation."
                ),
                expert=(
                    "Flexible RAID pool with distributed spare; many-to-many "
                    "rebuild. 100% thin-provisioned from factory — capacity is "
                    "policy, not carve-up."
                ),
            ),
            active_regions=["dme"] + _CPUS,
            power_watts=1780,
            fan_percent=45,
            elapsed_seconds=290,
            cycle_cost=3,
        ),
        PowerOnState(
            step=10,
            phase="services",
            label="Data services start",
            description=L(
                novice=(
                    "The data-service engines come up: deduplication and "
                    "compression running in dedicated hardware across the whole "
                    "array, local snapshots, and the replication engines. Two words "
                    "matter — 'inline' and 'global'. Reduction happens across the "
                    "entire array before data reaches flash, with no separate "
                    "cleanup pass afterwards, and the reduction ratio is "
                    "contractually guaranteed."
                ),
                plain=(
                    "The data-service engines come up: global inline data reduction "
                    "— deduplication and compression in dedicated hardware, "
                    "guaranteed 5:1 on open systems and 3:1 on mainframe — plus "
                    "SnapVX local snapshots and the SRDF replication engines. "
                    "'Inline' and 'global' matter: reduction happens across the "
                    "whole array before data reaches flash, with no post-process "
                    "pass."
                ),
                standard=(
                    "The data-service engines come up: global inline data "
                    "reduction (deduplication and compression, in dedicated "
                    "hardware, guaranteed 5:1 on open systems and 3:1 on "
                    "mainframe), SnapVX local snapshots, and the SRDF replication "
                    "engines. 'Inline' and 'global' matter — reduction happens "
                    "across the whole array before data reaches flash, with no "
                    "post-process pass."
                ),
                technical=(
                    "Data-service engines start: global inline reduction in "
                    "dedicated hardware with contractual 5:1 open-systems and 3:1 "
                    "mainframe ratios, SnapVX local snapshots, and SRDF "
                    "replication. Inline and array-global — reduction precedes the "
                    "flash write and spans the whole array rather than a pool, with "
                    "no post-process pass."
                ),
                expert=(
                    "Global inline reduction in hardware (5:1 open, 3:1 mainframe, "
                    "contractual), SnapVX, SRDF. Array-global, pre-flash, no "
                    "post-process."
                ),
            ),
            active_regions=_CPUS + _CACHE,
            power_watts=1830,
            fan_percent=42,
            elapsed_seconds=310,
        ),
        PowerOnState(
            step=11,
            phase="services",
            label="Front-end ports online",
            description=L(
                novice=(
                    "The front-end modules present the array to its hosts: several "
                    "block protocols over both Fibre Channel and Ethernet, and — "
                    "for IBM mainframes — the specialist mainframe protocols. "
                    "Replication ports light up for array-to-array copying. "
                    "Matching modules in both units mean every host connection "
                    "exists twice, once per unit, so restarting one never removes a "
                    "path a host depends on."
                ),
                plain=(
                    "The front-end modules present the array to the hosts that will "
                    "use it: Fibre Channel and FC-NVMe, iSCSI and NVMe over TCP on "
                    "Ethernet, and — for IBM mainframes — FICON and zHyperlink. "
                    "Replication ports come up for copying between arrays. Because "
                    "both directors carry matching modules, every host path exists "
                    "twice, so restarting one director never removes a path "
                    "something depends on."
                ),
                standard=(
                    "The front-end I/O modules present the array to hosts: Fibre "
                    "Channel and FC-NVMe, iSCSI and NVMe/TCP over Ethernet, and — "
                    "for IBM mainframe — FICON and zHyperlink. SRDF ports light up "
                    "for array-to-array replication. Matching modules in both "
                    "directors mean every host path exists twice, once per node, "
                    "so a director reboot never removes a path a host depends on."
                ),
                technical=(
                    "Front-end I/O modules present FC and FC-NVMe, iSCSI and "
                    "NVMe/TCP, plus FICON and zHyperlink for mainframe attach; SRDF "
                    "ports come up for array-to-array replication. Module symmetry "
                    "across directors duplicates every host path, so a director "
                    "reboot is never path-removing from a host's perspective."
                ),
                expert=(
                    "Front-end up: FC/FC-NVMe, iSCSI/NVMe-TCP, FICON/zHyperlink, "
                    "plus SRDF ports. Symmetric modules — every host path "
                    "duplicated per director."
                ),
            ),
            active_regions=_IOMODS,
            power_watts=1880,
            fan_percent=40,
            elapsed_seconds=330,
        ),
        PowerOnState(
            step=12,
            phase="services",
            label="Unisphere management up",
            description=L(
                novice=(
                    "The management application and its programming interface come "
                    "up on the management network, kept entirely off the path that "
                    "carries data. From here an administrator provisions storage, "
                    "sets service levels, and configures replication. The array "
                    "also sends telemetry home for fleet health monitoring and "
                    "capacity forecasting — which is the subject of the "
                    "observability twin elsewhere in this repo."
                ),
                plain=(
                    "Unisphere for PowerMax — the management application and its "
                    "REST API — comes up on the management network, kept entirely "
                    "off the data path. From here an administrator provisions "
                    "storage groups, sets service levels, and configures SRDF. The "
                    "array also phones telemetry home to CloudIQ for fleet health "
                    "and capacity forecasting."
                ),
                standard=(
                    "Unisphere for PowerMax — the management application and its "
                    "REST API — comes up on the management network, kept entirely "
                    "off the data path. From here an administrator provisions "
                    "storage groups, sets service levels, and configures SRDF; the "
                    "array also phones telemetry home to CloudIQ for fleet health "
                    "and capacity forecasting."
                ),
                technical=(
                    "Unisphere and its REST API come up on the management network, "
                    "isolated from the data path. Provisioning of storage groups, "
                    "service-level assignment, and SRDF configuration happen here. "
                    "Telemetry egresses to CloudIQ for fleet health and capacity "
                    "forecasting — the pipeline the CloudIQ twin models end to end."
                ),
                expert=(
                    "Unisphere and REST API up on the management network, off the "
                    "data path. Storage groups, service levels, SRDF. Telemetry "
                    "egress to CloudIQ."
                ),
            ),
            active_regions=_MGMT,
            power_watts=1890,
            fan_percent=38,
            elapsed_seconds=350,
        ),
        PowerOnState(
            step=13,
            phase="online",
            label="Serving I/O — mission-critical ready",
            description=L(
                novice=(
                    "The array is online. Both units serve host traffic and share "
                    "the load across the internal network; writes are mirrored "
                    "through cache and protected by the flash vault, reads come off "
                    "the drive pool, and data reduction runs on every write as it "
                    "arrives. A single pair plus one drive enclosure draws in the "
                    "region of two kilovolt-amperes with fans under thermal "
                    "control. From plugging in the cords to serving traffic: "
                    "minutes, with nobody touching the array."
                ),
                plain=(
                    "The array is serving. Both directors handle host traffic and "
                    "share the load across the fabric; writes are mirrored through "
                    "cache and protected by the flash vault, reads come from the "
                    "drive pool, and reduction runs on every write as it arrives. "
                    "One director pair with a single drive enclosure draws around "
                    "two kilovolt-amperes with fans under thermal control. Cords in "
                    "to serving traffic: minutes, unattended."
                ),
                standard=(
                    "The array is online. Both directors serve host I/O and share "
                    "the load across the fabric; writes mirror through cache and "
                    "are protected by vault-to-flash, reads come off the NVMe pool, "
                    "and data reduction runs inline on every write. Steady-state "
                    "draw for a single node pair plus one DME is in the two-kilovolt-"
                    "ampere range with fans on thermal control. From cords-in to "
                    "serving I/O: minutes, with no one touching the array."
                ),
                technical=(
                    "Online: both directors serving and load-sharing across the "
                    "fabric, writes cache-mirrored and vault-protected, reads from "
                    "the NVMe pool, reduction inline on every write. A single node "
                    "pair plus one DME draws in the 2 kVA range under thermal "
                    "control. Cords-in to serving in minutes, unattended."
                ),
                expert=(
                    "Online: both directors serving across fabric, cache-mirrored "
                    "vault-protected writes, NVMe reads, inline reduction. ~2 kVA "
                    "per pair plus DME. Unattended, minutes."
                ),
            ),
            active_regions=(
                ["dme", "fabric-bus"]
                + _CPUS + _CACHE + _FABRIC + _IOMODS + _MGMT + _VAULT + _FANS
            ),
            power_watts=1950,
            fan_percent=35,
            elapsed_seconds=375,
        ),
    ]
