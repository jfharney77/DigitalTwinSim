"""Data models for the Dell Pro Max 16 Plus on-device inference twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, weightsResidentGb, linkGbps,
tokensPerSecond, regionIds, ...), so the React frontend consumes responses
directly. None of the fields here camelize ambiguously (no embedded
numbers/acronyms), so no explicit aliases are needed — if you add one that
does, pin it with ``Field(alias=...)`` and check frontend/src/types.ts by
hand (see CLAUDE.md).

The twist versus every other compute twin in this repo: those are about
moving data fast. The XE9712 fuses 72 GPUs so gradients can cross at
1.8 TB/s; the SN6000 carries traffic between racks without dropping it; the
Exascale rack fans out reads from four data servers at once. This twin is
about the opposite move — **not** transferring. A model is compiled ahead
of time, loaded across the PCIe boundary once, and then it simply stays
there. Inference stops being a data-movement problem the moment the whole
model fits in memory that never has to be refilled.

That is why the subject is the *discrete NPU*, not the laptop around it.
The Dell Pro Max 16 Plus is the first mobile workstation with an
enterprise-grade discrete Neural Processing Unit: a Qualcomm AI 100 PC
Inference Card carrying two AI-100 NPUs, 32 AI cores, and 64 GB of
dedicated on-card AI memory — enough to hold a model of roughly 120 billion
parameters resident, at FP16, with no network connection at all.

``link_gbps`` is on every state and is nonzero during exactly one phase.
That is enforced in ``tests/test_engine.py`` and is the twin's whole point.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

RegionKind = Literal[
    "host",      # the host CPU — orchestrates, then gets out of the way
    "memory",    # system DRAM, on the host side of the boundary
    "storage",   # NVMe SSD: where the compiled model file lives at rest
    "link",      # the PCIe boundary the weights cross exactly once
    "npu",       # the AI-100 inference SoCs on the card
    "aimemory",  # 64 GB of dedicated on-card AI memory — the whole trick
    "thermal",   # vapor chamber and fans: sustained inference is a heat problem
    "power",     # adapter and battery rail feeding the card
    "runtime",   # compiler and runtime: ONNX to a hardware-specific container
]

# The life of a model on this machine, in order. It begins offline (a
# compile step that happens once, on a build machine) and ends offline
# (the network disconnected, with nothing changing) — which is the point.
InferencePhase = Literal[
    "off",        # laptop closed; the model is a file on disk
    "compile",    # ONNX graph → hardware-specific container, ahead of time
    "load",       # weights stream over PCIe into on-card AI memory
    "resident",   # the model is in place; the bus goes quiet for good
    "prefill",    # the prompt is processed in parallel — compute-bound
    "decode",     # tokens generated one at a time — memory-bandwidth-bound
    "sustained",  # a long generation continues at flat wattage, no throttle
    "offline",    # the network is disconnected and nothing changes
]


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Photo(CamelModel):
    """An image of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class DeviceRegion(CamelModel):
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


class DeviceAnatomy(CamelModel):
    """The inference-path floorplan. ``width``/``height`` set the viewBox."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[DeviceRegion]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class InferenceState(CamelModel):
    """One step in the life of a model on this machine; pure data.

    ``link_gbps`` exists to be zero. Traffic across the PCIe boundary is
    the thing a discrete accelerator is normally accused of — the bus is
    supposed to be the bottleneck. Here it is busy during exactly one
    phase and silent for every step of actual inference, because the
    weights are already on the far side of it.
    """

    step: int
    phase: InferencePhase
    label: str
    description: str
    # Region ids in the device map lit up at this step.
    active_regions: list[str]
    # Model weights resident in on-card AI memory, gigabytes. Monotonic,
    # and never evicted once the model is in place — no layer swapping is
    # what makes the token latency predictable.
    weights_resident_gb: int = Field(ge=0)
    # Traffic across the PCIe boundary, Gb/s. Nonzero during the load
    # phase and nowhere else.
    link_gbps: int = Field(ge=0)
    # Generation rate. Zero until the model is fully resident.
    tokens_per_second: int = Field(ge=0)
    # Card power draw, watts. Flat under sustained load — the discrete-NPU
    # claim versus a GPU that spikes and then thermally throttles.
    npu_watts: int = Field(ge=0)
    # Illustrative wall-clock seconds since the run began.
    elapsed_seconds: int
    # UI dwell ticks; long stages (loading 61 GB of weights) get more.
    cycle_cost: int = 1


class InferenceResponse(CamelModel):
    trace: list[InferenceState]


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to on-device
    # inference; spell out jargon (NPU, TOPS, FP16, quantization, ONNX,
    # prefill/decode, KV cache, mixture-of-experts) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "64 GB of on-card AI memory"
    # Device regions this category slots into (ids from anatomy.py).
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
