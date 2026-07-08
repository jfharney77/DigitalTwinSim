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

from .models import PipelineState

_SOURCES = ["src-storage", "src-compute", "src-network", "src-dataprot"]


def simulate() -> list[PipelineState]:
    """Telemetry's journey from a monitored system to an action, as pure data."""
    return [
        PipelineState(
            step=0,
            phase="idle",
            label="Connected & healthy",
            description=(
                "The monitored Dell systems are connected to CloudIQ and "
                "running normally. Health Scores sit at 100, nothing is "
                "anomalous, and the platform is quietly waiting for the next "
                "telemetry cycle. AIOps earns its keep in exactly this state — "
                "watching so no one has to."
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
            description=(
                "On their normal cycle, the monitored systems gather telemetry "
                "— health, capacity, performance counters, configuration, and "
                "logs. Storage and servers collect through their embedded "
                "SupportAssist client or the OpenManage Enterprise plugin; "
                "switches, Connectrix, and VMware collect through the on-site "
                "AIOps Collector, a small read-only virtual machine. Nothing "
                "leaves the data center yet."
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
            description=(
                "The Secure Connect Gateway batches the telemetry and opens a "
                "one-way, encrypted (TLS) outbound connection to Dell's cloud "
                "on port 443. The direction matters: the link is outbound and "
                "one-directional, so Dell's cloud can never reach back into "
                "your network — the property that makes a cloud-analyzed, "
                "on-prem fleet acceptable to security teams."
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
            description=(
                "In Dell's cloud the telemetry is parsed and normalized into a "
                "common model, then landed in a data lake next to history and "
                "the anonymized signals of Dell's whole installed base. "
                "Normalizing across products is what lets a single Health Score "
                "span storage, servers, and networking — and gives the models "
                "a fleet-wide baseline for what 'normal' looks like."
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
            description=(
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
            description=(
                "The models flag something: a latency anomaly on a storage "
                "pool, a capacity forecast that says 'full in ~10 weeks', and "
                "a cybersecurity finding — a configuration that has drifted "
                "from the security baseline. The affected system's Health Score "
                "drops, weighted by severity. This is the moment reactive "
                "monitoring would have waited for a user complaint; AIOps has "
                "it before the impact is felt."
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
            description=(
                "The findings appear in the CloudIQ / Dell AIOps app — in the "
                "browser and on mobile — as a lowered Health Score with a "
                "proactive health issue, a capacity forecast on the dashboard, "
                "a performance-impact view naming the contending workload, and "
                "a cybersecurity alert. Dashboards and reports update so an "
                "operator sees the fleet, and a manager sees the summary."
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
            description=(
                "The generative-AI AIOps Assistant puts the finding in plain "
                "language. Asked why the score dropped, it answers from both "
                "Dell's support knowledge (133,000+ resources) and this "
                "environment's actual state — Infrastructure Context Awareness "
                "— naming the pool, the likely cause, and the recommended "
                "remediation. A dashboard reading becomes a next step without "
                "opening a support case."
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
            description=(
                "The insight leaves CloudIQ. An email and mobile alert go out, "
                "a ServiceNow ticket is opened over the ITSM integration, and a "
                "webhook drives an automation — all via the REST API and "
                "webhooks that connect AIOps to the tools teams already run. As "
                "remediation begins (reclaim capacity, rebalance the noisy "
                "workload, re-apply the security setting), the Health Score "
                "recovers. The loop from telemetry to action is closed — the "
                "point of the whole platform."
            ),
            active_regions=["action"],
            progress_percent=100,
            health_score=88,
            data_points=48000,
            elapsed_seconds=128,
        ),
    ]
