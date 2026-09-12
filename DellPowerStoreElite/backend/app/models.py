"""Data models for the PowerStore Elite digital twin.

Same conventions as the other twins: snake_case in Python, camelCase over
the wire (activeRegions, iopsThousands, generationsInCluster, ...), so the
React frontend can consume responses directly. None of the fields here
camelize ambiguously (no embedded numbers/acronyms), so no explicit aliases
are needed — if you add one that does, pin it with ``Field(alias=...)`` and
check frontend/src/types.ts by hand (see CLAUDE.md).

The model shapes deliberately mirror the DellPowerStore twin's — the map is
still a ``ChassisAnatomy`` of ``ChassisRegion``s, because the subject is
still hardware in racks. What changes is the trace: this twin's story is not
a power-on but a *cluster join* — an existing PowerStore adopting a
PowerStore Elite appliance live, with the workloads never noticing — so the
per-step telemetry is ``JoinState``: served IOPS, effective capacity, how
many hardware generations share the cluster, and a downtime counter whose
entire purpose is to stay at zero.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "storage",     # NVMe drive bays + backplanes (prior 2.5″, Elite E3)
    "nvram",       # NVMe NVRAM write-cache slots
    "cpu",         # per-node Xeon socket + heatsink
    "memory",      # per-node DIMM banks (DDR5 on Elite)
    "io",          # front-end ports and hot-swap I/O modules
    "power",       # per-node PSUs
    "cooling",     # per-node fan packs
    "battery",     # battery backup units (cache vaulting)
    "management",  # management / service ports
    "board",       # node system boards and the cluster RDMA mesh
]

# The lifecycle of a modernization, not a boot: an old array serving,
# an Elite appliance waking beside it, the two fusing into one
# mixed-generation cluster, and the workloads rebalancing live.
JoinPhase = Literal[
    "steady",     # the prior-generation array serving I/O, alone
    "power",      # the Elite appliance racked, cabled, waking (dual-node)
    "join",       # Elite joins the existing cluster — generations become 2
    "mesh",       # the 200 Gb RDMA node interconnect links the appliances
    "rebalance",  # volumes migrate live across the mesh (the longest stage)
    "cutover",    # Elite becomes the primary server — performance triples
    "repurpose",  # the prior array takes a second role instead of a skip
    "elite",      # steady state on Elite, mixed-generation cluster intact
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """A photograph of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class ChassisRegion(CamelModel):
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


class ChassisAnatomy(CamelModel):
    """The cluster map: two appliances of different generations joined by
    the RDMA mesh. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[ChassisRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class JoinState(CamelModel):
    """One step of the cluster-join sequence; pure data the renderer consumes."""

    step: int
    phase: JoinPhase
    label: str
    description: str
    # Region ids in the cluster anatomy lit up at this step.
    active_regions: list[str]
    # Thousands of IOPS the cluster is serving hosts right now. Never zero:
    # service continuing through the whole modernization is the product claim.
    iops_thousands: int
    # Host-visible downtime, in seconds, accumulated so far. This field
    # exists to be zero — the twin's whole reason for existing.
    downtime_seconds: int
    # Hardware generations sharing the one cluster (1 → 2 at the join).
    generations_in_cluster: int = Field(ge=1, le=2)
    # Effective capacity (TB) the cluster presents, after data reduction.
    effective_tb: int
    # Illustrative wall-clock seconds since the Elite was racked (not
    # measured timing; the rebalance runs hours in real life).
    elapsed_seconds: int
    # UI dwell ticks; long stages (the live rebalance) get more.
    cycle_cost: int = 1


class JoinResponse(CamelModel):
    trace: list[JoinState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to storage arrays;
    # spell out Dell jargon (E3 NVMe, RDMA, data reduction ratio, ...) on
    # first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "40 drive slots per appliance"
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
