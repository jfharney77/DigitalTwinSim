"""Data models for the Dell Project Fort Zero zero-trust twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, resourcesReachable,
implicitTrustGrants, trustTtlSeconds, regionIds, ...), so the React
frontend consumes responses directly. None of the fields here camelize
ambiguously (no embedded numbers/acronyms), so no explicit aliases are
needed — if you add one that does, pin it with ``Field(alias=...)`` and
check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus every other twin in this repo: they all have a boundary,
and their lesson usually lives in it. The Pro Max Plus twin draws a PCIe
strip and pins that weights cross it once. The PowerProtect twin draws an
air gap and pins that the attack cannot cross it. The PowerFlex twin draws
a client band and a node band with nothing between. Boundaries are how
architecture diagrams normally carry meaning, and how security has
historically been designed: establish a perimeter, verify at it, and treat
what is behind it as safe.

Zero trust abolishes the idea. There is no inside. A request originating on
the corporate network, from a managed laptop, by an authenticated employee,
is granted nothing by any of those facts — they are *evidence* considered
by a policy decision, not authorization in themselves. So this twin's map
is deliberately drawn with no enclosing shape at all: seven co-equal
pillars around a central policy engine, and ``tests/test_anatomy.py``
asserts that nothing in it is large enough to be a perimeter.

Project Fort Zero is Dell's turnkey implementation, and in April 2025 it
completed the US Department of Defense's assessment for **Target Level**
zero-trust validation as a sovereign, on-premises private cloud — which is
the reason its pillars map onto the DoD's model rather than onto a vendor's
marketing.

``implicit_trust_grants`` is on every state and is zero on every step,
including at the moment an attacker is loose inside the network.
``tests/test_engine.py`` asserts exactly that.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# The seven pillars of the DoD zero-trust reference architecture, plus the
# policy engine that decides using all of them. The pillars are co-equal by
# design — none is the "main" one, and the geometry says so.
RegionKind = Literal[
    "identity",    # who is asking — user, credential, multi-factor
    "device",      # what they are asking from, and its posture
    "network",     # where the request came from — evidence, never permission
    "workload",    # the application or service being reached
    "data",        # the resource itself, classified and labelled
    "visibility",  # analytics: what is happening, continuously
    "automation",  # orchestrated response, faster than a human
    "policy",      # the decision point, consulted on every single request
]

# The life of one access request under continuous verification, and then a
# breach that gains nothing from being inside.
AccessPhase = Literal[
    "idle",       # no session exists; nothing is trusted
    "request",    # a user asks for a resource
    "verify",     # identity and device posture are established
    "context",    # location, time, behaviour — gathered as evidence only
    "decide",     # the policy engine rules on this request, using all pillars
    "grant",      # least-privilege access to one resource, for a limited time
    "monitor",    # continuous verification while the session lives
    "expire",     # trust runs out; the next request starts from nothing
    "breach",     # an attacker compromises a host inside the network
    "contained",  # and reaches nothing, because location grants nothing
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class Pillar(CamelModel):
    """One pillar of the architecture, or the policy engine at the centre."""

    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str
    photo: Photo | None = None


class SourceLink(CamelModel):
    label: str
    url: str


class Stat(CamelModel):
    label: str
    value: str


class ZeroTrustMap(CamelModel):
    """The architecture map. ``width``/``height`` set the viewBox.

    Named ``Map`` rather than ``Anatomy`` for the same reason the iDRAC twin
    uses ``SubsystemMap``: the subject is not a physical object. Here it is
    a decision architecture, and the significant property of the drawing is
    what it lacks — any shape big enough to be a perimeter.
    """

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[Pillar]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class AccessState(CamelModel):
    """One step in the life of an access request; pure data.

    ``implicit_trust_grants`` exists to be zero. Every access in this trace
    is authorized by a decision made for that specific request, never by
    where it came from, what network it is on, or the fact that something
    similar was allowed a moment ago. The counter is carried explicitly so
    that its flatness is visible at the exact step where a perimeter model
    would have failed.
    """

    step: int
    phase: AccessPhase
    label: str
    description: str
    # Pillar ids in the map lit up at this step.
    active_regions: list[str]
    # Confidence in this specific request, percent. Not durable — it decays
    # and has to be re-established.
    trust_score: int = Field(ge=0, le=100)
    # Resources this session can currently reach. Least privilege means at
    # most one, and never a network segment.
    resources_reachable: int = Field(ge=0)
    # Accesses granted on the basis of position rather than a decision.
    # Always zero; that is the architecture.
    implicit_trust_grants: int = 0
    # Verifications performed so far. Climbs continuously during a session,
    # because one check at the door is not the model.
    verifications: int = Field(ge=0)
    # How long the current grant remains valid. Zero when nothing is
    # granted — trust here is a lease, not a property.
    trust_ttl_seconds: int = Field(ge=0)
    # Illustrative seconds since the request began.
    elapsed_seconds: int
    # UI dwell ticks; continuous monitoring is the long one, which is the
    # honest shape of the cost.
    cycle_cost: int = 1


class AccessResponse(CamelModel):
    trace: list[AccessState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to zero trust; spell
    # out jargon (policy decision point, policy enforcement point,
    # microsegmentation, lateral movement, least privilege, posture,
    # SIEM/SOAR, Target Level) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "DoD Target Level validated"
    # Pillars this category slots into (ids from anatomy.py).
    region_ids: list[str] = Field(default_factory=list)
    options: list[CatalogOption]


class UseCaseItem(CamelModel):
    category_id: str
    option_id: str
    qty: int
    rationale: str


class UseCase(CamelModel):
    id: str
    title: str
    summary: str
    narrative: list[str]  # paragraphs
    config: list[UseCaseItem]
    outcomes: list[Stat] = Field(default_factory=list)
