"""Data models for the Dell circular-design lifecycle twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, massKg, recycledInputPercent,
reusedKg, reclaimedKg, lostKg, yearsInService, flowsTo, ...), so the React
frontend consumes responses directly. None of the fields here camelize
ambiguously (no embedded numbers/acronyms), so no explicit aliases are
needed — if you add one that does, pin it with ``Field(alias=...)`` and
check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus every other twin here: **the trace does not end.**

Every other trace in this repository terminates in the machine working —
``os``, ``steady``, ``ready``, ``offline``. The implicit claim is that
working forever is what machines do. It is not: every device modelled in
this repo will be decommissioned, and what happens next is either landfill
or the material input to the next generation. So this twin's map is drawn
as a cycle, its regions carry ``flows_to`` — the directed edges of the
loop — and its final phase, ``reborn``, lights the materials region the
trace started from.

The honesty mechanism is the ``loss`` region and the ``lost_kg`` counter.
A lifecycle map showing only the virtuous paths is marketing; this one
draws the leak, measures it, and — like the DellIR7000 twin's heat balance
— insists the books balance exactly: from recovery onward,
``reused_kg + reclaimed_kg + lost_kg == mass_kg``, no tolerance. Both
twins exist to say that something does not vanish just because it left
the diagram.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "materials",    # the material pool: recycled cobalt, copper, steel, plastics — plus virgin
    "manufacture",  # fabrication and assembly — the expensive step
    "packaging",    # recycled/renewable packaging feeding manufacture and shipping
    "deployment",   # devices in users' hands, doing work
    "service",      # repair and service-life extension — the largest lever
    "recovery",     # take-back: secure retirement, data sanitization, triage
    "refurbish",    # the inner return: whole devices back to deployment
    "reclaim",      # the outer return: shredded, sorted, smelted, back to materials
    "loss",         # the leak — material that does not come back. The only terminus.
]

# The life and afterlife of one device cohort, in order. `reborn` is the
# phase no other twin has: the output of this cycle is the input of the
# next one.
MaterialPhase = Literal[
    "materials",    # recovered + virgin material assembled as input
    "manufacture",  # fabrication and assembly (unique max cycle_cost)
    "ship",         # packed and shipped
    "deploy",       # in users' hands
    "serve",        # years of service
    "repair",       # a battery swap defers the whole recovery step
    "extend",       # refresh deferred; service life stretched past the no-repair baseline
    "recover",      # take-back and triage; the mass accounting begins
    "sort",         # refurbish / reclaim / loss — the three destinations
    "reborn",       # reclaimed material re-enters the materials pool
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class LifecycleRegion(CamelModel):
    id: str
    kind: RegionKind
    label: str
    x: float
    y: float
    w: float
    h: float
    description: str
    # The directed edges of the loop: ids of the regions material flows to
    # from here. The frontend draws arrows from these. `loss` is the only
    # region permitted an empty list — the only terminus, which is the
    # point — and tests/test_anatomy.py enforces exactly that.
    flows_to: list[str] = Field(default_factory=list)
    photo: Photo | None = None


class SourceLink(CamelModel):
    label: str
    url: str


class Stat(CamelModel):
    label: str
    value: str


class LifecycleMap(CamelModel):
    """The lifecycle map. ``width``/``height`` set the viewBox.

    Drawn as a cycle, not a left-to-right path: materials feed manufacture,
    manufacture feeds deployment, service loops devices back into
    deployment, and recovery forks three ways — the inner return
    (refurbish, back to deployment), the outer return (reclaim, back to
    materials), and the leak (loss, which goes nowhere, because that is
    what a leak is). ``tests/test_anatomy.py`` walks ``flows_to`` and pins
    the loop closed.
    """

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[LifecycleRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class MaterialState(CamelModel):
    """One step in the life and afterlife of a device cohort; pure data.

    ``lost_kg`` is the field this twin exists for. A trace claiming a
    perfectly closed loop would be lying, so the tests require the loss to
    be nonzero and stated. Its partner is the conservation identity —
    from ``recover`` onward, ``reused_kg + reclaimed_kg + lost_kg`` equals
    ``mass_kg`` exactly, the IR7000 heat balance applied to matter.
    """

    step: int
    phase: MaterialPhase
    label: str
    description: str
    # Region ids in the lifecycle map lit up at this step.
    active_regions: list[str]
    # Illustrative months since the cohort's material was assembled.
    elapsed_months: int
    # UI dwell ticks; the long stage is manufacture — the expensive step,
    # and the one every repair avoids repeating.
    cycle_cost: int = 1
    # Total mass in the cohort being traced. Constant: matter is neither
    # created nor destroyed by accounting.
    mass_kg: int = Field(ge=0)
    # How much of the input was already recovered material. Never zero —
    # and strictly higher on the second pass, which is the loop's thesis.
    recycled_input_percent: int = Field(ge=0, le=100)
    # The three destinations. Zero until recovery; then they sum to
    # mass_kg exactly, no tolerance.
    reused_kg: int = Field(ge=0)
    reclaimed_kg: int = Field(ge=0)
    lost_kg: int = Field(ge=0)
    # Service years accumulated so far. The repair steps push this past
    # what the no-repair path would have reached — the deferral the tests
    # demonstrate rather than assert.
    years_in_service: int = Field(ge=0)
    # Repairs performed; each one postpones an entire manufacturing cycle.
    repairs: int = Field(ge=0)


class MaterialResponse(CamelModel):
    trace: list[MaterialState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to circular design;
    # spell out jargon (closed-loop, hydrometallurgy, ITAD, embodied
    # carbon) on first use, and name the trade-offs plainly.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # the honest constraint, e.g. "rare elements recycle worst"
    # Lifecycle regions this category slots into (ids from anatomy.py).
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
