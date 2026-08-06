"""Data models for the Quantum-X800 InfiniBand fabric digital twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, fabricTbps, packetsSentWithoutCredit,
regionIds, ...), so the React frontend can consume responses directly. None
of the fields here camelize ambiguously (no embedded numbers/acronyms), so
no explicit aliases are needed — if you add one that does, pin it with
``Field(alias=...)`` and check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus the SN6000 Ethernet-fabric twin: that fabric must *prove*
it is lossless — Ethernet drops by default, so Spectrum-X layers ECN, PFC,
and adaptive routing on top and the twin drives a congestion step to show
zero drops under stress. InfiniBand starts from the opposite premise:
**lossless by construction**. A sender may not transmit until the receiver
has granted buffer credits, so a packet is never sent without a place to
land — the failure mode is waiting, never losing. Three architectural
consequences shape this twin: a *centralized* subnet manager discovers the
fabric and installs every routing table before a byte moves (the fabric is
programmed, not converged); congestion appears as brief credit stalls, not
drops; and SHARP moves the all-reduce arithmetic into the switch ASICs, so
less data crosses the fabric while more useful work completes. This is the
fabric NVIDIA ships as Quantum-X800 and Dell delivers in IRSS racks — the
interconnect TACC's Horizon names.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "spine",     # Quantum-X800 spine switches — every leaf reaches every one
    "leaf",      # leaf (top-of-rack) switches — where the GPU racks attach
    "endpoint",  # the GPU racks themselves, as fabric endpoints (ConnectX-8)
    "manager",   # the subnet manager (UFM) — the fabric's centralized brain
    "optics",    # the cabling layer: OSFP transceivers and fibre
    "cooling",   # liquid cooling for the switch silicon
]

# The fabric's life, in order: a centrally-programmed bring-up, then a
# training step's collective — offloaded into the switches by SHARP — and
# the incast burst that credits absorb without loss.
FabricPhase = Literal[
    "off",         # racked and cabled, dark
    "power",       # switches energize; liquid loop takes their heat
    "discover",    # the subnet manager sweeps the fabric — one brain, whole map
    "routes",      # the SM computes and installs every forwarding table
    "credits",     # receivers grant buffer credits; losslessness switches on
    "ready",       # fabric idle and ready, no job traffic yet
    "collective",  # an all-reduce runs — every GPU exchanging gradients
    "sharp",       # SHARP moves the reduction into the switch ASICs
    "burst",       # incast: senders stall on credits — waiting, never losing
    "steady",      # the training loop's traffic pattern, sustained
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class FabricRegion(CamelModel):
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


class FabricAnatomy(CamelModel):
    """The leaf/spine topology map. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[FabricRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class FabricState(CamelModel):
    """One step of the fabric's life; pure data the renderer consumes.

    ``packets_sent_without_credit`` exists to be zero — and unlike a drop
    counter it is zero *by construction*: transmission without a granted
    credit is not an error the fabric catches, it is a thing the link layer
    cannot express. ``stall_micros_per_sec`` is the honest ledger of what
    losslessness costs instead: under incast, senders wait.
    """

    step: int
    phase: FabricPhase
    label: str
    description: str
    # Region ids in the fabric map lit up at this step.
    active_regions: list[str]
    # Aggregate traffic crossing the fabric, terabits per second.
    fabric_tbps: int
    # Utilization of the busiest link, percent.
    peak_link_percent: int = Field(ge=0, le=100)
    # Packets transmitted without a granted receiver credit. Always zero:
    # InfiniBand's link layer has no way to say it.
    packets_sent_without_credit: int = 0
    # Time senders spent waiting for credits, microseconds per second —
    # nonzero only under the incast burst. Waiting is the price of never
    # losing; an honest twin shows the bill.
    stall_micros_per_sec: int = 0
    # Effective all-reduce rate the job observes, gigabits per second.
    # Rises when SHARP does the arithmetic in-fabric even as raw
    # fabric_tbps falls — less data crossing, more work finishing.
    allreduce_gbps: int = 0
    # Illustrative wall-clock seconds since power was applied.
    elapsed_seconds: int
    # UI dwell ticks; long stages (central route computation) get more.
    cycle_cost: int = 1


class FabricResponse(CamelModel):
    trace: list[FabricState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to InfiniBand;
    # spell out jargon (subnet manager, credit-based flow control, SHARP,
    # fat tree, OSFP, SuperNIC, ...) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "144 ports of 800 Gb/s per Q3400 chassis"
    # Fabric regions this category slots into (ids from anatomy.py).
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
