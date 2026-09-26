"""Data models for the iDRAC9 digital twin.

Same conventions as the PowerEdge R760 app: snake_case in Python, camelCase
over the wire (activeRegions, powerWatts, regionIds, ...), so the React
frontend can consume responses directly. None of the fields here camelize
ambiguously (no embedded numbers/acronyms), so no explicit aliases are
needed — if you add one that does, pin it with ``Field(alias=...)`` and check
frontend/src/types.ts by hand (see CLAUDE.md).

The twin's subject is a *subsystem*, not a chassis: the iDRAC9 baseboard
management controller (BMC) as a functional block diagram. So the shared
"anatomy" shape describes iDRAC's blocks and the buses that connect it to the
host and the outside world, and the "bring-up" trace is iDRAC's own firmware
boot from AC-applied standby to a ready, watching service processor.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from twinkit.models import CamelModel

RegionKind = Literal[
    "soc",       # the BMC system-on-chip / iDRAC service processor
    "memory",    # DRAM working memory + flash (firmware, Lifecycle Controller)
    "network",   # dedicated management NIC
    "sideband",  # host management buses: I2C/PMBus, eSPI/PECI, NC-SI
    "io",        # remote presence: virtual console, virtual media, iDRAC Direct
    "power",     # always-on standby power domain
    "security",  # silicon Root of Trust / cryptographic verification
    "sensor",    # monitoring + thermal-control engine
]

# iDRAC's own firmware bring-up, from no-AC to a ready service processor.
BringUpPhase = Literal[
    "off",       # no AC — the BMC domain is dark
    "standby",   # PSU standby rail energizes the always-on BMC domain
    "reset",     # SoC released from reset; boot ROM + Root of Trust
    "bootldr",   # first-stage bootloader (U-Boot): DRAM init, load firmware
    "kernel",    # embedded Linux boots; sideband + NIC drivers come up
    "services",  # management services + Lifecycle Controller initialize
    "ready",     # reachable, console live, watching the host out-of-band
]

# The firmware-update failure scenario (``engine.simulate_firmware_rollback``)
# starts where the bring-up ends — at ``ready`` — and walks its own phases.
# Additive: the bring-up trace never carries any of these.
UpdatePhase = Literal[
    "upload",     # the update package arrives over the management network
    "verify",     # its signature is checked against the Root of Trust
    "stage",      # the image is written to the *inactive* flash partition
    "reboot",     # iDRAC restarts; management is lost, the host is not
    "bootcheck",  # the new image is verified at boot, and fails
    "rollback",   # the bootloader falls back to the previous partition
    "restored",   # iDRAC is back on the old version, with a log entry
]

FlashPartition = Literal["A", "B"]


class Photo(CamelModel):
    """A photograph of the part; ``credit`` must always be rendered by the UI."""

    url: str
    caption: str
    credit: str


class Block(CamelModel):
    """One functional block of the iDRAC subsystem, placed in a normalized
    coordinate space the frontend renders as SVG."""

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


class SubsystemMap(CamelModel):
    """The iDRAC block diagram, annotated. ``width``/``height`` set the
    viewBox; ``regions`` are the functional blocks."""

    id: str
    name: str
    vendor: str
    form_factor: str
    generation: str
    year: int
    width: float
    height: float
    regions: list[Block]
    stats: list[Stat]
    sources: list[SourceLink] = Field(default_factory=list)
    overview: str
    photo: Photo | None = None


class BringUpState(CamelModel):
    """One step of the iDRAC bring-up sequence; pure data the renderer
    consumes. The clock lives in the frontend, never here."""

    step: int
    phase: BringUpPhase | UpdatePhase
    label: str
    description: str
    # Block ids in the subsystem map lit up at this step.
    active_regions: list[str]
    # Illustrative draw of the always-on BMC power domain (a few watts).
    power_watts: int
    # iDRAC initialization progress, 0–100 (not host boot progress).
    progress_percent: int = Field(ge=0, le=100)
    # Illustrative wall-clock seconds since AC plug-in (not measured timing).
    elapsed_seconds: int
    # UI dwell ticks; long stages (Lifecycle Controller init) get more.
    cycle_cost: int = 1

    # --- Failure-scenario fields (additive) --------------------------------
    # All default to None and the bring-up trace never sets them; the trace
    # route drops None fields, so the happy path's wire format is unchanged.
    # Is the host (the server proper) powered? The scenario's first invariant:
    # it is True on every step — an iDRAC update never touches the workload.
    host_powered: bool | None = None
    # Which flash partition iDRAC is running from, and what each side holds.
    active_partition: FlashPartition | None = None
    running_version: str | None = None
    # The partition being written at this step, if any — never the active one.
    writing_partition: FlashPartition | None = None
    # True once the uploaded package's signature has been verified.
    signature_verified: bool | None = None
    # How many flash partitions iDRAC counts as holding a bootable image.
    # Never zero. It is iDRAC's view, not ground truth: between the damaged
    # write and the failed boot check it reads 2 while only A would boot,
    # and the running partition keeps the true count at 1 or more throughout.
    bootable_images: int | None = None
    # Can an administrator reach iDRAC (web console, Redfish, RACADM)?
    management_reachable: bool | None = None
    # The hero number: cumulative seconds the management plane was dark.
    # Illustrative, and bounded.
    management_outage_seconds: int | None = None
    # Blocks to draw in the error colour (a subset of the map's ids).
    failed_regions: list[str] | None = None
    # What the Lifecycle log or job queue shows the administrator at this step.
    log_entry: str | None = None


class BringUpResponse(CamelModel):
    trace: list[BringUpState]


class ScenarioInfo(CamelModel):
    """One selectable trace: the bring-up, or a failure scenario. ``sources``
    are the documents the scenario's behaviour is drawn from."""

    id: str
    name: str
    summary: str
    phases: list[str]
    # The counter the scenario exists for, as the UI should name it.
    hero_label: str
    # What is sourced and what is illustrative, in one honest sentence.
    basis: str
    # The paragraph under the trace page's heading. It lives here, not in the
    # frontend, so that it follows the reading level like the rest of the prose.
    intro: str = ""
    sources: list[SourceLink] = Field(default_factory=list)


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to Dell systems
    # management; spell out jargon (Redfish, RACADM, NC-SI, LC, ...) on first
    # use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "Enterprise license or higher"
    # Subsystem blocks this capability lives in (ids from anatomy.py).
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
