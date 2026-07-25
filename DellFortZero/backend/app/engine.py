"""Pure access engine for the Project Fort Zero zero-trust twin.

``simulate()`` returns the deterministic trace of a single access request
under continuous verification — and then of an attacker who compromises a
host inside the network and gets nothing for it. Same purity rule as every
other twin in this repo: no FastAPI, no IO, no timers — the frontend owns
the playback clock, and each ``AccessState`` is plain data the renderer
consumes.

The idea this twin exists to teach: **there is no inside.**

Security has historically been perimeter-shaped. Verify at the boundary,
then treat what is behind it as trusted, because checking every internal
interaction was too expensive and the boundary was easy to draw. That model
fails identically every time: an attacker who gets in once inherits
everything the inside was permitted to do, and moves sideways at leisure —
which is why breach reports so consistently describe weeks of undetected
lateral movement after a single phished credential.

Zero trust does not harden the perimeter; it deletes the concept. Every
request is ruled on individually against one resource, using identity,
device posture, network context, workload and data sensitivity together,
and the ruling carries an expiry. A request from the corporate network, on
a managed laptop, by an authenticated employee, is granted nothing by any
of those facts — they are evidence a policy engine weighs.

Two things follow that this trace is built to show. Nothing accumulates:
being allowed to reach one resource a moment ago is not an argument for
reaching the next. And nothing is inherited from position: the breach step
puts an attacker on an internal host with valid network access, and
``resources_reachable`` stays at zero.

``implicit_trust_grants`` is zero on every step, and ``tests/test_engine.py``
asserts it — most pointedly at the breach, which is the exact step where a
perimeter model would have handed the attacker the estate.

Scores, counts, and timings are illustrative but plausible; favor a correct
mental model over measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .models import AccessState

# The seven DoD pillars, by region id. All of them feed the decision — the
# model is not a menu to pick from.
PILLARS = [
    "identity", "device", "network", "workload",
    "data", "visibility", "automation",
]

# Phases in which the session holds a live grant.
GRANTED_PHASES = {"grant", "monitor"}

# Phases in which an attacker is present on the internal network.
BREACH_PHASES = {"breach", "contained"}


def simulate() -> list[AccessState]:
    """One request, verified continuously — then a breach that gains
    nothing from being inside."""
    return [
        AccessState(
            step=0,
            phase="idle",
            label="No session — nothing is trusted",
            description=(
                "The starting position, and it is worth dwelling on how "
                "unusual it is. There is no logged-in state to inherit, no "
                "network segment that counts as safe, and no standing "
                "permission attached to anybody. A perimeter architecture "
                "at rest still has an inside; this one does not. Every "
                "counter that could represent accumulated trust reads "
                "zero, and it will return here at the end of every "
                "session."
            ),
            active_regions=[],
            trust_score=0,
            resources_reachable=0,
            implicit_trust_grants=0,
            verifications=0,
            trust_ttl_seconds=0,
            elapsed_seconds=0,
        ),
        AccessState(
            step=1,
            phase="request",
            label="A user asks for one specific resource",
            description=(
                "An employee, on a company laptop, on the office network, "
                "asks to open a document. In a perimeter model this "
                "sentence is already the end of the story — all three "
                "facts are the sort that historically granted access. Here "
                "none of them has done anything yet. Note also the shape "
                "of the request: it is for *one resource*, not for a "
                "network, a share, or a session. That framing is what "
                "makes least privilege enforceable rather than aspirational."
            ),
            active_regions=["identity", "policy"],
            trust_score=0,
            resources_reachable=0,
            implicit_trust_grants=0,
            verifications=0,
            trust_ttl_seconds=0,
            elapsed_seconds=1,
        ),
        AccessState(
            step=2,
            phase="verify",
            label="Identity and device posture established",
            description=(
                "Who is asking, and what state is the machine in. Strong "
                "authentication covers the first; posture covers the "
                "second — current patches, disk encryption, endpoint "
                "protection running and reporting, hardware attestation "
                "that the device is the one it claims to be. Both are "
                "checked now and both will be checked again shortly, which "
                "is the difference that matters. A stolen credential in "
                "this architecture has to keep surviving examination "
                "rather than being presented once at a gate."
            ),
            active_regions=["identity", "device", "policy"],
            trust_score=45,
            resources_reachable=0,
            implicit_trust_grants=0,
            verifications=2,
            trust_ttl_seconds=0,
            elapsed_seconds=2,
        ),
        AccessState(
            step=3,
            phase="context",
            label="Network location is gathered — as evidence, not permission",
            description=(
                "The step where the whole philosophy is visible in one "
                "counter. Network context is collected: the request comes "
                "from an internal segment, at a normal hour, from a "
                "location this user works from. Every one of those facts "
                "would have been sufficient in a perimeter model. Here "
                "they raise the confidence score and grant precisely "
                "nothing — resources reachable is still zero. Being on the "
                "network is not a way in; it is a mildly reassuring detail "
                "about a request that has not yet been decided."
            ),
            active_regions=["identity", "device", "network", "visibility", "policy"],
            trust_score=72,
            resources_reachable=0,
            implicit_trust_grants=0,
            verifications=4,
            trust_ttl_seconds=0,
            elapsed_seconds=3,
        ),
        AccessState(
            step=4,
            phase="decide",
            label="The policy engine rules, using all seven pillars",
            description=(
                "Identity, device, network, workload, data sensitivity, "
                "analytics, and the automation that will enforce the "
                "result — combined into one ruling, for this user, on this "
                "device, for this resource, right now. The DoD's model is "
                "not a menu of controls to adopt selectively; a gap in any "
                "pillar is a route around all of them, which is why "
                "validation is against the architecture rather than "
                "against a feature list. The cost is that this component "
                "must answer constantly and quickly. A slow policy engine "
                "gets routed around, and that is how zero-trust programmes "
                "usually die."
            ),
            active_regions=[*PILLARS, "policy"],
            trust_score=88,
            resources_reachable=0,
            implicit_trust_grants=0,
            verifications=5,
            trust_ttl_seconds=0,
            elapsed_seconds=4,
            cycle_cost=2,
        ),
        AccessState(
            step=5,
            phase="grant",
            label="One resource, for a limited time",
            description=(
                "Access is granted — to the single document requested, for "
                "a few minutes, and to nothing else. Two properties are "
                "worth naming. It is least privilege in the literal sense: "
                "one resource reachable, not a share, not a segment, not a "
                "role's worth of things. And it is a *lease*. The grant "
                "carries an expiry, after which the same user on the same "
                "device asking for the same document starts from nothing "
                "again. Trust here is something you hold briefly, not "
                "something you have."
            ),
            active_regions=["identity", "device", "workload", "data", "policy"],
            trust_score=88,
            resources_reachable=1,
            implicit_trust_grants=0,
            verifications=6,
            trust_ttl_seconds=300,
            elapsed_seconds=5,
        ),
        AccessState(
            step=6,
            phase="monitor",
            label="Continuous verification while the session lives",
            description=(
                "The long stage, and the honest location of zero trust's "
                "cost. Verification does not stop at the grant: posture is "
                "re-checked, behaviour is compared against the account's "
                "norm, and the ruling is revisited throughout. If the "
                "laptop's endpoint protection stops reporting, or the "
                "account starts touching things it never touches, access "
                "narrows automatically — in seconds, via the automation "
                "pillar, not in the morning via a ticket. The verification "
                "counter climbing here is the point: one check at the door "
                "is not this model, and a system that alerts humans to "
                "triage later is a perimeter with better logging."
            ),
            active_regions=[
                "identity", "device", "workload", "data",
                "visibility", "automation", "policy",
            ],
            trust_score=86,
            resources_reachable=1,
            implicit_trust_grants=0,
            verifications=31,
            trust_ttl_seconds=120,
            elapsed_seconds=185,
            cycle_cost=6,
        ),
        AccessState(
            step=7,
            phase="expire",
            label="The lease runs out — back to nothing",
            description=(
                "The grant expires and the session returns to the state it "
                "started in. Nothing carries forward: not the "
                "authentication, not the device check, not the fact that "
                "this exact access was approved five minutes ago. The next "
                "request will be decided on its own evidence. This is the "
                "property that makes the breach step ahead survivable, "
                "because there is no accumulated permission lying around "
                "for an attacker to inherit — the estate does not "
                "accumulate trust, it re-earns it."
            ),
            active_regions=["policy", "automation"],
            trust_score=0,
            resources_reachable=0,
            implicit_trust_grants=0,
            verifications=33,
            trust_ttl_seconds=0,
            elapsed_seconds=305,
        ),
        AccessState(
            step=8,
            phase="breach",
            label="An attacker compromises a host inside the network",
            description=(
                "The moment every perimeter architecture is judged on. An "
                "attacker phishes a credential, lands on an internal "
                "workstation, and now has genuine network access from a "
                "position that a boundary model defines as trusted. In "
                "that model this is effectively game over: the intruder "
                "inherits whatever the inside was permitted to do and "
                "begins moving sideways, typically undetected for weeks. "
                "Here the network pillar registers a host behaving oddly "
                "and the analytics pillar notices — but look at the "
                "counter that matters. Resources reachable: zero. Not "
                "because the attack was blocked, but because being inside "
                "was never worth anything."
            ),
            active_regions=["network", "visibility", "policy"],
            trust_score=0,
            resources_reachable=0,
            implicit_trust_grants=0,
            verifications=34,
            trust_ttl_seconds=0,
            elapsed_seconds=320,
            cycle_cost=3,
        ),
        AccessState(
            step=9,
            phase="contained",
            label="Lateral movement finds nothing to move to",
            description=(
                "The attacker tries the ordinary next steps — reach a file "
                "share, call an internal API, authenticate to an adjacent "
                "service — and each one is a fresh request that has to "
                "stand on its own evidence. The stolen credential does not "
                "come with a healthy device posture. The compromised host "
                "does not have a segment of neighbours to sweep. Nothing "
                "is inherited because nothing was accumulated. Meanwhile "
                "the automation pillar has already narrowed what that host "
                "can attempt, in seconds rather than at the next review. "
                "This is the whole architecture in one step, and it is why "
                "the Department of Defense assessed the design against "
                "sophisticated attack rather than against a checklist."
            ),
            active_regions=["network", "visibility", "automation", "policy"],
            trust_score=0,
            resources_reachable=0,
            implicit_trust_grants=0,
            verifications=41,
            trust_ttl_seconds=0,
            elapsed_seconds=335,
            cycle_cost=2,
        ),
    ]
