"""The narrated tour of the Fort Zero zero-trust map — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: nine beats that
move a camera across the seven pillars and the policy engine, pin the access
trace at the moments that carry the story, and narrate each one. The
frontend player owns the clock; nothing here knows about time, IO or the web
(AST-checked in ``tests/test_tour.py``, the same rule as ``engine.py``).

The signature beat is ``breach-reaches-nothing``: an attacker holds a
position inside the network that a perimeter would have honoured, and
reaches zero resources. Every claim the scripts make is one the engine, the
anatomy and ``tests/test_engine.py`` already make — each beat's
``trace_cursor`` is the step whose description says the same thing.

Layers (region id -> layer) ride with the tour rather than on the map model,
so ``ZeroTrustMap`` is unchanged. There is no outside and inside to peel
here — the map deliberately has no perimeter, and nothing in the tour draws
one. The only "layer" is the centre:

    0  the seven co-equal pillars, which are what a reader sees first
    1  the policy engine at the centre, which the first request wakes
"""

from __future__ import annotations

from twinkit.tour import (
    Tour,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import ZeroTrustMap

#: The step the tests pin: the twin's one idea lives here.
SIGNATURE_STEP_ID = "breach-reaches-nothing"

_PILLARS = 0
_CENTRE = 1

PILLAR_IDS = [
    "identity", "device", "network", "workload",
    "data", "visibility", "automation",
]


def layer_map(anatomy: ZeroTrustMap) -> dict[str, int]:
    """Every region's layer, derived from its kind: the policy engine is the
    centre, everything else is a pillar."""
    return {
        r.id: (_CENTRE if r.kind == "policy" else _PILLARS)
        for r in anatomy.regions
    }


def build_tour(anatomy: ZeroTrustMap) -> Tour:
    """The Fort Zero tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0):
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="seven-pillars",
            title="Seven pillars and no wall",
            script=L(
                novice=(
                    "This is Dell's Project Fort Zero, a complete private cloud "
                    "built on an idea called zero trust. What you are looking at "
                    "is not a machine but a way of making decisions. The seven "
                    "boxes are the seven pillars of the US Department of "
                    "Defense's zero-trust model: who is asking, what device they "
                    "are on, where on the network they are, which application is "
                    "involved, what data is at stake, what the monitoring sees, "
                    "and the automation that acts on it. All seven are drawn the "
                    "same size because the model treats them as equals. And "
                    "notice what is missing: there is no wall around anything. "
                    "Nothing on this map is an inside."
                ),
                standard=(
                    "This is Dell Project Fort Zero, a turnkey zero-trust "
                    "private cloud that completed the US Department of "
                    "Defense's (DoD's) assessment for Target Level, the "
                    "baseline tier of its zero-trust strategy, in April 2025. "
                    "The map is a "
                    "decision architecture, not hardware. The seven boxes are "
                    "the DoD reference architecture's pillars: identity, "
                    "device, network context, application and workload, data, "
                    "visibility and analytics, and automation. They are drawn "
                    "identical in size because the model treats them as "
                    "co-equal. Notice what is absent: no ring, no enclosure, no "
                    "perimeter. Most maps in this repo carry their lesson in a "
                    "boundary. This one carries it in the lack of one."
                ),
                expert=(
                    "Fort Zero: turnkey zero-trust private cloud, DoD Target "
                    "Level, April 2025. Seven co-equal DoD pillars, drawn "
                    "identical. No perimeter on the map, by design."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=list(PILLAR_IDS),
            layer_reveal=_PILLARS,
            trace_cursor=0,
            duration_ms=30_000,
        ),
        TourStep(
            id="a-request-arrives",
            title="A request for one thing",
            script=L(
                novice=(
                    "Someone asks for something. An employee, on a company "
                    "laptop, in the office, wants to open one document. In a "
                    "traditional setup, those three facts together would already "
                    "be enough to let them in. Here they have done nothing yet. "
                    "The request wakes the one thing at the centre of the map, "
                    "the policy engine: the part that makes every decision. Also "
                    "notice that the request is for one document, not for a whole "
                    "folder or a whole network. Asking for one thing at a time is "
                    "what makes it possible to hand out as little access as "
                    "possible."
                ),
                standard=(
                    "An employee, on a company laptop, on the office network, "
                    "asks to open one document. In a perimeter model that "
                    "sentence is already a yes. Here none of those facts has "
                    "done anything yet. The request wakes the policy engine at "
                    "the centre, the decision point consulted on every request "
                    "from here on. The shape of the request matters too: one "
                    "resource, not a share, a segment or a session. That "
                    "framing is what makes least privilege (the smallest access "
                    "that does the job) enforceable rather than aspirational."
                ),
                expert=(
                    "Request: authenticated user, managed device, internal "
                    "segment, one resource. Policy engine engaged. Nothing "
                    "granted by any of it."
                ),
            ),
            camera=frame("identity", "policy", pad=4.0),
            region_ids=["identity", "policy"],
            layer_reveal=_CENTRE,
            trace_cursor=1,
            duration_ms=26_000,
        ),
        TourStep(
            id="location-is-evidence",
            title="Being on the network grants nothing",
            script=L(
                novice=(
                    "The person has signed in, and the laptop has been checked: "
                    "up to date, encrypted, its protection software running. Now "
                    "the system looks at where the request came from. It is "
                    "inside the office network, at a normal hour, from a place "
                    "this person usually works. In an older setup, being on the "
                    "office network is the permission. Here it only makes the "
                    "request look a little less surprising. The confidence score "
                    "goes up, to 72 on this made-up scale, and the number of "
                    "things this person can reach stays exactly where it was: "
                    "zero."
                ),
                standard=(
                    "Identity and device posture (patches, disk encryption, "
                    "endpoint protection reporting) are established, and now "
                    "network context is gathered: an internal segment, a normal "
                    "hour, a familiar location. Every one of those facts would "
                    "have been sufficient in a perimeter model. Here they raise "
                    "the confidence score to 72, an illustrative figure, and "
                    "grant precisely nothing. Resources reachable is still "
                    "zero. Network position is an input to policy, not a way in."
                ),
                expert=(
                    "Authn and posture done; network context gathered. "
                    "Confidence 72 (illustrative). Reachable: 0. Position is a "
                    "policy input, not an entry path."
                ),
            ),
            camera=frame(
                "identity", "device", "network", "visibility", "policy", pad=3.0
            ),
            region_ids=["identity", "device", "network", "visibility", "policy"],
            layer_reveal=_CENTRE,
            trace_cursor=3,
            duration_ms=28_000,
        ),
        TourStep(
            id="all-seven-decide",
            title="Every pillar feeds the ruling",
            script=L(
                novice=(
                    "Now the policy engine decides, and every line on the map "
                    "lights at once. Who is asking, the laptop's condition, the "
                    "network, the application, how sensitive the document is, "
                    "what the monitoring has seen, and the automation that will "
                    "carry out the answer: all seven go into one decision, for "
                    "this person, on this laptop, for this document, right now. "
                    "The Defense Department's model is not a menu where you pick "
                    "the parts you like. A weak spot in any one pillar is a way "
                    "around all the others. The catch is that this engine has to "
                    "answer all the time, and fast. If it is slow, people find "
                    "ways around it."
                ),
                standard=(
                    "The policy engine rules, and every spoke lights at once. "
                    "Identity, device, network, workload, data sensitivity, "
                    "analytics and the automation that will enforce the result "
                    "combine into one ruling: this user, this device, this "
                    "resource, now. The DoD model is an architecture, not a "
                    "menu; a gap in any pillar is a route around all of them, "
                    "which is why validation is against the whole design. The "
                    "cost is that this component must answer constantly and "
                    "quickly. A slow policy engine gets routed around, and that "
                    "is how zero-trust programmes usually die."
                ),
                expert=(
                    "Decision: all seven pillars plus the policy engine, one "
                    "ruling per request. Architecture, not menu. Latency is the "
                    "failure mode."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[*PILLAR_IDS, "policy"],
            layer_reveal=_CENTRE,
            trace_cursor=4,
            duration_ms=30_000,
        ),
        TourStep(
            id="trust-is-a-lease",
            title="A grant with an expiry",
            script=L(
                novice=(
                    "The answer is yes, but a very narrow yes. The person can "
                    "reach exactly one thing, the document they asked for, and "
                    "nothing else: not the folder it sits in, not the rest of "
                    "the network. And the yes comes with a timer. In this "
                    "example it lasts 300 seconds, five minutes, a figure made "
                    "up for this example. When the timer runs out, the same person "
                    "on the same laptop asking for the same document starts "
                    "again from nothing. Trust here is borrowed for a while, "
                    "like a lease, not something you get to keep."
                ),
                standard=(
                    "Access is granted to the single document requested, and to "
                    "nothing else. That is least privilege in the literal sense: "
                    "one resource reachable, never a share or a segment, and "
                    "the tests hold it to at most one on every step. The grant "
                    "is also a lease. It carries a time to live, 300 seconds in "
                    "this illustrative trace, after which the same user on the "
                    "same device asking for the same document starts from "
                    "nothing. Outside a grant there is no lease at all. Trust "
                    "is something you hold briefly, not something you have."
                ),
                expert=(
                    "Grant: one resource, TTL 300 s (illustrative). At most one "
                    "reachable, ever. No lease outside a grant; re-derived from "
                    "zero at expiry."
                ),
            ),
            camera=frame("identity", "device", "workload", "data", "policy", pad=2.0),
            region_ids=["identity", "device", "workload", "data", "policy"],
            layer_reveal=_CENTRE,
            trace_cursor=5,
            duration_ms=26_000,
        ),
        TourStep(
            id="checking-never-stops",
            title="The checking never stops",
            script=L(
                novice=(
                    "This is the longest part of the story, and it is where zero "
                    "trust really costs something. Checking does not stop once "
                    "the answer is yes. The laptop's condition is looked at "
                    "again and again, the person's behaviour is compared with "
                    "what is normal for them, and the decision keeps being "
                    "revisited. Watch the check counter climb from 6 to 31 while "
                    "the session is open. If the laptop's protection stops "
                    "reporting, or the account starts touching things it never "
                    "touches, the automation narrows access within seconds, "
                    "without waiting for a person to read an alert the next "
                    "morning."
                ),
                standard=(
                    "The longest stage in the trace, and the honest location of "
                    "zero trust's cost. Verification does not stop at the grant: "
                    "posture is re-checked, behaviour is compared against the "
                    "account's norm, and the ruling is revisited throughout. The "
                    "verification counter climbs from 6 to 31 while the session "
                    "is live. If endpoint protection stops reporting, or the "
                    "account touches things it never touches, the automation "
                    "pillar narrows access in seconds. A system that only files "
                    "alerts for humans to triage later is a perimeter with "
                    "better logging."
                ),
                expert=(
                    "Longest stage. Continuous re-verification, 6 to 31 checks "
                    "in-session. Automated narrowing in seconds. The cost is "
                    "the not-stopping."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[
                "identity", "device", "workload", "data",
                "visibility", "automation", "policy",
            ],
            layer_reveal=_CENTRE,
            trace_cursor=6,
            duration_ms=32_000,
        ),
        TourStep(
            id="the-lease-runs-out",
            title="Back to nothing",
            script=L(
                novice=(
                    "The timer runs out and everything goes back to where it "
                    "started. The sign-in, the laptop check, the fact that this "
                    "exact request was approved five minutes ago: none of it "
                    "carries forward. The next request will be judged only on "
                    "its own evidence. This is what makes the next scene "
                    "survivable. Because the system never builds up a pile of "
                    "leftover permissions, there is nothing lying around for an "
                    "intruder to pick up."
                ),
                standard=(
                    "The lease expires and the session returns to the state it "
                    "started in: confidence zero, nothing reachable. Nothing "
                    "carries forward, not the authentication, not the device "
                    "check, not the fact that this exact access was approved "
                    "minutes ago. The next request is decided on its own "
                    "evidence. That non-accumulation is what makes the breach "
                    "ahead survivable: there is no residual permission lying "
                    "around for an attacker to inherit."
                ),
                expert=(
                    "Lease expires: confidence 0, reachable 0. No carry-forward. "
                    "Non-accumulation is what makes the breach survivable."
                ),
            ),
            camera=frame("policy", "automation", pad=4.0),
            region_ids=["policy", "automation"],
            layer_reveal=_CENTRE,
            trace_cursor=7,
            duration_ms=22_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Inside, and reaching nothing",
            script=L(
                novice=(
                    "This is the moment every security design is really judged "
                    "on. An attacker tricks someone into giving up a password "
                    "and lands on a computer inside the office network. That is "
                    "exactly the position an old-style setup calls trusted: in "
                    "that world the intruder would now inherit everything the "
                    "inside was allowed to do, and could wander from machine to "
                    "machine, often unnoticed for weeks. Here the network pillar "
                    "notices a machine behaving oddly, and the monitoring "
                    "notices too. But look at the number that matters. Things "
                    "the attacker can reach: zero. Confidence: zero. That is "
                    "not because a guard stopped the attack. It is because "
                    "being inside was never worth anything."
                ),
                standard=(
                    "The step every architecture is judged on. An attacker "
                    "phishes a credential and lands on an internal workstation, "
                    "with genuine network access from exactly the position a "
                    "perimeter would have honoured. In that model this is game "
                    "over: the intruder inherits whatever the inside was "
                    "permitted and begins lateral movement, sideways from host "
                    "to host, often undetected for weeks. Here the network "
                    "pillar registers a host behaving oddly and analytics "
                    "notices. Resources reachable: zero. Confidence: zero. "
                    "Implicit trust grants: zero, as on every step. Not "
                    "because the attack was blocked, but because being inside "
                    "was never worth anything."
                ),
                expert=(
                    "Signature: compromised internal host, valid network "
                    "position, terminal in a boundary model. Reachable 0, "
                    "confidence 0, implicit grants 0. Not blocked; position "
                    "never authorized."
                ),
            ),
            camera=frame("network", "visibility", "policy", pad=2.0),
            region_ids=["network", "visibility", "policy"],
            layer_reveal=_CENTRE,
            trace_cursor=8,
            duration_ms=42_000,
        ),
        TourStep(
            id="nothing-to-move-to",
            title="Still no wall, and still watching",
            script=L(
                novice=(
                    "The attacker tries the usual next moves: open a shared "
                    "drive, call an internal service, sign in to something "
                    "nearby. Each one is a brand-new request that has to prove "
                    "itself, and the stolen password does not come with a "
                    "healthy laptop attached. The automation has already "
                    "narrowed what that machine can even try. And the checking "
                    "has not stopped: the counter has kept climbing, to 41, "
                    "with nobody logged in at all. Look at the whole map again. "
                    "There is still no wall anywhere. Three other twins in this "
                    "project answer the questions people mix up with this one: "
                    "iDRAC for hardware you can trust, PowerProtect for a copy "
                    "that survives, and Cyber Detect for a copy that is intact."
                ),
                standard=(
                    "Lateral movement finds nothing to move to. Every attempt "
                    "(a file share, an internal application programming "
                    "interface (API), an adjacent service) is a "
                    "fresh request standing on its own evidence, the stolen "
                    "credential carries no healthy device posture, and the "
                    "automation pillar has already narrowed what the host can "
                    "attempt. Verification never stopped: the counter reached "
                    "41 with no session live. The map is still whole, with no "
                    "wall drawn. Three neighbouring twins answer questions "
                    "people confuse with this one: iDRAC (a hardware root of "
                    "trust), PowerProtect (does a copy survive) and Cyber "
                    "Detect (is the copy intact)."
                ),
                expert=(
                    "Contained: each lateral hop a fresh decision; no posture, "
                    "no neighbours. Verifications at 41 with no session. See "
                    "iDRAC, PowerProtect, Cyber Detect."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["network", "visibility", "automation", "policy"],
            layer_reveal=_PILLARS,
            trace_cursor=9,
            duration_ms=30_000,
        ),
    ]

    return Tour(
        id="fortzero-tour",
        title="A centre, and no inside",
        intro=L(
            novice=(
                "A guided walk through one request, from the moment it arrives "
                "to an intruder who gets nowhere, narrated beat by beat. Sit "
                "back and watch, or pause and click any pillar to look closer; "
                "the tour waits for you."
            ),
            standard=(
                "A narrated walk through one access request and one breach. "
                "Watch it play, or pause and explore; Resume tour brings the "
                "camera back."
            ),
            expert="Narrated request-to-breach walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: ZeroTrustMap) -> TourResponse:
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
