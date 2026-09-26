"""Failure scenarios for the CloudIQ / Dell AIOps pipeline — pure, like the engine.

The happy path (``engine.simulate``) shows telemetry becoming an insight. This
module holds the traces where it does not, starting with the onboarding failure
users actually report: the system says **connected** and no telemetry arrives.

Same rules as ``engine.py`` and AST-checked the same way: no FastAPI, no IO, no
timers, no randomness. A scenario is a second deterministic ``PipelineState[]``
built from the same model, extended only additively (``failed_regions``,
``score_state``, ``minutes_without_data``, ``backlog_points`` — all defaulted so
the happy path is unchanged in every original field).

What the real product does, and where each behaviour here comes from:

* A system that has never delivered data has **no Health Score**: CloudIQ draws
  a grey dash, and grey *with* a number means "connectivity issue, uncertain
  score" — never green (Dell EMC CloudIQ detailed review, H15691).
* The Connectivity view sorts systems into four groups — Connected, Lost
  Connection, Not Set Up, Install Base Issues — and Dell defines them by what
  the system is doing: Connected is *successfully sending data*, Lost
  Connection is *was sending and stopped*, Not Set Up is *not set up to send
  data through Secure Remote Services* (H15691). A gateway that passes its own
  connection test is therefore not making CloudIQ's claim. An array that has
  never delivered lands outside Connected; the twin shows Not Set Up, which is
  where that definition puts it, and the listing is the sourced part rather
  than the bucket. So the cloud does not *detect* this failure by timing
  missed sends — the array is outside Connected from the start, and what takes
  time is a person being entitled to read the grey dash as a fault: Dell tells
  both ME4 and PowerMax owners to expect about an hour before a newly enabled
  system shows data (Dell KB 000181685; H15691).
* The usual causes are on the customer side of the wire: outbound TCP 443 to
  Dell's telemetry endpoint blocked, a proxy misconfigured, DNS wrong, or
  collection simply disabled on the array (Dell KB 000181685); a gateway
  upgrade that moves a port does the same to the Collector (Dell KB 000196110).
* Telemetry leaves on a schedule — 5 minutes for alerts and performance, an
  hour for capacity and configuration on Unity (H15691); 15 and 60 minutes on
  the ME4 (KB 000181685).
* Remote connectivity uses more than one port and destination (H15691 names
  443 and 8443 to Dell's Global Access Servers), so an allowlist can be right
  for one and wrong for another. *Which* destination the proxy refuses in this
  trace is illustrative: Dell does not publish the gateway's connection test
  in enough detail to say exactly what a pass does and does not cover.

Illustrative, and said so in the prose: every count and timing, and above all
the **backfill**. How much history a system or gateway holds while egress is
blocked varies by product and is not something Dell publishes as one number; a
long outage in the real product can leave a gap in the charts. The trace shows
the full backlog arriving because that keeps the ledger readable, not because
it is a guarantee.
"""

from __future__ import annotations

from .engine import simulate
from .leveling import L
from .models import PipelineState, ScenarioInfo, SourceLink

HEALTHY = "healthy"
CONNECTED_NO_DATA = "connected-no-data"

# One collection interval, and what it gathers (illustrative; the happy path's
# collect step uses the same 5,200 points).
INTERVAL_SECONDS = 300
POINTS_PER_INTERVAL = 5200

CONNECTED_NO_DATA_PHASES = [
    "register", "handshake", "collect", "blocked", "starved", "stale",
    "repair", "backfill", "analyze", "resume",
]

