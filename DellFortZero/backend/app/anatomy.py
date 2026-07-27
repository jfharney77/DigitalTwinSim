"""Zero-trust map data: the seven DoD pillars around a policy engine.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over product accuracy (project
scope guardrail).

The organizing choice is a negative one. Every other map in this repo has a
boundary somewhere and puts its lesson in it: a PCIe strip, an air gap, a
band of nodes with nothing above them. This map has no enclosing shape at
all, and ``tests/test_anatomy.py`` enforces that nothing in it is large
enough to act as one. Seven co-equal pillars sit around a policy engine at
the centre. There is a middle; there is no inside.

The pillars are the US Department of Defense zero-trust reference
architecture's, not a vendor's list, because Project Fort Zero was
validated against the DoD's model — reaching Target Level as a sovereign,
on-premises private cloud in April 2025.
"""

from __future__ import annotations

from .leveling import L
from .models import Pillar, Photo, SourceLink, Stat, ZeroTrustMap

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell product image — with an honest credit line.
PILLAR_ILLO = Photo(
    url="/fortzero-pillars.svg",
    caption=(
        "A decision architecture with a centre and no edge. Every request "
        "is ruled on by the policy engine using all seven pillars, and "
        "being on the network is one input among them rather than a way in."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)

# Pillar geometry: a ring around the policy engine. Every pillar is drawn
# the same size, because the DoD model treats them as co-equal and a
# diagram that made one bigger would be arguing with it.
PILLAR_W = 28.0
PILLAR_H = 12.0

MAP_W = 100.0
MAP_H = 72.0


def _pillar(pid: str, kind: str, label: str, x: float, y: float, desc: str) -> Pillar:
    return Pillar(
        id=pid, kind=kind, label=label,
        x=x, y=y, w=PILLAR_W, h=PILLAR_H, description=desc,
    )


ANATOMY = ZeroTrustMap(
    id="fortzero",
    name="Dell Project Fort Zero — zero-trust decision architecture",
    vendor="Dell Technologies",
    form_factor="Turnkey sovereign on-premises private cloud",
    generation="US DoD Target Level zero-trust validation (April 2025)",
    year=2026,
    width=MAP_W,
    height=MAP_H,
    overview=L(
        novice=(
            "Most computer security has worked like a walled building. You "
            "check people at the door, and once they are inside you assume "
            "they "
            "belong there. The flaw is obvious once stated: anyone who does "
            "get "
            "in — a stolen password is usually enough — can then wander "
            "freely, "
            "and attackers routinely spend weeks doing exactly that before "
            "anyone notices. Zero trust throws the walls away rather than "
            "making them thicker. There is no inside. Every single request to "
            "reach something is judged on its own, using who is asking, what "
            "machine they are on, where they are connecting from, and how "
            "sensitive the thing is — and the permission it grants expires "
            "shortly afterwards. Being on the company network counts as a "
            "small "
            "piece of evidence, not as a key. This diagram deliberately has no "
            "box drawn around anything, because there is nothing to be inside "
            "of: seven equally important considerations arranged around the "
            "component that makes the decisions. Watch what happens in the "
            "story when an attacker does get onto the internal network. "
            "Nothing "
            "happens, and that is the whole idea."
        ),
        plain=(
            "Project Fort Zero is Dell's ready-built zero-trust private cloud, "
            "and in April 2025 it passed the US Department of Defense's Target "
            "Level assessment as a sovereign, on-premises deployment, tested "
            "against serious attack. What makes it worth a twin is the "
            "assumption it reverses. Security was traditionally built on a "
            "perimeter: check at the boundary, then treat everything behind it "
            "as trustworthy. That fails the same way every time — whoever gets "
            "in inherits everything the inside was allowed to do and moves "
            "sideways at leisure. Zero trust deletes the idea instead of "
            "reinforcing it. Every request is decided individually on "
            "identity, "
            "the device's condition, network context, the application, and the "
            "sensitivity of the data — and the decision expires. Being on the "
            "corporate network is evidence, not entry. So the map is drawn "
            "with "
            "no enclosing shape at all: seven equal pillars around a decision "
            "point. Note what the trace shows when an attacker compromises a "
            "machine inside the network: nothing."
        ),
        standard=(
            "Project Fort Zero is Dell's turnkey zero-trust private cloud, and "
            "in April 2025 it completed the US Department of Defense's "
            "assessment for Target Level validation — tested against "
            "sophisticated attack, as a sovereign, on-premises deployment. "
            "What "
            "makes it worth a twin is not the product's feature list but the "
            "assumption it inverts. Security has historically been built on a "
            "perimeter: verify at the boundary, then treat what is behind it "
            "as "
            "trusted. That model fails the same way every time — an attacker "
            "who gets inside once inherits everything the inside was allowed "
            "to "
            "do, and moves sideways at leisure. Zero trust removes the concept "
            "rather than hardening it. There is no inside. Every request is "
            "ruled on individually, using identity, device posture, network "
            "context, workload, and data sensitivity together, and the ruling "
            "expires. Being on the corporate network is evidence a policy "
            "engine weighs; it is not a way in. This map is therefore drawn "
            "with no enclosing shape at all: seven co-equal pillars around a "
            "decision point. Note what happens in the trace when an attacker "
            "compromises a host *inside* the network — nothing does, which is "
            "the entire architecture in one step."
        ),
        technical=(
            "Dell's turnkey zero-trust private cloud, DoD Target Level "
            "validated in April 2025 as a sovereign on-premises deployment and "
            "tested under adversarial assessment. The point is the inverted "
            "assumption, not the feature list. Perimeter security verifies at "
            "the boundary and trusts what is behind it, which fails "
            "identically "
            "every time: initial access confers everything the interior was "
            "permitted, and lateral movement follows. Zero trust removes the "
            "concept. Authorization is per-request across identity, device "
            "posture, network context, workload, and data sensitivity, with an "
            "expiring decision. Network position is an input, not an entry "
            "path. Hence a map with no enclosing shape: seven co-equal pillars "
            "around a policy decision point. The breach step is the "
            "architecture in one frame."
        ),
        expert=(
            "Turnkey zero-trust private cloud; DoD Target Level, April 2025, "
            "sovereign on-prem, adversarially assessed. Inverts the perimeter "
            "assumption: no implicit trust from position, per-request "
            "authorization across the seven DoD pillars, expiring decisions, "
            "least privilege at single-resource granularity. Network position "
            "is an input to policy, not an entry path — so lateral movement "
            "has "
            "nothing to inherit. Map carries no enclosing shape by design."
        ),
    ),
    regions=[
        _pillar(
            "identity", "identity", "Identity",
            2, 2,
            "Who is asking. Strong authentication, multi-factor by "
            "default, and — the part organizations underestimate — "
            "authorization that is re-evaluated rather than issued once. A "
            "credential here is not a key that opens doors for eight "
            "hours; it is one input to a decision that will be made again "
            "shortly. The practical consequence is that a stolen "
            "credential buys an attacker far less than it does in a "
            "perimeter model, because it has to survive continuous "
            "re-examination alongside device posture and behaviour rather "
            "than being presented once at a gate.",
        ),
        _pillar(
            "device", "device", "Device",
            36, 2,
            "What the request is coming from, and whether that machine is "
            "in a state anyone should trust today. Posture means current "
            "patch level, disk encryption, whether endpoint protection is "
            "running and reporting, whether the device is the one it "
            "claims to be. A managed laptop is not automatically "
            "trustworthy — it is trustworthy while its posture holds, and "
            "the moment it stops reporting cleanly its access narrows "
            "without anybody filing a ticket. This is also where the "
            "hardware root of trust matters, which this repo's iDRAC twin "
            "covers at the server level.",
        ),
        _pillar(
            "network", "network", "Network context",
            70, 2,
            "Where the request came from — and the pillar most likely to "
            "be misread. In a perimeter architecture, network position "
            "*is* the authorization: get onto the internal segment and you "
            "are in. Here it is evidence and nothing more, weighed "
            "alongside everything else. A request from the office network "
            "is not granted; it is merely slightly less surprising. What "
            "the network layer does contribute is segmentation fine enough "
            "that a compromised host has almost nothing adjacent to reach "
            "— which is why the breach step in this trace goes nowhere.",
        ),
        _pillar(
            "workload", "workload", "Application & workload",
            2, 30,
            "The application or service being reached, treated as "
            "something that must also authenticate rather than as a thing "
            "sitting safely behind a firewall. Services verify each other; "
            "an internal API does not accept a call simply because the "
            "caller is internal. This is the part of zero trust that "
            "rearranges the most existing software, because a great deal "
            "of enterprise code was written on the assumption that "
            "anything able to reach it was entitled to talk to it.",
        ),
        _pillar(
            "data", "data", "Data",
            70, 30,
            "The resource itself — classified, labelled, and protected "
            "independently of wherever it happens to be sitting. The "
            "discipline is that sensitivity travels with the data rather "
            "than being a property of the folder it is in, so a file does "
            "not become less confidential by being copied somewhere "
            "convenient. This is also the pillar with the most overlap "
            "with the rest of this repo: this repo's PowerProtect twin "
            "protects data by isolating it, and the Cyber Detect twin "
            "verifies its integrity — access control decides who may reach "
            "it in the first place.",
        ),
        _pillar(
            "visibility", "visibility", "Visibility & analytics",
            19, 58,
            "What is actually happening, continuously. Zero trust needs "
            "far more telemetry than a perimeter model, for a structural "
            "reason: if decisions are made per request rather than once at "
            "a gate, the decisions need evidence per request. Behaviour "
            "analytics feed the policy engine so an account doing "
            "something out of character sees its access narrow "
            "automatically. This repo's CloudIQ twin covers the same "
            "instinct applied to infrastructure health — watch "
            "everything, notice the anomaly, act before the incident.",
        ),
        _pillar(
            "automation", "automation", "Automation & orchestration",
            53, 58,
            "Response that moves faster than a person can. When analytics "
            "flag something, the reaction — narrowing access, forcing "
            "re-authentication, isolating a host — has to happen in "
            "seconds, because an attacker with a foothold is measuring "
            "their opportunity in exactly that unit. This is the pillar "
            "that decides whether the architecture is real or "
            "aspirational: continuous verification that produces alerts "
            "for humans to triage in the morning is a perimeter model "
            "with better logging.",
        ),
        Pillar(
            id="policy", kind="policy", label="Policy engine",
            x=36, y=30, w=PILLAR_W, h=PILLAR_H,
            description=(
                "The decision point, consulted on every single request — "
                "and the only thing in this diagram at the centre of "
                "anything. It combines all seven pillars into one ruling "
                "for one request against one resource, then attaches a "
                "lifetime to it. Two properties follow that are easy to "
                "state and hard to build. First, the decision is per "
                "request, so nothing accumulates: being allowed to read "
                "one document a moment ago is not an argument for reading "
                "the next one. Second, the decision expires, so trust here "
                "is a lease rather than a property. The engineering cost "
                "of that is real — this is a component that has to answer "
                "constantly, quickly, and correctly, and if it is slow the "
                "organization will route around it, which is how zero "
                "trust projects usually die."
            ),
        ),
    ],
    stats=[
        Stat(label="Model", value="US DoD zero-trust reference architecture"),
        Stat(label="Validation", value="DoD Target Level, April 2025"),
        Stat(label="Deployment", value="Sovereign, on-premises private cloud"),
        Stat(label="Pillars", value="7, co-equal, plus a central policy engine"),
        Stat(label="Decision scope", value="One request, one resource, one lease"),
        Stat(label="Implicit trust", value="None — including inside the network"),
        Stat(label="Verification", value="Continuous, not once at a gate"),
        Stat(label="Assessment", value="Tested against sophisticated attack"),
    ],
    photo=PILLAR_ILLO,
    sources=[
        SourceLink(
            label="Dell achieves US DoD validation for zero-trust solution (April 2025)",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2025~04~dell-technologies-achieves-us-department-of-defense-validation-for-zero-trust-solution.htm",
        ),
        SourceLink(
            label="Dell — Zero Trust",
            url="https://www.dell.com/en-us/lp/dt/security-zero-trust",
        ),
        SourceLink(
            label="Dell Technologies Project Fort Zero to transform security",
            url="https://investors.delltechnologies.com/news-releases/news-release-details/dell-technologies-project-fort-zero-transform-security",
        ),
    ],
)
