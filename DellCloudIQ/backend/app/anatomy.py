"""Platform-architecture data: the CloudIQ / Dell AIOps telemetry-to-insight
pipeline, annotated.

Unlike the hardware twins, there is no chassis here — CloudIQ is a
cloud-native SaaS. So the shared "anatomy" is a **left-to-right architecture
diagram**: monitored Dell systems on the left (telemetry in), the Secure
Connect Gateway and cloud ingest in the middle, the ML analytics and
cybersecurity engines at the core, and the insights, AIOps Assistant, and
notifications on the right (insights out). Regions are placed in a normalized
100×58 space the frontend renders as SVG. The layout is a stylized mental
model of Dell's published AIOps architecture, not an internal system diagram.
"""

from __future__ import annotations

from .leveling import L
from .models import PlatformMap, PlatformRegion, SourceLink, Stat

ANATOMY = PlatformMap(
    id="cloudiq",
    name="CloudIQ / Dell AIOps — platform architecture",
    vendor="Dell Technologies",
    form_factor="Cloud-native SaaS (APEX AIOps)",
    generation="Dell AIOps (formerly CloudIQ)",
    year=2025,
    width=100,
    height=58,
    overview=L(
        novice=(
            "Everything else in this repo is a physical object. This one is "
            "software running as a service, so instead of a floorplan you get a "
            "diagram of a journey — the journey a piece of measurement data "
            "takes from a machine in a customer's building to a useful piece of "
            "advice. Equipment constantly reports on itself: temperatures, "
            "error counts, how full the drives are. That reporting is "
            "collected, sent securely to Dell, and analysed by machine-learning "
            "models looking for patterns a person would never notice — a drive "
            "that is failing slowly, or capacity that will run out in six weeks "
            "at the current rate. Watch the health score in the trace: it "
            "starts perfect, dips when a problem is detected, and recovers once "
            "it is dealt with."
        ),
        plain=(
            "CloudIQ — now Dell AIOps — is cloud-native observability software "
            "rather than hardware, so both of this repo's usual metaphors are "
            "adapted. The map is a platform architecture diagram laid out left "
            "to right, and the trace is the lifecycle of a batch of telemetry "
            "becoming an actionable insight: collected from monitored systems, "
            "sent through the Secure Connect Gateway, ingested, analysed by "
            "machine-learning models, surfaced as an insight, and notified. The "
            "analysis stage is the longest. The health score starts at 100, "
            "dips when an anomaly is detected, and partly recovers — telemetry "
            "flows one way, which the tests assert."
        ),
        standard=(
            "CloudIQ is Dell's cloud-based AIOps application for observing and "
            "managing Dell infrastructure — rebranded Dell AIOps and folded into "
            "APEX AIOps, but still the same idea: connect your Dell systems, and a "
            "SaaS platform continuously scores their health, forecasts capacity, "
            "detects performance anomalies, watches cybersecurity posture, and "
            "tells you about problems before they cause downtime. Nothing is "
            "installed on a desktop; telemetry flows one way from your systems, "
            "through the Secure Connect Gateway, to Dell's cloud, where machine "
            "learning turns it into insights you reach from a browser or the "
            "mobile app. A generative-AI AIOps Assistant, trained on Dell's "
            "support knowledge and aware of your environment, answers questions in "
            "plain language. It is included at no additional cost with ProSupport, "
            "ProSupport Plus, and ProSupport One agreements. This diagram traces a "
            "batch of telemetry from the monitored systems on the left to the "
            "insights and actions on the right."
        ),
        technical=(
            "Cloud-native AIOps observability, so the anatomy is a "
            "telemetry-to-insight architecture diagram rather than a floorplan: "
            "sources → Secure Connect Gateway → cloud ingest → ML analytics and "
            "cybersecurity → insights and assistant → notify. Phase order is "
            "collect → transmit → ingest → analyze → detect → surface → assist "
            "→ notify, with the ML analyze stage holding max dwell. "
            "`healthScore` starts at 100, dips at or after detect, and recovers "
            "above the low-water mark without returning to 100; first transmit "
            "precedes first surface, asserting one-way flow. No power model at "
            "all."
        ),
        expert=(
            "AIOps pipeline: sources → SCG → ingest → ML analytics → insight → "
            "notify. ML analyze holds max dwell. `healthScore` 100 → dip "
            "at/after detect → partial recovery; one-way flow asserted via "
            "transmit-before-surface. Capability catalog, not a bill of "
            "materials."
        ),
    ),
    regions=[
        # --- Sources: monitored Dell systems (telemetry in) ---------------
        PlatformRegion(
            id="src-storage", kind="source", label="Storage",
            x=1, y=2, w=15, h=12,
            description=(
                "Monitored Dell storage: PowerStore, PowerMax, PowerScale, "
                "PowerFlex, PowerVault, and Unity XT. Each array runs an agent "
                "(SupportAssist / the embedded connectivity client) that "
                "periodically gathers telemetry — health, capacity, "
                "performance counters, configuration, and logs — and hands it "
                "to the gateway. This is read-only observation; CloudIQ never "
                "controls the array."
            ),
        ),
        PlatformRegion(
            id="src-compute", kind="source", label="Servers & HCI",
            x=1, y=15, w=15, h=12,
            description=(
                "Monitored compute: PowerEdge servers (via the OpenManage "
                "Enterprise CloudIQ plugin) and VxRail hyperconverged "
                "clusters. Server telemetry adds firmware/BIOS levels, "
                "component health, and utilization to the same fleet view as "
                "storage and networking — the point of AIOps is one pane over "
                "all of it."
            ),
        ),
        PlatformRegion(
            id="src-network", kind="source", label="Networking",
            x=1, y=28, w=15, h=12,
            description=(
                "Monitored networking: PowerSwitch switches and Connectrix SAN "
                "directors. These are collected through the AIOps Collector — "
                "a small read-only virtual machine (OVA) on site that reaches "
                "switches over a non-privileged REST API and, for VMware and "
                "Connectrix, vCenter over the VMware API."
            ),
        ),
        PlatformRegion(
            id="src-dataprot", kind="source", label="Data protection",
            x=1, y=41, w=15, h=15,
            description=(
                "Monitored data protection: PowerProtect DD (Data Domain) "
                "appliances and PowerProtect Data Manager. Backup and "
                "protection telemetry lets CloudIQ watch protection status and "
                "feed the cybersecurity view — an unprotected or newly "
                "misconfigured system is itself a risk signal."
            ),
        ),
        # --- Gateway: secure one-way transport ----------------------------
        PlatformRegion(
            id="gateway", kind="gateway", label="Secure Connect Gateway",
            x=20, y=16, w=13, h=26,
            description=(
                "The Secure Connect Gateway (SCG) — with SupportAssist and the "
                "AIOps Collector — is how telemetry leaves your data center. "
                "It batches the collected data and opens a one-way, encrypted "
                "(TLS) outbound connection to Dell's cloud on port 443; the "
                "collector talks to the gateway on 9443. The connection is "
                "outbound and one-directional by design — Dell's cloud cannot "
                "reach back into your network, which is what makes the SaaS "
                "model acceptable to security teams."
            ),
        ),
        # --- Cloud ingest -------------------------------------------------
        PlatformRegion(
            id="ingest", kind="ingest", label="Cloud ingest & data lake",
            x=37, y=16, w=13, h=26,
            description=(
                "In Dell's cloud, incoming telemetry is ingested, parsed, and "
                "normalized into a common model, then landed in a data lake "
                "alongside history and the anonymized signals of Dell's whole "
                "installed base. Normalizing across products is what lets one "
                "health score span storage, servers, and networking, and what "
                "gives the anomaly models a fleet-wide baseline to compare "
                "against."
            ),
        ),
        # --- Analytics core -----------------------------------------------
        PlatformRegion(
            id="analytics", kind="analytics", label="ML analytics engine",
            x=54, y=2, w=16, h=30,
            description=(
                "The machine-learning core, and the heaviest stage. It "
                "computes each system's Health Score (a 0–100 roll-up of "
                "configuration, capacity, performance, and component issues), "
                "detects performance anomalies against learned baselines, "
                "identifies workload contention (the 'noisy neighbor' stealing "
                "another's performance), and forecasts capacity — projecting "
                "when a pool will fill and how much reclaimable space is "
                "trapped. These models run on the fleet-wide data lake, so an "
                "anomaly is judged against how similar systems normally behave."
            ),
        ),
        PlatformRegion(
            id="security", kind="security", label="Cybersecurity engine",
            x=54, y=34, w=16, h=22,
            description=(
                "The cybersecurity monitoring engine evaluates each system "
                "against a security baseline — flagging misconfigurations, "
                "drift from hardening guidelines, and risk indicators such as "
                "patterns consistent with ransomware. It turns the same "
                "telemetry stream into a security posture, so a disabled "
                "encryption setting or an unexpected configuration change "
                "becomes an alert, not a surprise found during an audit."
            ),
        ),
        # --- Insights + assistant (insights out) --------------------------
        PlatformRegion(
            id="insight", kind="insight", label="Insights · web & mobile app",
            x=74, y=2, w=15, h=30,
            description=(
                "The CloudIQ / Dell AIOps application itself: the browser and "
                "mobile experience where the analytics surface as Health "
                "Scores, proactive health issues, capacity forecasts, "
                "performance-impact views, cybersecurity findings, and "
                "sustainability (energy and carbon) trends. Customizable "
                "dashboards and reports roll the fleet up for an operator or a "
                "report up for a manager — this is where a human meets the "
                "platform."
            ),
        ),
        PlatformRegion(
            id="assistant", kind="assistant", label="AIOps Assistant (GenAI)",
            x=74, y=34, w=15, h=22,
            description=(
                "A generative-AI assistant trained on 133,000+ Dell knowledge "
                "resources and made aware of your connected environment "
                "('Infrastructure Context Awareness'). You can ask, in plain "
                "language, why a health score dropped or what to do about an "
                "alert, and it answers using both Dell's support knowledge and "
                "your systems' actual state — turning a dashboard reading into "
                "a next step without opening a support case."
            ),
        ),
        # --- Actions & integrations ---------------------------------------
        PlatformRegion(
            id="action", kind="action", label="Notify & integrate",
            x=92, y=16, w=7, h=26,
            description=(
                "The outbound edge: email and mobile push notifications, and "
                "integrations to the tools teams already run — ITSM systems "
                "like ServiceNow, chat, and any automation via REST APIs and "
                "webhooks. This is how an insight leaves CloudIQ and becomes a "
                "ticket, a message, or an automated remediation, closing the "
                "loop from telemetry to action."
            ),
        ),
    ],
    stats=[
        Stat(label="Delivery", value="Cloud-native SaaS · no desktop install"),
        Stat(label="Cost", value="Included with ProSupport / Plus / One"),
        Stat(label="Connectivity", value="Secure Connect Gateway · one-way TLS"),
        Stat(label="Analytics", value="Health · capacity · performance · security"),
        Stat(label="Assistant", value="GenAI · 133k+ Dell knowledge resources"),
        Stat(label="Monitors", value="Storage · servers · network · data protection"),
        Stat(label="Integrations", value="REST API · webhooks · ITSM · mobile"),
        Stat(label="Claimed impact", value="Up to 10× faster issue resolution"),
    ],
    sources=[
        SourceLink(
            label="Dell AIOps (CloudIQ) product page",
            url="https://www.dell.com/en-us/shop/dell-aiops/sl/aiops",
        ),
        SourceLink(
            label="Dell AIOps: install the AIOps Collector (KB)",
            url="https://www.dell.com/support/kbdoc/en-us/000304306/apex-aiops-observability-how-do-i-install-the-new-apex-aiops-observability-collector-v1-17-0",
        ),
        SourceLink(
            label="Secure Connect Gateway — connectivity for Dell systems",
            url="https://www.delltechnologies.com/asset/en-us/services/support/briefs-summaries/secure-connect-gateway-customer-faq.pdf",
        ),
    ],
)
