"""Worked use cases: what teams actually use CloudIQ / Dell AIOps for.

Each use case is a narrative plus a set of capabilities whose category/option
ids must resolve against catalog.py (enforced in tests/test_catalog.py).
Written for a technically skilled reader new to AIOps. Unlike the hardware
twins, the "config" is not a bill of materials but the set of platform
capabilities the scenario leans on — the point being that CloudIQ is enabled,
not assembled.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="prevent-capacity-shortfall",
        title="Predict and prevent a capacity shortfall",
        summary=(
            "Capacity forecasting warns, months ahead, that a storage pool "
            "will fill — and reclaimable-capacity analysis buys back space "
            "before anyone has to place an emergency purchase order."
        ),
        narrative=[
            (
                "The situation: a storage team runs a fleet of Dell arrays for "
                "dozens of application teams who provision freely and clean up "
                "rarely. Capacity emergencies are a recurring fire drill — a "
                "pool hits 100%, writes fail, and someone spends a weekend "
                "migrating volumes while procurement scrambles for drives that "
                "have a lead time. The team is tired of being surprised by a "
                "number they should have seen coming."
            ),
            (
                "How CloudIQ changes it: because every array streams capacity "
                "telemetry to the cloud, the machine-learning forecast projects "
                "a 'full-in' date per pool with a confidence band, and rolls "
                "those up to a fleet view of which systems need attention this "
                "quarter. Weeks before a pool fills, it appears on the "
                "dashboard and drops the system's Health Score. Reclaimable-"
                "capacity analysis runs in parallel, flagging space already "
                "trapped in idle volumes, stale snapshots, and orphaned data — "
                "so the first response is often 'reclaim 40 TB you already "
                "own', not 'buy more'."
            ),
            (
                "The workflow: the forecast opens a ServiceNow ticket "
                "automatically through the ITSM integration, so the work lands "
                "in the operations queue with weeks of runway. A scheduled "
                "capacity report gives the manager the quarter's expansion "
                "plan on one page. The emergency becomes a planned, boring, "
                "budgeted event — which is the entire goal."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="monitored-systems",
                option_id="mon-storage",
                qty=1,
                rationale=(
                    "The forecast needs the storage arrays connected and "
                    "reporting capacity telemetry."
                ),
            ),
            UseCaseItem(
                category_id="connectivity",
                option_id="conn-scg",
                qty=1,
                rationale=(
                    "One Secure Connect Gateway carries the whole fleet's "
                    "telemetry out over a single outbound TLS connection."
                ),
            ),
            UseCaseItem(
                category_id="capacity",
                option_id="cap-forecast",
                qty=1,
                rationale=(
                    "The 'full-in' projection is the early warning the whole "
                    "scenario turns on."
                ),
            ),
            UseCaseItem(
                category_id="capacity",
                option_id="cap-reclaimable",
                qty=1,
                rationale=(
                    "Reclaiming trapped space is cheaper than buying, and often "
                    "resolves the forecast outright."
                ),
            ),
            UseCaseItem(
                category_id="health",
                option_id="health-score",
                qty=1,
                rationale=(
                    "The dropping Health Score is what makes an approaching "
                    "shortfall impossible to miss on the fleet view."
                ),
            ),
            UseCaseItem(
                category_id="integrations",
                option_id="int-itsm",
                qty=1,
                rationale=(
                    "Auto-opening a ServiceNow ticket puts the work in the "
                    "system of record with weeks of runway."
                ),
            ),
            UseCaseItem(
                category_id="access-licensing",
                option_id="access-reports",
                qty=1,
                rationale=(
                    "A scheduled capacity report turns continuous monitoring "
                    "into the quarter's expansion plan."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Warning lead time", value="Weeks to months ahead"),
            Stat(label="First response", value="Reclaim before buy"),
            Stat(label="Capacity emergency", value="Planned event, not a fire drill"),
            Stat(label="Extra cost", value="None (included with ProSupport)"),
        ],
    ),
    UseCase(
        id="find-noisy-neighbor",
        title="Find and fix a performance anomaly",
        summary=(
            "Performance anomaly detection spots latency drifting off its "
            "learned baseline, impact analysis names the noisy-neighbor "
            "workload causing it, and the AIOps Assistant recommends the fix — "
            "before the help desk fills up."
        ),
        narrative=[
            (
                "The situation: an application team reports that their database "
                "'feels slow' in the afternoons, but the array's dashboards "
                "look fine at a glance and no static threshold has tripped. "
                "The storage team is stuck doing what static monitoring forces: "
                "eyeballing graphs after the fact, trying to correlate a "
                "complaint with a spike, usually inconclusively."
            ),
            (
                "How CloudIQ changes it: the anomaly detector learned this "
                "system's normal rhythm across the day and week, so it flags "
                "the afternoon latency as a statistically real deviation rather "
                "than waiting for a fixed alarm that was set too high to ever "
                "fire. Performance impact analysis then does the hard part — "
                "separating the workload causing the impact (a batch analytics "
                "job that moved to afternoons and is now the 'noisy neighbor' "
                "consuming shared resources) from the databases suffering it. "
                "'The array is slow' becomes 'this job is the cause'."
            ),
            (
                "The workflow: an engineer asks the AIOps Assistant why the "
                "score dropped, and — with Infrastructure Context Awareness — "
                "it answers using this system's actual analytics, naming the "
                "contending workload and recommending a remediation (reschedule "
                "the batch job or cap its QoS). A mobile notification had "
                "already flagged it, so the fix happens before the afternoon's "
                "complaints turn into a help-desk queue."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="monitored-systems",
                option_id="mon-storage",
                qty=1,
                rationale=(
                    "Per-volume performance telemetry from the array is the "
                    "raw material for anomaly and impact analysis."
                ),
            ),
            UseCaseItem(
                category_id="connectivity",
                option_id="conn-supportassist",
                qty=1,
                rationale=(
                    "Embedded SupportAssist on the array streams the "
                    "performance counters with no separate collector."
                ),
            ),
            UseCaseItem(
                category_id="performance",
                option_id="perf-anomaly",
                qty=1,
                rationale=(
                    "Learned baselines catch the slow afternoon drift a static "
                    "threshold never would."
                ),
            ),
            UseCaseItem(
                category_id="performance",
                option_id="perf-impact",
                qty=1,
                rationale=(
                    "Naming the noisy neighbor is what makes the anomaly "
                    "actionable instead of merely visible."
                ),
            ),
            UseCaseItem(
                category_id="assistant",
                option_id="assist-context",
                qty=1,
                rationale=(
                    "Context-aware answers turn the finding into a specific "
                    "recommended fix for this system."
                ),
            ),
            UseCaseItem(
                category_id="integrations",
                option_id="int-notify",
                qty=1,
                rationale=(
                    "A mobile alert gets the on-call engineer on it before the "
                    "complaints arrive."
                ),
            ),
            UseCaseItem(
                category_id="access-licensing",
                option_id="access-apps",
                qty=1,
                rationale=(
                    "Engineers investigate from the browser and mobile app, "
                    "wherever they are."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Detection", value="Learned baseline, not fixed alarm"),
            Stat(label="Root cause", value="Noisy neighbor named"),
            Stat(label="Time to answer", value="Assistant, not a support case"),
            Stat(label="Resolution", value="Up to 10× faster (Dell claim)"),
        ],
    ),
    UseCase(
        id="cybersecurity-posture",
        title="Watch cybersecurity posture across the fleet",
        summary=(
            "Continuous evaluation against a security baseline catches a "
            "configuration drift and a ransomware risk indicator, the "
            "Assistant explains the exposure, and an ITSM ticket drives the "
            "fix — infrastructure security without a manual audit."
        ),
        narrative=[
            (
                "The situation: a security team is responsible for the "
                "hardening posture of a large Dell estate, but their only tool "
                "is a periodic manual audit — a spreadsheet exercise that is "
                "stale the day it is finished. Between audits, a well-meaning "
                "change (someone disables an encryption setting to "
                "troubleshoot, and forgets to re-enable it) can sit unnoticed "
                "for months."
            ),
            (
                "How CloudIQ changes it: the cybersecurity engine continuously "
                "evaluates each system against a security baseline — "
                "encryption, secure protocols, hardening settings — and raises "
                "an alert the moment a system drifts out of compliance, not at "
                "the next audit. Dell puts the scale of the win plainly: "
                "automating these checks across roughly a thousand systems is "
                "about a three-minute affair versus days by hand. Alongside the "
                "static checks, behavioral risk indicators consistent with "
                "ransomware are surfaced as high-priority findings, using the "
                "same telemetry the platform already collects — including from "
                "the data-protection systems that are a ransomware target."
            ),
            (
                "The workflow: the drift finding opens a ServiceNow incident "
                "automatically, and an analyst asks the AIOps Assistant to "
                "explain the exposure and the remediation in plain language "
                "before assigning it. The manual audit becomes a continuous, "
                "automated control — and the months-long window in which a "
                "misconfiguration goes unnoticed closes to minutes."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="monitored-systems",
                option_id="mon-storage",
                qty=1,
                rationale=(
                    "Storage configuration is the primary surface the security "
                    "baseline is evaluated against."
                ),
            ),
            UseCaseItem(
                category_id="monitored-systems",
                option_id="mon-dataprot",
                qty=1,
                rationale=(
                    "Data-protection systems are both a ransomware target and "
                    "a source of protection-status signal."
                ),
            ),
            UseCaseItem(
                category_id="connectivity",
                option_id="conn-scg",
                qty=1,
                rationale=(
                    "Fleet-wide security monitoring needs the whole estate "
                    "connected through the gateway."
                ),
            ),
            UseCaseItem(
                category_id="cybersecurity",
                option_id="cyber-misconfig",
                qty=1,
                rationale=(
                    "Continuous baseline evaluation is what replaces the "
                    "periodic manual audit."
                ),
            ),
            UseCaseItem(
                category_id="cybersecurity",
                option_id="cyber-ransomware",
                qty=1,
                rationale=(
                    "Behavioral risk indicators add a threat-detection line "
                    "inside the infrastructure layer."
                ),
            ),
            UseCaseItem(
                category_id="assistant",
                option_id="assist-genai",
                qty=1,
                rationale=(
                    "Plain-language explanation of the exposure and fix speeds "
                    "triage before assignment."
                ),
            ),
            UseCaseItem(
                category_id="integrations",
                option_id="int-itsm",
                qty=1,
                rationale=(
                    "Auto-created ServiceNow incidents route the fix into the "
                    "security operations workflow."
                ),
            ),
            UseCaseItem(
                category_id="access-licensing",
                option_id="access-included",
                qty=1,
                rationale=(
                    "The whole capability is already paid for under the "
                    "existing ProSupport agreement."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Audit model", value="Continuous, not periodic"),
            Stat(label="Drift window", value="Months → minutes"),
            Stat(label="1,000-system check", value="~3 minutes (Dell claim)"),
            Stat(label="Threat coverage", value="Misconfig + ransomware indicators"),
        ],
    ),
]
