"""Data models for the Dell PowerScale scale-out NAS twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, capacityTb, usedPercent,
migrationsRequired, regionIds, ...), so the React frontend consumes
responses directly. None of the fields here camelize ambiguously (no
embedded numbers/acronyms), so no explicit aliases are needed — if you add
one that does, pin it with ``Field(alias=...)`` and check
frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus every other storage twin here: **there are no volumes.**

Conventional network-attached storage makes an administrator carve capacity
into fixed containers before anyone knows what will be needed. Reality then
diverges from the guess, and the rest of the system's life is spent on the
consequences — this volume 95% full while that one sits empty, and moving
capacity between them meaning a migration, a maintenance window, and a
negotiation with whoever owns the data.

OneFS — the operating system every PowerScale node runs — declines to
partition. One file system spans every node in the cluster. Adding a node
makes the single volume larger and the cluster redistributes data onto the
new hardware while clients keep reading. Two counters in ``NamespaceState``
exist to carry that argument: ``namespaces`` is 1 on every step at every
cluster size, and ``migrations_required`` is 0 forever — the administrative
cost conventional NAS pays quarterly and this architecture does not pay at
all. ``tests/test_engine.py`` asserts both.

This twin's sibling is DellPowerFlex: that one removed the *controller*
from block storage, this one removes the *volume* from file storage. Both
refusals buy the same freedom — the system's shape can change while it is
running.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "node",          # a PowerScale node: compute + memory + network + drives
    "media",         # the drives inside one node
    "protocol",      # NFS / SMB / S3 / HDFS access, reachable cluster-wide
    "interconnect",  # the back-end network the nodes stripe over
    "namespace",     # the single file system — the one shape spanning all nodes
    "management",    # cluster management and telemetry
]

# The life of a cluster, in order — including the part conventional NAS
# cannot do this way, which is growing without a migration.
NamespacePhase = Literal[
    "off",        # nodes racked, drives unjoined
    "form",       # nodes discover each other; OneFS forms one cluster
    "stripe",     # the single file system is laid out across every node
    "serve",      # NFS, SMB, S3, and HDFS all up, on every node
    "fill",       # data pours in; the one namespace fills
    "addnode",    # two nodes join; the volume simply becomes larger
    "rebalance",  # data redistributes onto the new hardware, live
    "served",     # steady state at six nodes — same single namespace
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
    """The cluster map. ``width``/``height`` set the viewBox.

    The one region worth staring at is the namespace: it is drawn as a
    single continuous shape spanning every node, and ``tests/test_anatomy.py``
    pins it as the *only* region whose horizontal extent does. Everything
    else in the picture belongs to a node or sits in a band; the namespace
    is the one thing that refuses to be partitioned, and the drawing has to
    say so.
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


class NamespaceState(CamelModel):
    """One step in the life of a cluster; pure data the renderer consumes.

    ``namespaces`` is the field this twin exists for. On a conventional NAS
    it would be a climbing count of provisioned volumes, each a future
    migration. Here it is 1, at four nodes and at six, forever. Its partner
    is ``migrations_required``, which is the bill conventional storage pays
    for having guessed wrong — and which stays at zero across the expansion,
    because there is no container boundary for data to be moved across.
    """

    step: int
    phase: NamespacePhase
    label: str
    description: str
    # Region ids in the cluster map lit up at this step.
    active_regions: list[str]
    # Illustrative wall-clock seconds since power was applied.
    elapsed_seconds: int
    # UI dwell ticks; the long stage is rebalancing onto new nodes — slow,
    # and the price of never having to migrate.
    cycle_cost: int = 1
    # Nodes participating in the cluster: 4, then 6 after expansion.
    nodes: int = Field(ge=0)
    # Exists to be 1. At every cluster size. This twin's droppedPackets.
    namespaces: int = Field(ge=0)
    # Raw capacity of the single file system. Grows only when nodes join —
    # never because anyone planned, carved, or provisioned anything.
    capacity_tb: int = Field(ge=0)
    # How full the one namespace is. Rises toward the expansion, falls
    # after it — as a consequence of new hardware, not of anything being
    # deleted or moved by hand.
    used_percent: int = Field(ge=0, le=100)
    # Also exists to be zero. The administrative cost of growth.
    migrations_required: int = Field(ge=0)
    # True while AutoBalance redistributes data onto new nodes — with
    # clients still being served, which the tests insist on.
    rebalancing: bool = False


class NamespaceResponse(CamelModel):
    trace: list[NamespaceState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to scale-out NAS;
    # spell out jargon (OneFS, NFS/SMB/S3/HDFS, erasure coding, node pool)
    # on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "3 to 252 nodes in one cluster"
    # Cluster regions this category slots into (ids from anatomy.py).
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
