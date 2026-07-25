"""Component catalog: what you actually choose when adopting zero trust,
as backend data.

Written for a technically skilled reader new to the model: policy decision
point, policy enforcement point, microsegmentation, lateral movement, least
privilege, posture, SIEM/SOAR, and the DoD's Target and Advanced levels are
all spelled out on first use. Categories map to the pillars in
``anatomy.py`` via ``region_ids``, and ``tests/test_catalog.py`` enforces
that every id resolves.

The categories are the DoD's pillars rather than a product line, because
the model is an architecture and a gap in any pillar is a route around all
of them. That is also why there is no "perimeter" category: it is not that
Fort Zero has a better one, it is that the concept has been removed.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="policy",
        name="Policy decision and enforcement",
        blurb=(
            "The engine consulted on every request, and the points that "
            "carry out its rulings."
        ),
        limits="Per-request decisions with expiry; must answer in milliseconds",
        region_ids=["policy"],
        options=[
            CatalogOption(
                id="pdp",
                name="Policy decision point",
                summary=(
                    "One component combining all pillars into one ruling "
                    "for one request."
                ),
                details=(
                    "The policy decision point is where identity, device "
                    "posture, network context, workload, data sensitivity, "
                    "and analytics are combined into a verdict. Two "
                    "properties define it: the decision is per request, so "
                    "nothing accumulates, and it carries a lifetime, so "
                    "trust is a lease. The engineering constraint is "
                    "latency. This thing answers constantly, and if it is "
                    "slow the organization will build exceptions around it "
                    "— which is the most common way a zero-trust programme "
                    "quietly reverts to a perimeter."
                ),
            ),
            CatalogOption(
                id="pep",
                name="Policy enforcement points",
                summary=(
                    "Where the ruling is actually applied — gateways, "
                    "proxies, agents, service meshes."
                ),
                details=(
                    "A decision that nothing enforces is a log entry. "
                    "Enforcement points sit in front of applications, "
                    "inside service-to-service calls, and on endpoints. "
                    "The design question is coverage: any path to a "
                    "resource that does not pass an enforcement point is a "
                    "path where the old model still applies, and attackers "
                    "are extremely good at finding exactly those. "
                    "Inventorying them honestly is usually the hardest "
                    "part of an adoption."
                ),
            ),
            CatalogOption(
                id="maturity",
                name="Maturity level — Target or Advanced",
                summary=(
                    "The DoD grades zero-trust implementations; Fort Zero "
                    "is validated at Target Level."
                ),
                details=(
                    "The Department of Defense defines graded levels of "
                    "zero-trust maturity, and Project Fort Zero completed "
                    "assessment for Target Level as a sovereign, "
                    "on-premises private cloud in April 2025, tested "
                    "against sophisticated attack. The value of an "
                    "external grading is that it is an assessment of the "
                    "*architecture* rather than of a feature list — which "
                    "matters in a model where a single gap makes the other "
                    "controls irrelevant."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="identity",
        name="Identity",
        blurb=(
            "Who is asking — established strongly, and re-established "
            "continuously."
        ),
        limits="Multi-factor by default; authorization re-evaluated, not issued once",
        region_ids=["identity"],
        options=[
            CatalogOption(
                id="mfa",
                name="Strong authentication",
                summary=(
                    "Phishing-resistant multi-factor as the baseline, not "
                    "an option."
                ),
                details=(
                    "Multi-factor authentication is table stakes, and the "
                    "distinction that matters now is phishing resistance: "
                    "hardware-backed credentials that cannot be relayed to "
                    "an attacker's site, rather than codes a user can be "
                    "talked into reading aloud. In a zero-trust model the "
                    "credential is worth less than it is elsewhere — it "
                    "has to keep surviving examination — but making it "
                    "hard to steal is still the cheapest control available."
                ),
            ),
            CatalogOption(
                id="continuous-authz",
                name="Continuous authorization",
                summary=(
                    "Permission is re-evaluated during a session, not "
                    "granted at the start of one."
                ),
                details=(
                    "The difference between authentication and "
                    "authorization is where most of the value sits. "
                    "Authenticating well and then issuing an eight-hour "
                    "session token reproduces the perimeter in miniature: "
                    "one check at a gate, then trust. Continuous "
                    "authorization means the ruling is revisited while the "
                    "session runs, so a credential that becomes suspect "
                    "mid-session loses access without anyone filing a "
                    "ticket."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="device",
        name="Device",
        blurb=(
            "What the request comes from, and whether its state justifies "
            "trusting it today."
        ),
        limits="Posture evaluated per request; hardware root of trust",
        region_ids=["device"],
        options=[
            CatalogOption(
                id="posture",
                name="Device posture",
                summary=(
                    "Patch level, encryption, endpoint protection, "
                    "attestation — checked, not assumed."
                ),
                details=(
                    "Posture is the current state of the machine rather "
                    "than its enrolment status. A managed laptop is not "
                    "trustworthy because it is managed; it is trustworthy "
                    "while it is patched, encrypted, and reporting "
                    "cleanly. When any of that lapses, access narrows "
                    "automatically. This is also where much of the "
                    "user-experience risk lives: posture rules that are "
                    "too brittle generate exactly the friction that "
                    "produces workarounds."
                ),
            ),
            CatalogOption(
                id="root-of-trust",
                name="Hardware root of trust",
                summary=(
                    "Silicon-anchored attestation that the device is what "
                    "it claims to be."
                ),
                details=(
                    "Everything above depends on the machine reporting "
                    "honestly about itself, which is only meaningful if "
                    "the reporting is anchored in hardware that malware "
                    "cannot forge. Silicon Root of Trust and cryptographic "
                    "firmware signing give that anchor — this repo's iDRAC "
                    "twin covers the same machinery at the server level, "
                    "where a compromised management controller would "
                    "otherwise be able to lie about everything above it."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="network",
        name="Network",
        blurb=(
            "Location as evidence, and segmentation fine enough that a "
            "foothold has nowhere to go."
        ),
        limits="Microsegmentation; location never authorizes",
        region_ids=["network"],
        options=[
            CatalogOption(
                id="microsegmentation",
                name="Microsegmentation",
                summary=(
                    "Segments small enough that a compromised host has "
                    "almost nothing adjacent."
                ),
                details=(
                    "Lateral movement — an attacker with one foothold "
                    "working sideways to reach something valuable — is the "
                    "step that turns an incident into a disaster, and it "
                    "depends on there being neighbours to reach. "
                    "Microsegmentation shrinks the blast radius until "
                    "sideways is not a direction that goes anywhere. It is "
                    "the network pillar's real contribution, and it is "
                    "quite separate from the mistake of treating a segment "
                    "as trusted."
                ),
            ),
            CatalogOption(
                id="encrypted-transit",
                name="Encrypted transit everywhere",
                summary=(
                    "Including inside the datacenter, where it was "
                    "historically skipped."
                ),
                details=(
                    "Internal traffic went unencrypted for years on the "
                    "reasoning that the internal network was safe — the "
                    "perimeter assumption applied to the wire. Once there "
                    "is no inside, that reasoning evaporates and "
                    "service-to-service traffic is encrypted and "
                    "mutually authenticated like anything else. The cost "
                    "is real and mostly falls on legacy applications that "
                    "were never designed to identify themselves."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="workload",
        name="Application and workload",
        blurb=(
            "Services that authenticate to each other rather than trusting "
            "whoever can reach them."
        ),
        limits="Per-call authorization between services",
        region_ids=["workload"],
        options=[
            CatalogOption(
                id="service-identity",
                name="Workload identity",
                summary=(
                    "Every service has a credential; internal calls are "
                    "authorized like external ones."
                ),
                details=(
                    "This is the pillar that rearranges the most existing "
                    "software, because an enormous amount of enterprise "
                    "code assumes that anything able to reach it is "
                    "entitled to talk to it. Giving workloads their own "
                    "identities and authorizing each call is "
                    "straightforward for new services and genuinely "
                    "difficult for an estate of twenty-year-old ones, "
                    "which is why adoption is usually staged rather than "
                    "flipped."
                ),
            ),
            CatalogOption(
                id="legacy-wrapping",
                name="Wrapping legacy applications",
                summary=(
                    "Enforcement in front of software that cannot be "
                    "changed."
                ),
                details=(
                    "The pragmatic answer for applications that cannot "
                    "learn to authenticate: put an enforcement point in "
                    "front of them and let it make the decisions the "
                    "application cannot. It is not as good as a "
                    "zero-trust-native service — the application still "
                    "trusts whatever reaches it — but it moves the "
                    "boundary from the network edge to the application's "
                    "front door, which is a very large improvement for a "
                    "modest amount of work."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="data",
        name="Data",
        blurb=(
            "Classification and protection that travel with the resource "
            "rather than with its location."
        ),
        limits="Sensitivity is a property of the data, not the folder",
        region_ids=["data"],
        options=[
            CatalogOption(
                id="classification",
                name="Classification and labelling",
                summary=(
                    "Knowing what is sensitive, so decisions can be "
                    "proportionate."
                ),
                details=(
                    "A policy engine cannot make a proportionate decision "
                    "about a resource whose sensitivity nobody has "
                    "recorded — everything ends up either over-restricted "
                    "or under-protected. Classification is unglamorous, "
                    "usually incomplete, and the thing most likely to be "
                    "deferred; deferring it caps how good the rest of the "
                    "architecture can be."
                ),
            ),
            CatalogOption(
                id="data-protection",
                name="Protection at rest and in use",
                summary=(
                    "Encryption, immutability, and integrity verification "
                    "underneath access control."
                ),
                details=(
                    "Access control decides who may reach data; it does "
                    "not decide whether the data is intact or whether a "
                    "copy of it survives. Those are different questions "
                    "with different answers, both twinned separately in "
                    "this repo — the PowerProtect twin for isolation and "
                    "immutability, the Cyber Detect twin for verifying "
                    "that a copy is uncorrupted. A complete design needs "
                    "all three and they are frequently confused for one "
                    "another."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="visibility",
        name="Visibility and analytics",
        blurb=(
            "Far more telemetry than a perimeter needs, because decisions "
            "are made far more often."
        ),
        limits="Per-request evidence; behavioural baselines",
        region_ids=["visibility"],
        options=[
            CatalogOption(
                id="behaviour",
                name="Behavioural analytics",
                summary=(
                    "Comparing what an account is doing against what it "
                    "normally does."
                ),
                details=(
                    "If rulings are made per request, they need evidence "
                    "per request, and the most useful evidence is "
                    "behavioural: this account has never touched this "
                    "system, at this hour, at this rate. Feeding that into "
                    "the policy engine lets access narrow on suspicion "
                    "rather than on proof, which is the right threshold "
                    "when the alternative is waiting for certainty about "
                    "an intruder already inside."
                ),
            ),
            CatalogOption(
                id="siem",
                name="Aggregation and correlation",
                summary=(
                    "Security event management joining signals that are "
                    "innocuous alone."
                ),
                details=(
                    "Security information and event management collects "
                    "signals from every pillar so that patterns invisible "
                    "in any one of them become visible together — a "
                    "posture lapse, an unusual login hour, and a service "
                    "call that has never happened before, each "
                    "unremarkable and jointly not. The failure mode is "
                    "volume: a system generating more alerts than anyone "
                    "reviews has converted a security control into a "
                    "compliance artefact."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="automation",
        name="Automation and orchestration",
        blurb=(
            "Response measured in seconds, because that is the unit an "
            "attacker is working in."
        ),
        limits="Automated containment; human review after, not before",
        region_ids=["automation"],
        options=[
            CatalogOption(
                id="soar",
                name="Automated response",
                summary=(
                    "Narrowing access, forcing re-authentication, "
                    "isolating a host — without waiting for a person."
                ),
                details=(
                    "Security orchestration and automated response is the "
                    "pillar that decides whether the architecture is real "
                    "or aspirational. Continuous verification that "
                    "produces alerts for humans to triage in the morning "
                    "is a perimeter model with better logging. The "
                    "uncomfortable requirement is trusting automation to "
                    "act on incomplete evidence, which means accepting "
                    "some false positives — and designing the response so "
                    "a false positive is survivable rather than "
                    "catastrophic."
                ),
            ),
            CatalogOption(
                id="adoption",
                name="Staged adoption",
                summary=(
                    "Turnkey validated architecture versus building it "
                    "pillar by pillar."
                ),
                details=(
                    "Most organizations adopt zero trust incrementally and "
                    "spend years partially there, which is genuinely "
                    "better than not starting — but a partial "
                    "implementation has the property that its weakest "
                    "pillar sets its actual strength. A pre-integrated, "
                    "externally validated architecture like Fort Zero "
                    "trades flexibility for the assurance that no pillar "
                    "was quietly skipped, which is the specific "
                    "reassurance a graded assessment provides."
                ),
            ),
        ],
    ),
]
