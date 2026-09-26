"""The validation-rules engine: evaluated on every config change, each
rule yielding ok | warning | error with a human-readable explanation and
a source citation. The panel is meant to read like a miniature of a
storage sizing guide — that is the pedagogical intent.

Pure module: no FastAPI, no IO — rules are data in, findings out.
"""

from __future__ import annotations

from .constants import value as C
from .engine import drive_iops, rebuild_mbps
from .models import (
    ArrayConfig,
    MODEL_MAX_DRIVES,
    Scenario,
    Validation,
    WRITE_PENALTY,
)

RAID_MIN = {"1": 2, "5": 3, "6": 4, "10": 4}


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    wl = scenario.workload
    out: list[Validation] = []
    group_n = cfg.drive_count - cfg.spares

    # Rule 1 — the enclosure has a fixed number of slots.
    max_drives = MODEL_MAX_DRIVES[cfg.model]
    if cfg.drive_count > max_drives:
        out.append(Validation(
            rule_id="slots", level="error",
            message=(
                f"The {cfg.model} base enclosure holds {max_drives} drives; "
                f"this build asks for {cfg.drive_count}. (Real arrays add "
                "expansion shelves — this sim models one enclosure.)"
            ),
            source="Dell PowerVault ME5000 spec sheet — ME5012 12 × 3.5-inch, "
                   "ME5024 24 × 2.5-inch bays",
        ))
    else:
        out.append(Validation(
            rule_id="slots", level="ok",
            message=f"{cfg.drive_count} drives fit the {cfg.model}'s "
                    f"{max_drives} slots.",
            source="Dell PowerVault ME5000 spec sheet — ME5012 12 × 3.5-inch, "
                   "ME5024 24 × 2.5-inch bays",
        ))

    # Rule 2 — RAID minimum member counts (and evenness for RAID 10).
    if group_n < RAID_MIN[cfg.raid_level]:
        out.append(Validation(
            rule_id="raid-members", level="error",
            message=(
                f"RAID {cfg.raid_level} needs at least "
                f"{RAID_MIN[cfg.raid_level]} members; after "
                f"{cfg.spares} spare(s) this group has {group_n}."
            ),
            source="RAID arithmetic — member minimums",
        ))
    elif cfg.raid_level in ("1", "10") and group_n % 2 != 0:
        out.append(Validation(
            rule_id="raid-members", level="error",
            message=(
                f"Mirrored RAID {cfg.raid_level} needs an even member "
                f"count; this group has {group_n}. Add a drive or make "
                "one a spare."
            ),
            source="RAID arithmetic — mirrors come in pairs",
        ))
    elif cfg.raid_level == "1" and group_n > 2:
        out.append(Validation(
            rule_id="raid-members", level="error",
            message=(
                f"RAID 1 is a single mirrored pair; {group_n} members "
                "wants RAID 10."
            ),
            source="RAID arithmetic",
        ))
    else:
        out.append(Validation(
            rule_id="raid-members", level="ok",
            message=f"RAID {cfg.raid_level} group of {group_n} is legal.",
            source="RAID arithmetic — member minimums",
        ))

    # Rule 2b — the drive catalog. The sim lets any size ride any drive
    # type (the rebuild arithmetic is the lesson), but says so when the
    # combination is not one Dell sells.
    catalog_note = None
    if cfg.drive_type == "hdd-10k" and cfg.drive_tb > 2:
        catalog_note = (
            f"Dell's ME5 10k SAS drives top out at 2.4 TB; a {cfg.drive_tb} "
            "TB 10k spindle is illustrative, not a part you can order."
        )
    elif cfg.drive_type == "hdd-7.2k" and cfg.model == "ME5024":
        catalog_note = (
            "Dell lists 7.2k NL-SAS for the ME5 as 3.5-inch drives (4–22 "
            "TB); the ME5024's 24 bays are 2.5-inch, so this build is "
            "illustrative. The ME5012 is the 3.5-inch enclosure."
        )
    elif cfg.drive_type == "ssd" and cfg.drive_tb > 8:
        catalog_note = (
            f"Dell's ME5 SSDs top out at 7.68 TB; a {cfg.drive_tb} TB SSD "
            "is illustrative, not a part you can order."
        )
    if catalog_note:
        out.append(Validation(
            rule_id="drive-catalog", level="warning",
            message=catalog_note,
            source="Dell PowerVault ME5000 spec sheet — storage media list",
        ))

    # Rule 3 — big drives on single-parity RAID: the rebuild-window rule.
    if cfg.raid_level == "5" and cfg.drive_tb >= 8:
        hours = cfg.drive_tb * 1000.0 / (rebuild_mbps(cfg.drive_type) * 3.6)
        out.append(Validation(
            rule_id="rebuild-window", level="warning",
            message=(
                f"RAID 5 with {cfg.drive_tb} TB drives: a rebuild takes "
                f"roughly {hours:.0f} hours at best, and the whole window "
                "is one failure from data loss. This is why RAID 6 "
                "replaced RAID 5 as drives grew — run the rebuild "
                "scenario and watch the risk gauge."
            ),
            source="estimate — rebuild rate constant; the window "
                   "arithmetic is exact given it",
        ))

    # Rule 4 — no hot spare on a parity group.
    if cfg.spares == 0 and cfg.raid_level in ("5", "6"):
        out.append(Validation(
            rule_id="spare", level="warning",
            message=(
                "No hot spare: after a failure the group stays degraded "
                "until a human swaps a drive — the rebuild window becomes "
                "the time to notice plus the drive to arrive plus the "
                "rebuild itself."
            ),
            source="sizing practice — spares buy back the human hours",
        ))

    # Rule 5 — single controller.
    if cfg.controllers == 1:
        out.append(Validation(
            rule_id="controller", level="warning",
            message=(
                "Single controller: no failover partner, and write cache "
                "runs write-through (nowhere to mirror it). One fault "
                "takes the array offline — the sim will demonstrate."
            ),
            source="Dell ME5000 spec sheet — 2U models support single or dual "
                   "controllers; dual is what buys failover",
        ))

    # Rule 6 — offered load vs what the build can carry (warn, don't
    # block; the simulator shows the saturation).
    per_drive = drive_iops(cfg.drive_type)
    wp = WRITE_PENALTY[cfg.raid_level]
    budget = max(group_n, 0) * per_drive
    rf = wl.read_pct / 100.0
    cost_per_iop = rf + (1.0 - rf) * wp
    capable_kiops = min(
        budget / cost_per_iop / 1000.0 if cost_per_iop else 0.0,
        cfg.controllers * C("ctrl_cap_kiops"),
    )
    if wl.offered_kiops > capable_kiops * 1.02:
        out.append(Validation(
            rule_id="headroom", level="warning",
            message=(
                f"Offered {wl.offered_kiops:g} kIOPS exceeds the ~"
                f"{capable_kiops:.1f} kIOPS this build can serve at a "
                f"{wl.read_pct}/{100 - wl.read_pct} mix (write penalty "
                f"×{wp}). The array will saturate and latency will climb "
                "the queue curve — watch it happen."
            ),
            source="drive-IOPS budget ÷ RAID write penalty — arithmetic "
                   "over estimated drive constants",
        ))
    else:
        out.append(Validation(
            rule_id="headroom", level="ok",
            message=(
                f"Offered load fits: ~{capable_kiops:.1f} kIOPS available "
                f"at this mix, {wl.offered_kiops:g} asked."
            ),
            source="drive-IOPS budget ÷ RAID write penalty",
        ))

    return out
