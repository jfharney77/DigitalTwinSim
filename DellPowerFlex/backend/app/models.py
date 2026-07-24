"""Data models for the Dell PowerFlex software-defined storage twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, nodesOnline, rebuildParticipants,
protectedPercent, regionIds, ...), so the React frontend consumes responses
directly. None of the fields here camelize ambiguously (no embedded
numbers/acronyms), so no explicit aliases are needed — if you add one that
does, pin it with ``Field(alias=...)`` and check frontend/src/types.ts by
hand (see CLAUDE.md).

The twist versus the two storage twins already here: PowerStore and
PowerMax are *controller* architectures. PowerStore has two active-active
controller nodes; PowerMax has directors in node pairs. In both, every byte
a host writes flows through a controller, and that controller is
simultaneously the system's performance ceiling and its failure domain. The
whole engineering effort in those designs goes into making the controller
redundant enough that its centrality stops being frightening.

PowerFlex refuses the shape. Every server contributes its local NVMe to a
shared pool; volumes are chopped into chunks that are scattered and
mirrored across every node in that pool; and a client talks *directly* to
whichever nodes hold the chunks it wants. There is no controller tier at
all, which is why this twin's anatomy has no region that sits on every data
path — and why ``tests/test_anatomy.py`` checks that the one coordinating
component in the picture is the smallest thing in it.

The consequence worth building a twin for is what happens when a node dies.
In a controller array the surviving controller performs the rebuild: one
device reading, one device writing, hours of degraded exposure. Here every
surviving node rebuilds a sliver of the lost data simultaneously, from
every other node — so rebuild time *falls* as the cluster grows.
``rebuild_participants`` equals ``nodes_online`` during the rebuild, never a
subset, and ``tests/test_engine.py`` asserts exactly that.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "client",      # storage data clients — the servers consuming volumes
    "network",     # the IP fabric the pool runs over; there is no SAN here
    "coordinator", # metadata manager: maps chunks, referees failures
    "node",        # a server contributing local NVMe to the pool
    "protection",  # mirroring, erasure coding, and the rebuild engine
    "management",  # lifecycle, upgrade, and telemetry
]

# The life of a pool, in order — including the part that matters, which is
# a node dying and the cluster not caring very much.
ClusterPhase = Literal[
    "off",         # servers racked, local drives unpooled
    "cluster",     # nodes join; the metadata manager is elected
    "pool",        # local drives contributed; chunks scattered and mirrored
    "volumes",     # volumes presented; clients map them
    "io",          # steady state: clients talk straight to the nodes
    "failure",     # a node dies mid-flight
    "rebuild",     # every surviving node rebuilds a sliver, all at once
    "rebalanced",  # full protection restored on a smaller cluster
    "steady",      # back to normal, with one fewer server
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class ClusterRegion(CamelModel):
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


class ClusterAnatomy(CamelModel):
    """The pool map. ``width``/``height`` set the viewBox.

    Named like the VxRail twin's ``ClusterAnatomy`` because both subjects
    are clusters; the two apps are independent, so the name collision is
    only in the reader's head.
    """

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[ClusterRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class ClusterState(CamelModel):
    """One step in the life of a pool; pure data the renderer consumes.

    ``rebuild_participants`` is the field this twin exists for. In a
    controller array it would be 1, whatever the cluster size. Here it
    equals the number of surviving nodes, which is why recovery gets
    faster — not slower — as the system grows.
    """

    step: int
    phase: ClusterPhase
    label: str
    description: str
    # Region ids in the pool map lit up at this step.
    active_regions: list[str]
    # Servers contributing storage and participating in the pool.
    nodes_online: int = Field(ge=0)
    # Nodes actively rebuilding lost data. Zero outside a rebuild; equal to
    # nodes_online during one — never a subset.
    rebuild_participants: int = Field(ge=0)
    # Aggregate client I/O, thousands of operations per second. Notably
    # does not collapse when a node dies.
    iops_thousands: int = Field(ge=0)
    # Share of data currently holding its full protection level. Dips when
    # a node is lost and returns to 100 — it is not allowed to settle
    # anywhere else.
    protected_percent: int = Field(ge=0, le=100)
    # Illustrative wall-clock seconds since power was applied.
    elapsed_seconds: int
    # UI dwell ticks; the long stage here is building the pool, not
    # recovering from a failure — which is the point.
    cycle_cost: int = 1


class ClusterResponse(CamelModel):
    trace: list[ClusterState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to software-defined
    # storage; spell out jargon (SDS, SDC, metadata manager, mesh mirroring,
    # erasure coding, fault set, two-layer vs hyperconverged) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "3 to 2,000+ nodes"
    # Pool regions this category slots into (ids from anatomy.py).
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
