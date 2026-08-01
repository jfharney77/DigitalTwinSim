"""Data models for the Exascale Storage + Lightning File System twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, throughputGbps, dataServersStreaming,
regionIds, ...), so the React frontend can consume responses directly. None
of the fields here camelize ambiguously (no embedded numbers/acronyms), so
no explicit aliases are needed — if you add one that does, pin it with
``Field(alias=...)`` and check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus the block-storage twins (PowerStore, PowerMax): those move
every byte through a controller. A **parallel** file system deliberately
does not. Dell's Lightning File System — the production form of Project
Lightning, built on PowerScale's OneFS using pNFS (parallel NFS) with a
metadata server and Flex Files layouts — splits the two jobs apart: a
client asks a metadata server *where* a file's stripes live, gets a layout,
and then reads those stripes straight from many data servers at once, with
the metadata server no longer in the path. That separation is this twin's
whole subject, and ``tests/test_engine.py`` enforces it.

Exascale Storage is the rack that unifies the engines — PowerFlex (block),
PowerScale and Lightning (file), ObjectScale (object) — into one footprint
feeding an AI factory at multiple TB/s.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "client",      # GPU compute racks — the readers and checkpoint writers
    "fabric",      # the scale-out network between clients and storage
    "metadata",    # Lightning metadata server: hands out layouts, then steps aside
    "dataserver",  # data servers holding the stripes — the parallel read path
    "media",       # the NVMe flash behind the data servers
    "protocol",    # the multi-protocol engines (file / object / block)
    "management",  # the control plane over the Exascale rack
]

# The life of an AI training job's data, in order. The client mounts,
# fetches a layout, then streams stripes in parallel; GPUs saturate; a
# checkpoint burst writes back; cold data tiers to object; steady state.
DataPhase = Literal[
    "idle",        # rack online, no job attached
    "mount",       # client mounts the parallel filesystem
    "layout",      # client asks the metadata server where the stripes live
    "stripe",      # parallel read fans out across data servers — MDS steps aside
    "feed",        # GPUs saturated; the file system is at full read throughput
    "checkpoint",  # training checkpoint written back across the same stripes
    "tier",        # cold data ages from file to object within the rack
    "steady",      # the loop runs: read, train, checkpoint, repeat
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class PlatformRegion(CamelModel):
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


class PlatformAnatomy(CamelModel):
    """The data-path map, annotated. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[PlatformRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class DataState(CamelModel):
    """One step of the data path; pure data the renderer consumes.

    ``data_servers_streaming`` is the twin's headline number: a parallel
    file system's throughput is the *sum* of many servers streaming at
    once, not one controller's ceiling, so this counter and
    ``throughput_gbps`` rise together.
    """

    step: int
    phase: DataPhase
    label: str
    description: str
    # Region ids in the platform map lit up at this step.
    active_regions: list[str]
    # Aggregate throughput across the rack, gigabits per second.
    throughput_gbps: int
    # How many data servers are streaming in parallel right now (0–4 drawn).
    data_servers_streaming: int = Field(ge=0, le=4)
    # Whether the client currently holds a layout (pNFS delegation) telling
    # it where the stripes live. Once held, reads bypass the metadata server.
    layout_held: bool = False
    # Illustrative wall-clock seconds since the job attached.
    elapsed_seconds: int
    # UI dwell ticks; long stages (the checkpoint burst) get more.
    cycle_cost: int = 1


class DataResponse(CamelModel):
    trace: list[DataState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to parallel storage;
    # spell out jargon (pNFS, layout, stripe, OneFS, GPUDirect, RDMA, ...)
    # on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "6 TB/s per Exascale rack"
    # Platform regions this category slots into (ids from anatomy.py).
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
