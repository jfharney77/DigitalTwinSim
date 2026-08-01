"""Pure pipeline engine for CloudIQ / Dell AIOps.

``simulate()`` returns the deterministic trace of how a batch of telemetry
becomes an actionable insight — the SaaS analogue of the hardware twins'
power-on sequence. Same purity rule as every other engine in the repo: no
FastAPI, no IO, no timers — the frontend owns the playback clock, and each
``PipelineState`` is plain data the renderer consumes. ``cycle_cost`` marks the
heavy stage (the ML analyze pass) so the UI dwells on it.

The story: monitored Dell systems collect telemetry; the Secure Connect
Gateway ships it one-way to Dell's cloud; the cloud ingests and normalizes it;
the ML engine scores health, detects anomalies, and forecasts capacity;
something crosses a threshold and the Health Score drops; the insight surfaces
in the app; the AIOps Assistant explains it; and notifications/integrations
fire so a human (or an automation) can act. Numbers are illustrative — CloudIQ
collects on intervals and runs analytics periodically, not second-by-second;
favor a correct mental model over measured timing (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import PipelineState

_SOURCES = ["src-storage", "src-compute", "src-network", "src-dataprot"]


def simulate() -> list[PipelineState]:
    """Telemetry's journey from a monitored system to an action, as pure data."""
    return [
        PipelineState(
            step=0,
            phase="idle",
            label="Connected & healthy",
            description=L(
                novice=(
                    "The monitored equipment is connected and running normally. "
                    "Health scores sit at 100, nothing looks unusual, and the "
                    "platform is quietly waiting for the next batch of "
                    "measurements. This kind of software earns its keep in exactly "
                    "this state — watching, so that nobody has to."
                ),
                plain=(
                    "The monitored Dell systems are connected and running normally. "
                    "Health Scores sit at 100, nothing is anomalous, and the "
                    "platform waits for the next telemetry cycle. AIOps earns its "
                    "keep in exactly this state — watching so no one has to."
                ),
                standard=(
                    "The monitored Dell systems are connected to CloudIQ and "
                    "running normally. Health Scores sit at 100, nothing is "
                    "anomalous, and the platform is quietly waiting for the next "
                    "telemetry cycle. AIOps earns its keep in exactly this state — "
                    "watching so no one has to."
                ),
                technical=(
                    "Monitored estate connected and nominal. Health Scores at 100, "
                    "no anomalies, platform idle between telemetry cycles. The "
                    "steady state is where the value accrues — continuous "
                    "observation without an operator."
                ),
                expert=(
                    "Estate nominal, Health Scores 100, idle between cycles. Value "
                    "accrues in the steady state, unattended."
                ),
            ),
            active_regions=[],
            progress_percent=0,
            health_score=100,
            data_points=0,
            elapsed_seconds=0,
        ),
        PipelineState(
            step=1,
            phase="collect",
            label="Telemetry collected on the systems",
            description=L(
                novice=(
                    "On their normal schedule, the monitored machines gather "
                    "measurements about themselves — how healthy they are, how "
                    "full, how fast, how they are configured, and what their logs "
                    "say. Storage systems and servers collect this through software "
                    "built into them; switches and virtualization platforms are "
                    "collected by a small read-only virtual machine installed on "
                    "site. Nothing has left the building yet."
                ),
                plain=(
                    "On their normal cycle the monitored systems gather telemetry — "
                    "health, capacity, performance counters, configuration, and "
                    "logs. Storage and servers collect through their embedded "
                    "SupportAssist client or the OpenManage Enterprise plugin; "
                    "switches, Connectrix, and VMware collect through the on-site "
                    "AIOps Collector, a small read-only virtual machine. Nothing "
                    "has left the data centre yet."
                ),
                standard=(
                    "On their normal cycle, the monitored systems gather telemetry "
                    "— health, capacity, performance counters, configuration, and "
                    "logs. Storage and servers collect through their embedded "
                    "SupportAssist client or the OpenManage Enterprise plugin; "
                    "switches, Connectrix, and VMware collect through the on-site "
                    "AIOps Collector, a small read-only virtual machine. Nothing "
                    "leaves the data center yet."
                ),
                technical=(
                    "Scheduled collection: health, capacity, performance counters, "
                    "configuration, logs. Storage and servers via embedded "
                    "SupportAssist or the OpenManage Enterprise plugin; switches, "
                    "Connectrix, and VMware via the on-site AIOps Collector, a "
                    "read-only VM. Nothing egresses at this step."
                ),
                expert=(
                    "Scheduled collection — health, capacity, performance, config, "
                    "logs. Embedded agents for storage/servers, read-only Collector "
                    "VM for the rest. No egress yet."
                ),
            ),
            active_regions=_SOURCES,
            progress_percent=12,
            health_score=100,
            data_points=5200,
            elapsed_seconds=5,
        ),
        PipelineState(
            step=2,
            phase="transmit",
            label="Secure Connect Gateway sends it out",
            description=L(
                novice=(
                    "The gateway bundles the measurements and opens an encrypted "
                    "connection outward to Dell's cloud. The direction matters more "
                    "than anything else in this step: the connection is outbound "
                    "and one-way, so Dell's cloud can never reach back into your "
                    "network. That single property is what makes cloud-based "
                    "analysis of on-site equipment acceptable to security teams."
                ),
                plain=(
                    "The Secure Connect Gateway batches the telemetry and opens a "
                    "one-way, encrypted outbound connection to Dell's cloud on port "
                    "443. The direction matters: the link is outbound and "
                    "one-directional, so Dell's cloud can never reach back into "
                    "your network — the property that makes a cloud-analyzed, "
                    "on-premises fleet acceptable to security teams."
                ),
                standard=(
                    "The Secure Connect Gateway batches the telemetry and opens a "
                    "one-way, encrypted (TLS) outbound connection to Dell's cloud "
                    "on port 443. The direction matters: the link is outbound and "
                    "one-directional, so Dell's cloud can never reach back into "
                    "your network — the property that makes a cloud-analyzed, "
                    "on-prem fleet acceptable to security teams."
                ),
                technical=(
                    "Secure Connect Gateway batches and egresses over TLS/443, "
                    "outbound-initiated and unidirectional. The directionality is "
                    "the security property: no inbound path exists from the cloud "
                    "into the estate, which is what makes cloud analytics over "
                    "on-premises infrastructure approvable."
                ),
                expert=(
                    "SCG batches, egresses TLS/443, outbound-only and "
                    "unidirectional. No inbound path — the property that makes "
                    "cloud analytics approvable."
                ),
            ),
            active_regions=["gateway"],
            progress_percent=24,
            health_score=100,
            data_points=5200,
            elapsed_seconds=8,
        ),
        PipelineState(
            step=3,
            phase="ingest",
            label="Cloud ingests & normalizes",
            description=L(
                novice=(
                    "In Dell's cloud the measurements are parsed and converted into "
                    "a common format, then stored alongside history and the "
                    "anonymized signals of Dell's entire installed base. Converting "
                    "everything to one format is what allows a single health score "
                    "to cover storage, servers, and networking together — and it "
                    "gives the models a picture of what 'normal' looks like across "
                    "the whole fleet, not just yours."
                ),
                plain=(
                    "In Dell's cloud the telemetry is parsed and normalized into a "
                    "common model, then landed in a data lake next to history and "
                    "the anonymized signals of Dell's whole installed base. "
                    "Normalizing across products is what lets a single Health Score "
                    "span storage, servers, and networking — and gives the models a "
                    "fleet-wide baseline for what normal looks like."
                ),
                standard=(
                    "In Dell's cloud the telemetry is parsed and normalized into a "
                    "common model, then landed in a data lake next to history and "
                    "the anonymized signals of Dell's whole installed base. "
                    "Normalizing across products is what lets a single Health Score "
                    "span storage, servers, and networking — and gives the models "
                    "a fleet-wide baseline for what 'normal' looks like."
                ),
                technical=(
                    "Ingest: parsed and normalized to a common model, landed in a "
                    "data lake alongside historical and anonymized installed-base "
                    "signals. Cross-product normalization is what permits a single "
                    "Health Score to span storage, servers, and networking, and "
                    "supplies the fleet-wide baseline the models score against."
                ),
                expert=(
                    "Parsed, normalized to a common model, landed beside history "
                    "and anonymized installed-base signal. Normalization enables a "
                    "cross-product Health Score and a fleet baseline."
                ),
            ),
            active_regions=["ingest"],
            progress_percent=38,
            health_score=100,
            data_points=48000,
            elapsed_seconds=20,
        ),
        PipelineState(
            step=4,
            phase="analyze",
            label="ML engine scores, detects, forecasts",
            description=L(
                novice=(
                    "The machine-learning core runs — the heaviest stage. It "
                    "recalculates each system's health score, compares live "
                    "performance against what it has learned is normal to spot "
                    "anomalies, checks whether one workload is stealing another's "
                    "performance, and projects when storage will fill up and how "
                    "much reclaimable space is trapped. Because it runs against the "
                    "whole fleet's history rather than just yours, it can recognise "
                    "patterns your own equipment has never produced before."
                ),
                plain=(
                    "The machine-learning core runs — the heaviest stage. It "
                    "recomputes each system's Health Score, compares live "
                    "performance against learned baselines to spot anomalies, "
                    "checks for workload contention (a noisy neighbour stealing "
                    "another workload's performance), and projects capacity: when a "
                    "pool will fill and how much reclaimable space is trapped. "
                    "Running against the fleet lets it recognise patterns your "
                    "estate has never produced."
                ),
                standard=(
                    "The machine-learning core runs — the heaviest stage. It "
                    "recomputes each system's Health Score, compares live "
                    "performance against learned baselines to spot anomalies, "
                    "checks for workload contention (a 'noisy neighbor' stealing "
                    "another workload's performance), and projects capacity: when "
                    "a pool will fill and how much reclaimable space is trapped. "
                    "Because it runs against the fleet-wide data lake, behavior is "
                    "judged against how similar systems normally act, not a static "
                    "rule."
                ),
                technical=(
                    "Max-dwell stage. Health Score recomputation, anomaly detection "
                    "against learned baselines, contention analysis for "
                    "noisy-neighbour identification, and capacity forecasting "
                    "including reclaimable space. Fleet-scale training means the "
                    "model recognises signatures absent from any single estate's "
                    "history."
                ),
                expert=(
                    "Max dwell: Health Score recomputation, baseline anomaly "
                    "detection, contention analysis, capacity forecast. "
                    "Fleet-trained, so it recognises signatures absent locally."
                ),
            ),
            active_regions=["analytics", "ingest"],
            progress_percent=60,
            health_score=100,
            data_points=48000,
            elapsed_seconds=80,
            cycle_cost=4,
        ),
        PipelineState(
            step=5,
            phase="detect",
            label="A risk crosses threshold",
            description=L(
                novice=(
                    "The models flag something: a latency anomaly on a storage "
                    "pool, a capacity forecast saying it will be full in about ten "
                    "weeks, and a security finding where a setting has drifted away "
                    "from the approved baseline. The affected system's health score "
                    "drops, weighted by how serious each finding is. This is the "
                    "moment traditional monitoring would still be waiting for "
                    "someone to complain."
                ),
                plain=(
                    "The models flag something: a latency anomaly on a storage "
                    "pool, a capacity forecast that says full in about ten weeks, "
                    "and a cybersecurity finding where a configuration has drifted "
                    "from the security baseline. The affected system's Health Score "
                    "drops, weighted by severity. This is the moment reactive "
                    "monitoring would have waited for a user complaint; the "
                    "analysis has it before the impact."
                ),
                standard=(
                    "The models flag something: a latency anomaly on a storage "
                    "pool, a capacity forecast that says 'full in ~10 weeks', and "
                    "a cybersecurity finding — a configuration that has drifted "
                    "from the security baseline. The affected system's Health Score "
                    "drops, weighted by severity. This is the moment reactive "
                    "monitoring would have waited for a user complaint; AIOps has "
                    "it before the impact is felt."
                ),
                technical=(
                    "Detections cross threshold: a latency anomaly on a pool, a "
                    "~10-week capacity forecast, and a configuration drift from the "
                    "security baseline. Health Score decrements weighted by "
                    "severity. Reactive monitoring surfaces this at the complaint; "
                    "the forecast surfaces it ahead of impact."
                ),
                expert=(
                    "Threshold crossings: latency anomaly, ~10-week capacity "
                    "forecast, security baseline drift. Health Score decrements by "
                    "severity — ahead of impact rather than at complaint."
                ),
            ),
            active_regions=["analytics", "security"],
            progress_percent=74,
            health_score=71,
            data_points=48000,
            elapsed_seconds=95,
            cycle_cost=2,
        ),
        PipelineState(
            step=6,
            phase="surface",
            label="Insight surfaces in the app",
            description=L(
                novice=(
                    "The findings appear in the application, in a browser and on a "
                    "phone: a lowered health score with a description of the "
                    "problem, a capacity forecast on the dashboard, a view naming "
                    "the workload that is causing the contention, and a security "
                    "alert. Dashboards and reports update so that an operator sees "
                    "the fleet and a manager sees the summary."
                ),
                plain=(
                    "The findings appear in the CloudIQ app — in the browser and on "
                    "mobile — as a lowered Health Score with a proactive health "
                    "issue, a capacity forecast on the dashboard, a "
                    "performance-impact view naming the contending workload, and a "
                    "cybersecurity alert. Dashboards and reports update so an "
                    "operator sees the fleet and a manager sees the summary."
                ),
                standard=(
                    "The findings appear in the CloudIQ / Dell AIOps app — in the "
                    "browser and on mobile — as a lowered Health Score with a "
                    "proactive health issue, a capacity forecast on the dashboard, "
                    "a performance-impact view naming the contending workload, and "
                    "a cybersecurity alert. Dashboards and reports update so an "
                    "operator sees the fleet, and a manager sees the summary."
                ),
                technical=(
                    "Findings surface in the application across browser and mobile: "
                    "decremented Health Score with an associated proactive issue, "
                    "capacity forecast, performance-impact view identifying the "
                    "contending workload, and a cybersecurity alert. Dashboards and "
                    "reports update for both operator and management views."
                ),
                expert=(
                    "Surfaced: decremented Health Score with proactive issue, "
                    "capacity forecast, contention attribution, security alert. "
                    "Operator and management views update."
                ),
            ),
            active_regions=["insight"],
            progress_percent=85,
            health_score=71,
            data_points=48000,
            elapsed_seconds=105,
        ),
        PipelineState(
            step=7,
            phase="assist",
            label="AIOps Assistant explains & recommends",
            description=L(
                novice=(
                    "A generative-AI assistant puts the finding into plain "
                    "language. Asked why the score dropped, it answers using both "
                    "Dell's support knowledge and this environment's actual state — "
                    "naming the specific storage pool, the likely cause, and what "
                    "to do about it. A number on a dashboard becomes a next step, "
                    "without anyone opening a support case."
                ),
                plain=(
                    "The AIOps Assistant, which is generative AI, restates the "
                    "finding in ordinary language. Ask it why the score fell and it "
                    "draws on two sources at once — Dell's support knowledge base "
                    "of more than 133,000 resources, and the live state of this "
                    "specific environment, which Dell calls Infrastructure Context "
                    "Awareness. The answer names the affected pool, the likely "
                    "cause, and what to do. A number on a dashboard turns into a "
                    "next step, with no support case opened."
                ),
                standard=(
                    "The generative-AI AIOps Assistant puts the finding in plain "
                    "language. Asked why the score dropped, it answers from both "
                    "Dell's support knowledge (133,000+ resources) and this "
                    "environment's actual state — Infrastructure Context Awareness "
                    "— naming the pool, the likely cause, and the recommended "
                    "remediation. A dashboard reading becomes a next step without "
                    "opening a support case."
                ),
                technical=(
                    "The AIOps Assistant renders the finding conversationally, "
                    "grounded in both Dell's support corpus (133,000+ resources) "
                    "and the live environment state via Infrastructure Context "
                    "Awareness — naming the affected pool, probable cause, and "
                    "remediation. Converts a dashboard reading into an action "
                    "without a support case."
                ),
                expert=(
                    "Assistant grounds the finding in the support corpus plus live "
                    "environment state (Infrastructure Context Awareness): pool, "
                    "probable cause, remediation. Dashboard reading → action, no "
                    "case opened."
                ),
            ),
            active_regions=["assistant", "insight"],
            progress_percent=93,
            health_score=71,
            data_points=48000,
            elapsed_seconds=118,
        ),
        PipelineState(
            step=8,
            phase="notify",
            label="Notify, integrate, remediate",
            description=L(
                novice=(
                    "The insight leaves the platform. An email and a phone alert go "
                    "out, a ticket is opened automatically in the organization's "
                    "service-management system, and an automated process is "
                    "triggered — all through the interfaces that connect this "
                    "platform to the tools teams already use. As the fixes take "
                    "effect, the health score recovers. Note that it does not go "
                    "all the way back to where it started, and that is honest: the "
                    "estate has learned something about itself."
                ),
                plain=(
                    "The insight leaves CloudIQ. An email and mobile alert go out, "
                    "a ServiceNow ticket is opened over the ITSM integration, and a "
                    "webhook drives an automation — all via the REST API and "
                    "webhooks that connect the platform to the tools teams already "
                    "run. As remediation begins, the Health Score recovers. Note it "
                    "recovers above the low-water mark but not to 100, which is "
                    "deliberate honesty."
                ),
                standard=(
                    "The insight leaves CloudIQ. An email and mobile alert go out, "
                    "a ServiceNow ticket is opened over the ITSM integration, and a "
                    "webhook drives an automation — all via the REST API and "
                    "webhooks that connect AIOps to the tools teams already run. As "
                    "remediation begins (reclaim capacity, rebalance the noisy "
                    "workload, re-apply the security setting), the Health Score "
                    "recovers. The loop from telemetry to action is closed — the "
                    "point of the whole platform."
                ),
                technical=(
                    "Egress of the insight: email and mobile notification, "
                    "ServiceNow ticket via the ITSM integration, and webhook-driven "
                    "automation over the REST API. Health Score recovers as "
                    "remediation proceeds — above the low-water mark, below 100, "
                    "which the engine asserts. Telemetry flow remains one-way "
                    "throughout, also asserted."
                ),
                expert=(
                    "Insight egress: notification, ITSM ticket, webhook automation "
                    "over REST. Score recovers above low-water, below 100 — "
                    "asserted, as is one-way flow."
                ),
            ),
            active_regions=["action"],
            progress_percent=100,
            health_score=88,
            data_points=48000,
            elapsed_seconds=128,
        ),
    ]
