"""Use cases: three zero-trust adoptions, as backend data.

Each is a build sheet whose category and option ids must resolve against
``catalog.py`` — enforced in ``tests/test_catalog.py``. The narratives are
written for a reader who understands infrastructure but has not designed
around the assumption that the network is hostile.

All three turn on the same reversal from different angles: position grants
nothing. What differs is what the organization is defending against — a
nation-state, a supply chain, or its own sprawl.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="sovereign-classified",
        title="A sovereign environment that must assume it is already breached",
        summary=(
            "Classified work in a facility where the threat model includes "
            "a capable adversary already holding a position inside."
        ),
        narrative=[
            "Defence and intelligence environments start from an "
            "assumption most enterprises resist: an adversary with time, "
            "budget, and patience is inside, or will be. Once that is the "
            "premise, perimeter security stops being a partial answer and "
            "becomes an actively misleading one, because its entire value "
            "proposition is that the inside can be trusted.",
            "Zero trust is the design that survives the assumption. Every "
            "request is ruled on individually, so an intruder holding a "
            "credential and a network position holds two pieces of "
            "evidence rather than a key. Lateral movement — the step that "
            "converts a foothold into a catastrophe — has nowhere to go, "
            "because segments are small and each hop is a fresh decision. "
            "The breach step in this twin's trace is precisely this "
            "scenario, and the counter that matters stays at zero.",
            "Sovereignty adds the second requirement. The environment has "
            "to run on-premises, under the organization's own control, "
            "with no dependency on a provider's cloud identity service or "
            "on data leaving the jurisdiction. Project Fort Zero was "
            "assessed by the US Department of Defense in exactly that "
            "configuration — a sovereign, on-premises private cloud "
            "reaching Target Level validation — which is a different and "
            "more useful assurance than a feature comparison, because it "
            "grades the architecture rather than the inventory.",
        ],
        config=[
            UseCaseItem(
                category_id="policy", option_id="maturity", qty=1,
                rationale=(
                    "External grading of the architecture, not of a "
                    "feature list — the distinction that matters when a "
                    "single gap voids the rest."
                ),
            ),
            UseCaseItem(
                category_id="policy", option_id="pdp", qty=1,
                rationale=(
                    "Per-request decisions with expiry; nothing "
                    "accumulates for an intruder to inherit."
                ),
            ),
            UseCaseItem(
                category_id="network", option_id="microsegmentation", qty=1,
                rationale=(
                    "Lateral movement is the step that turns an incident "
                    "into a disaster, and it needs neighbours to reach."
                ),
            ),
            UseCaseItem(
                category_id="device", option_id="root-of-trust", qty=1,
                rationale=(
                    "Posture reporting is only meaningful if it is "
                    "anchored in hardware malware cannot forge."
                ),
            ),
            UseCaseItem(
                category_id="identity", option_id="mfa", qty=1,
                rationale=(
                    "Phishing-resistant credentials — the cheapest control "
                    "available against the most common entry."
                ),
            ),
            UseCaseItem(
                category_id="data", option_id="classification", qty=1,
                rationale=(
                    "A policy engine cannot be proportionate about a "
                    "resource whose sensitivity nobody recorded."
                ),
            ),
            UseCaseItem(
                category_id="automation", option_id="soar", qty=1,
                rationale=(
                    "An attacker measures opportunity in seconds; a "
                    "response measured in shifts is not a response."
                ),
            ),
            UseCaseItem(
                category_id="visibility", option_id="siem", qty=1,
                rationale=(
                    "Signals that are innocuous alone and damning "
                    "together."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Threat model", value="Adversary assumed already inside"),
            Stat(label="Value of a network foothold", value="Zero"),
            Stat(label="Deployment", value="Sovereign, on-premises"),
            Stat(label="Assurance", value="DoD Target Level validation"),
        ],
    ),
    UseCase(
        id="supply-chain",
        title="A manufacturer whose suppliers need access but not trust",
        summary=(
            "Hundreds of third parties reaching specific systems, without "
            "any of them being on a trusted network."
        ),
        narrative=[
            "The traditional answer to supplier access is a virtual "
            "private network, and it has a structural flaw that everyone "
            "quietly knows about: a VPN grants network presence, and "
            "network presence in a perimeter architecture is most of the "
            "way to everything. A supplier who needs to see one scheduling "
            "system ends up on a segment from which a great deal more is "
            "reachable, and their security posture becomes yours.",
            "Per-request authorization dissolves the problem rather than "
            "managing it. The supplier is granted the one application they "
            "need, for as long as they need it, on the basis of who they "
            "are and what device they are on — and nothing else becomes "
            "reachable, because nothing is reachable by virtue of "
            "position. There is no segment to be on. A compromised "
            "supplier is a compromised supplier rather than a compromised "
            "manufacturer.",
            "The work in this configuration is mostly on the workload "
            "pillar, and it is the honest hard part. Systems that suppliers "
            "reach are typically old, were written to trust anything that "
            "could connect to them, and cannot be modified. Wrapping them "
            "in enforcement points is the pragmatic answer: it does not "
            "make the application zero-trust-native, but it moves the "
            "decision from the network edge to the application's front "
            "door, which is a very large improvement for modest effort.",
        ],
        config=[
            UseCaseItem(
                category_id="workload", option_id="legacy-wrapping", qty=1,
                rationale=(
                    "The systems suppliers reach are old and cannot be "
                    "changed; enforcement in front of them is the "
                    "practical answer."
                ),
            ),
            UseCaseItem(
                category_id="policy", option_id="pep", qty=1,
                rationale=(
                    "Any path that misses an enforcement point is a path "
                    "where the old model still applies."
                ),
            ),
            UseCaseItem(
                category_id="identity", option_id="continuous-authz", qty=1,
                rationale=(
                    "A long-lived session token for a third party "
                    "reproduces the VPN problem in miniature."
                ),
            ),
            UseCaseItem(
                category_id="device", option_id="posture", qty=1,
                rationale=(
                    "The supplier's device hygiene is now an input to your "
                    "decisions rather than an assumption."
                ),
            ),
            UseCaseItem(
                category_id="network", option_id="encrypted-transit", qty=1,
                rationale=(
                    "Once there is no inside, unencrypted internal traffic "
                    "loses its justification."
                ),
            ),
            UseCaseItem(
                category_id="data", option_id="data-protection", qty=1,
                rationale=(
                    "Access control decides who may reach data; it does "
                    "not keep the data intact or recoverable."
                ),
            ),
            UseCaseItem(
                category_id="visibility", option_id="behaviour", qty=1,
                rationale=(
                    "A supplier account doing something out of character "
                    "should narrow on suspicion, not on proof."
                ),
            ),
            UseCaseItem(
                category_id="automation", option_id="adoption", qty=1,
                rationale=(
                    "Staged rollout, accepting that the weakest pillar "
                    "sets the real strength until it is done."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Supplier network presence", value="None"),
            Stat(label="Reachable per grant", value="One application"),
            Stat(label="Blast radius of a compromised supplier", value="That supplier"),
            Stat(label="Legacy systems", value="Wrapped, not rewritten"),
        ],
    ),
    UseCase(
        id="hybrid-estate",
        title="An enterprise whose perimeter stopped existing years ago",
        summary=(
            "Remote staff, three clouds, and contractors — an organization "
            "already without a boundary, formalizing the fact."
        ),
        narrative=[
            "The most common starting point is not a decision to adopt "
            "zero trust but the realization that the perimeter has already "
            "gone. Staff work from home, workloads run in three clouds, "
            "contractors come and go, and personal devices touch corporate "
            "data daily. The boundary still appears on architecture "
            "diagrams and no longer corresponds to anything. Security "
            "controls built on it are protecting a shape that dissolved.",
            "Adopting zero trust here is less a transformation than an "
            "admission, and that reframing is useful politically as well "
            "as technically: the argument is not 'let us build something "
            "radical' but 'let us stop pretending'. The practical work "
            "starts with the policy decision point and enforcement "
            "coverage, because a decision engine nothing enforces is a log "
            "and a path that misses enforcement is where the old "
            "assumptions survive.",
            "Two failure modes are worth naming in advance. Latency: a "
            "policy engine that answers slowly gets exceptions built "
            "around it, and the exceptions become permanent. And alert "
            "volume: continuous verification generates far more telemetry "
            "than a perimeter needs, and a system producing more alerts "
            "than anyone reviews has converted a security control into a "
            "compliance artefact. Both are organizational failures rather "
            "than technical ones, and both are how most adoptions actually "
            "stall.",
        ],
        config=[
            UseCaseItem(
                category_id="policy", option_id="pdp", qty=1,
                rationale=(
                    "The starting component — and the one whose latency "
                    "decides whether people route around the architecture."
                ),
            ),
            UseCaseItem(
                category_id="policy", option_id="pep", qty=1,
                rationale=(
                    "Inventorying every path to every resource honestly is "
                    "the hardest and most valuable step."
                ),
            ),
            UseCaseItem(
                category_id="identity", option_id="mfa", qty=1,
                rationale=(
                    "Phishing-resistant credentials across a workforce "
                    "that is no longer on any particular network."
                ),
            ),
            UseCaseItem(
                category_id="device", option_id="posture", qty=1,
                rationale=(
                    "Personal and contractor devices become inputs rather "
                    "than exceptions — but brittle rules produce "
                    "workarounds."
                ),
            ),
            UseCaseItem(
                category_id="workload", option_id="service-identity", qty=1,
                rationale=(
                    "Services across three clouds cannot rely on being "
                    "reachable only by each other."
                ),
            ),
            UseCaseItem(
                category_id="visibility", option_id="behaviour", qty=1,
                rationale=(
                    "Per-request decisions need per-request evidence, and "
                    "behaviour is the most useful kind."
                ),
            ),
            UseCaseItem(
                category_id="automation", option_id="adoption", qty=1,
                rationale=(
                    "Incremental adoption is normal; the weakest pillar "
                    "sets the actual strength until it closes."
                ),
            ),
            UseCaseItem(
                category_id="data", option_id="classification", qty=1,
                rationale=(
                    "Usually deferred, and deferring it caps how good "
                    "everything else can be."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Perimeter", value="Already gone; now acknowledged"),
            Stat(label="Decision scope", value="Per request, with expiry"),
            Stat(label="Main risk", value="Policy latency and alert volume"),
            Stat(label="Adoption", value="Staged, weakest pillar sets the strength"),
        ],
    ),
]
