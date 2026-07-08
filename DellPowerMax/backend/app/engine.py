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
            description=(
                "Line cords are connected to the cabinet's intelligent power "
                "distribution units — two power zones, fed from separate "
                "feeds. The array is dark. As with any storage array there is "
                "no power button: an array is expected to return to service by "
                "itself after an outage, so what happens next is entirely "
                "automatic."
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
            description=(
                "Each director's power supplies detect line voltage and bring "
                "their rails up. The intelligent PDUs begin streaming "
                "telemetry — power, voltage, current, temperature, humidity. "
                "Both nodes of the pair wake in parallel: from here on, "
                "everything happens twice, once per director, because "
                "redundancy starts with the assumption that the partner might "
                "not be there."
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
            description=(
                "Each node tests its standby power supply (SPS) — the battery "
                "behind vault-to-flash. The SPS is not a UPS and cannot keep "
                "the array serving; its only job is to power the director "
                "through the seconds it takes to flush DRAM cache to flash if "
                "line power is lost. Until both nodes know a power loss is "
                "survivable, the array will not accept a single write."
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
            description=(
                "Both nodes' fans run up hard, then settle once thermal "
                "sensors report in. PowerMax runs its Xeons continuously in "
                "turbo, so cooling is deliberately aggressive — the Adaptive "
                "Cooling algorithm and the fans work harder at high ambient "
                "temperature, which is why the spec sheet quotes a higher "
                "power figure above 35 °C than below 26 °C."
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
            description=(
                "Before booting the storage stack, each node checks its "
                "vault-to-flash modules. PowerMax's write cache lives in "
                "volatile DRAM; on a power loss the SPS powered a flush of "
                "that cache to these NVMe SED flash modules. On this boot the "
                "array validates the vault — and if the last shutdown was "
                "dirty, restores cache from flash before anything else — so no "
                "acknowledged write is ever lost across a power event."
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
            description=(
                "Each director is a complete multi-socket x86 compute complex. "
                "Each sequences power to its own Intel Xeon processors, tests "
                "its own DRAM cache, and runs its own firmware from its own "
                "flash. The two directors boot independently and know nothing "
                "of each other yet — the fabric that joins them comes up in a "
                "later stage."
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
            description=(
                "Each director boots PowerMaxOS 10 — the operating environment "
                "that runs the entire storage stack: global memory management, "
                "data reduction, SnapVX, SRDF, and the front-end emulations "
                "that make one array speak Fibre Channel, iSCSI, NVMe, and "
                "mainframe FICON at once. This is the longest single stage; a "
                "mission-critical storage OS with its integrity checks is "
                "minutes, not seconds, and the array boots headless."
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
            description=(
                "The InfiniBand Dynamic Fabric initializes at 100 Gb/s per "
                "port and the two directors find each other over it. Cache "
                "mirroring and heartbeat now cross the fabric — every dirty "
                "write is copied to the partner before it is acknowledged, and "
                "each node watches the other for instant failover. On a "
                "PowerMax 8500 this same fabric is a dual redundant mesh that "
                "connects every node pair to every other; on the 2500 it is a "
                "direct connection between the pair."
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
            description=(
                "The directors enumerate the Dynamic Media Enclosure over the "
                "fabric. Every NVMe drive is dual-ported and reached across "
                "the InfiniBand fabric rather than off one node's PCIe bus — "
                "so any director in the array, in any node pair, has a path to "
                "any drive. That is the physical reason PowerMax scales out: "
                "compute and capacity are separate modules joined by the "
                "fabric, and either can grow without the other."
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
            description=(
                "PowerMaxOS assembles the storage resource pool with Flexible "
                "RAID — RAID 1, 5, or 6 layouts spread across the DME's drives "
                "with distributed spare capacity. When a drive fails, every "
                "remaining drive contributes to the rebuild at once instead of "
                "a single hot spare becoming the bottleneck. The array is 100% "
                "thin-provisioned from the factory, so usable capacity is a "
                "policy over this pool, not a fixed carve-up."
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
            description=(
                "The data-service engines come up: global inline data "
                "reduction (deduplication and compression, in dedicated "
                "hardware, guaranteed 5:1 on open systems and 3:1 on "
                "mainframe), SnapVX local snapshots, and the SRDF replication "
                "engines. 'Inline' and 'global' matter — reduction happens "
                "across the whole array before data reaches flash, with no "
                "post-process pass."
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
            description=(
                "The front-end I/O modules present the array to hosts: Fibre "
                "Channel and FC-NVMe, iSCSI and NVMe/TCP over Ethernet, and — "
                "for IBM mainframe — FICON and zHyperlink. SRDF ports light up "
                "for array-to-array replication. Matching modules in both "
                "directors mean every host path exists twice, once per node, "
                "so a director reboot never removes a path a host depends on."
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
            description=(
                "Unisphere for PowerMax — the management application and its "
                "REST API — comes up on the management network, kept entirely "
                "off the data path. From here an administrator provisions "
                "storage groups, sets service levels, and configures SRDF; the "
                "array also phones telemetry home to CloudIQ for fleet health "
                "and capacity forecasting."
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
            description=(
                "The array is online. Both directors serve host I/O and share "
                "the load across the fabric; writes mirror through cache and "
                "are protected by vault-to-flash, reads come off the NVMe pool, "
                "and data reduction runs inline on every write. Steady-state "
                "draw for a single node pair plus one DME is in the two-kilovolt-"
                "ampere range with fans on thermal control. From cords-in to "
                "serving I/O: minutes, with no one touching the array."
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
