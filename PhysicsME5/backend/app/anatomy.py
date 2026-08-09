"""Enclosure map for the ME5 storage simulator — a stylized front-and-rear
composite of an ME5024: the 24-slot 2.5-inch drive bay across the top,
and the rear FRUs (two controller canisters with their mirrored write
cache, two PSUs) along the bottom. Regions are *state zones* keyed to the
engine's ``region_states`` dict; the frontend paints them by status
(ok / failed / rebuilding / spare / empty / write-through). Stylized — a
mental model, not a service manual (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import ArrayMap, ArrayRegion


def _slot(i: int) -> ArrayRegion:
    return ArrayRegion(
        id=f"drive-{i}", kind="drive", label=f"{i + 1}",
        x=1.0 + i * 4.1, y=0.5, w=3.6, h=20.0,
        description=(
            "One 2.5-inch drive slot. Every populated drive contributes "
            "its IOPS to the group's budget and its capacity to the raw "
            "total; RAID decides how much of each survives the "
            "protection tax. Click a healthy drive to fail it, and a "
            "failed one to replace it."
        ),
    )


ANATOMY = ArrayMap(
    id="me5-physics",
    name="PowerVault ME5 · RAID physics model",
    vendor="Dell Technologies",
    form_factor="2U SAN array — 24-slot enclosure, dual controllers",
    generation="ME5 series (ME5012 / ME5024; ME5084 is the 5U84 sibling)",
    year=2022,
    width=100,
    height=40,
    overview=L(
        novice=(
            "This is Dell's entry-level storage array — a box of drives "
            "that servers share over a network. It is the perfect first "
            "storage machine to learn on, because everything inside is "
            "the classic version of itself: a shelf of up to 24 drives, "
            "two controller computers (so one can die without anyone "
            "noticing), and RAID — the trick of spreading data across "
            "drives with spare arithmetic so a dead drive loses nothing. "
            "The catch this simulator exists to teach: protection is "
            "paid for in writes. Mirroring writes everything twice; the "
            "cleverer parity schemes turn one small write into four or "
            "even six disk operations. Set up an array, load it, break "
            "a drive, and watch the arithmetic play out."
        ),
        plain=(
            "An ME5024 drawn as state zones: the 24-slot drive bay on "
            "top, and below it the rear field-replaceable units — two "
            "controllers with mirrored write cache, two power supplies. "
            "Drives set the I/O budget (a 10k spindle manages ~170 "
            "random IOPS; an SSD, tens of thousands), RAID sets the "
            "write tax (×2 mirror, ×4 RAID 5, ×6 RAID 6), and the "
            "controllers set the front-end ceiling. Fail a drive and "
            "the rebuild window opens — hours or days during which a "
            "second failure may mean data loss."
        ),
        standard=(
            "Dell's entry SAN, drawn as the RAID physics lab it "
            "genuinely is: 24 drive slots whose population sets the "
            "disk-I/O budget, two active-active controller canisters "
            "whose mirrored write cache degrades to write-through the "
            "moment its partner dies, and nothing else — no dedupe, no "
            "tiering, no machinery between you and the arithmetic. Host "
            "writes are multiplied by the RAID write penalty (×2 "
            "mirrored, ×4 single-parity, ×6 dual-parity: read data, "
            "read parity, write both — twice for RAID 6) before they "
            "touch drives, so the same 24 spindles serve wildly "
            "different write rates under different layouts. Failures "
            "convert time into risk: the rebuild window is drive "
            "capacity over an effective rebuild rate that a busy array "
            "makes worse, which is precisely why RAID 6 displaced "
            "RAID 5 as drives outgrew the window. The simplicity is "
            "the point — learn the ledger here, and PowerStore's added "
            "machinery becomes legible by contrast."
        ),
        technical=(
            "One disk group + global spares; per-drive IOPS constants "
            "(80/170/20k), M/M/1-shaped latency knee, front-end cap per "
            "controller. Ledger identities asserted per tick: backend "
            "ops = reads×read_cost + writes×penalty (penalty 2/4/6 by "
            "level; read_cost 2× while parity-degraded), and raw = "
            "usable + overhead + spares exactly. Rebuild: capacity ÷ "
            "(rate × (1 − 0.5·util)), 20% budget reserve while active; "
            "risk index ∝ remaining window × level exposure factor."
        ),
        expert=(
            "Classic RAID ledger, nothing else. IOPS balance and "
            "capacity identity asserted per tick; penalties 2/4/6; "
            "rebuild window = TB/(rate·derate); R6 vs R5 is the risk "
            "gauge. Constants estimated and tagged."
        ),
    ),
    regions=[
        *[_slot(i) for i in range(24)],
        ArrayRegion(
            id="cache-a", kind="cache", label="Cache A",
            x=1.0, y=22.5, w=8.0, h=16.5,
            description=(
                "Controller A's write cache. Writes are acknowledged "
                "from cache and mirrored to the partner controller so a "
                "controller death loses nothing; lose the partner and "
                "the survivor drops to write-through — every write waits "
                "for the drives, and the write penalty stops hiding."
            ),
        ),
        ArrayRegion(
            id="ctrl-a", kind="controller", label="Controller A",
            x=10.0, y=22.5, w=31.0, h=16.5,
            description=(
                "The first controller canister — half of the "
                "active-active pair that runs the array: RAID math, "
                "cache, and the SAS/iSCSI/FC host ports. Each controller "
                "has a front-end ceiling that spindles never reach but a "
                "shelf of SSDs will. Click to fail it and watch the "
                "survivor own everything."
            ),
        ),
        ArrayRegion(
            id="ctrl-b", kind="controller", label="Controller B",
            x=42.0, y=22.5, w=31.0, h=16.5,
            description=(
                "The second controller. Dual controllers are why an ME5 "
                "survives a controller failure in place: the survivor "
                "takes over all volumes at the price of a shared ceiling "
                "and write-through cache until its partner returns."
            ),
        ),
        ArrayRegion(
            id="cache-b", kind="cache", label="Cache B",
            x=74.0, y=22.5, w=8.0, h=16.5,
            description=(
                "Controller B's write cache — the mirror half. Cache "
                "contents are protected against power loss (supercap + "
                "flash on the real hardware); this model cares about the "
                "mirroring, because that is what changes when a "
                "controller dies."
            ),
        ),
        ArrayRegion(
            id="psu-a", kind="power", label="PSU 1",
            x=83.0, y=22.5, w=7.5, h=16.5,
            description=(
                "Redundant power supply. Not a player in this sim's "
                "physics — drawn because the enclosure has it, and "
                "because storage arrays owe their five-nines habit to "
                "there being two of everything."
            ),
        ),
        ArrayRegion(
            id="psu-b", kind="power", label="PSU 2",
            x=91.5, y=22.5, w=7.5, h=16.5,
            description=(
                "The second power supply — same story: two of "
                "everything, so service survives any single part."
            ),
        ),
    ],
    sources=[
        {"label": "Dell PowerVault ME5 spec sheet",
         "url": "https://www.dell.com/en-us/shop/productdetailstxn/powervault-me5"},
        {"label": "Dell ME5 Administrator's Guide (RAID levels, spares)",
         "url": "https://www.dell.com/support/home/en-us/product-support/product/powervault-me5012/docs"},
        {"label": "physics_specs/10-additional-products.md §3 (this repo)",
         "url": "../physics_specs/10-additional-products.md"},
    ],
)