_SOURCES = [
    SourceLink(
        label=(
            "Dell EMC CloudIQ: a detailed review (H15691) — Connectivity "
            "categories, Last Contact Time, grey dash / grey number Health "
            "Score, 5-minute and hourly collection, ports 443 and 8443"
        ),
        url="https://vepimg.b8cdn.com/uploads/vjfnew/743/content/docs/1588809544h15691-emc-cloudiq-overview.pdf",
    ),
    SourceLink(
        label=(
            "Dell KB 000181685 — PowerVault ME4: troubleshooting CloudIQ upload "
            "failures (outbound 443, proxy, DNS, collection disabled; 15/60-minute sends)"
        ),
        url="https://www.dell.com/support/kbdoc/en-us/000181685/cloudiq-me4-how-to-troubleshoot-cloudiq-upload-failures",
    ),
    SourceLink(
        label=(
            "Dell KB 000196110 — CloudIQ Collector shows Connection in Trouble "
            "after a gateway port change"
        ),
        url="https://www.dell.com/support/kbdoc/en-us/000196110/cloudiq-cloudiq-collector-shows-connection-in-triuble-after-port-changes",
    ),
    SourceLink(
        label=(
            "Dell KB 000022684 — CloudIQ is not sending data to Dell "
            "Technologies (Dell sign-in required)"
        ),
        url="https://www.dell.com/support/kbdoc/en-us/000022684/dell-emc-unity-cloud-iq-is-not-sending-data-to-emc-user-correctable",
    ),
    SourceLink(
        label=(
            "Dell Community — OME not updating anything to APEX AIOps "
            "(plugin installed, devices managed, nothing arrives; unresolved)"
        ),
        url="https://www.dell.com/community/en/conversations/dell-openmanage-enterprise/ome-not-updating-anything-to-apex-aiops/67efba72457e32024d38a05d",
    ),
]

