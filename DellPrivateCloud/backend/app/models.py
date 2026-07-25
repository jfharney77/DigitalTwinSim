"""Data models for the Dell Private Cloud disaggregated-infrastructure twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, computeUnits, storageTb,
hypervisorsActive, workloadDowntimeSeconds, regionIds, ...), so the React
frontend consumes responses directly. None of the fields here camelize
ambiguously (no embedded numbers/acronyms), so no explicit aliases are
needed — if you add one that does, pin it with ``Field(alias=...)`` and
check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus the VxRail twin already here: that twin models
hyperconverged infrastructure, where each node contributes compute *and*
storage and the cluster grows by adding both together. Hyperconvergence
bought its famous simplicity with coupling — you scale in fixed ratios
whether or not the ratio is what you need, and the software stack that
makes the magic work is the software stack you are now married to.

Dell Private Cloud un-buys it. Compute, storage, and networking are pooled
separately and scale separately, one control plane spans all of them, and
the hypervisor sits on top as a swappable layer: VMware, Red Hat, Nutanix,
or Microsoft, with Nutanix support added in February 2026. Dell cites
research that 52% of IT leaders are considering multiple hypervisors
specifically to reduce lock-in, which is a fairly direct description of
what the last few years taught people.

So the subject here is not a component or a property but an *option*.
``workloads`` stays constant while storage doubles and while a second
hypervisor appears beside the first, and ``control_planes`` stays at one
throughout — because multi-hypervisor is only worth having if it does not
also mean multi-management. ``tests/test_engine.py`` asserts both.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "controlplane",  # one management plane over everything below
    "workload",      # the virtual machines and containers that actually matter
    "hypervisor",    # a swappable slot: VMware, Red Hat, Nutanix, Microsoft
    "compute",       # a pool of servers, scaled on its own
    "storage",       # a pool of storage, scaled on its own
    "network",       # a pool of networking, scaled on its own
    "fabric",        # what joins the pools, and why disaggregation works now
]

# The life of a private cloud that keeps its options open.
CloudPhase = Literal[
    "off",           # racks of separate compute, storage, and networking
    "pools",         # resources pooled independently — not fused into nodes
    "control",       # one control plane claims all three pools
    "install",       # a hypervisor is chosen and installed
    "deploy",        # workloads land
    "run",           # steady state
    "growstorage",   # storage runs short; storage alone is added
    "switch",        # some workloads move to a second hypervisor
    "mixed",         # two hypervisors, one control plane, steady
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class CloudRegion(CamelModel):
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


class CloudAnatomy(CamelModel):
    """The stack map. ``width``/``height`` set the viewBox.

    Drawn as layers rather than as a floorplan, because the subject is what
    is decoupled from what. The hypervisor band is four identical slots for
    exactly that reason.
    """

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[CloudRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class CloudState(CamelModel):
    """One step in the life of a private cloud; pure data.

    ``workload_downtime_seconds`` exists to be zero, and ``control_planes``
    exists to be one. Together they are the claim: you can change the shape
    of the infrastructure and the platform it runs on, and neither the
    workloads nor the people operating them have to care.
    """

    step: int
    phase: CloudPhase
    label: str
    description: str
    # Region ids in the stack map lit up at this step.
    active_regions: list[str]
    # Servers in the compute pool. Changes only when compute is added.
    compute_units: int = Field(ge=0)
    # Capacity in the storage pool, terabytes. Changes only when storage is
    # added — which is the whole difference from a hyperconverged node.
    storage_tb: int = Field(ge=0)
    # Hypervisors in use. Rises to two without anything else moving.
    hypervisors_active: int = Field(ge=0)
    # Virtual machines and containers running. Constant once deployed,
    # through both the storage expansion and the hypervisor migration.
    workloads: int = Field(ge=0)
    # Management planes the operators deal with. Always one — multi-
    # hypervisor is not worth having if it means multi-management.
    control_planes: int = Field(ge=0)
    # Interruption visible to the workloads. Always zero.
    workload_downtime_seconds: int = 0
    # Illustrative minutes since the build began.
    elapsed_minutes: int
    # UI dwell ticks; moving workloads between hypervisors is the long one,
    # because the freedom is real but it is not free.
    cycle_cost: int = 1


class CloudResponse(CamelModel):
    trace: list[CloudState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to private cloud;
    # spell out jargon (hyperconverged, disaggregated, three-tier,
    # hypervisor, control plane, live migration, lock-in) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "VMware, Red Hat, Nutanix, Microsoft"
    # Stack regions this category slots into (ids from anatomy.py).
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
