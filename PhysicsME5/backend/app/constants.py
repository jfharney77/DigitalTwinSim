"""Every model constant in one place, each with units and a source.

``source`` is honest per the repo's no-invented-specs rule: values taken
from published documentation or plain arithmetic say so; everything else
says ``estimate`` and the UI badges readouts that derive from estimates.
The ME5-specific figures the spec flags ``verify`` (enclosure drive
counts, the marketing IOPS ceiling) are labeled with where they came from
and, where memory rather than a document is the basis, marked estimated.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Drive mechanics ---------------------------------------------------
    "hdd_72k_iops": Constant(
        value=80, unit="IOPS/drive",
        source="estimate — classic small-random figure for 7.2k NL-SAS",
        estimated=True,
        blurb="Small-random IOPS one 7.2k HDD sustains: seek + half a "
              "rotation bounds it near 80, and no firmware changes that.",
    ),
    "hdd_10k_iops": Constant(
        value=170, unit="IOPS/drive",
        source="estimate — classic small-random figure for 10k SAS",
        estimated=True,
        blurb="Small-random IOPS one 10k HDD sustains (~150–200 range).",
    ),
    "ssd_iops": Constant(
        value=20000, unit="IOPS/drive",
        source="estimate — conservative sustained mixed-I/O figure for "
               "enterprise SAS SSDs (spec-sheet peaks run far higher)",
        estimated=True,
        blurb="Small-random IOPS one SAS SSD sustains — two orders of "
              "magnitude over any spindle, which is the whole story.",
    ),
    "hdd_latency_ms": Constant(
        value=6.0, unit="ms",
        source="estimate — seek + rotational latency, 10k class",
        estimated=True,
        blurb="Unloaded service time of one HDD I/O.",
    ),
    "hdd_72k_latency_ms": Constant(
        value=10.0, unit="ms",
        source="estimate — seek + rotational latency, 7.2k class",
        estimated=True,
        blurb="Unloaded service time of one 7.2k HDD I/O.",
    ),
    "ssd_latency_ms": Constant(
        value=0.25, unit="ms",
        source="estimate — SAS SSD read service time",
        estimated=True,
        blurb="Unloaded service time of one SSD I/O — no seek to wait for.",
    ),
    # --- Rebuild -----------------------------------------------------------
    "hdd_rebuild_mbps": Constant(
        value=50, unit="MB/s",
        source="estimate — effective RAID rebuild rate onto one spindle "
               "under light host load; the reason 20 TB rebuilds take days",
        estimated=True,
        blurb="Effective rebuild rate to a spare HDD. Sequential-write "
              "spec sheets say ~200 MB/s; real rebuilds share the group "
              "with host I/O and verify as they go.",
    ),
    "ssd_rebuild_mbps": Constant(
        value=200, unit="MB/s",
        source="estimate — SSD rebuild is bounded by group read + verify, "
               "not the target's write speed",
        estimated=True,
        blurb="Effective rebuild rate to a spare SSD.",
    ),
    "rebuild_reserve_frac": Constant(
        value=0.2, unit="fraction of disk budget",
        source="estimate — arrays reserve a slice of I/O for rebuild so "
               "it finishes at all under load",
        estimated=True,
        blurb="Share of the group's disk-I/O budget the rebuild takes "
              "while active; the hosts feel it as lost headroom.",
    ),
    "rebuild_load_derate": Constant(
        value=0.5, unit="fraction at 100% host util",
        source="estimate", estimated=True,
        blurb="How much host load slows the rebuild: rate × (1 − derate × "
              "utilization). Busy arrays rebuild slower — the window grows "
              "exactly when the risk is highest.",
    ),
    # --- Degraded operation --------------------------------------------------
    "degraded_read_cost": Constant(
        value=2.0, unit="disk I/Os per host read",
        source="estimate — averaged reconstruct-on-read cost with one "
               "member missing (reads that hit the dead drive must read "
               "the whole stripe)",
        estimated=True,
        blurb="Average disk I/Os one host read costs while a parity group "
              "runs degraded.",
    ),
    "degraded_latency_ms": Constant(
        value=2.0, unit="ms",
        source="estimate", estimated=True,
        blurb="Added service latency while degraded (reconstruct math and "
              "extra queueing).",
    ),
    # --- Controllers ---------------------------------------------------------
    "ctrl_cap_kiops": Constant(
        value=320, unit="kIOPS/controller",
        source="Dell ME5 spec sheet claims up to 640K IOPS per array — "
               "halved per controller; verify against current document",
        estimated=True,
        blurb="Front-end ceiling of one controller. Spindles never reach "
              "it; a shelf of SSDs does — which is the teaching point.",
    ),
    "ctrl_overhead_ms": Constant(
        value=0.2, unit="ms",
        source="estimate", estimated=True,
        blurb="Controller pass-through latency (cache lookup, protocol).",
    ),
    "failover_latency_ms": Constant(
        value=0.5, unit="ms",
        source="estimate", estimated=True,
        blurb="Added latency while one controller carries both ports' "
              "traffic after a failover.",
    ),
    # --- Queueing ------------------------------------------------------------
    "util_knee_cap": Constant(
        value=0.95, unit="fraction",
        source="M/M/1-style queueing shape — modeling choice",
        estimated=True,
        blurb="Utilization cap in the latency law latency = service ÷ "
              "(1 − util): past the knee, queues, not drives, set latency.",
    ),
    "latency_cap_ms": Constant(
        value=500, unit="ms",
        source="modeling choice — hosts time out long before this",
        estimated=True,
        blurb="Ceiling on reported latency, where the model stops "
              "pretending precision.",
    ),
    # --- Risk gauge ------------------------------------------------------------
    "risk_per_hour": Constant(
        value=0.8, unit="index points/hour",
        source="estimate — illustrative exposure index, not a probability",
        estimated=True,
        blurb="Risk-index points per hour of remaining rebuild window, "
              "scaled by the RAID level's exposure factor.",
    ),
}

# Second-failure exposure factor by RAID level while one drive is out.
# RAID 6 still has parity in hand; the others are one failure from loss.
# Illustrative weighting, not a probability model.
RISK_FACTOR: dict[str, float] = {"5": 1.0, "1": 0.5, "10": 0.5, "6": 0.15}
RISK_FACTOR_SOURCE = "estimate — illustrative exposure weights"


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value