SCENARIOS: list[ScenarioInfo] = [
    ScenarioInfo(
        id=HEALTHY,
        name="Healthy pipeline",
        summary=(
            "Telemetry leaves, arrives, is analyzed, and a risk becomes an "
            "insight and a notification."
        ),
        intro=L(
            novice=(
                "CloudIQ is a service that runs in Dell's cloud, so there is "
                "nothing to switch on. What it has instead is a pipeline, a fixed "
                "series of stages that measurements pass through. Your Dell "
                "equipment gathers measurements about itself, called telemetry. "
                "A piece of software on your site, the Secure Connect Gateway, "
                "sends them out to Dell's cloud, and nothing ever comes back in "
                "the other way. There, software that has learned what normal "
                "looks like gives each system a Health Score out of 100 and looks "
                "for anything unusual. When it finds a problem the score drops, "
                "the problem appears in the app with an explanation from the "
                "AIOps Assistant, and an alert goes out. Press Run and watch each "
                "stage light up the part of the platform it happens in."
            ),
            plain=(
                "CloudIQ is a cloud service, so it has no power button. What it "
                "has is a pipeline. Your monitored Dell systems collect "
                "telemetry, meaning measurements about themselves. The Secure "
                "Connect Gateway on your site sends it one way to Dell's cloud. "
                "Machine learning there gives each system a Health Score and "
                "looks for anomalies, readings that do not fit the usual "
                "pattern. When something crosses a line the score drops, the "
                "insight appears in the app, the AIOps Assistant explains it, and "
                "a notification goes out. Play the trace and watch each stage "
                "light up the part of the platform it runs in."
            ),
            standard=(
                "CloudIQ has no power button: it is a cloud service. What it does "
                "have is a pipeline: your monitored Dell systems collect "
                "telemetry, the Secure Connect Gateway ships it one-way to Dell's "
                "cloud, machine learning scores health and hunts for anomalies, "
                "and when something crosses a line the Health Score drops, the "
                "insight surfaces, the AIOps Assistant explains it, and a "
                "notification fires. Play the trace and watch each stage light up "
                "the part of the platform it runs in."
            ),
            technical=(
                "The trace follows one telemetry batch through the SaaS "
                "pipeline: scheduled collection on the estate, outbound-only "
                "transmit through the Secure Connect Gateway, ingest and "
                "normalization, the ML pass (health scoring, anomaly detection, "
                "forecasting), a threshold crossing that drops the Health Score, "
                "the insight and AIOps Assistant, then notification and "
                "integrations. Each step lights the regions it runs in."
            ),
            expert=(
                "One telemetry batch: collect, SCG outbound transmit, ingest, ML "
                "scoring, threshold crossing, insight, Assistant, notify. "
                "Regions light per step."
            ),
        ),
        note=L(
            novice=(
                "The Health Score is the number CloudIQ is known for. It is 100 "
                "when all is well and drops when a problem is found. It goes back "
                "up only when a later batch of measurements shows the problem is "
                "gone, never just because an alert was sent. Every count and "
                "time here is illustrative, not a measurement of your systems."
            ),
            standard=(
                "The Health Score is CloudIQ's signature metric: 100 when "
                "healthy, it drops when a risk is detected and recovers once a "
                "later collection shows the issue cleared. Counts and timings "
                "are illustrative, not a measurement of your fleet."
            ),
            expert=(
                "Health Score: 100 nominal, decrements on detection, recomputed "
                "per collection. All values illustrative."
            ),
        ),
        hero_field="healthScore",
        phases=[
            "idle", "collect", "transmit", "ingest", "analyze", "detect",
            "surface", "assist", "notify",
        ],
    ),
    ScenarioInfo(
        id=CONNECTED_NO_DATA,
        name="Connected, but no data",
        summary=(
            "A newly onboarded array passes the gateway's connection test while "
            "the customer's own proxy refuses the telemetry upload. The platform "
            "shows no score rather than a good one, lists the array as not "
            "sending data, and resumes once the proxy allows the upload out."
        ),
        intro=L(
            novice=(
                "This is the setup failure people report most. A new storage "
                "array is added to CloudIQ. The Secure Connect Gateway, the "
                "software on site that sends measurements to Dell, tests its "
                "connection and passes. But the company's own proxy, the "
                "checkpoint all outgoing internet traffic has to pass, refuses "
                "to let the measurements through. Watch what the platform does "
                "when nothing arrives: it shows no Health Score at all instead "
                "of a good one, it lists the array as not sending data, and it "
                "starts working only after an administrator inside the company "
                "opens the way out through the firewall. Every count and time "
                "here is illustrative."
            ),
            plain=(
                "The onboarding failure people actually report. A new array is "
                "registered and the Secure Connect Gateway passes its connection "
                "test, but the company's own outbound proxy, the checkpoint for "
                "traffic leaving the network, refuses the telemetry upload. "
                "Watch what the platform does with no data: it shows no Health "
                "Score instead of a good one, lists the array as not sending "
                "data, and resumes only after an administrator opens the way "
                "out through the firewall from the company's side. Counts and "
                "timings are illustrative."
            ),
            standard=(
                "The onboarding failure people actually report. A new array is "
                "registered and the Secure Connect Gateway passes its connection "
                "test, but the company's own outbound proxy refuses the "
                "telemetry upload. Watch what the platform does with no data: it "
                "shows no Health Score instead of a good one, lists the array as "
                "not sending data, and resumes only after an administrator "
                "allows the upload through the proxy from the customer side. "
                "Counts and timings are illustrative."
            ),
            technical=(
                "Onboarding failure: the array is registered and the gateway's "
                "connectivity test passes, but the customer's egress proxy "
                "(egress meaning traffic leaving the network) has no allow rule "
                "for the telemetry upload's destination. The platform shows a "
                "grey dash rather than a score, lists the system outside "
                "Connected, and resumes after a customer-side rule change. "
                "Counts and timings illustrative."
            ),
            expert=(
                "Registered, SCG test green, telemetry upload denied at the "
                "customer egress proxy. Grey dash, not Connected, customer-side "
                "fix. Values illustrative."
            ),
        ),
        note=L(
            novice=(
                "Minutes without data is the number to watch in this scenario: "
                "how long Dell's cloud has heard nothing from the array, counted "
                "from the moment it was added, because an array that has never "
                "sent anything has no last-contact time to count from. While "
                "it climbs, the score stays a grey dash, never green, and "
                "nothing is analyzed. Everything the array gathers waits on "
                "site and is delivered after the fix. That complete catch-up is "
                "illustrative: how much a real system keeps while it cannot "
                "send varies by product."
            ),
            standard=(
                "Minutes without data is this scenario's number: how long the "
                "cloud has heard nothing from the array, counted from onboarding, "
                "since a system that never delivered has no Last Contact Time to "
                "count from. While it climbs, the "
                "score stays a grey dash, never green, and nothing is analyzed. "
                "Everything collected waits on site and is delivered after the "
                "fix; that full backfill is illustrative, since real retention "
                "varies by product."
            ),
            expert=(
                "Hero counter: minutes since onboarding — no Last Contact Time "
                "exists to count from. Grey dash throughout, "
                "no analytics. Full backfill illustrative; retention is "
                "product-specific."
            ),
        ),
        hero_field="minutesWithoutData",
        phases=CONNECTED_NO_DATA_PHASES,
        sources=_SOURCES,
    ),
]

