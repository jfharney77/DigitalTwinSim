"""Every model constant with units and a source. Storage numbers are the
most benchmark-abused figures in the industry, so the honesty rule works
overtime here: everything below is an ``estimate`` for legibility — the
knee's shape is the lesson, not the absolute IOPS.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Media latency (spec 02's table) ----------------------------------
    "lat_nvme_ms": Constant(
        value=0.1, unit="ms", source="estimate — spec 02 media table",
        estimated=True, blurb="NVMe media service latency.",
    ),
    "lat_ssd_ms": Constant(
        value=0.3, unit="ms", source="estimate — spec 02 media table",
        estimated=True, blurb="SAS/SATA SSD service latency.",
    ),
    "lat_hdd_ms": Constant(
        value=8.0, unit="ms", source="estimate — spec 02 media table",
        estimated=True, blurb="7.2k HDD service latency (seek + rotate).",
    ),
    "cache_hit_lat_ms": Constant(
        value=0.05, unit="ms", source="estimate — DRAM/NVRAM hit",
        estimated=True, blurb="Latency of a cache hit.",
    ),
    # --- Per-unit performance ceilings ------------------------------------
    "iops_per_unit_powerstore_k": Constant(
        value=400, unit="thousand IOPS", source="estimate — spec 02: hundreds of thousands per appliance",
        estimated=True, blurb="Front-end 8K IOPS ceiling per PowerStore appliance.",
    ),
    "iops_per_unit_powermax_k": Constant(
        value=900, unit="thousand IOPS", source="estimate — brick-class ceiling",
        estimated=True, blurb="Per-brick IOPS ceiling, PowerMax.",
    ),
    "iops_per_node_scaleout_k": Constant(
        value=80, unit="thousand IOPS", source="estimate", estimated=True,
        blurb="Per-node IOPS contribution, PowerScale/ObjectScale class.",
    ),
    "iops_per_node_powerflex_k": Constant(
        value=150, unit="thousand IOPS", source="estimate — SDS node with local NVMe",
        estimated=True, blurb="Per-node IOPS ceiling before the network cap, PowerFlex.",
    ),
    "iops_per_node_lightning_k": Constant(
        value=120, unit="thousand IOPS",
        source="estimate — parallel-FS node, sequential-optimized", estimated=True,
        blurb="Per-node contribution in a Lightning parallel-FS pool.",
    ),
    "coordination_tax_per_node": Constant(
        value=0.02, unit="fraction/node beyond 10",
        source="estimate — spec 02: ~2%/node beyond 10", estimated=True,
        blurb="Scale-out coordination tax on per-node contribution.",
    ),
    "coordination_tax_cap": Constant(
        value=0.35, unit="fraction", source="estimate", estimated=True,
        blurb="Ceiling on the coordination tax.",
    ),
    "gbps_per_iopsk_8k": Constant(
        value=0.0082, unit="GB/s per 1k 8K IOPS",
        source="8 KB × 1000/s = 8 MB/s — arithmetic", estimated=False,
        blurb="Throughput per thousand IOPS at 8 KB blocks (scales with block size).",
    ),
    "small_object_tax": Constant(
        value=0.45, unit="fraction of throughput lost",
        source="estimate — per-object metadata dominates small objects",
        estimated=True,
        blurb="ObjectScale throughput penalty when the object mix is small.",
    ),
    # --- Queueing ----------------------------------------------------------
    "rho_clamp": Constant(
        value=0.98, unit="—", source="M/M/1 divergence guard — modeling choice",
        estimated=False,
        blurb="Utilization clamp in the 1/(1−ρ) latency multiplier.",
    ),
    "p99_multiplier": Constant(
        value=3.0, unit="× mean", source="estimate — heavy-tail proxy",
        estimated=True, blurb="p99 latency as a multiple of the queue-adjusted mean.",
    ),
    # --- Protection overheads ----------------------------------------------
    "ovh_raid5": Constant(
        value=0.125, unit="fraction", source="7+1 RAID 5 — arithmetic",
        estimated=False, blurb="Capacity overhead, RAID 5 (7+1).",
    ),
    "ovh_raid6": Constant(
        value=0.25, unit="fraction", source="6+2 RAID 6 — arithmetic",
        estimated=False, blurb="Capacity overhead, RAID 6 (6+2).",
    ),
    "ovh_mirror": Constant(
        value=0.5, unit="fraction", source="2× mirror — arithmetic",
        estimated=False, blurb="Capacity overhead, mesh mirroring.",
    ),
    "ovh_ec8_2": Constant(
        value=0.2, unit="fraction", source="8+2 erasure coding — arithmetic",
        estimated=False, blurb="Capacity overhead, EC 8+2.",
    ),
    "ovh_ec16_4": Constant(
        value=0.2, unit="fraction", source="16+4 erasure coding — arithmetic",
        estimated=False, blurb="Capacity overhead, EC 16+4 (wider stripe, same rate).",
    ),
    "snapshot_ovh_per_snap_pct": Constant(
        value=0.05, unit="% of used per snapshot per day",
        source="estimate — change-rate dependent", estimated=True,
        blurb="Snapshot capacity growth per retained daily snapshot.",
    ),
    # --- Rebuild ------------------------------------------------------------
    "rebuild_gbps_controller": Constant(
        value=1.2, unit="GB/s", source="estimate — controller array, host I/O competing",
        estimated=True,
        blurb="Rebuild bandwidth for a dual-controller array (PowerStore/PowerMax).",
    ),
    "rebuild_gbps_per_node": Constant(
        value=0.5, unit="GB/s per surviving node",
        source="estimate — cluster-wide rebuild parallelism", estimated=True,
        blurb="Rebuild bandwidth contribution per surviving scale-out node.",
    ),
    "rebuild_gbps_per_node_powerflex": Constant(
        value=2.0, unit="GB/s per surviving node",
        source="estimate — every node rebuilds a slice at once", estimated=True,
        blurb="PowerFlex's massively parallel rebuild rate per node.",
    ),
    "rebuild_latency_penalty": Constant(
        value=1.6, unit="× latency", source="estimate — rebuild I/O competes",
        estimated=True, blurb="Latency multiplier while a rebuild runs.",
    ),
    # --- Replication --------------------------------------------------------
    "srdf_ms_per_km": Constant(
        value=0.01, unit="ms/km one-way",
        source="speed of light in fiber ≈ 200 km/ms — physics", estimated=False,
        blurb="One-way light latency per km of fiber (×2 for the round trip).",
    ),
    "async_link_gbs": Constant(
        value=2.0, unit="GB/s", source="estimate — WAN replication link",
        estimated=True, blurb="Async SRDF link bandwidth; RPO grows when writes outrun it.",
    ),
    # --- PowerMax personality ----------------------------------------------
    "blip_ms": Constant(
        value=4.0, unit="ms", source="estimate — director failover blip",
        estimated=True,
        blurb="Transient latency added by a PowerMax component failure (decays).",
    ),
    "blip_decay_h": Constant(
        value=2.0, unit="h", source="estimate", estimated=True,
        blurb="Decay constant of the failover blip.",
    ),
    # --- Exascale / AI workload --------------------------------------------
    "checkpoint_period_h": Constant(
        value=6, unit="h", source="estimate — large-model checkpoint cadence",
        estimated=True, blurb="Hours between training checkpoint bursts.",
    ),
    "checkpoint_burst_multiplier": Constant(
        value=6.0, unit="× write demand", source="estimate", estimated=True,
        blurb="Write-demand spike during a checkpoint burst.",
    ),
}


def value(name: str) -> float:
    return CONSTANTS[name].value


PROTECTION_OVERHEAD = {
    "raid5": "ovh_raid5",
    "raid6": "ovh_raid6",
    "mirror": "ovh_mirror",
    "ec8+2": "ovh_ec8_2",
    "ec16+4": "ovh_ec16_4",
}

# How many simultaneous failures each protection scheme survives.
PROTECTION_SURVIVES = {
    "raid5": 1,
    "raid6": 2,
    "mirror": 1,
    "ec8+2": 2,
    "ec16+4": 4,
}
