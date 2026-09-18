"""The narrated tour of one NativeEdge site's onboarding — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: eight beats that
move a camera across the platform map, peel it from the estate (the sites and
the WAN) to the trust gate and the Orchestrator and then to the control plane
behind it, pin the onboarding trace at the moments that carry the story, and
narrate each one. The frontend player owns the clock; nothing here knows about
time, IO or the web (AST-checked in ``tests/test_tour.py``, the same rule as
``engine.py``).

The signature beat is ``zero-touch``: the trace step where someone plugs in
power and a network cable, ``operator_actions`` reaches 1, and — per
``tests/test_engine.py::test_exactly_one_human_action`` — never moves again.
Every claim the scripts make is one the engine and the anatomy already make;
the trace index each beat pins is the step whose description says the same
thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``PlatformMap`` is unchanged:

    0  the estate: the edge endpoints at the sites, and the WAN they share
    1  the trust gate and the brain: secure onboarding, the Orchestrator
    2  the control plane behind it: blueprints, catalog, policy, observability
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

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "zero-touch"

_ESTATE = 0
_GATE = 1
_CONTROL = 2

_ENDPOINTS = ["endpoint-e1", "endpoint-e2", "endpoint-e3", "endpoint-e4"]

#: The control plane close-up: blueprints, catalog, policy and observability
#: whole, with the top of the Orchestrator, starting right of the
#: secure-onboarding block so nothing on the estate side is cut mid-label.
#: (A frame built around the Orchestrator's full height had to be nearly the
#: whole map wide, and sliced the edge sites through their names.)
_CONTROL_PLANE = CameraTarget(x=41, y=0, w=59, h=34.3)


def layer_map(anatomy: PlatformMap) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    by_kind = {
        "endpoint": _ESTATE,
        "network": _ESTATE,
        "identity": _GATE,
        "orchestrator": _GATE,
    }
    return {r.id: by_kind.get(r.kind, _CONTROL) for r in anatomy.regions}


def build_tour(anatomy: PlatformMap) -> Tour:
    """The NativeEdge tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="sealed-crate",
            title="A sealed crate at a site with no IT staff",
            script=L(
                novice=(
                    "This map is one company's edge estate: small computers that "
                    "live out where the work happens, at a shop, a factory line, an "
                    "electrical substation, a garage at a race track. On the left "
                    "are four sites, drawn identical on purpose, because an estate "
                    "is one building block repeated. None of these places has "
                    "anyone from IT. A sealed crate has just arrived at each one, "
                    "holding a computer exactly as Dell's factory built it, with "
                    "its identity built in and nothing set up for this site. Watch "
                    "the operator actions counter, which counts things a person "
                    "has to do. It reads zero now."
                ),
                standard=(
                    "This is Dell NativeEdge, edge operations software, drawn as a "
                    "map: the estate on the left, the control side on the right. "
                    "Four identical edge sites stand for hundreds, a branch, a "
                    "factory line, a substation, a trackside garage, and none of "
                    "them has IT staff. A sealed crate has arrived at each, holding "
                    "an edge device exactly as Dell's factory built it: signed "
                    "firmware, an identity burned in at manufacture, nothing "
                    "configured for this site. Operator actions reads zero."
                ),
                expert=(
                    "NativeEdge estate map: four identical sites left, control "
                    "plane right. Crated devices, factory identity, signed "
                    "firmware, unconfigured. No site IT. operatorActions = 0."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=list(_ENDPOINTS),
            layer_reveal=_ESTATE,
            trace_cursor=0,
            duration_ms=28_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Power and a network cable, and nothing else",
            script=L(
                novice=(
                    "This is the most important moment in the tour. Someone at the "
                    "site, a shop manager whose job is not computers, follows a "
                    "one-line instruction: plug in the power lead and the network "
                    "cable. The operator actions counter goes from zero to one, and "
                    "that is the last time it ever moves, because this is the last "
                    "thing any person does in the whole story. Nobody connects a "
                    "laptop, types a password or logs in. Instead the device starts "
                    "up and reaches out across the wide-area network, the WAN, "
                    "toward the central Orchestrator, the software that runs the "
                    "estate. The device asks to be claimed rather than waiting to "
                    "be set up. Every other hardware twin in this collection has a "
                    "person at the key moment. This one takes the person out, and "
                    "that is the only version that works at hundreds of sites."
                ),
                standard=(
                    "The whole idea in one step. Someone on site plugs in power "
                    "and the network cable, and the operator-actions counter ticks from "
                    "zero to one. It never moves again: this is the last thing any "
                    "human does. The device boots the firmware Dell signed, finds "
                    "the WAN (wide-area network), and reaches out to the "
                    "Orchestrator. Nothing is pushed at it, no laptop is attached, "
                    "nobody logs in locally. The device asks to be claimed instead "
                    "of waiting to be configured, and that inversion is what "
                    "survives multiplication by hundreds of sites."
                ),
                expert=(
                    "The only human action: power + network cable; "
                    "operatorActions 0 -> 1, frozen thereafter. Device boots "
                    "signed firmware, dials out to the Orchestrator. No local "
                    "login, no push."
                ),
            ),
            camera=frame(*_ENDPOINTS, "network", pad=2.0),
            region_ids=[*_ENDPOINTS, "network"],
            layer_reveal=_GATE,
            trace_cursor=1,
            duration_ms=40_000,
        ),
        TourStep(
            id="attestation",
            title="Proving it is the machine Dell built",
            script=L(
                novice=(
                    "Now the slowest part, and it is slow on purpose. The device "
                    "shows the secure onboarding service its identity, a "
                    "certificate made at the factory, along with measurements of "
                    "the hardware and firmware it started up with. The service "
                    "checks those against what Dell actually built and shipped. "
                    "This check is called attestation. "
                    "Until it passes, the device is just an unknown computer that "
                    "plugged itself into the network, and it gets nothing at all: "
                    "no software, no passwords, no place in the estate. The iDRAC "
                    "twin tells the same trust story from inside a single server."
                ),
                standard=(
                    "Attestation, the longest stage in the trace, deliberately. "
                    "The device presents its factory-issued cryptographic identity "
                    "and measurements of its own boot chain to the secure-"
                    "onboarding service, which checks them against what Dell "
                    "manufactured: the hardware root-of-trust story the iDRAC twin "
                    "tells inside one server. Until the proof completes, this is an "
                    "unknown machine on the network and receives nothing. "
                    "Zero-touch without attestation is just an unauthenticated "
                    "machine joining politely."
                ),
                expert=(
                    "Attestation, max cycleCost: factory identity plus measured "
                    "boot chain verified against manufacture. Nothing delivered "
                    "before trust. Cf. iDRAC root of trust."
                ),
            ),
            # Close on the gate: the WAN the proof travels over, the
            # secure-onboarding block, and the Orchestrator it is trying to
            # join. The box sits in the empty columns between the sites
            # (x <= 14) and the control plane (x >= 66), so no block is
            # sliced through its label; the sites were the previous beat.
            camera=CameraTarget(x=17, y=14, w=46, h=26.8),
            region_ids=[*_ENDPOINTS, "network", "identity"],
            layer_reveal=_GATE,
            trace_cursor=2,
            duration_ms=34_000,
        ),
        TourStep(
            id="claimed",
            title="Claimed as a set",
            script=L(
                novice=(
                    "The proof passes, and from here to the end the device is "
                    "trusted; that trust is never taken back. The Orchestrator, the "
                    "big block in the middle, now claims the devices into the "
                    "estate. They appear on its list, tied to this site. The "
                    "endpoints online counter jumps from zero to four in one step, "
                    "because a whole site is claimed together, not one box at a "
                    "time. Notice two things. The Orchestrator is not in that "
                    "count, because it does the claiming and is never claimed. And "
                    "operator actions still reads one: the machines did this "
                    "between themselves."
                ),
                standard=(
                    "The proof lands and trust is established, true from here to "
                    "the end and never revoked. The NativeEdge Orchestrator, the "
                    "biggest block because one control plane is the product, "
                    "claims the devices into inventory, bound to this site. "
                    "Endpoints online snaps from zero to four in one step: a site "
                    "is claimed as a set. The Orchestrator is not in that count, "
                    "since it is the claimer and never the claimed, and operator "
                    "actions still reads one."
                ),
                expert=(
                    "Trust established, monotone. Orchestrator claims the site; "
                    "endpointsOnline 0 -> 4 atomically, Orchestrator excluded. "
                    "operatorActions still 1."
                ),
            ),
            # The whole map: the four sites being counted and the Orchestrator
            # counting them both run nearly the map's full height, so any
            # tighter box sliced the sites through their names.
            camera=whole_map(anatomy),
            region_ids=[*_ENDPOINTS, "network", "identity", "orchestrator"],
            layer_reveal=_GATE,
            trace_cursor=3,
            duration_ms=28_000,
        ),
        TourStep(
            id="pulled-not-pushed",
            title="Pulled, never pushed",
            script=L(
                novice=(
                    "Next the operating system and the platform's own software "
                    "arrive on all four devices at once. Each device asks the "
                    "Orchestrator what it should run, downloads it over the WAN, "
                    "and checks it is genuine using the trust it just earned before "
                    "installing it. Nobody sends software to an address someone "
                    "typed, and there is no USB stick anywhere. Edge links are "
                    "assumed to be bad, so a device that loses its connection "
                    "halfway through simply carries on when the link comes back. "
                    "The VxRail twin's nodes start up together the same way."
                ),
                standard=(
                    "Operating systems and the platform runtime land on all four "
                    "endpoints in lockstep, the same beat as VxRail's nodes booting "
                    "together. Every byte is pulled: the device asks the "
                    "Orchestrator what to run, fetches it over the WAN, verifies "
                    "the signatures against the trust established at attestation, "
                    "and installs. No USB stick exists in this story, and a "
                    "download interrupted by a bad link resumes when the link "
                    "returns."
                ),
                expert=(
                    "OS + runtime provisioned in lockstep, pulled over the WAN, "
                    "signature-verified against attested trust. Resumable over "
                    "intermittent links. No USB."
                ),
            ),
            camera=frame(*_ENDPOINTS, "orchestrator", pad=2.0),
            region_ids=[*_ENDPOINTS, "network", "orchestrator"],
            layer_reveal=_GATE,
            trace_cursor=4,
            duration_ms=26_000,
        ),
        TourStep(
            id="blueprint",
            title="The destination, not the directions",
            script=L(
                novice=(
                    "Now the control side of the map opens up. The Orchestrator "
                    "applies this site's blueprint: a description, written once by "
                    "an engineer who will never visit, of what a site like this "
                    "should run, including its apps, settings, security rules and "
                    "update times. The blueprint says where to end up, not how to "
                    "get there. The Orchestrator works out the steps each site "
                    "needs, which is the only approach that copes with hundreds of "
                    "sites that are each a little different. Change the blueprint "
                    "next quarter, and every site moves to the new version with no "
                    "visits."
                ),
                standard=(
                    "The control plane opens up. The Orchestrator applies the "
                    "site's blueprint, a declarative description, written once by "
                    "an engineer who will never visit, of what a site of this class "
                    "runs: applications, configuration, policy, update windows. "
                    "Declarative means it states the destination, not the driving "
                    "directions; the Orchestrator computes the steps each site "
                    "needs. When the blueprint changes, the estate converges on the "
                    "new destination the same way, with no site visits."
                ),
                expert=(
                    "Declarative blueprint applied: apps, config, policy, update "
                    "windows. Orchestrator derives per-site steps; estate "
                    "reconverges on change. No visits."
                ),
            ),
            camera=_CONTROL_PLANE,
            region_ids=[*_ENDPOINTS, "orchestrator", "blueprint"],
            layer_reveal=_CONTROL,
            trace_cursor=5,
            duration_ms=26_000,
        ),
        TourStep(
            id="workload",
            title="The site starts doing its job",
            script=L(
                novice=(
                    "The apps arrive and start, taken from the application "
                    "catalog, which works like an app store for the estate: "
                    "software packaged by Dell, by other software companies, and "
                    "the customer's own. What lands depends on the blueprint, "
                    "perhaps a camera model checking parts on a factory line, or "
                    "the tills at a shop. It is the same motion as everything "
                    "before: ask, download, check, run. Every future update will "
                    "travel the same way, so a model improved at headquarters "
                    "reaches every site without anyone driving out to it."
                ),
                standard=(
                    "Workloads land and start, pulled from the application catalog "
                    "(Dell-packaged software, offerings from independent "
                    "software vendors, or ISVs, and the customer's own "
                    "containers) exactly as the "
                    "blueprint dictates: a vision-inspection model on a factory "
                    "line, point-of-sale at a branch. It is the same motion as "
                    "before, pull, verify, run, and it will deliver every future "
                    "update, so a model retrained centrally reaches every site "
                    "without a visit."
                ),
                expert=(
                    "Workloads pulled from the catalog (Dell, ISV, customer "
                    "containers) per blueprint; same pull-verify-run path carries "
                    "every future update."
                ),
            ),
            camera=_CONTROL_PLANE,
            region_ids=[*_ENDPOINTS, "orchestrator", "blueprint", "catalog"],
            layer_reveal=_CONTROL,
            trace_cursor=6,
            duration_ms=26_000,
        ),
        TourStep(
            id="managed-estate",
            title="Managed, with no one there",
            script=L(
                novice=(
                    "The whole map lights up, because managed means the loop is "
                    "closed, not just that software arrived. Security rules are "
                    "enforced on every device, trusting nothing by default, which "
                    "is the FortZero twin's idea applied at the edge. Health "
                    "reports flow back to the monitoring side, where the CloudIQ "
                    "twin picks up the story. Read the counters one last time: "
                    "four endpoints online, trust never taken back, and operator "
                    "actions exactly one. In this illustrative timeline it took "
                    "about thirteen minutes, and a shop manager plugged in two "
                    "cables and went back to work."
                ),
                standard=(
                    "Managed: the whole platform is lit, because managed means the "
                    "loop is closed. Zero Trust policy is enforced on every "
                    "endpoint, the FortZero twin's argument at the edge; telemetry "
                    "streams to observability, where the CloudIQ twin takes over. "
                    "Four endpoints online, trust never revoked, operator actions "
                    "exactly one, about thirteen minutes on this illustrative "
                    "timeline. The Dell Pro Max Plus twin is one endpoint this "
                    "estate could hold."
                ),
                expert=(
                    "Managed: full platform lit. Zero Trust enforced, telemetry to "
                    "observability. 4 online, trust held, operatorActions = 1, "
                    "~13 min (illustrative)."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[r.id for r in anatomy.regions],
            layer_reveal=_ESTATE,
            trace_cursor=7,
            duration_ms=28_000,
        ),
    ]

    return Tour(
        id="nativeedge-tour",
        title="One edge site, from sealed crate to managed estate",
        intro=L(
            novice=(
                "A guided walk through one site joining a NativeEdge estate, "
                "narrated beat by beat. Sit back and watch, or pause and click "
                "anything to look closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through zero-touch onboarding of one site. Watch "
                "it play, or pause and explore; Resume tour brings the camera back."
            ),
            expert="Narrated zero-touch onboarding walk-through. Pause to explore; resume restores framing.",
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
