"""The capabilities-and-options menu for CloudIQ / Dell AIOps.

Unlike the hardware twins, there is nothing to build to order — CloudIQ is a
SaaS. So the "catalog" is the platform's **capabilities**, grouped the way
Dell presents them, with ``region_ids`` tying each capability to the part of
the architecture diagram it runs in. ``details`` are written for a technically
skilled reader new to AIOps; observability jargon (telemetry, Secure Connect
Gateway, Health Score, anomaly detection, RPO, ITSM, ...) is spelled out on
first use. Figures follow Dell's public AIOps material; treat them as
product-literature claims, not benchmarks.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="monitored-systems",
        name="Monitored systems",
        blurb=(
            "What CloudIQ observes. Connect a Dell system and its telemetry — "
            "health, capacity, performance, configuration — starts flowing "
            "into one fleet-wide view, whatever kind of system it is."
        ),
        limits="Read-only observation; CloudIQ never controls the systems",
        region_ids=["src-storage", "src-compute", "src-network", "src-dataprot"],
        options=[
            CatalogOption(
                id="mon-storage",
                name="Storage",
                summary="PowerStore, PowerMax, PowerScale, PowerFlex, PowerVault, Unity XT.",
                details=(
                    "The deepest-instrumented family: block, file, and object "
                    "arrays report health, capacity, and per-volume/per-pool "
                    "performance. Storage is where the capacity-forecasting and "
                    "performance-anomaly analytics have the most to work with, "
                    "and where CloudIQ started before it grew into a "
                    "whole-infrastructure tool."
                ),
            ),
            CatalogOption(
                id="mon-compute",
                name="Servers & HCI",
                summary="PowerEdge servers and VxRail hyperconverged clusters.",
                details=(
                    "PowerEdge telemetry is collected through the OpenManage "
                    "Enterprise (OME) CloudIQ plugin — OME already inventories "
                    "and manages the servers, and the plugin forwards the "
                    "signals CloudIQ needs. VxRail reports cluster health "
                    "directly. Bringing servers into the same pane is what "
                    "turns storage monitoring into infrastructure "
                    "observability."
                ),
            ),
            CatalogOption(
                id="mon-network",
                name="Networking",
                summary="PowerSwitch switches and Connectrix SAN directors.",
                details=(
                    "Collected through the on-site AIOps Collector — a small "
                    "read-only virtual machine that reaches switches over a "
                    "non-privileged REST API and Connectrix/VMware through "
                    "their APIs. Network health in the same tool means a path "
                    "problem and a storage problem can be seen together instead "
                    "of in two consoles."
                ),
            ),
            CatalogOption(
                id="mon-dataprot",
                name="Data protection",
                summary="PowerProtect DD (Data Domain) and PowerProtect Data Manager.",
                details=(
                    "Backup appliances and the data-protection control plane "
                    "report capacity, health, and protection status. This "
                    "feeds both operations (is everything protected?) and the "
                    "cybersecurity view (an unprotected or newly misconfigured "
                    "system is a risk in its own right)."
                ),
            ),
            CatalogOption(
                id="mon-multicloud",
                name="Multicloud footprints",
                summary="APEX and Dell software running on AWS, Azure, and OpenShift.",
                details=(
                    "CloudIQ's reach extends to Dell storage-as-a-service and "
                    "software deployed in public clouds and on OpenShift, so a "
                    "hybrid estate is one fleet rather than an on-prem view "
                    "plus blind spots in the cloud."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="connectivity",
        name="Connectivity",
        blurb=(
            "How telemetry leaves your data center. Every path is outbound and "
            "one-way to Dell's cloud — nothing installs on a desktop, and the "
            "cloud cannot reach back into your network."
        ),
        limits="Outbound TLS only; one-directional by design",
        region_ids=["gateway"],
        options=[
            CatalogOption(
                id="conn-scg",
                name="Secure Connect Gateway (SCG)",
                summary="Dell's support-connectivity gateway — the usual front door.",
                details=(
                    "A hardened appliance or virtual gateway that batches "
                    "telemetry from many systems and opens a single encrypted "
                    "(TLS) outbound connection to Dell on port 443. The "
                    "successor to Secure Remote Services (SRS); it also carries "
                    "SupportAssist automated support cases. One gateway serves "
                    "a whole site."
                ),
            ),
            CatalogOption(
                id="conn-collector",
                name="AIOps Collector (OVA)",
                summary="Small read-only VM for VMware, Connectrix, and PowerSwitch.",
                details=(
                    "A lightweight virtual machine deployed on site that polls "
                    "systems lacking their own embedded connectivity — "
                    "switches, SAN directors, vCenter — using non-privileged, "
                    "read-only credentials. It reaches the Secure Connect "
                    "Gateway on port 9443, or connects directly to Dell "
                    "Services."
                ),
            ),
            CatalogOption(
                id="conn-supportassist",
                name="SupportAssist / embedded connectivity",
                summary="The client built into storage and servers themselves.",
                details=(
                    "Many Dell systems collect and send their own telemetry "
                    "through embedded SupportAssist, no separate collector "
                    "needed. This is the simplest onboarding path: enable "
                    "connectivity on the array, point it at the gateway or Dell "
                    "directly, and it appears in CloudIQ."
                ),
            ),
            CatalogOption(
                id="conn-direct",
                name="Direct connect",
                summary="Connect straight to Dell Services without a gateway.",
                details=(
                    "For smaller footprints, the collector or embedded client "
                    "can connect directly to Dell Services over the internet "
                    "instead of through a Secure Connect Gateway — fewer moving "
                    "parts when there is no fleet-scale gateway to justify."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="health",
        name="Health monitoring",
        blurb=(
            "The core proactive-monitoring capability: a single score per "
            "system and the specific issues behind it, so you fix problems "
            "before they become outages."
        ),
        limits="Continuously recalculated from incoming telemetry",
        region_ids=["analytics", "insight"],
        options=[
            CatalogOption(
                id="health-score",
                name="Health Score",
                summary="A 0–100 roll-up of each system's health, worst-issue weighted.",
                details=(
                    "CloudIQ distills configuration, capacity, performance, "
                    "component, and data-protection issues into one 0–100 "
                    "score per system, driven by the most severe open issue. "
                    "It is deliberately blunt — a number an operator can scan "
                    "across a fleet — with the contributing issues one click "
                    "underneath."
                ),
            ),
            CatalogOption(
                id="health-proactive",
                name="Proactive health issues",
                summary="Named, prioritized issues with recommended remediation.",
                details=(
                    "Behind the score, each issue is spelled out — what it is, "
                    "which system and component, how severe, and what to do — "
                    "so 'the score dropped' becomes 'this pool is 95% full, "
                    "reclaim or expand it'. Issues are prioritized so the fleet "
                    "sorts itself worst-first."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="capacity",
        name="Capacity analytics",
        blurb=(
            "Predictive capacity planning: not just how full things are now, "
            "but when they will fill and what space is being wasted — the "
            "forecasting AIOps is built for."
        ),
        limits="Forecasts improve as history accumulates",
        region_ids=["analytics", "insight"],
        options=[
            CatalogOption(
                id="cap-forecast",
                name="Capacity forecasting",
                summary="Projects when a pool or system will run out — weeks or months ahead.",
                details=(
                    "Machine learning on the capacity trend projects a "
                    "'full-in' date and the confidence around it, so expansion "
                    "is a planned purchase months ahead rather than a "
                    "3 a.m. emergency. Forecasts roll up to the fleet: which "
                    "systems need attention this quarter."
                ),
            ),
            CatalogOption(
                id="cap-reclaimable",
                name="Reclaimable capacity",
                summary="Finds space trapped in idle volumes, stale snapshots, and orphans.",
                details=(
                    "The flip side of forecasting: before buying more, CloudIQ "
                    "identifies capacity you already have but aren't using — "
                    "volumes with no I/O, old snapshots, orphaned data — and "
                    "quantifies how much reclaiming them would buy back."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="performance",
        name="Performance analytics",
        blurb=(
            "Anomaly detection and impact analysis for performance — spotting "
            "when something is slow, and, harder, telling you why."
        ),
        limits="Baselines learned per system from its own history",
        region_ids=["analytics"],
        options=[
            CatalogOption(
                id="perf-anomaly",
                name="Performance anomaly detection",
                summary="Flags latency/IOPS/bandwidth that deviate from a learned baseline.",
                details=(
                    "Rather than a fixed threshold, CloudIQ learns what normal "
                    "looks like for each system across the day and week, then "
                    "flags statistically significant deviations. That catches "
                    "the slow creep a static alarm misses and avoids the false "
                    "alarms a static alarm creates."
                ),
            ),
            CatalogOption(
                id="perf-impact",
                name="Performance impact analysis",
                summary="Separates the workload causing an impact from the ones suffering it.",
                details=(
                    "When latency rises, CloudIQ distinguishes the 'noisy "
                    "neighbor' — the workload whose surge is consuming shared "
                    "resources — from the workloads being impacted by it. "
                    "Naming the culprit turns 'the array is slow' into an "
                    "actionable 'this job is the cause'."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="cybersecurity",
        name="Cybersecurity monitoring",
        blurb=(
            "Turns the same telemetry into a security posture: continuously "
            "checking systems against a security baseline and flagging drift "
            "and risk."
        ),
        limits="Evaluation against Dell security baselines",
        region_ids=["security"],
        options=[
            CatalogOption(
                id="cyber-misconfig",
                name="Misconfiguration & drift detection",
                summary="Evaluates each system against a security baseline, flags drift.",
                details=(
                    "CloudIQ compares each system's configuration to a set of "
                    "security evaluation criteria — encryption enabled, secure "
                    "protocols, hardening settings — and raises an alert when a "
                    "system drifts out of compliance. Dell claims automating "
                    "these checks across 1,000 systems takes about three "
                    "minutes versus days by hand."
                ),
            ),
            CatalogOption(
                id="cyber-ransomware",
                name="Ransomware & threat indicators",
                summary="Watches for signals consistent with ransomware and active threats.",
                details=(
                    "Beyond static configuration, the cybersecurity engine "
                    "looks for behavioral risk indicators — patterns "
                    "consistent with ransomware activity — and surfaces them "
                    "as high-priority findings. It is a last line inside the "
                    "infrastructure layer, complementing, not replacing, "
                    "endpoint and network security."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="sustainability",
        name="Sustainability",
        blurb=(
            "The same telemetry, read for energy: power draw and the carbon "
            "behind it, trended across the fleet — increasingly a reporting "
            "requirement, not a nicety."
        ),
        limits="Derived from power/environmental telemetry",
        region_ids=["analytics", "insight"],
        options=[
            CatalogOption(
                id="sustain-energy",
                name="Energy & carbon tracking",
                summary="Trends power consumption and estimated carbon footprint per system and fleet.",
                details=(
                    "CloudIQ turns power and environmental telemetry into "
                    "energy-consumption and estimated-carbon trends, so "
                    "efficiency can be measured and reported alongside health "
                    "and capacity. It also flags the least efficient systems, "
                    "which are often the oldest and the next to replace."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="assistant",
        name="AIOps Assistant",
        blurb=(
            "The generative-AI layer: ask about your environment in plain "
            "language and get an answer grounded in both Dell's knowledge and "
            "your systems' real state."
        ),
        limits="Trained on 133,000+ Dell knowledge resources",
        region_ids=["assistant"],
        options=[
            CatalogOption(
                id="assist-genai",
                name="Generative-AI assistant",
                summary="Natural-language queries and troubleshooting, in the app.",
                details=(
                    "A built-in chat assistant that answers questions about "
                    "your infrastructure — 'why did this score drop?', 'what "
                    "should I do about this alert?' — drawing on a large body "
                    "of Dell support knowledge so the answer includes the "
                    "recommended fix, not just a definition."
                ),
            ),
            CatalogOption(
                id="assist-context",
                name="Infrastructure Context Awareness",
                summary="Answers are grounded in your connected environment's actual state.",
                details=(
                    "The 2025 enhancement that makes the assistant more than a "
                    "documentation search: it can reason over your systems' "
                    "current health scores, analytics, and alerts, so a "
                    "question about 'my PowerStore in the DR site' is answered "
                    "with that system's real data, not a generic article."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="integrations",
        name="Integrations & notifications",
        blurb=(
            "How insights leave CloudIQ and become action — reaching the tools "
            "and people that already run the environment."
        ),
        limits="REST API and webhooks; ITSM and mobile out of the box",
        region_ids=["action"],
        options=[
            CatalogOption(
                id="int-rest",
                name="REST API & webhooks",
                summary="Programmatic access to everything CloudIQ knows.",
                details=(
                    "A REST API exposes health, capacity, performance, and "
                    "security data for pulling into a data warehouse or a "
                    "custom dashboard, and webhooks push events out as they "
                    "happen — the foundation every other integration is built "
                    "on, and the hook for home-grown automation."
                ),
            ),
            CatalogOption(
                id="int-itsm",
                name="ITSM integration (ServiceNow)",
                summary="Turn a proactive health issue into a ticket automatically.",
                details=(
                    "Integration with IT service management tools like "
                    "ServiceNow so a CloudIQ finding opens (and updates) an "
                    "incident in the system of record — the issue lands in the "
                    "operations queue rather than waiting to be noticed in yet "
                    "another console."
                ),
            ),
            CatalogOption(
                id="int-notify",
                name="Email & mobile notifications",
                summary="Alerts to inboxes and the CloudIQ mobile app.",
                details=(
                    "Configurable email alerts and push notifications to the "
                    "mobile app, so the on-call engineer hears about a dropping "
                    "health score or a cybersecurity finding wherever they "
                    "are, without watching the dashboard."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="access-licensing",
        name="Access & licensing",
        blurb=(
            "How you get in and what it costs. The short answer on cost: "
            "nothing extra — it is included with the support agreements most "
            "Dell infrastructure already carries."
        ),
        limits="Included with ProSupport, ProSupport Plus, ProSupport One",
        region_ids=["insight"],
        options=[
            CatalogOption(
                id="access-included",
                name="Included with ProSupport & above",
                summary="No separate purchase — bundled with the support contract.",
                details=(
                    "CloudIQ / Dell AIOps is included at no additional cost "
                    "with ProSupport, ProSupport Plus, and ProSupport One "
                    "service agreements. You sign in with the Dell Support "
                    "Account tied to those contracts; there is no license to "
                    "buy and nothing to size."
                ),
            ),
            CatalogOption(
                id="access-apps",
                name="Web & mobile apps",
                summary="Browser experience plus an iOS/Android companion app.",
                details=(
                    "The full application runs in a browser — no client to "
                    "install — with a mobile app for health, alerts, and "
                    "notifications on the go. Access is via the Dell Support "
                    "Account, with role-based visibility across the "
                    "organization's connected systems."
                ),
            ),
            CatalogOption(
                id="access-reports",
                name="Dashboards & custom reports",
                summary="Fleet dashboards and scheduled/exportable reports.",
                details=(
                    "Customizable dashboards for day-to-day operations and "
                    "custom reports that can be saved, scheduled, and exported "
                    "— the artifact that turns continuous monitoring into the "
                    "monthly capacity or security review a manager signs off."
                ),
            ),
        ],
    ),
]
