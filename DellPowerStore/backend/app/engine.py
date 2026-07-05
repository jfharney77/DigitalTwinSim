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
            description=(
                "Both power cords are plugged in — ideally to separate "
                "feeds, one per node. The enclosure is dark: no fans, no "
                "LEDs, no draw. Unlike a server, nothing more is required "
                "of you; a storage appliance has no power button, and what "
                "happens next is entirely automatic."
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
            description=(
                "Each node's power supply detects line voltage and brings "
                "its rails up. Applying AC *is* the power-on: an array is "
                "expected to return to service by itself after any outage, "
                "with no human at the rack to press anything. Both node "
                "canisters begin waking in parallel — from here on, "
                "everything happens twice."
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
            description=(
                "Each node tests its battery backup unit (BBU) before "
                "anything else matters. The BBU is not a UPS — it cannot "
                "keep the array running. Its only job is 'vaulting': on AC "
                "loss it powers the node for the few seconds needed to "
                "flush cached writes to non-volatile media. Until both "
                "nodes know a power loss is survivable, the array will not "
                "accept a single write."
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
            description=(
                "Both nodes' fan packs run up hard, then settle once "
                "thermal sensors report in — the same conservative "
                "max-airflow-first policy servers use. Airflow is front to "
                "rear: in across the 25 NVMe drives, through each node "
                "canister, out past its PSU. Each node cools itself; a fan "
                "failure in one canister never threatens the other."
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
            description=(
                "Each controller node is a complete x86 computer, and each "
                "runs its own BIOS/UEFI firmware from its own flash, "
                "sequences power to its own Xeon, and tests its own DRAM. "
                "The two nodes boot independently and know nothing of each "
                "other yet — redundancy starts with the assumption that "
                "the partner may not be there."
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
            description=(
                "Each node boots PowerStoreOS from its internal M.2 device "
                "— an embedded Linux that runs the entire storage stack as "
                "containers: block services, file services, management, "
                "data mobility. This is the longest single stage; booting "
                "a storage operating system with its integrity checks is "
                "minutes, not seconds. The console would show nothing — "
                "arrays boot headless."
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
            description=(
                "Each node enumerates the drive bay over PCIe. Every drive "
                "is dual-ported: it has two independent PCIe connections, "
                "one to each node, with no SAS expanders or protocol "
                "bridges between. Both controllers therefore reach all 25 "
                "slots directly — the physical reason failover is instant: "
                "the surviving node doesn't take over the drives, it "
                "already owns a path to them."
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
            description=(
                "The four NVMe NVRAM drives come up as the write cache. "
                "From now on, a host write lands in NVRAM mirrored across "
                "both nodes' views and is acknowledged immediately; the "
                "destage to capacity SSDs happens later, off the latency "
                "path. Because NVRAM is non-volatile and mirrored, an "
                "acknowledged write survives a node failure and a power "
                "loss both."
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
            description=(
                "The two boots converge. Over the internal interconnect "
                "the nodes exchange heartbeats, establish the cache "
                "mirroring path, and negotiate active/active operation — "
                "both nodes will own volumes and serve I/O at once, rather "
                "than one idling as a spare. Each also starts watching the "
                "other: if a node ever stops answering, its partner takes "
                "over all host paths in seconds."
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
            description=(
                "The dynamic resiliency engine — PowerStore's replacement "
                "for fixed RAID groups — assembles the pool. Every drive "
                "is carved into slices, and redundancy (parity) is spread "
                "across all drives with spare capacity distributed the "
                "same way. When a drive fails, every remaining drive "
                "contributes to the rebuild in parallel, instead of one "
                "hot-spare becoming the bottleneck."
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
            description=(
                "The data-service containers come up on both nodes: inline "
                "deduplication and compression, snapshots, and thin "
                "provisioning. 'Inline' and 'always on' matter — every "
                "write is reduced before it touches flash, there is no "
                "post-process pass and no switch to forget. Dedup finds "
                "identical blocks and stores them once; compression "
                "shrinks what remains."
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
            description=(
                "The embedded mezzanine ports and the hot-swap I/O modules "
                "present the array to hosts: Fibre Channel and iSCSI block "
                "targets, NVMe-oF (NVMe-over-Fabrics — the NVMe protocol "
                "carried over FC or TCP, skipping SCSI translation "
                "entirely), and NFS/SMB file shares. Matching modules in "
                "both nodes mean every host path exists twice, once per "
                "node."
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
            description=(
                "PowerStore Manager — the web UI and REST API — comes up "
                "on a cluster IP that floats between the nodes' management "
                "ports, so the address you bookmark keeps working through "
                "a node failure. Management traffic stays on its own 1 GbE "
                "ports, completely off the data path."
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
            description=(
                "The array is online. Both nodes serve host I/O and share "
                "the load; writes mirror through NVRAM, reads come off the "
                "NVMe pool, and data reduction runs inline on every write. "
                "Steady-state draw for a dual-node all-NVMe 2U appliance "
                "idles in the several-hundred-watt range with fans on "
                "thermal control. From cords-in to serving I/O: minutes, "
                "with no one touching the box."
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
