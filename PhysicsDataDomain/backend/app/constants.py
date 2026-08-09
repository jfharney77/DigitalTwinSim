"""Every model constant in one place, each with units and a source — the
suite's constants discipline (physics_specs/BUILD_PLAN.md): no invented
Dell specs presented as fact. Values confirmed by Dell documentation cite
it; everything else says ``estimate`` and the UI badges readouts derived
from estimates. The appliance table lives here too, same rule.
"""

from __future__ import annotations

from .models import Appliance, Constant

CONSTANTS: dict[str, Constant] = {
    # --- Chunking & the store ---------------------------------------------
    "avg_chunk_kb": Constant(
        value=8.0, unit="KiB",
        source="Data Domain SISL/variable-length segmenting averages ~8 KB "
               "segments (Dell DDOS architecture papers) — estimate of the mean",
        estimated=True,
        blurb="Average variable-length segment (chunk) size the chunker emits.",
    ),
    "index_entry_bytes": Constant(
        value=64.0, unit="B/chunk",
        source="estimate — fingerprint (SHA-1 class, 20 B) plus container "
               "locator and index structure overhead",
        estimated=True,
        blurb="In-memory fingerprint-index cost per unique chunk.",
    ),
    "metadata_overhead_fraction": Constant(
        value=0.04, unit="fraction",
        source="estimate — container metadata, checksums, filesystem overhead",
        estimated=True,
        blurb="Physical overhead multiplier on stored chunk bytes (1 + this).",
    ),
    "lz_max_ratio": Constant(
        value=2.0, unit="×",
        source="estimate — typical local (lz) compression on low-entropy "
               "business data after dedupe",
        estimated=True,
        blurb="Local compression ratio at entropy 0; falls to 1.0× at entropy 100.",
    ),
    # --- Entropy & the smoke alarm ----------------------------------------
    "encrypted_entropy_pct": Constant(
        value=98.0, unit="%",
        source="ciphertext is computationally indistinguishable from random "
               "— information theory",
        estimated=False,
        blurb="Stream entropy of encrypted data. Compression and dedupe both die here.",
    ),
    "entropy_alarm_delta": Constant(
        value=20.0, unit="points",
        source="estimate — anomaly threshold above the dataset's own baseline",
        estimated=True,
        blurb="Stream entropy this far above baseline trips the smoke alarm.",
    ),
    "entropy_alarm_floor_pct": Constant(
        value=85.0, unit="%",
        source="estimate — absolute entropy that is alarming regardless of baseline",
        estimated=True,
        blurb="Stream entropy above this always trips the alarm.",
    ),
    # --- Ingest vs index pressure ------------------------------------------
    "ram_resident_fraction": Constant(
        value=0.05, unit="fraction",
        source="estimate — SISL-style sampling keeps only a fraction of "
               "fingerprints RAM-resident; locality prefetch covers the rest",
        estimated=True,
        blurb="Fraction of the fingerprint index that must live in RAM to "
              "keep lookups fast.",
    ),
    "boost_max_speedup": Constant(
        value=20.0, unit="×",
        source="estimate — practical ceiling on effective logical ingest "
               "from client-side dedupe (DD Boost class behavior)",
        estimated=True,
        blurb="Cap on logical-vs-physical ingest speedup when almost "
              "nothing is novel.",
    ),
    "index_knee_factor": Constant(
        value=1.5, unit="—",
        source="estimate — throughput divisor slope once the fingerprint "
               "index outgrows RAM and lookups spill to flash/disk",
        estimated=True,
        blurb="Ingest GB/s divisor per unit of index-over-RAM pressure.",
    ),
    "capacity_warn_pct": Constant(
        value=85.0, unit="%",
        source="estimate — common capacity-planning alert threshold",
        estimated=True,
        blurb="Capacity fraction where planning alarms fire.",
    ),
}


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value


# --- The appliance table -----------------------------------------------------
# Capacity figures follow the claims the DellPowerProtect narrative twin
# carries from the Data Domain family data sheet; RAM and ingest are
# estimates pending a research pass (flagged).

APPLIANCES: dict[str, Appliance] = {
    "dd3410": Appliance(
        id="dd3410",
        name="Data Domain DD3410 (edge/ROBO)",
        usable_tb=32.0,
        index_ram_gb=8.0,
        base_ingest_gbps=3.0,
        blurb="The entry appliance — branch offices and small estates. Same "
              "DDOS filesystem, same dedupe, small index RAM: the knee is "
              "easiest to reach here.",
        source="usable capacity per Data Domain family data sheet (8–32 TBu "
               "class); RAM and ingest are estimates",
        estimated=True,
    ),
    "dd9910": Appliance(
        id="dd9910",
        name="Data Domain DD9910 (disk flagship)",
        usable_tb=1500.0,
        index_ram_gb=192.0,
        base_ingest_gbps=15.0,
        blurb="The datacenter flagship — petabyte-class usable, multi-tens "
              "of PB logical after dedupe.",
        source="capacity class per Data Domain family data sheet; RAM and "
               "ingest are estimates",
        estimated=True,
    ),
    "dd-all-flash": Appliance(
        id="dd-all-flash",
        name="Data Domain All-Flash (2025 generation)",
        usable_tb=300.0,
        index_ram_gb=96.0,
        base_ingest_gbps=20.0,
        blurb="The all-flash generation (announced September 2025): the "
              "headline change is restore and replication speed; ingest "
              "gains too.",
        source="generation per Dell September 2025 announcement (via the "
               "DellPowerProtect twin); all figures are estimates",
        estimated=True,
    ),
}
