"""The validation-rules engine: evaluated on every scenario change, each
rule yielding ok | warning | error with an explanation and a source. The
panel reads like a miniature capacity-planning review — warn, don't
block, then let the simulator show the consequence (the R760 twin's
§3.5 idiom).

Pure module: no FastAPI, no IO — rules are data in, findings out.
"""

from __future__ import annotations

from .constants import APPLIANCES, value as C
from .engine import local_compression
from .models import Scenario, Validation


def steady_state_physical_tb(scenario: Scenario) -> float:
    """Closed-form steady-state physical footprint, no events: image plus
    (retention − 1) days of stranded churn, plus metadata overhead."""
    ds = scenario.dataset
    r = scenario.schedule.retention_days
    cf = local_compression(ds.entropy_pct)
    c = ds.daily_change_pct / 100.0
    data = (ds.full_tb / cf) * (1.0 + (r - 1) * c)
    return data * (1.0 + C("metadata_overhead_fraction"))


def validate(scenario: Scenario) -> list[Validation]:
    ds = scenario.dataset
    appliance = APPLIANCES[scenario.appliance]
    out: list[Validation] = []
    cf = local_compression(ds.entropy_pct)

    # Rule 1 — one backup must physically fit (hard error).
    first_backup = (ds.full_tb / cf) * (1.0 + C("metadata_overhead_fraction"))
    if first_backup > appliance.usable_tb:
        out.append(Validation(
            rule_id="first-fit", level="error",
            message=(
                f"A single full backup stores ≈{first_backup:.0f} TB, which "
                f"does not fit the {appliance.name}'s {appliance.usable_tb:g} "
                "TB usable. No retention policy can save this — pick a "
                "bigger appliance or a smaller dataset."
            ),
            source="capacity arithmetic — raw → usable → effective "
                   "(BUILD_PLAN house identity)",
        ))
    else:
        out.append(Validation(
            rule_id="first-fit", level="ok",
            message=f"First full stores ≈{first_backup:.0f} TB of "
                    f"{appliance.usable_tb:g} TB usable.",
            source="capacity arithmetic",
        ))

    # Rule 2 — steady-state forecast vs usable capacity.
    steady = steady_state_physical_tb(scenario)
    used_pct = 100.0 * steady / appliance.usable_tb
    if used_pct > 100.0:
        out.append(Validation(
            rule_id="capacity-forecast", level="warning",
            message=(
                f"At {ds.daily_change_pct:g}%/day change and "
                f"{scenario.schedule.retention_days} generations, the store "
                f"settles near {steady:.0f} TB — {used_pct:.0f}% of usable. "
                "It will fill before retention does. The simulator will let "
                "you run it and watch the day it happens."
            ),
            source="steady-state ledger: (full/cf)·(1+(R−1)·c) — warn, "
                   "don't block; simulate the consequence",
        ))
    elif used_pct > C("capacity_warn_pct"):
        out.append(Validation(
            rule_id="capacity-forecast", level="warning",
            message=(
                f"Steady state forecast ≈{steady:.0f} TB "
                f"({used_pct:.0f}% of usable) — above the "
                f"{C('capacity_warn_pct'):g}% planning threshold. One "
                "surprise (a re-baseline, an encrypted source) fills it."
            ),
            source="steady-state ledger: (full/cf)·(1+(R−1)·c)",
        ))
    else:
        out.append(Validation(
            rule_id="capacity-forecast", level="ok",
            message=f"Steady state forecast ≈{steady:.0f} TB "
                    f"({used_pct:.0f}% of usable).",
            source="steady-state ledger: (full/cf)·(1+(R−1)·c)",
        ))

    # Rule 3 — host-side encryption anywhere in the plan.
    if any(e.action == "enable-host-encryption" for e in scenario.events):
        enc_steady = (
            scenario.schedule.retention_days * ds.full_tb
            * (1.0 + C("metadata_overhead_fraction"))
        )
        out.append(Validation(
            rule_id="encrypted-source", level="warning",
            message=(
                "This scenario turns on host-side encryption. Fresh session "
                "keys make every backup unique ciphertext: dedupe ratio "
                f"collapses toward 1:1 and the store heads for "
                f"≈{enc_steady:.0f} TB (retention × full size). Encrypt at "
                "the target or after dedupe, not before it."
            ),
            source="ciphertext does not deduplicate — information theory, "
                   "and Dell's own DD guidance",
        ))

    # Rule 4 — high-entropy source data.
    if ds.entropy_pct >= 80:
        out.append(Validation(
            rule_id="entropy", level="warning",
            message=(
                f"Dataset entropy {ds.entropy_pct:g}%: local compression "
                f"is ≈{cf:.2f}× (near none). Cross-generation dedupe still "
                "works if the data is *static* ciphertext — but expect the "
                "capacity model of a much bigger dataset."
            ),
            source="lz compression vs entropy — estimate curve in constants.py",
        ))

    # Rule 5 — fingerprint index vs RAM at steady state.
    steady_data = steady / (1.0 + C("metadata_overhead_fraction"))
    chunks = steady_data * 1e12 / (C("avg_chunk_kb") * 1024.0)
    index_gb = chunks * C("index_entry_bytes") * C("ram_resident_fraction") / 1e9
    if index_gb > appliance.index_ram_gb:
        out.append(Validation(
            rule_id="index-pressure", level="warning",
            message=(
                f"Steady state means ≈{chunks / 1e9:.1f} B unique chunks — "
                f"an index footprint of ≈{index_gb:.0f} GB against "
                f"{appliance.index_ram_gb:g} GB of index RAM. Ingest will "
                "degrade past the knee before the disks fill."
            ),
            source="index arithmetic: chunks × entry bytes × RAM-resident "
                   "fraction — all three flagged estimates",
        ))
    else:
        out.append(Validation(
            rule_id="index-pressure", level="ok",
            message=f"Index forecast ≈{index_gb:.0f} GB fits "
                    f"{appliance.index_ram_gb:g} GB of index RAM.",
            source="index arithmetic (estimates flagged in constants.py)",
        ))

    return out
