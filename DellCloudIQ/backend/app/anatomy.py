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
            "Most Dell products are physical objects. CloudIQ is software "
            "running as a service, so instead of a floorplan you get a "
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
            "CloudIQ — renamed Dell AIOps in 2025 — is cloud-native observability software "
            "rather than hardware, so both of the usual hardware views (floorplan and power-on) are "
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
            "managing Dell infrastructure — renamed APEX AIOps Infrastructure "
            "Observability in 2024 and Dell AIOps in 2025, but still the same "
            "idea: connect your Dell systems, and a "
            "SaaS platform continuously scores their health, forecasts capacity, "
            "detects performance anomalies, watches cybersecurity posture, and "
            "tells you about problems before they cause downtime. Nothing is "
            "installed on a desktop; telemetry flows one way from your systems, "
            "through the Secure Connect Gateway, to Dell's cloud, where machine "
            "learning turns it into insights you reach from a browser or the "
            "mobile app. A generative-AI AIOps Assistant, trained on Dell's "
            "support knowledge and aware of your environment, answers questions in "
            "plain language. Dell includes it at no additional cost with "
            "ProSupport and ProSupport Plus for Infrastructure and ProSupport One "
            "for Data Center agreements. This diagram traces a "
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
            "Health Score starts at 100, dips at or after detect, and recovers "
            "above the low-water mark without returning to 100; first transmit "
            "precedes first surface, asserting one-way flow. No power model at "
            "all."
        ),
        expert=(
            "AIOps pipeline: sources → SCG → ingest → ML analytics → insight → "
            "notify. ML analyze holds max dwell. Health Score 100 → dip "
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
            description=L(
                novice=(
                    "The storage systems being watched: the machines that hold a "
                    "company's data, such as PowerStore, PowerMax, PowerScale, "
                    "PowerFlex, PowerVault and Unity XT. Each one runs a small "
                    "piece of Dell software that regularly writes down how it is "
                    "doing — how healthy it is, how full, how fast it is "
                    "answering, how it is set up, and what its logs say — and "
                    "hands that over to the gateway. It only reads and reports. "
                    "Nothing here can change the storage system."
                ),
                standard=(
                    "Monitored Dell storage: PowerStore, PowerMax, PowerScale, "
                    "PowerFlex, PowerVault, and Unity XT. Each array runs an agent "
                    "(SupportAssist / the embedded connectivity client) that "
                    "periodically gathers telemetry — health, capacity, "
                    "performance counters, configuration, and logs — and hands it "
                    "to the gateway. This is read-only observation; CloudIQ never "
                    "controls the array."
                ),
            ),
        ),
        PlatformRegion(
            id="src-compute", kind="source",
            label=L(
                novice="Servers & all-in-one clusters",
                standard="Servers & HCI",
            ),
            x=1, y=15, w=15, h=12,
            description=L(
                novice=(
                    "The computers being watched: PowerEdge servers, and VxRail "
                    "clusters, which are groups of servers that also act as the "
                    "storage — all-in-one boxes, called hyperconverged. The "
                    "servers report through a Dell management add-on. What they "
                    "report adds a few things storage does not: which versions of "
                    "their low-level software they are running, whether each part "
                    "inside is healthy, and how busy they are. It all lands in one "
                    "view with the storage and the network, which is the point: "
                    "one place to look instead of four."
                ),
                standard=(
                    "Monitored compute: PowerEdge servers (via the OpenManage "
                    "Enterprise AIOps plugin, formerly the CloudIQ plugin) and "
                    "VxRail hyperconverged "
                    "clusters. Server telemetry adds firmware/BIOS levels, "
                    "component health, and utilization to the same fleet view as "
                    "storage and networking — the point of AIOps is one pane over "
                    "all of it."
                ),
            ),
        ),
        PlatformRegion(
            id="src-network", kind="source", label="Networking",
            x=1, y=28, w=15, h=12,
            description=L(
                novice=(
                    "The network equipment being watched: the switches that carry "
                    "traffic between machines, and the directors that carry it to "
                    "storage. These cannot report on themselves, so a small "
                    "read-only program runs on a server on site, logs in to each "
                    "of them with an account that is allowed to look and not to "
                    "change anything, and collects the readings on their behalf."
                ),
                standard=(
                    "Monitored networking: PowerSwitch switches and Connectrix SAN "
                    "directors. These are collected through the AIOps Collector — "
                    "a small read-only virtual machine (OVA) on site that reaches "
                    "switches with a non-privileged account and, for VMware, "
                    "vCenter with read-only privileges."
                ),
            ),
        ),
        PlatformRegion(
            id="src-dataprot", kind="source", label="Data protection",
            x=1, y=41, w=15, h=15,
            description=L(
                novice=(
                    "The backup equipment being watched: the appliances that keep "
                    "copies of the company's data, and the software that runs the "
                    "copying. Watching them answers a question nobody wants to ask "
                    "late — is everything actually being backed up? A system whose "
                    "backups quietly stopped, or whose settings changed without "
                    "anyone noticing, is itself a warning sign, so these readings "
                    "also feed the security side of the picture."
                ),
                standard=(
                    "Monitored data protection: PowerProtect DD (Data Domain) "
                    "appliances and PowerProtect Data Manager. Backup and "
                    "protection telemetry lets CloudIQ watch protection status and "
                    "feed the cybersecurity view — an unprotected or newly "
                    "misconfigured system is itself a risk signal."
                ),
            ),
        ),
        # --- Gateway: secure one-way transport ----------------------------
        PlatformRegion(
            id="gateway", kind="gateway", label="Secure Connect Gateway",
            x=20, y=16, w=13, h=26,
            description=L(
                novice=(
                    "The Secure Connect Gateway is the one door the readings leave "
                    "by. It gathers what the machines have collected and opens an "
                    "encrypted connection outward to Dell's cloud, over the same "
                    "kind of connection a browser uses for a bank. The direction is "
                    "the whole point: every connection is started from inside the "
                    "company's own network, and the readings only travel outward, "
                    "so Dell's cloud has no way to reach in. That single property "
                    "is what lets security teams approve it. (Dell's support staff "
                    "can use the same outward tunnel for a remote session when you "
                    "let them, and you can log and restrict that separately; it is "
                    "a support function, not part of the monitoring.)"
                ),
                standard=(
                    "The Secure Connect Gateway (SCG) — with SupportAssist and the "
                    "AIOps Collector — is how telemetry leaves your data center. "
                    "It replaces the older SupportAssist Enterprise and Secure "
                    "Remote Services software. It batches the collected data and "
                    "opens an encrypted (mutual TLS) outbound connection to Dell's "
                    "cloud on port 443; the collector talks to the gateway on 9443. "
                    "Every connection is opened from inside your network, and the "
                    "AIOps telemetry travels one way — Dell's cloud cannot open a "
                    "connection into your network, which is what makes the SaaS "
                    "model acceptable to security teams. (Dell support can separately "
                    "use the same outbound tunnel for remote-support sessions, which "
                    "you can audit and restrict with Dell's Policy Manager; that is "
                    "a support function, not part of AIOps.)"
                ),
            ),
        ),
        # --- Cloud ingest -------------------------------------------------
        PlatformRegion(
            id="ingest", kind="ingest", label="Cloud ingest & data lake",
            x=37, y=16, w=13, h=26,
            description=L(
                novice=(
                    "Where the readings arrive in Dell's cloud. Every product "
                    "describes itself in its own words, so the first job is "
                    "translation: everything is rewritten into one shared "
                    "vocabulary and stored next to its own history and to the "
                    "same readings from every other customer's equipment, with "
                    "the names stripped off. Two things follow from that. One "
                    "health score can cover storage, servers and network "
                    "together. And there is a picture of what normal looks like "
                    "across all of it, not just yours."
                ),
                standard=(
                    "In Dell's cloud, incoming telemetry is ingested, parsed, and "
                    "normalized into a common model, then landed in a data lake "
                    "alongside history and the anonymized signals of Dell's whole "
                    "installed base. Normalizing across products is what lets one "
                    "health score span storage, servers, and networking, and what "
                    "gives the anomaly models a fleet-wide baseline to compare "
                    "against."
                ),
            ),
        ),
        # --- Analytics core -----------------------------------------------
        PlatformRegion(
            id="analytics", kind="analytics",
            label=L(
                novice="Analytics engine (machine learning)",
                standard="ML analytics engine",
            ),
            x=54, y=2, w=16, h=30,
            description=L(
                novice=(
                    "The part that does the thinking, and the slowest step. It "
                    "gives each system a health score out of 100, rolling up how "
                    "it is configured, how full it is, how fast it is answering "
                    "and whether any part inside it is failing. It compares "
                    "today's behaviour with what it has learned is normal for "
                    "that system, so it can notice something answering more "
                    "slowly than it usually does. It works out when one workload "
                    "is stealing performance from the others. And it projects "
                    "forward: when this will run out of space, and how much space "
                    "could be won back. Because it has learned from the whole "
                    "installed base, it judges your equipment against how similar "
                    "equipment normally behaves, not against a fixed rule."
                ),
                standard=(
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
        ),
        PlatformRegion(
            id="security", kind="security", label="Cybersecurity engine",
            x=54, y=34, w=16, h=22,
            description=L(
                novice=(
                    "The security half of the same analysis. It checks each system "
                    "against a list of how it ought to be set up, and raises a "
                    "flag when something has been left wrong, has drifted away "
                    "from that list, or matches a weakness Dell has published a "
                    "warning about. It also watches for signs of a ransomware "
                    "attack, which Dell lists for PowerMax storage first. It reads "
                    "exactly the same stream of measurements as everything else "
                    "here — so a switched-off encryption setting becomes an alert "
                    "this week, rather than a surprise during next year's audit."
                ),
                standard=(
                    "The cybersecurity monitoring engine evaluates each system "
                    "against a security baseline — flagging misconfigurations, "
                    "drift from hardening guidelines, Dell security advisories "
                    "(published vulnerabilities) that apply to your systems, and "
                    "possible ransomware incidents (Dell lists this for PowerMax "
                    "first). It turns the same "
                    "telemetry stream into a security posture, so a disabled "
                    "encryption setting or an unexpected configuration change "
                    "becomes an alert, not a surprise found during an audit."
                ),
            ),
        ),
        # --- Insights + assistant (insights out) --------------------------
        PlatformRegion(
            id="insight", kind="insight", label="Insights · web & mobile app",
            x=74, y=2, w=15, h=30,
            description=L(
                novice=(
                    "The application people actually look at, in a web browser or "
                    "on a phone. This is where the analysis becomes something "
                    "readable: each system's health score and what is wrong with "
                    "it, when it will run out of space, which workload is slowing "
                    "the others down, security findings, and how much energy and "
                    "carbon the equipment is accounting for. The screens can be "
                    "arranged for whoever is looking — the whole estate at a "
                    "glance for the person running it, a summary for the person "
                    "paying for it. This is where a human meets the platform."
                ),
                standard=(
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
        ),
        PlatformRegion(
            id="assistant", kind="assistant",
            label=L(
                novice="Assistant — answers in plain words",
                standard="AIOps Assistant (GenAI)",
            ),
            x=74, y=34, w=15, h=22,
            description=L(
                novice=(
                    "An assistant you can ask questions, of the kind that writes "
                    "its answers rather than picking them off a list. Dell says it "
                    "has read more than 133,000 of its own support articles, "
                    "manuals and release notes, and that it also knows the state "
                    "of the equipment you have connected. So you can type why did "
                    "this score drop, or what should I do about this alert, and "
                    "get back an answer naming your own storage, the likely cause "
                    "and the next step — instead of a number on a dashboard and a "
                    "support case to open."
                ),
                standard=(
                    "A generative-AI assistant that Dell says is trained on more "
                    "than 133,000 Dell Knowledge Base articles, manuals, and "
                    "release notes, and made aware of your connected environment "
                    "('Infrastructure Context Awareness'). You can ask, in plain "
                    "language, why a health score dropped or what to do about an "
                    "alert, and it answers using both Dell's support knowledge and "
                    "your systems' actual state — turning a dashboard reading into "
                    "a next step without opening a support case."
                ),
            ),
        ),
        # --- Actions & integrations ---------------------------------------
        PlatformRegion(
            id="action", kind="action", label="Notify & integrate",
            x=92, y=16, w=7, h=26,
            description=L(
                novice=(
                    "The way out. A finding here becomes an email, an alert on "
                    "someone's phone, a job in whatever system the team uses to "
                    "track work, a message in their chat, or a trigger for a "
                    "script that does something about it. Nothing on this edge "
                    "touches the equipment itself — it hands the finding to "
                    "people and to the tools they already run, and they do the "
                    "repair. That is what closes the loop from a measurement to "
                    "somebody acting."
                ),
                standard=(
                    "The outbound edge: email and mobile push notifications, and "
                    "integrations to the tools teams already run — ITSM systems "
                    "like ServiceNow, chat, and any automation via REST APIs and "
                    "webhooks. This is how an insight leaves CloudIQ and becomes a "
                    "ticket, a message, or an automated remediation, closing the "
                    "loop from telemetry to action."
                ),
            ),
        ),
    ],
    stats=[
        Stat(label="Delivery", value="Cloud-native SaaS · no desktop install"),
        Stat(label="Cost", value="Included with ProSupport / Plus / One (Dell)"),
        Stat(label="Connectivity", value="Secure Connect Gateway · outbound TLS"),
        Stat(label="Analytics", value="Health · capacity · performance · security"),
        Stat(label="Assistant", value="GenAI · 133k+ Dell KB articles (Dell's figure)"),
        Stat(label="Monitors", value="Storage · servers · network · data protection"),
        Stat(label="Integrations", value="REST API · webhooks · ITSM · mobile"),
        Stat(label="Claimed impact", value="Up to 10× faster resolution (Dell user survey, Jan 2026)"),
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
            label="Secure Connect Gateway — customer FAQ (connectivity, security, remote support)",
            url="https://www.delltechnologies.com/asset/en-us/services/support/briefs-summaries/secure-connect-gateway-customer-faq.pdf",
        ),
        SourceLink(
            label="Dell AIOps for Infrastructure Observability — solution brief (health score, 10× survey claim, ProSupport)",
            url="https://www.delltechnologies.com/assetlink/doc/en-gb/dell-aiops-infrastructure-observability-sb-dl11i2fc-original.pdf",
        ),
        SourceLink(
            label="Dell blog, Oct 2025 — AIOps Assistant and Infrastructure Context Awareness (133,000+ articles)",
            url="https://www.dell.com/en-us/blog/dell-s-aiops-assistant-just-got-smarter-here-s-how/",
        ),
        SourceLink(
            label="Dell KB — ransomware incident detection for PowerMax in CloudIQ",
            url="https://www.dell.com/support/kbdoc/en-us/000223022/cloudiq-general-procedures-to-enable-cybersecurity-ransomware-incident-detection-for-powermax-in-cloudiq",
        ),
    ],
)
