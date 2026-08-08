"""Every model constant with units and a source — resilience edition."""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Detection (Cyber Detect's ROC knob) -------------------------------
    "detect_threshold_base_h": Constant(
        value=60, unit="h at sensitivity 1",
        source="estimate — days-scale detection at the laxest setting",
        estimated=True,
        blurb="Detection latency at minimum sensitivity; divides by sensitivity.",
    ),
    "false_alarms_per_month_per_sensitivity": Constant(
        value=1.2, unit="alarms/month per sensitivity point",
        source="estimate — the ROC trade, taught by knob", estimated=True,
        blurb="False alarms per month scale with sensitivity.",
    ),
    "investigation_h_per_alarm": Constant(
        value=3, unit="h", source="estimate — triage + evidence + all-clear",
        estimated=True,
        blurb="Admin-hours each false alarm costs.",
    ),
    "score_visible_threshold": Constant(
        value=15, unit="score", source="estimate", estimated=True,
        blurb="Corruption score at which a detector at sensitivity 10 fires.",
    ),
    # --- Response (MDR) -----------------------------------------------------
    "mdr_triage_h": Constant(
        value=0.25, unit="h", source="estimate — 24/7 SOC, minutes to triage",
        estimated=True,
        blurb="MDR mean time from alert to containment action.",
    ),
    "inhouse_triage_h": Constant(
        value=2.0, unit="h", source="estimate — during business hours",
        estimated=True,
        blurb="In-house triage time once someone is actually at a desk.",
    ),
    # --- Recovery -----------------------------------------------------------
    "decision_hours": Constant(
        value=6, unit="h",
        source="estimate — spec 05: decision + validation time in RTO",
        estimated=True,
        blurb="Hours spent deciding and validating before bytes move.",
    ),
    "failed_restore_penalty_h": Constant(
        value=8, unit="h",
        source="estimate — discover corruption, pick an older point, restart",
        estimated=True,
        blurb="Hours lost when a restore turns out to be corrupt.",
    ),
    # --- Fort Zero ----------------------------------------------------------
    "perimeter_reach_fraction": Constant(
        value=0.9, unit="fraction of assets",
        source="estimate — inside the wall, broadly connected", estimated=True,
        blurb="Share of assets reachable from one compromised identity, perimeter model.",
    ),
    "spread_hops_per_h": Constant(
        value=8, unit="assets/h",
        source="estimate — abstract reachability flood rate", estimated=True,
        blurb="How fast the reachable set fills in after a compromise (abstract).",
    ),
    "zt_policy_checks": Constant(
        value=9, unit="checks/session",
        source="estimate — identity + device health + policy per edge",
        estimated=True,
        blurb="Policy evaluations per session under zero trust (the friction cost).",
    ),
    "perimeter_policy_checks": Constant(
        value=1, unit="checks/session", source="estimate — the login, once",
        estimated=True,
        blurb="Policy evaluations per session inside a perimeter.",
    ),
    "grant_decay_per_user_month": Constant(
        value=0.5, unit="stale grants/user/month",
        source="estimate — access entropy without review", estimated=True,
        blurb="Unused-but-live grants accumulated monthly without access review.",
    ),
}


def value(name: str) -> float:
    return CONSTANTS[name].value
