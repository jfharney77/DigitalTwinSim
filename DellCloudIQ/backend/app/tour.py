"""The narrated tour of CloudIQ / Dell AIOps — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
follow one batch of telemetry left to right across the platform diagram, from
the monitored estate through the Secure Connect Gateway and cloud ingest into
the ML core, where the Health Score dips, and out again as an insight, an
assistant's explanation and a notification. The frontend player owns the
clock; nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

There is no box to open, so the layers are not a chassis being peeled. They
run from the edges of the diagram to its core:

    0  the ends: the monitored estate you own, and the tools insights reach
    1  the cloud service you see: gateway, ingest, the app, the assistant
    2  the analysis core: the ML analytics and cybersecurity engines

The signature beat is ``analyze-dip``: the trace step where a risk crosses a
threshold and the Health Score first drops below 100. Every claim the scripts
make is one ``engine.py`` and ``anatomy.py`` already make; each beat pins the
trace step whose description says the same thing.
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import PlatformMap

#: The step the tests pin: the twin's one idea lives here.
SIGNATURE_STEP_ID = "analyze-dip"

_ENDS = 0
_SERVICE = 1
_CORE = 2


def layer_map(anatomy: PlatformMap) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    by_kind = {
        "source": _ENDS,
        "action": _ENDS,
        "gateway": _SERVICE,
        "ingest": _SERVICE,
        "insight": _SERVICE,
        "assistant": _SERVICE,
        "analytics": _CORE,
        "security": _CORE,
    }
    return {r.id: by_kind.get(r.kind, _ENDS) for r in anatomy.regions}


def build_tour(anatomy: PlatformMap) -> Tour:
    """The CloudIQ tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    sources = [r.id for r in anatomy.regions if r.kind == "source"]

    steps = [
        TourStep(
            id="the-estate",
            title="No box, just an estate",
            script=L(
                novice=(
                    "Most of the Dell products in this collection are machines you "
                    "could put your hand on. CloudIQ, now also called Dell AIOps "
                    "(AIOps is short for artificial intelligence for IT "
                    "operations), is not. It is software that runs as a service in "
                    "Dell's cloud, "
                    "so instead of a floorplan this picture is a journey, read from "
                    "left to right. On the left is the estate: the Dell equipment a "
                    "company owns, such as storage arrays, servers, network "
                    "switches and backup appliances. Right now everything is "
                    "healthy. Every health score reads 100 out of 100, and the "
                    "service is quietly waiting for the next batch of "
                    "measurements. Watching like this, so that nobody has to, is "
                    "where it earns its keep."
                ),
                standard=(
                    "CloudIQ, renamed Dell AIOps (AI for IT operations) in 2025, has no "
                    "chassis: it is a cloud-native SaaS (software as a service), so "
                    "this map is an "
                    "architecture diagram that reads left to right. On the left is "
                    "the monitored estate: storage such as PowerStore and "
                    "PowerMax, PowerEdge servers and VxRail clusters, PowerSwitch "
                    "networking, and PowerProtect data protection, several of "
                    "which have their own twins here. Everything is connected and "
                    "nominal. Health Scores sit at 100, and the platform waits for "
                    "the next telemetry cycle."
                ),
                expert=(
                    "Cloud-native AIOps, no chassis: a left-to-right pipeline. "
                    "Estate of storage, compute/HCI, networking, data protection. "
                    "Nominal, Health Scores 100, idle between cycles."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=sources,
            layer_reveal=_ENDS,
            trace_cursor=0,
            duration_ms=28_000,
        ),
        TourStep(
            id="one-way-gateway",
            title="Out through a one-way door",
            script=L(
                novice=(
                    "On their normal schedule the machines have gathered "
                    "measurements about themselves, called telemetry: how healthy "
                    "they are, how full, how fast, how they are set up, and what "
                    "their logs say. Storage and servers do this with software "
                    "built into them; switches and virtualization use a small "
                    "read-only virtual machine installed on site. Now the Secure "
                    "Connect Gateway bundles it all up and sends it to Dell's "
                    "cloud over an encrypted connection. The key detail is the "
                    "direction. The gateway only ever calls out. Dell's cloud has "
                    "no way to open a connection into the company's network, and that is "
                    "why security teams accept it."
                ),
                standard=(
                    "The systems have already collected their telemetry: health, "
                    "capacity, performance counters, configuration and logs, "
                    "by one of three routes. Storage arrays and most servers use "
                    "SupportAssist, the connectivity client built into the system "
                    "itself. Servers managed as a fleet use the AIOps plugin for "
                    "OpenManage Enterprise, Dell's server-management console. "
                    "Switches and virtualization, which have no client of their "
                    "own, use the AIOps Collector, a read-only virtual machine on "
                    "site. Now the Secure Connect Gateway batches it "
                    "and opens an encrypted TLS (Transport Layer Security) "
                    "connection outbound to Dell's cloud on port 443. The link is "
                    "always opened from inside and the telemetry travels one way: "
                    "Dell's cloud can never open a connection into your "
                    "network, which is what makes the model acceptable to "
                    "security teams."
                ),
                expert=(
                    "Collection done (embedded agents, read-only Collector VM). "
                    "SCG batches and egresses TLS/443, outbound-initiated. No "
                    "inbound-initiated path from cloud to estate."
                ),
            ),
            camera=frame("src-compute", "src-network", "gateway", pad=3.0),
            region_ids=["gateway"],
            layer_reveal=_SERVICE,
            trace_cursor=2,
            duration_ms=28_000,
        ),
        TourStep(
            id="cloud-ingest",
            title="One common model in the data lake",
            script=L(
                novice=(
                    "In Dell's cloud the measurements arrive and are translated "
                    "into one common format, whatever machine they came from. "
                    "They are then stored in a data lake, a very large store of "
                    "raw data, next to this estate's own history and anonymized "
                    "signals from Dell's whole installed base. Using one format is "
                    "what lets a single health score cover storage, servers and "
                    "networking together. Having the whole fleet's history is "
                    "what gives the models a sense of what normal looks like."
                ),
                standard=(
                    "In the cloud, the telemetry is parsed and normalized into a "
                    "common model, then landed in a data lake beside history and "
                    "the anonymized signals of Dell's whole installed base. "
                    "Normalizing across products is what lets one Health Score "
                    "span storage, servers and networking, and the fleet-wide "
                    "history is the baseline the anomaly models compare against. "
                    "The data-point counter jumps here; its values are "
                    "illustrative."
                ),
                expert=(
                    "Ingest: parse, normalize to a common model, land in the data "
                    "lake with history and anonymized fleet signal. Enables a "
                    "cross-product Health Score and a fleet baseline."
                ),
            ),
            camera=frame("gateway", "ingest", pad=4.0),
            region_ids=["ingest"],
            layer_reveal=_SERVICE,
            trace_cursor=3,
            duration_ms=26_000,
        ),
        TourStep(
            id="ml-analyze",
            title="The heaviest stage",
            script=L(
                novice=(
                    "Now the core of the diagram opens up. This is the "
                    "machine-learning engine, and it is the slowest, heaviest step "
                    "in the whole journey, so the timeline lingers here. It "
                    "recalculates every system's health score, compares live "
                    "performance with what it has learned is normal, checks "
                    "whether one workload is stealing performance from another, "
                    "which people call a noisy neighbour, and predicts when "
                    "storage will fill up. It judges your equipment against how "
                    "similar equipment behaves across the whole fleet, not against "
                    "a fixed rule."
                ),
                standard=(
                    "Peeling to the core: the ML analytics engine, the longest "
                    "stage in the trace, which is why playback dwells here. It "
                    "recomputes each system's Health Score (a 0 to 100 roll-up of "
                    "configuration, capacity, performance and component issues), "
                    "compares live performance against learned baselines, checks "
                    "for workload contention (a noisy neighbor), and forecasts "
                    "capacity. It reads from the fleet-wide data lake, so behavior "
                    "is judged against similar systems rather than a static rule."
                ),
                expert=(
                    "Core, max dwell: Health Score recomputation, baseline anomaly "
                    "detection, contention analysis, capacity forecast, all "
                    "against the fleet-trained baseline."
                ),
            ),
            camera=frame("ingest", "analytics", pad=3.0),
            region_ids=["analytics", "ingest"],
            layer_reveal=_CORE,
            trace_cursor=4,
            duration_ms=30_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="The score dips before anyone complains",
            script=L(
                novice=(
                    "This is the moment the whole platform exists for. The models "
                    "find three things at once. A storage pool is answering more "
                    "slowly than it normally does. At the current rate that pool "
                    "will be full in about ten weeks. And a security setting has "
                    "drifted away from the approved baseline, which the separate "
                    "cybersecurity engine catches. The affected system's health "
                    "score drops, from 100 to 71 in this illustrative run, with "
                    "more serious problems counting for more. Nothing has broken "
                    "yet, and no user has noticed anything. Old-style monitoring "
                    "would still be waiting for someone to call and complain. "
                    "Here the problem has been found before anyone feels it."
                ),
                standard=(
                    "This is the twin's one idea. The models flag a latency "
                    "anomaly on a storage pool, a capacity forecast of full in "
                    "about ten weeks, and, from the cybersecurity engine, a "
                    "configuration that has drifted from the security baseline. "
                    "The affected system's Health Score drops, weighted by "
                    "severity: 100 to 71 in this illustrative run, and never "
                    "before detection. Reactive monitoring would have waited for "
                    "a user complaint. AIOps has the risk before the impact is "
                    "felt."
                ),
                expert=(
                    "Signature: detections cross threshold (latency anomaly, "
                    "~10-week capacity forecast, security baseline drift). Health "
                    "Score 100 to 71, illustrative, severity-weighted, never "
                    "before detect. Ahead of impact."
                ),
            ),
            # Both engines run the full height of the map, so any box that
            # contains them is the whole map: this beat cannot zoom, and it
            # focuses by peeling layers 0 and 1 instead (ghosted around the
            # lit core). The same holds for the assistant beat's column.
            camera=frame("analytics", "security", pad=2.0),
            region_ids=["analytics", "security"],
            layer_reveal=_CORE,
            trace_cursor=5,
            duration_ms=42_000,
        ),
        TourStep(
            id="insight-surfaces",
            title="Where a person meets the platform",
            script=L(
                novice=(
                    "The findings now appear in the CloudIQ application, in a web "
                    "browser and on a phone. The operator sees the lowered health "
                    "score with a note explaining the problem, a forecast on the "
                    "dashboard showing when the pool fills, a view naming the "
                    "workload causing the slowdown, and a security alert. Reports "
                    "update too, so a manager sees the summary without digging "
                    "through the detail. Notice that information only ever moved "
                    "one way to get here: out of the building first, and only "
                    "then into the app."
                ),
                standard=(
                    "The findings surface in the CloudIQ / Dell AIOps app, in the "
                    "browser and on mobile: a lowered Health Score with a "
                    "proactive health issue, a capacity forecast, a "
                    "performance-impact view naming the contending workload, and "
                    "a cybersecurity alert. Dashboards serve the operator and "
                    "reports serve the manager. Telemetry left the data center "
                    "before any insight appeared, and the twin's tests assert "
                    "that order."
                ),
                expert=(
                    "Surfaced in app, browser and mobile: decremented score with "
                    "proactive issue, forecast, contention attribution, security "
                    "alert. Transmit precedes surface, asserted."
                ),
            ),
            camera=frame("analytics", "insight", pad=3.0),
            region_ids=["insight"],
            layer_reveal=_CORE,
            trace_cursor=6,
            duration_ms=26_000,
        ),
        TourStep(
            id="assistant-explains",
            title="A number becomes a next step",
            script=L(
                novice=(
                    "Next the AIOps Assistant, a generative AI that answers "
                    "questions in ordinary language, explains what happened. Ask "
                    "it why the score dropped and it answers from two places at "
                    "once: Dell's support knowledge, which Dell puts at more than "
                    "133,000 support articles and manuals, and the real current state of "
                    "this particular estate. Its answer names the pool, the likely "
                    "cause, and what to do about it. A number on a dashboard "
                    "turns into an instruction, and nobody had to open a support "
                    "case to get it."
                ),
                standard=(
                    "The AIOps Assistant, a generative-AI assistant, puts the "
                    "finding in plain language. Asked why the score dropped, it "
                    "answers from both Dell's support knowledge (133,000+ "
                    "articles, Dell's figure) and this environment's actual "
                    "state, which Dell calls Infrastructure Context Awareness. "
                    "The answer names the pool, the likely cause and the "
                    "recommended remediation, turning a dashboard reading into a "
                    "next step without a support case."
                ),
                expert=(
                    "Assistant: grounded in the support corpus (133k+, Dell's "
                    "figure) plus live state via Infrastructure Context "
                    "Awareness. Pool, probable cause, remediation; no case opened."
                ),
            ),
            camera=frame("insight", "assistant", pad=2.0),
            region_ids=["assistant", "insight"],
            layer_reveal=_CORE,
            trace_cursor=7,
            duration_ms=26_000,
        ),
        TourStep(
            id="notify-close-loop",
            title="The loop closes, one way",
            script=L(
                novice=(
                    "Finally the insight leaves the platform. An email and a phone "
                    "alert go out, a ticket opens automatically in the company's "
                    "service-management system, and an automated process is "
                    "triggered, all through the connections that link this "
                    "service to the tools teams already use. None of that fixes "
                    "anything, and the health score is still 71. People then do "
                    "the repair with their own tools. The score is worked out "
                    "again only when a later batch of measurements arrives, about "
                    "an hour on in this illustrative run, and it reads 88. That "
                    "is why the whole path is lit again here: the later batch is "
                    "a second trip through it, collected, sent, taken in and "
                    "scored. The score is "
                    "not back to 100, and that is honest: one of the three "
                    "problems, the storage filling up, is still open. Stepping back to the whole picture, the "
                    "data travelled one way, from the machines on the left to "
                    "action on the right, and never the reverse."
                ),
                standard=(
                    "The insight leaves CloudIQ: email and mobile alerts, a "
                    "ServiceNow ticket over the ITSM (IT service management) "
                    "integration, and a webhook driving an automation, all over "
                    "the REST API. A ticket does not move the score; it is still "
                    "71. The team fixes the estate with its own tools, and the "
                    "Health Score is recomputed from a later collection, about an "
                    "hour on in this illustrative run: 88, above its low-water "
                    "mark but not 100, because the capacity forecast is still "
                    "open. The whole path lights again for it — that recovery is "
                    "a second cycle, not a ticket. The whole trip ran one way, from telemetry "
                    "on the left to action on the right. The Cyber Detect twin "
                    "points here for getting its verdict to a person, and the "
                    "NativeEdge twin for the watching half of an edge estate."
                ),
                expert=(
                    "Egress: notification, ITSM ticket, webhook automation over "
                    "REST; score still 71. Remediation out of band; next "
                    "post-fix collection (~1 h, illustrative) recomputes to 88, "
                    "above low-water and below 100. One-way flow, end to end."
                ),
            ),
            camera=whole_map(anatomy),
            # The closing beat lights the whole path, not just the outbound
            # edge: the recovery to 88 comes from a *later* collection, so the
            # picture has to show a second cycle running rather than a ticket
            # that fixed something. This is the one beat whose lit regions sit
            # left of the previous beat's, and it is why the loop closes.
            region_ids=[
                *sources, "gateway", "ingest", "analytics", "insight", "action",
            ],
            layer_reveal=_ENDS,
            trace_cursor=8,
            duration_ms=28_000,
        ),
    ]

    return Tour(
        id="cloudiq-tour",
        title="One batch of telemetry, start to finish",
        intro=L(
            novice=(
                "A guided walk that follows one batch of measurements from the "
                "equipment it describes to the person who acts on it, narrated "
                "beat by beat. Sit back and watch, or pause and click any block "
                "to look closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk that follows one batch of telemetry through the "
                "platform. Watch it play, or pause and explore; Resume tour "
                "brings the camera back."
            ),
            expert="Narrated telemetry-to-action walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: PlatformMap) -> TourResponse:
    """The ``GET /api/tour`` payload: the tour plus the layer map and bounds."""
    return TourResponse(
        tour=build_tour(anatomy),
        layers=layer_map(anatomy),
        map_width=anatomy.width,
        map_height=anatomy.height,
    )


# Built once at import, like ANATOMY: importing the module registers the
# narration's reading-level variants, which tests/test_leveling.py relies on.
from .anatomy import ANATOMY  # noqa: E402  (after the builders it feeds)

TOUR_RESPONSE = build_response(ANATOMY)
