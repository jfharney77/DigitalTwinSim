"""Validation rules for the resilience simulator. Pure module."""

from __future__ import annotations

from .constants import value as C
from .models import Scenario, Validation


def validate(scenario: Scenario) -> list[Validation]:
    cfg = scenario.config
    p = cfg.product
    out: list[Validation] = []

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
    rto = C("decision_hours") + cfg.estate_tb * 1000.0 / (cfg.restore_gbps * 3600.0)
    if rto > 48:
        out.append(Validation(
            rule_id="rto", level="warning",
            message=(
                f"Restoring {cfg.estate_tb:g} TB at {cfg.restore_gbps:g} "
                f"GB/s ≈ {rto:.0f} hours ≈ {rto / 24:.1f} days — before "
                "anything goes wrong, know that this is the floor."
            ),
            source="spec 05 — the RTO surprise, done as arithmetic",
        ))
    else:
        out.append(Validation(
            rule_id="rto", level="ok",
            message=f"Full-estate restore ≈ {rto:.0f} h at this throughput.",
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

    # Rule 6 — zero trust without review decays.
    if p == "fortzero" and cfg.architecture == "zerotrust" \
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
