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

from .leveling import L
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
            description=L(
                novice=(
                    "The starting position, and it is worth noticing how unusual it "
                    "is. Nobody is logged in, no part of the network counts as "
                    "safe, and nobody holds any standing permission. A traditional "
                    "security setup, even when idle, still has an 'inside'. This "
                    "one does not. Every counter that could represent accumulated "
                    "trust reads zero, and it will come back here at the end of "
                    "every session."
                ),
                plain=(
                    "The starting position, and it is worth dwelling on how unusual "
                    "it is. There is no logged-in state to inherit, no network "
                    "segment that counts as safe, and no standing permission "
                    "attached to anybody. A perimeter architecture at rest still "
                    "has an inside; this one does not. Every counter that could "
                    "represent accumulated trust reads zero, and it returns here at "
                    "the end of every session."
                ),
                standard=(
                    "The starting position, and it is worth dwelling on how "
                    "unusual it is. There is no logged-in state to inherit, no "
                    "network segment that counts as safe, and no standing "
                    "permission attached to anybody. A perimeter architecture "
                    "at rest still has an inside; this one does not. Every "
                    "counter that could represent accumulated trust reads "
                    "zero, and it will return here at the end of every "
                    "session."
                ),
                technical=(
                    "Initial state: no session, no trusted segment, no standing "
                    "grant. A perimeter architecture at rest still has an interior; "
                    "this has none. All accumulated-trust counters zero, and they "
                    "return here after every session."
                ),
                expert=(
                    "No session, no trusted segment, no standing grant. Perimeter "
                    "models retain an interior at rest; this does not."
                ),
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
            description=L(
                novice=(
                    "An employee, on a company laptop, on the office network, asks "
                    "to open a document. In the traditional model that sentence is "
                    "already the end of the story — all three facts are the sort "
                    "that used to grant access. Here none of them has done anything "
                    "yet. Notice the shape of the request too: it is for *one "
                    "document*, not for a drive, a folder, or a session. That "
                    "framing is what makes 'least privilege' something you can "
                    "actually enforce rather than aspire to."
                ),
                plain=(
                    "An employee, on a company laptop, on the office network, asks "
                    "to open a document. In a perimeter model that sentence is "
                    "already the end of the story — all three facts historically "
                    "granted access. Here none of them has done anything yet. Note "
                    "the shape of the request: one resource, not a network, a "
                    "share, or a session. That framing is what makes least "
                    "privilege enforceable rather than aspirational."
                ),
                standard=(
                    "An employee, on a company laptop, on the office network, "
                    "asks to open a document. In a perimeter model this "
                    "sentence is already the end of the story — all three "
                    "facts are the sort that historically granted access. Here "
                    "none of them has done anything yet. Note also the shape "
                    "of the request: it is for *one resource*, not for a "
                    "network, a share, or a session. That framing is what "
                    "makes least privilege enforceable rather than aspirational."
                ),
                technical=(
                    "Request from an authenticated user, managed device, internal "
                    "segment — three facts that constitute authorization in a "
                    "perimeter model and none here. Scope is a single resource "
                    "rather than a share, segment, or session, which is what makes "
                    "least privilege enforceable."
                ),
                expert=(
                    "Request: authenticated user, managed device, internal segment "
                    "— authorization in a perimeter model, evidence here. "
                    "Single-resource scope makes least privilege enforceable."
                ),
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
            description=L(
                novice=(
                    "Who is asking, and what condition is their machine in. Strong "
                    "sign-in covers the first; checking the machine covers the "
                    "second — is it up to date, is its disk encrypted, is its "
                    "protection software running and reporting, is it really the "
                    "machine it claims to be. Both are checked now and both will be "
                    "checked again shortly, which is the difference that matters. A "
                    "stolen password in this design has to keep surviving "
                    "examination rather than being shown once at a door."
                ),
                plain=(
                    "Who is asking, and what state is the machine in. Strong "
                    "authentication covers the first; posture covers the second — "
                    "current patches, disk encryption, endpoint protection running "
                    "and reporting, hardware attestation that the device is what it "
                    "claims. Both are checked now and both will be checked again "
                    "shortly, which is the difference that matters. A stolen "
                    "credential here has to keep surviving examination rather than "
                    "being presented once at a gate."
                ),
                standard=(
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
                technical=(
                    "Identity and device posture established: strong "
                    "authentication, patch level, disk encryption, endpoint agent "
                    "reporting, hardware attestation. Both are re-evaluated shortly "
                    "— a stolen credential must survive continuous examination "
                    "rather than a single gate check."
                ),
                expert=(
                    "Identity plus posture: authn, patch state, encryption, agent "
                    "telemetry, hardware attestation. Re-evaluated continuously — "
                    "credentials must survive, not merely present."
                ),
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
            description=L(
                novice=(
                    "The step where the whole philosophy is visible in one number. "
                    "Where the request came from is collected: an internal part of "
                    "the network, at a normal hour, from a place this person "
                    "usually works. Every one of those would have been enough on "
                    "its own in the traditional model. Here they raise the "
                    "confidence score and grant precisely nothing — the count of "
                    "things reachable is still zero. Being on the network is not a "
                    "way in; it is a mildly reassuring detail about a request that "
                    "has not been decided yet."
                ),
                plain=(
                    "The step where the philosophy is visible in one counter. "
                    "Network context is collected: an internal segment, a normal "
                    "hour, a location this user works from. Every one of those "
                    "would have been sufficient in a perimeter model. Here they "
                    "raise the confidence score and grant precisely nothing — "
                    "resources reachable is still zero. Being on the network is not "
                    "a way in; it is a mildly reassuring detail about a request "
                    "that has not yet been decided."
                ),
                standard=(
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
                technical=(
                    "Network context gathered — internal segment, normal hour, "
                    "familiar location — each of which is sufficient authorization "
                    "in a perimeter model. Here they raise confidence and grant "
                    "nothing: reachable resources still zero. Position is an input "
                    "to policy, not an entry path."
                ),
                expert=(
                    "Context gathered: segment, time, geo. Confidence rises, "
                    "reachable stays zero. Position is a policy input, not an entry "
                    "path."
                ),
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
            description=L(
                novice=(
                    "Who is asking, what machine they are on, where from, what "
                    "application, how sensitive the data, what is normal for them, "
                    "and what will enforce the answer — all combined into a single "
                    "ruling, for this person, on this machine, for this one "
                    "document, right now. The reference model this is built against "
                    "is not a menu of options to adopt selectively: a gap in any "
                    "one consideration is a way around all of them, which is why "
                    "the system is assessed as a whole rather than feature by "
                    "feature. The cost is that this component has to answer "
                    "constantly and quickly. A slow decision-maker gets worked "
                    "around, and that is how these projects usually die."
                ),
                plain=(
                    "Identity, device, network, workload, data sensitivity, "
                    "analytics, and the automation that will enforce the result — "
                    "combined into one ruling, for this user, on this device, for "
                    "this resource, right now. The DoD's model is not a menu of "
                    "controls to adopt selectively; a gap in any pillar is a route "
                    "around all of them, which is why validation is against the "
                    "architecture rather than a feature list. The cost is that this "
                    "component must answer constantly and quickly. A slow policy "
                    "engine gets routed around, and that is how zero-trust "
                    "programmes usually die."
                ),
                standard=(
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
                technical=(
                    "All seven pillars combined into a single per-request ruling: "
                    "identity, device, network, workload, data sensitivity, "
                    "analytics, and the enforcement path. The reference "
                    "architecture is not selectively adoptable — a gap in any "
                    "pillar routes around the rest, hence architectural rather than "
                    "feature-level validation. The engineering constraint is "
                    "latency: a slow PDP gets exceptions built around it, which is "
                    "the usual failure mode."
                ),
                expert=(
                    "Per-request ruling across all seven pillars. Not selectively "
                    "adoptable — any gap routes around the rest. Constraint is PDP "
                    "latency; exceptions built around a slow engine are the usual "
                    "failure mode."
                ),
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
            description=L(
                novice=(
                    "Access is granted — to the single document requested, for a "
                    "few minutes, and to nothing else. Two things are worth naming. "
                    "It is least privilege in the literal sense: one thing "
                    "reachable, not a folder, not a section of the network, not "
                    "everything a job title implies. And it is a *lease*. The "
                    "permission has an expiry, after which the same person on the "
                    "same machine asking for the same document starts from nothing "
                    "again. Trust here is something you hold briefly, not something "
                    "you have."
                ),
                plain=(
                    "Access is granted — to the single document requested, for a "
                    "few minutes, and to nothing else. Two properties are worth "
                    "naming. It is least privilege in the literal sense: one "
                    "resource reachable, not a share, not a segment, not a role's "
                    "worth of things. And it is a lease. The grant carries an "
                    "expiry, after which the same user on the same device asking "
                    "for the same document starts from nothing. Trust here is "
                    "something you hold briefly, not something you have."
                ),
                standard=(
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
                technical=(
                    "Grant issued: single resource, bounded TTL, nothing else. "
                    "Least privilege literally — one object, not a share, segment, "
                    "or role scope. And a lease, not a property: at expiry the "
                    "identical request re-derives from zero."
                ),
                expert=(
                    "Grant: one resource, bounded TTL. Least privilege literal; "
                    "trust leased, not held. Identical request re-derives at "
                    "expiry."
                ),
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
            description=L(
                novice=(
                    "The long step, and the honest location of what this approach "
                    "costs. Checking does not stop once access is granted: the "
                    "machine's condition is re-examined, the person's behaviour is "
                    "compared against what is normal for them, and the decision is "
                    "revisited throughout. If the laptop's protection software "
                    "stops reporting, or the account starts touching things it "
                    "never touches, access narrows automatically — in seconds, not "
                    "in the morning via a support ticket. The rising check count is "
                    "the point: one check at the door is not this model, and a "
                    "system that just files alerts for people to review later is "
                    "the old approach with better logging."
                ),
                plain=(
                    "The long stage, and the honest location of zero trust's cost. "
                    "Verification does not stop at the grant: posture is "
                    "re-checked, behaviour is compared against the account's norm, "
                    "and the ruling is revisited throughout. If endpoint protection "
                    "stops reporting, or the account touches things it never "
                    "touches, access narrows automatically — in seconds, via "
                    "automation, not in the morning via a ticket. The verification "
                    "counter climbing is the point: one check at the door is not "
                    "this model, and a system that alerts humans to triage later is "
                    "a perimeter with better logging."
                ),
                standard=(
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
                technical=(
                    "Max-dwell stage and the honest cost centre. Verification "
                    "continues through the session: posture re-evaluated, behaviour "
                    "compared against baseline, ruling revisited. Posture lapse or "
                    "anomalous access narrows the grant automatically in seconds "
                    "via the automation pillar. The climbing verification count is "
                    "the model — single-gate checking with deferred human triage is "
                    "a perimeter with better logging."
                ),
                expert=(
                    "Continuous re-verification: posture, behaviour, ruling. "
                    "Automated narrowing in seconds on lapse or anomaly. Max dwell "
                    "— the cost is the not-stopping. Single-gate plus deferred "
                    "triage is a perimeter with logging."
                ),
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
            description=L(
                novice=(
                    "The permission expires and the session returns to where it "
                    "started. Nothing carries forward: not the sign-in, not the "
                    "machine check, not the fact that this exact access was "
                    "approved five minutes ago. The next request will be decided on "
                    "its own evidence. This is the property that makes the break-in "
                    "ahead survivable, because there is no accumulated permission "
                    "lying around for an intruder to inherit — the system does not "
                    "build up trust, it re-earns it."
                ),
                plain=(
                    "The grant expires and the session returns to the state it "
                    "started in. Nothing carries forward: not the authentication, "
                    "not the device check, not the fact that this exact access was "
                    "approved five minutes ago. The next request is decided on its "
                    "own evidence. This is the property that makes the breach ahead "
                    "survivable — there is no accumulated permission lying around "
                    "to inherit. The estate does not accumulate trust, it re-earns "
                    "it."
                ),
                standard=(
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
                technical=(
                    "Grant expires; session state returns to initial. Nothing "
                    "carries forward — authentication, posture check, and the prior "
                    "ruling all lapse, and the next request derives from its own "
                    "evidence. This non-accumulation is what makes the subsequent "
                    "breach survivable: there is no residual permission to inherit."
                ),
                expert=(
                    "Lease expires, state returns to initial. No carry-forward of "
                    "authn, posture, or ruling. Non-accumulation is what makes the "
                    "breach survivable."
                ),
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
            description=L(
                novice=(
                    "The moment every security design is really judged on. An "
                    "attacker steals a password, lands on a machine inside the "
                    "office network, and now has genuine access from a position "
                    "that the traditional model defines as trusted. In that model "
                    "this is effectively the end: the intruder inherits whatever "
                    "the inside was allowed to do and starts moving sideways, "
                    "typically undetected for weeks. Here the network layer notices "
                    "a machine behaving oddly and the analytics layer notices too — "
                    "but look at the number that matters. Things reachable: zero. "
                    "Not because the attack was blocked, but because being inside "
                    "was never worth anything."
                ),
                plain=(
                    "The moment every perimeter architecture is judged on. An "
                    "attacker phishes a credential, lands on an internal "
                    "workstation, and now has genuine network access from a "
                    "position a boundary model defines as trusted. In that model "
                    "this is effectively game over: the intruder inherits whatever "
                    "the inside was permitted and begins moving sideways, typically "
                    "undetected for weeks. Here the network pillar registers a host "
                    "behaving oddly and analytics notices — but look at the counter "
                    "that matters. Resources reachable: zero. Not because the "
                    "attack was blocked, but because being inside was never worth "
                    "anything."
                ),
                standard=(
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
                technical=(
                    "The step every architecture is judged on. Credential phished, "
                    "internal workstation compromised — genuine network position, "
                    "and in a boundary model effectively terminal: the interior's "
                    "permissions are inherited and lateral movement proceeds, "
                    "typically undetected for weeks. Here the network and "
                    "visibility pillars register anomalous host behaviour and "
                    "reachable resources stays at zero. Not blocked — position was "
                    "never worth anything."
                ),
                expert=(
                    "Compromised internal host, valid network position — terminal "
                    "in a boundary model. Reachable: zero. Not blocked; position "
                    "carries no authorization."
                ),
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
            description=L(
                novice=(
                    "The attacker tries the obvious next moves — reach a shared "
                    "drive, call an internal service, sign in to something nearby — "
                    "and each one is a fresh request that has to stand on its own "
                    "evidence. The stolen password does not come with a healthy "
                    "machine attached. The compromised computer does not have a "
                    "neighbourhood of other machines to sweep. Nothing is inherited "
                    "because nothing was accumulated. Meanwhile the automation has "
                    "already narrowed what that machine can even attempt, in "
                    "seconds rather than at the next review meeting. This is the "
                    "whole design in one step, and it is why the Department of "
                    "Defense assessed it against real attack rather than against a "
                    "checklist."
                ),
                plain=(
                    "The attacker tries the ordinary next steps — reach a file "
                    "share, call an internal API, authenticate to an adjacent "
                    "service — and each is a fresh request that has to stand on its "
                    "own evidence. The stolen credential does not come with a "
                    "healthy device posture. The compromised host does not have a "
                    "segment of neighbours to sweep. Nothing is inherited because "
                    "nothing was accumulated. Meanwhile automation has already "
                    "narrowed what that host can attempt, in seconds rather than at "
                    "the next review. This is the architecture in one step, and it "
                    "is why the DoD assessed the design against sophisticated "
                    "attack rather than a checklist."
                ),
                standard=(
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
                technical=(
                    "Lateral movement attempted — file share, internal API, "
                    "adjacent service authentication — each a fresh request "
                    "standing on its own evidence. The credential carries no device "
                    "posture; the host has no reachable neighbours to sweep. "
                    "Nothing inherited because nothing accumulated. Automation has "
                    "already constrained the host's attempt surface within seconds. "
                    "This step is the architecture, and the reason validation was "
                    "adversarial rather than checklist-based."
                ),
                expert=(
                    "Lateral movement: each hop a fresh per-request decision. "
                    "Credential carries no posture; microsegmentation leaves no "
                    "neighbours. Nothing inherited. Automated constraint applied "
                    "within seconds."
                ),
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