SCENARIO_IDS = [s.id for s in SCENARIOS]


def _collected(elapsed_seconds: int) -> int:
    """Telemetry the array has gathered by this moment: one batch per elapsed
    collection interval. Pure arithmetic, so the ledger can be tested."""
    return POINTS_PER_INTERVAL * (elapsed_seconds // INTERVAL_SECONDS)


def simulate_scenario(scenario: str = HEALTHY) -> list[PipelineState]:
    """The trace for a scenario id. Unknown ids raise ``KeyError`` — the HTTP
    layer turns that into a 404; the engine does not guess."""
    if scenario == HEALTHY:
        return simulate()
    if scenario == CONNECTED_NO_DATA:
        return simulate_connected_no_data()
    raise KeyError(scenario)


def simulate_connected_no_data() -> list[PipelineState]:
    """Connected, but no data: the telemetry upload is refused at the customer's
    own egress, and the platform has to say so instead of showing a score."""
    t_collect, t_blocked, t_starved, t_stale, t_repair, t_backfill = (
        300, 310, 900, 7200, 9000, 9300,
    )
    delivered = _collected(t_backfill)
    return [
        PipelineState(
            step=0,
            phase="register",
            label="Array registered in the portal",
            description=L(
                novice=(
                    "An administrator switches on CloudIQ for a new storage "
                    "array. The portal already knows the array exists, because "
                    "Dell keeps a record of which equipment belongs to which "
                    "customer site. Nothing has been measured yet, so there is "
                    "no health score to show. The real product draws a grey dash "
                    "in the score circle at this point, and so does this twin. A dash is an "
                    "honest answer: it says nothing is known yet, which is very "
                    "different from saying everything is fine."
                ),
                standard=(
                    "An administrator onboards a new storage array: CloudIQ is "
                    "enabled on the array, and the portal lists the system "
                    "without ever having heard from it — its Connectivity view "
                    "has an Install Base Issues category, so it works from Dell's "
                    "record of what is installed at the site. No "
                    "telemetry has arrived, so no Health Score has "
                    "been calculated — the real product draws a grey dash in the "
                    "score circle, and the twin's counter reads the same. A dash "
                    "claims nothing, which is the point."
                ),
                expert=(
                    "Array onboarded; listed from Dell's install-base record, zero "
                    "telemetry received. No Health Score computed — grey dash, per "
                    "the product. Absence of a score is not a score."
                ),
            ),
            active_regions=["src-storage", "insight"],
            progress_percent=0,
            health_score=0,
            score_state="no-data",
            data_points=0,
            elapsed_seconds=0,
        ),
        PipelineState(
            step=1,
            phase="handshake",
            label="Gateway connection test passes",
            description=L(
                novice=(
                    "The Secure Connect Gateway — the small on-site server that "
                    "carries messages from Dell equipment out to Dell — runs its "
                    "connection test, and the test passes. The gateway's own "
                    "screen says it is connected. This is true, and it is also "
                    "the trap: the test proves the gateway can reach Dell's "
                    "connectivity servers. It does not prove that the array's "
                    "measurements can get out as well. Dell's connection uses "
                    "more than one door, and the test tried only one. Exactly "
                    "which door is shut in this story is illustrative."
                ),
                standard=(
                    "The Secure Connect Gateway runs its connection test and "
                    "passes: outbound TLS on port 443 to Dell's connectivity "
                    "servers works, and the gateway reports itself connected. "
                    "That status is true and narrower than it sounds. Dell's "
                    "remote connectivity uses more than one port and destination "
                    "(the CloudIQ white paper names 443 and 8443), and the "
                    "company's outbound proxy (the server all internet-bound "
                    "traffic must pass through) allows the one the test used and "
                    "not the one the upload needs. Which destination is refused "
                    "here is illustrative."
                ),
                expert=(
                    "SCG connectivity test green: control channel on TLS/443 "
                    "up. Connectivity spans more than one port and destination "
                    "(443 and 8443 per H15691); the egress allowlist covers the "
                    "tested one only. Refused destination illustrative. "
                    "'Connected' here is the gateway's claim, not CloudIQ's."
                ),
            ),
            active_regions=["gateway"],
            progress_percent=10,
            health_score=0,
            score_state="no-data",
            minutes_without_data=1,
            data_points=0,
            elapsed_seconds=60,
        ),
        PipelineState(
            step=2,
            phase="collect",
            label="The array collects its first batch",
            description=L(
                novice=(
                    "On schedule, the array gathers its first set of "
                    "measurements about itself: how healthy it is, how full, how "
                    "fast, and how it is set up. This part works perfectly, "
                    "because it happens entirely inside the array. The batch is "
                    "now waiting to be sent. The numbers in this trace are "
                    "illustrative, not measured."
                ),
                standard=(
                    "On its normal interval the array gathers its first batch of "
                    "telemetry — health, capacity, performance counters, "
                    "configuration. Collection is local to the array and works. "
                    "The batch is queued for upload; the backlog counter starts "
                    "here. Interval and batch size are illustrative."
                ),
                expert=(
                    "First scheduled collection succeeds locally; batch queued "
                    "for upload. Backlog ledger starts. Interval and volume "
                    "illustrative."
                ),
            ),
            active_regions=["src-storage"],
            progress_percent=20,
            health_score=0,
            score_state="no-data",
            minutes_without_data=t_collect // 60,
            data_points=0,
            backlog_points=_collected(t_collect),
            elapsed_seconds=t_collect,
        ),
        PipelineState(
            step=3,
            phase="blocked",
            label="The upload is refused at the proxy",
            description=L(
                novice=(
                    "The batch tries to leave the building and is turned back. "
                    "The company's proxy — the checkpoint all outgoing internet "
                    "traffic passes through — has no rule allowing connections "
                    "to the address Dell receives measurements on, so it refuses "
                    "this one. Nothing is damaged and nothing has leaked; the "
                    "data simply stays where it was. Nobody is told, either: a "
                    "refused upload writes a line in a log file on the customer's "
                    "side, and Dell's cloud cannot see a message that never "
                    "arrived."
                ),
                standard=(
                    "The upload leaves the array, reaches the outbound proxy, "
                    "and is refused: there is no allow rule for the destination "
                    "the upload needs. Dell's own troubleshooting lists "
                    "this family of causes — a blocked outbound port, a "
                    "misconfigured proxy, wrong DNS, or collection switched off "
                    "on the array. Nothing is lost or exposed; the batch stays "
                    "queued. The failure is recorded only in customer-side logs, "
                    "because the cloud cannot observe a request it never received."
                ),
                expert=(
                    "Egress proxy denies the upload's destination — no "
                    "allowlist entry. Same class as blocked 443, bad proxy, bad "
                    "DNS, or collection disabled (Dell KB 000181685). Batch "
                    "stays queued; evidence exists only in local logs."
                ),
            ),
            active_regions=["src-storage", "gateway"],
            failed_regions=["gateway"],
            progress_percent=30,
            health_score=0,
            score_state="no-data",
            minutes_without_data=t_blocked // 60,
            data_points=0,
            backlog_points=_collected(t_blocked),
            elapsed_seconds=t_blocked,
        ),
        PipelineState(
            step=4,
            phase="starved",
            label="Intervals pass; the cloud receives nothing",
            description=L(
                novice=(
                    "More collection cycles go by. Each time the array gathers "
                    "a fresh batch, tries to send it, and is refused again. In "
                    "Dell's cloud, the part that receives measurements has "
                    "nothing from this array at all. The analysis stage does not "
                    "run for it, because there is nothing to analyze — and it "
                    "does not guess. On the portal the array still shows a grey "
                    "dash where a health score would be."
                ),
                standard=(
                    "Further intervals pass and every upload is refused. Cloud "
                    "ingest has received nothing from this array, so the ML "
                    "engine has nothing to score and does not run for it — no "
                    "baseline is assumed and no score is inferred. The portal "
                    "still shows a grey dash, and the array has no Last Contact "
                    "Time, the field that records when CloudIQ last received "
                    "data. The backlog on the customer side keeps growing."
                ),
                expert=(
                    "Repeated refusals; ingest has zero records for the system. "
                    "Analytics does not run on an empty input and nothing is "
                    "inferred. Grey dash, no Last Contact Time, backlog "
                    "growing."
                ),
            ),
            active_regions=["src-storage", "gateway", "ingest"],
            failed_regions=["gateway", "ingest"],
            progress_percent=30,
            health_score=0,
            score_state="no-data",
            minutes_without_data=t_starved // 60,
            data_points=0,
            backlog_points=_collected(t_starved),
            elapsed_seconds=t_starved,
        ),
        PipelineState(
            step=5,
            phase="stale",
            label="The portal lists the array as not sending data",
            description=L(
                novice=(
                    "For the first hour, a grey dash means nothing: Dell says a "
                    "newly added system can take up to an hour to show data. "
                    "After that, the dash is a symptom. The portal's Connectivity "
                    "view sorts every system by whether data is arriving, and "
                    "this array is not under Connected. The cloud did not work "
                    "this out by listening to the silence. It knows the array "
                    "exists from Dell's customer records and has simply never "
                    "received anything from it. No alert goes out to anyone in this "
                    "trace; someone has to look. This is the longest step, and the "
                    "most important behaviour in it: the product never shows a "
                    "green score for a system it has not heard from."
                ),
                standard=(
                    "Dell tells owners of a newly enabled system to expect about "
                    "an hour before data shows, so only now can the grey dash be "
                    "read as a fault, which is why this is the longest stage. The "
                    "portal's Connectivity view lists the array outside "
                    "Connected: CloudIQ defines Connected as successfully sending "
                    "data, a stricter claim than the gateway's. Dell's other "
                    "category for a system that has never delivered is Not Set "
                    "Up — not set up to send data through the gateway — which is "
                    "where this one belongs; a system that had been sending and "
                    "went quiet would move to Lost Connection and show a grey "
                    "number, meaning uncertain. Green is never drawn on no data. "
                    "The listing is passive in this trace, so someone has to "
                    "look. The two-hour mark is illustrative."
                ),
                expert=(
                    "Max dwell: past the roughly one-hour onboarding allowance "
                    "the dash is a fault. Connectivity view: never-delivered "
                    "systems fall under Not Set Up; previously-sending ones go to "
                    "Lost Connection with a grey number. 'Connected' means data "
                    "arriving. Never green on no data. Passive listing; timing "
                    "illustrative."
                ),
            ),
            active_regions=["insight"],
            failed_regions=["gateway", "ingest"],
            progress_percent=30,
            health_score=0,
            score_state="no-data",
            minutes_without_data=t_stale // 60,
            data_points=0,
            backlog_points=_collected(t_stale),
            elapsed_seconds=t_stale,
            cycle_cost=4,
        ),
        PipelineState(
            step=6,
            phase="repair",
            label="The administrator unblocks the upload",
            description=L(
                novice=(
                    "An administrator sees the flag and investigates from "
                    "inside the company network, because that is the only place "
                    "the fix can be made. Following Dell's troubleshooting steps, "
                    "they confirm collection is switched on at the array, test "
                    "whether Dell's receiving address can be reached on port 443 "
                    "(the numbered channel that secure web traffic uses), find that the proxy is refusing it, and add a rule to allow "
                    "it. Dell's cloud took no part in this. It cannot reach into "
                    "the customer's network, and that is by design."
                ),
                standard=(
                    "The administrator works the problem from the customer "
                    "side, the only side it can be fixed from. Dell's "
                    "troubleshooting order: confirm SupportAssist (the array's "
                    "built-in connectivity client) and CloudIQ collection are "
                    "enabled on the array, check DNS, then test the telemetry "
                    "endpoint on outbound 443. The test fails at the proxy; an "
                    "allow rule is added. The cloud did nothing here — it has no "
                    "inbound path into the estate, by design."
                ),
                expert=(
                    "Customer-side fix: verify SupportAssist and collection "
                    "enabled, DNS, then outbound 443 to the telemetry endpoint; "
                    "proxy allow rule added. No cloud-side action is possible — "
                    "no inbound path exists."
                ),
            ),
            active_regions=["src-storage", "gateway"],
            progress_percent=45,
            health_score=0,
            score_state="no-data",
            minutes_without_data=t_repair // 60,
            data_points=0,
            backlog_points=_collected(t_repair),
            elapsed_seconds=t_repair,
            cycle_cost=2,
        ),
        PipelineState(
            step=7,
            phase="backfill",
            label="The waiting telemetry flows",
            description=L(
                novice=(
                    "With the rule in place, the next upload goes through, and "
                    "the batches that were waiting follow it. They travel the "
                    "same way telemetry always travels: outward, started from "
                    "the customer's side. Dell's cloud receives and files them. "
                    "One honest caveat: this twin shows every waiting batch "
                    "arriving, which keeps the arithmetic easy to follow. How "
                    "much a real system keeps while it cannot send varies by "
                    "product, and after a long block the real charts can show a "
                    "gap."
                ),
                standard=(
                    "The next scheduled upload succeeds and the queued telemetry "
                    "follows it through the gateway — outbound-initiated, one "
                    "way, exactly as on a healthy day. Cloud ingest parses and "
                    "lands it; the array now has a Last Contact Time. The full "
                    "backfill is illustrative: how much a system or gateway "
                    "retains while egress is blocked varies by product, and a "
                    "long outage can leave a gap in the history."
                ),
                expert=(
                    "Upload succeeds; queue drains outbound-initiated through "
                    "SCG; ingest lands it; Last Contact Time set. Full backfill "
                    "is illustrative — real retention varies and long outages "
                    "leave gaps."
                ),
            ),
            active_regions=["src-storage", "gateway", "ingest"],
            progress_percent=65,
            health_score=0,
            score_state="no-data",
            minutes_without_data=0,
            data_points=delivered,
            backlog_points=0,
            elapsed_seconds=t_backfill,
        ),
        PipelineState(
            step=8,
            phase="analyze",
            label="ML engine scores the array for the first time",
            description=L(
                novice=(
                    "Now that real measurements exist, the machine-learning "
                    "stage runs on them for the first time. It works out the "
                    "array's health score and starts learning what normal looks "
                    "like for this machine. The score readout stays grey until "
                    "this pass finishes, because a score is only shown once it "
                    "has been calculated from data that actually arrived."
                ),
                standard=(
                    "With delivered telemetry in the data lake, the ML engine "
                    "runs against this array for the first time: a Health Score "
                    "is computed and baselines begin to form. The readout stays "
                    "grey until the pass completes — a score is shown only once "
                    "it has been calculated from data that arrived."
                ),
                expert=(
                    "First analytics pass over delivered data: Health Score "
                    "computed, baselines seeded. Readout grey until the pass "
                    "completes."
                ),
            ),
            active_regions=["analytics", "ingest"],
            progress_percent=85,
            health_score=0,
            score_state="no-data",
            minutes_without_data=0,
            data_points=delivered,
            backlog_points=0,
            elapsed_seconds=9400,
            cycle_cost=3,
        ),
        PipelineState(
            step=9,
            phase="resume",
            label="A real Health Score appears",
            description=L(
                novice=(
                    "The array's first real health score appears in the portal, "
                    "in colour, and the Connectivity view now lists the array as "
                    "connected — this time meaning that data is arriving. From "
                    "here the array follows the healthy pipeline like every "
                    "other system. The lesson of the whole trace is in what did "
                    "not happen: at no point did the platform show a good score "
                    "for a system it knew nothing about."
                ),
                standard=(
                    "The first real Health Score surfaces in the app, in colour, "
                    "and the Connectivity view lists the array as Connected — "
                    "now in CloudIQ's sense, data arriving. From here the array "
                    "follows the healthy pipeline. What the trace shows is what "
                    "never happened: no insight and no green score was produced "
                    "for a system the cloud had not heard from. The score value "
                    "is illustrative."
                ),
                expert=(
                    "First computed Health Score surfaces; system Connected in "
                    "CloudIQ's sense. Joins the healthy pipeline. No insight and "
                    "no green score was ever produced on no data. Value "
                    "illustrative."
                ),
            ),
            active_regions=["insight"],
            progress_percent=100,
            health_score=100,
            score_state="fresh",
            minutes_without_data=0,
            data_points=delivered,
            backlog_points=0,
            elapsed_seconds=9500,
        ),
    ]
