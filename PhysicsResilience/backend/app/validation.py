"""Validation rules for the resilience simulator. Pure module."""

from __future__ import annotations

from .constants import value as C
from .models import Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    p = cfg.product
    out: list[Validation] = []

    # Fort Zero runs the access graph only: no backups, vault, restore, or
    # detection dials are in play (the UI hides them), so their rules
    # would judge settings the run never uses.
    if p == "fortzero":
        return out + _access_rules(cfg)

    # Rule 1 — the 3-2-1 shape (spec 05's checklist as a rule engine).
    if not cfg.vault:
        out.append(Validation(
            rule_id="three-two-one", level="warning",
            message=(
                "No vault: every copy is reachable from production, and "
                "an incident that encrypts production usually encrypts "
                "them too. The repository-only run demonstrates it."
            ),
            source="spec 05 — 3-2-1 as a rule-engine output",
        ))
    else:
        out.append(Validation(
            rule_id="three-two-one", level="ok",
            message="An isolated, locked copy exists behind the gap.",
            source="spec 05",
        ))

    # Rule 2 — the RTO surprise, stated before the run.
    decide_h = C("decision_hours")
    move_h = cfg.estate_tb * 1000.0 / (cfg.restore_gbps * 3600.0)
    rto = decide_h + move_h
    # Whole-estate restore is the worst case; the model has no partial
    # restore, so the message says which case the arithmetic covers.
    terms = (
        f"≈ {decide_h:.0f} h to decide and validate + ≈ {move_h:.0f} h to "
        f"move {cfg.estate_tb:g} TB at {cfg.restore_gbps:g} GB/s"
    )
    if rto > 48:
        out.append(Validation(
            rule_id="rto", level="warning",
            message=(
                f"Full-estate restore: {terms} ≈ {rto:.0f} hours ≈ "
                f"{rto / 24:.1f} days, counted from the restore order. "
                "Known before anything goes wrong. Restoring only the "
                "damaged volumes would be quicker; this model always "
                "restores everything."
            ),
            source="spec 05 — the RTO surprise, done as arithmetic",
        ))
    else:
        out.append(Validation(
            rule_id="rto", level="ok",
            message=f"Full-estate restore: {terms} ≈ {rto:.0f} h.",
            source="spec 05",
        ))

    # Rule 3 — RPO vs backup cadence.
    if cfg.backup_every_h > 24:
        out.append(Validation(
            rule_id="rpo", level="warning",
            message=(
                f"Backups every {cfg.backup_every_h} h: the best possible "
                f"RPO is {cfg.backup_every_h} hours of lost change — "
                "before detection delay is added."
            ),
            source="spec 05 — RPO from schedule",
        ))

    # Rule 4 — detection sensitivity extremes.
    if (cfg.detection or p == "cyberdetect") and cfg.sensitivity >= 9:
        alarms = C("false_alarms_per_month_per_sensitivity") * cfg.sensitivity
        out.append(Validation(
            rule_id="sensitivity", level="warning",
            message=(
                f"Sensitivity {cfg.sensitivity}: ≈ {alarms:.0f} false "
                f"alarms/month at {C('investigation_h_per_alarm'):g} h "
                "each. Earlier detection is being bought with someone's "
                "afternoons — the ROC trade has no free end."
            ),
            source="spec 05 — sensitivity/false-positive slider",
        ))

    # Rule 5 — in-house response with heavy noise.
    if p == "mdr" and cfg.response == "inhouse" \
            and cfg.noise_alerts_day > cfg.inhouse_capacity_day:
        out.append(Validation(
            rule_id="fatigue", level="warning",
            message=(
                f"{cfg.noise_alerts_day} alerts/day against a team that "
                f"can work {cfg.inhouse_capacity_day}: the backlog only "
                "grows, and the real alert waits in it. Alert fatigue "
                "is a queueing problem."
            ),
            source="spec 05 — the alert-fatigue scenario",
        ))

    return out


def _access_rules(cfg) -> list[Validation]:
    out: list[Validation] = []
    # Rule 6 — zero trust without review decays.
    if cfg.product == "fortzero" and cfg.architecture == "zerotrust" \
            and cfg.review_cadence_days == 0:
        out.append(Validation(
            rule_id="review", level="warning",
            message=(
                "Zero trust with no access review: unused grants "
                "accumulate (~0.5/user/month) and the blast radius "
                "quietly regrows. Least privilege is a maintenance "
                "schedule, not a project."
            ),
            source="spec 05 — least-privilege decay",
        ))

    return out
