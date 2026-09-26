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
        source="Zhu, Li & Patterson, 'Avoiding the Disk Bottleneck in the Data "
               "Domain Deduplication File System' (USENIX FAST 2008): "
               "variable-length segments of 4–12 KB, ~8 KB average — "
               "https://www.usenix.org/legacy/event/fast08/tech/full_papers/zhu/zhu.pdf "
               "— the mean is used as a modeling estimate",
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
        source="estimate — Data Domain's SISL design (FAST 2008) keeps a "
               "compact summary vector plus a locality-preserved cache in "
               "RAM rather than the whole index; this fraction is a "
               "modeling stand-in for that, not a Dell figure",
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
    "capacity_notice_margin_pct": Constant(
        value=20.0, unit="%",
        source="estimate — this simulator's rule for when a capacity curve "
               "has left its trend, set wide enough that a month-end batch "
               "would not trip it; real growth alerts vary by site",
        estimated=True,
        blurb="How far physical must rise above the projected pre-event "
              "trend before the capacity notice is logged.",
    ),
    "capacity_trend_window_days": Constant(
        value=10.0, unit="days",
        source="estimate — trailing window used to fit the pre-event trend",
        estimated=True,
        blurb="Days of history behind the straight line the capacity "
              "notice compares against.",
    ),
}


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value


# --- The appliance table -----------------------------------------------------
# Usable capacities are the maxima from Dell's PowerProtect Data Domain
# family spec sheet (© 2026, checked 2026-09): DD3410 8–40 TB, DD9910
# 576 TB–2.1 PB, DD9910F 272 TB–1.1 PB. Index RAM and base (pre-Boost)
# ingest are modeling estimates — Dell publishes only a maximum DD Boost
# throughput per model, which the sources quote for scale.
SPEC_SHEET = (
    "https://www.delltechnologies.com/asset/en-us/products/cyber-resilience/technical-support/dell-powerprotect-data-domain-family-spec-sheet.pdf"
)

APPLIANCES: dict[str, Appliance] = {
    "dd3410": Appliance(
        id="dd3410",
        name="Data Domain DD3410 (edge/ROBO)",
        usable_tb=40.0,
        index_ram_gb=8.0,
        base_ingest_gbps=3.0,
        blurb="The entry appliance — branch offices and small estates. Same "
              "DDOS filesystem, same dedupe, small index RAM: the knee is "
              "easiest to reach here.",
        source="usable capacity 8–40 TB (maximum used) per Dell PowerProtect "
               "Data Domain family spec sheet, which also lists up to "
               "20.7 TB/hr with DD Boost — " + SPEC_SHEET + "; index RAM "
               "and base ingest are estimates",
        estimated=True,
    ),
    "dd9910": Appliance(
        id="dd9910",
        name="Data Domain DD9910 (disk flagship)",
        usable_tb=2100.0,
        index_ram_gb=192.0,
        base_ingest_gbps=15.0,
        blurb="The datacenter flagship — up to 2.1 PB usable; Dell quotes "
              "up to 158.4 PB logical, a vendor figure that assumes "
              "typically 75:1 data reduction.",
        source="usable capacity 576 TB–2.1 PB (maximum used), logical up to "
               "158.4 PB and up to 130 TB/hr with DD Boost per Dell "
               "PowerProtect Data Domain family spec sheet — " + SPEC_SHEET
               + "; index RAM and base ingest are estimates",
        estimated=True,
    ),
    "dd-all-flash": Appliance(
        id="dd-all-flash",
        name="Data Domain DD9910F (all-flash, 2025)",
        usable_tb=1100.0,
        index_ram_gb=96.0,
        base_ingest_gbps=20.0,
        blurb="The all-flash appliance, unveiled at Dell Technologies World "
              "in May 2025. Dell's headline claims are about getting data "
              "back out — up to 4x faster restores and 2x faster "
              "replication than its disk-based systems; the spec sheet "
              "lists the same maximum DD Boost ingest as the DD9910.",
        source="usable capacity 272 TB–1.1 PB (maximum used) and up to "
               "130 TB/hr with DD Boost per Dell PowerProtect Data Domain "
               "family spec sheet — " + SPEC_SHEET + "; restore and "
               "replication claims are Dell's own (Dell blog, 20 May 2025 — "
               "https://www.dell.com/en-us/blog/achieving-cyber-resilience-with-dell-powerprotect/); "
               "index RAM and base ingest are estimates",
        estimated=True,
    ),
}
