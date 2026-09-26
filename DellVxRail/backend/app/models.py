"""Data models for the VxRail digital twin.

Same conventions as the other twins in this repo: snake_case in Python,
camelCase over the wire (activeRegions, powerWatts, progressPercent,
regionIds, ...), so the React frontend can consume responses directly. None
of the fields here camelize ambiguously (no embedded numbers/acronyms), so
no explicit aliases are needed — if you add one that does, pin it with
``Field(alias=...)`` and check frontend/src/types.ts by hand (see CLAUDE.md).

The twist versus the single-chassis twins (R760, PowerStore, PowerMax): the
subject is a *cluster*, not one box. The shared "anatomy" is a stack of
identical hyperconverged (HCI) nodes plus the top-of-rack fabric that joins
them, and the "power-on" trace is the cluster's **first run** — several
PowerEdge nodes booting in lockstep, electing a primary that runs VxRail
Manager, then fusing their local NVMe into one vSAN datastore.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from twinkit.models import CamelModel

RegionKind = Literal[
    "compute",     # per-node CPU socket(s)
    "memory",      # per-node DDR5 DIMM banks
    "storage",     # per-node NVMe drives (the raw material of the vSAN datastore)
    "boot",        # per-node BOSS-N1 / M.2 boot device that ESXi loads from
    "network",     # per-node NIC — OCP/NDC ports carrying vSAN, vMotion, VM traffic
    "management",  # per-node iDRAC service processor
    "power",       # per-node PSUs
    "fabric",      # shared top-of-rack switch pair (the cluster network)
]

# Cluster first-run phases, in order. The host nodes power on together, boot
# ESXi, discover one another, elect a primary (VxRail Manager), build the
# vSphere cluster, assemble the vSAN datastore, then serve VMs.
BringUpPhase = Literal[
    "off",         # nodes racked, AC connected, everything dark
    "power",       # PSUs energize, iDRAC standby → full power, POST
    "esxi",        # ESXi hypervisor boots from BOSS on every node
    "discovery",   # nodes find each other on the private management VLAN
    "primary",     # primary-node election; VxRail Manager VM powers up on the winner
    "cluster",     # VxRail Manager validates config and builds the vSphere cluster
    "vsan",        # vSAN datastore assembles across every node's NVMe
    "online",      # cluster online, serving virtual machines
]


# Day-2 node-add phases (the ``node-add-mismatch`` scenario, app/nodeadd.py).
# A separate vocabulary on purpose: the cluster is already online when this
# trace starts, so none of the first-run phases describe it.
NodeAddPhase = Literal[
    "serving",     # the four-node cluster is online and running workloads
    "racked",      # a fifth node is racked, cabled, powered, booted from its factory image
    "found",       # VxRail Manager discovers the new node on the internal management network
    "check",       # the add-hosts wizard compares the node's version with the cluster's
    "refused",     # version mismatch: the add is refused before the node touches vSAN
    "reimage",     # the admin re-images the node to the cluster's version
    "recheck",     # the node is rediscovered and the compatibility check passes
    "join",        # validation, host added to the vSphere cluster, vSAN claims its drives
    "rebalance",   # vSAN spreads existing data across five nodes
    "expanded",    # five nodes, one larger datastore
]


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
    """The cluster floorplan, annotated. ``width``/``height`` set the viewBox."""

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


class FirstRunState(CamelModel):
    """One step of the cluster first-run sequence; pure data the renderer consumes."""

    step: int
    phase: BringUpPhase | NodeAddPhase
    label: str
    description: str
    # Region ids in the cluster anatomy lit up at this step.
    active_regions: list[str]
    # Whole-cluster draw in watts (all nodes plus the fabric).
    power_watts: int
    # VxRail Manager's build progress, 0→100 — replaces the chassis twins'
    # fanPercent; the real first-run UI shows exactly this bar.
    progress_percent: int = Field(ge=0, le=100)
    # Illustrative wall-clock seconds since the nodes were powered on.
    elapsed_seconds: int
    # UI dwell ticks; long stages (ESXi boot, cluster build) get more.
    cycle_cost: int = 1
    # --- Scenario-only fields, added for the day-2 node-add trace. All are
    # None on the first-run trace, and the trace route serializes with
    # exclude_none, so the first-run response is byte-identical to what it
    # was before these existed (pinned in tests/test_nodeadd.py).
    # Regions the step draws as failed/refused (ids from the scenario's map).
    failed_regions: list[str] | None = None
    # Hosts contributing drives to the vSAN datastore.
    vsan_nodes: int | None = None
    # Hosts in vSAN whose VxRail version differs from the cluster's. Exists
    # to be zero.
    mismatched_nodes_in_vsan: int | None = None
    # Illustrative raw datastore capacity, TB.
    datastore_tb: int | None = None
    # Illustrative count of running virtual machines on the cluster.
    vms_running: int | None = None
    # VxRail software versions (illustrative numbers, see nodeadd.SOURCES).
    cluster_version: str | None = None
    node_version: str | None = None


class FirstRunResponse(CamelModel):
    trace: list[FirstRunState]


class Scenario(CamelModel):
    """One selectable trace. ``first-run`` is the happy path."""

    id: str
    title: str
    kind: Literal["happy", "failure"]
    summary: str
    # The number the counters panel leads with, and why it matters.
    hero: str
    phases: list[str]
    sources: list[SourceLink] = Field(default_factory=list)


class CatalogOption(CamelModel):
    id: str
    name: str
    summary: str  # one sentence
    # A paragraph for a technically skilled reader new to HCI; spell out Dell
    # and VMware jargon (vSAN, ESA, BOSS, VCF, RoCE, ...) on first use.
    details: str


class CatalogCategory(CamelModel):
    id: str
    name: str
    blurb: str
    limits: str  # e.g. "2–64 nodes per cluster"
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
