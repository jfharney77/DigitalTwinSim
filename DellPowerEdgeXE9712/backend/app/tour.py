"""The narrated tour of the PowerEdge XE9712 rack — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: seven beats that
move a camera across the rack elevation, peel it from the faces you can see
to the liquid loop and then into the compute trays, pin the power-on trace at
the moments that carry the story, and narrate each one. The frontend player
owns the clock; nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The storyboard: rack exterior, the coolant loop first (liquid before
silicon), one GB200 tray, the mid-rack NVLink switch trays and why they sit
centrally, fabric training (the longest stage), the atomic fuse, ready. The
signature beat is ``atomic-fuse``: 72 GPUs become one domain, all at once.
Every claim the scripts make is one the engine and the anatomy already make —
the trace index named in each beat is the step whose description says the
same thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``RackAnatomy`` is unchanged:

    0  the faces you see from the aisle: power shelves, rack management,
       tray network ports, the NVLink switch trays
    1  the liquid loop: CDU and supply/return manifolds
    2  inside each compute tray: the Grace CPUs and the Blackwell GPUs
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import RackAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "atomic-fuse"

_OUTSIDE = 0
_LOOP = 1
_TRAY = 2

_TRAYS = ["t1", "t2", "t3", "t4"]


def _all(prefix: str) -> list[str]:
    return [f"{prefix}-{t}" for t in _TRAYS]


def layer_map(anatomy: RackAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.kind == "cooling":
            layers[region.id] = _LOOP
        elif region.kind in {"gpu", "compute"}:
            layers[region.id] = _TRAY
        else:
            layers[region.id] = _OUTSIDE
    return layers


def build_tour(anatomy: RackAnatomy) -> Tour:
    """The XE9712 tour, framed against ``anatomy``."""

    gpus = _all("gpu")
    switches = ["nvswitch-a", "nvswitch-b"]

    steps = [
        TourStep(
            id="rack-exterior",
            title="The rack is the computer",
            script=L(
                novice=(
                    "This is a Dell PowerEdge XE9712, seen from the front. It is "
                    "not a computer that goes in a rack; the whole rack is one "
                    "computer, built and cabled at the factory and wheeled in as a "
                    "unit. A real one holds 18 compute trays and 9 switch trays. "
                    "This drawing shows four compute trays and two blocks standing "
                    "in for the switch trays, enough to see the pattern. Power "
                    "units sit at the top and bottom, and the pipes for the cooling "
                    "water run up the right edge. It is plugged into the building's "
                    "power and water, and nothing is switched on yet."
                ),
                standard=(
                    "This is a Dell PowerEdge XE9712, NVIDIA GB200 NVL72 inside, "
                    "drawn as a front-of-rack elevation. It ships as one integrated "
                    "rack: 18 compute trays, 9 NVLink switch trays, power shelves "
                    "and pre-run copper cabling, built and tested at the factory. "
                    "The drawing shows four compute trays and two blocks for the "
                    "switch trays, a stylized mental model rather than a rack-"
                    "accurate one. It is connected to facility power and facility "
                    "water, and nothing is on."
                ),
                expert=(
                    "XE9712, GB200 NVL72, front elevation (4 of 18 compute trays, "
                    "2 blocks for 9 NVSwitch trays; stylized). Factory-integrated, "
                    "sited, connected, dark."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="liquid-before-silicon",
            title="Liquid before silicon",
            script=L(
                novice=(
                    "The power units have already turned the building's electricity "
                    "into direct current on a copper bar down the back of the rack, "
                    "but only the small management computers are awake. Now the "
                    "cooling comes first. The cooling unit at the bottom, called "
                    "the CDU (coolant distribution unit), starts its pumps and "
                    "fills the pipes, called manifolds, that run up the side to "
                    "every tray. It checks each branch for leaks and for flow. "
                    "Roughly ninety percent of this rack's heat leaves through "
                    "water, not air, so no big chip is allowed to switch on until "
                    "the water is proven. Every air-cooled machine does this the "
                    "other way round. The IR7000 cooling twin tells this same step "
                    "from the water's side."
                ),
                standard=(
                    "The power shelves have already energized the DC busbar, but "
                    "only on standby: management wakes, no compute silicon does. "
                    "Next, the in-rack CDU (coolant distribution unit) starts its "
                    "pumps, pressurizes the supply and return manifolds, and checks "
                    "every branch for leaks and flow, with quick-disconnect "
                    "fittings to seal one that fails. Roughly ninety percent of the "
                    "heat leaves through water, so GPU power is interlocked on "
                    "coolant flow. Liquid before silicon inverts every air-cooled "
                    "twin here; the IR7000 twin is this step from the other side."
                ),
                expert=(
                    "Busbar on standby only. CDU primes, manifolds pressurize, "
                    "per-branch leak/flow verified; GPU power interlocked on flow. "
                    "~90% liquid-borne. Coolant precedes trayboot (asserted); see "
                    "IR7000."
                ),
            ),
            # The plant corner: the CDU and the lower run of the manifolds.
            camera=CameraTarget(x=44, y=36, w=56, h=48),
            region_ids=["cdu", "manifold"],
            layer_reveal=_LOOP,
            trace_cursor=2,
            duration_ms=30_000,
        ),
        TourStep(
            id="gb200-tray",
            title="One tray: two Grace, four Blackwell",
            script=L(
                novice=(
                    "We open up the top compute tray. It holds two superchips. A "
                    "superchip is one processor fused to two graphics chips on a "
                    "single board, with a very fast direct link between them. Here "
                    "the processor is an NVIDIA Grace, with 72 cores, and the "
                    "graphics chips are NVIDIA Blackwell GPUs (graphics processing "
                    "units, the chips that do the maths behind AI). So one tray is "
                    "two Grace processors and four Blackwell GPUs. With the water "
                    "flowing, the processors start first, and every tray starts at "
                    "the same moment, like a row of identical computers switched on "
                    "together. The graphics chips on the left stay dark for now: they "
                    "wake in the next stage. For now the trays are still separate "
                    "computers that share a rack."
                ),
                standard=(
                    "Inside one compute tray: two GB200 superchips. A superchip is "
                    "one NVIDIA Grace CPU (72 Arm cores) fused to two Blackwell "
                    "GPUs on one board over NVLink-C2C, a chip-to-chip link far "
                    "faster than PCIe. So every tray is two Grace and four "
                    "Blackwell, under cold plates instead of fan-cooled heatsinks. With coolant "
                    "flowing, the Grace CPUs boot first, and every tray boots in "
                    "lockstep, as VxRail nodes do; the GPUs stay dark until the "
                    "next stage. The trays below mirror this one. For now they "
                    "are separate Arm servers that share a rack."
                ),
                expert=(
                    "Tray: 2x GB200 = 2 Grace (72 Arm cores each) + 4 Blackwell, one "
                    "Grace + 2 Blackwell per superchip over NVLink-C2C, cold-plated. "
                    "Grace boots, GPUs still in reset; trays in lockstep on -t1..-t4. "
                    "Still discrete systems."
                ),
            ),
            # Close on trays 1 and 2; trays 3 and 4 below are identical.
            camera=CameraTarget(x=0, y=4, w=66, h=57),
            region_ids=_all("cpu"),
            layer_reveal=_TRAY,
            trace_cursor=3,
            duration_ms=30_000,
        ),
        TourStep(
            id="switch-trays-mid-rack",
            title="Why the switch trays sit in the middle",
            script=L(
                novice=(
                    "Now all 72 graphics chips wake up on their cold plates. This is "
                    "where the rack's power use jumps the most: in this model each "
                    "chip is tested under load as it wakes, and a working chip can "
                    "draw around a kilowatt (an illustrative figure). A chip with "
                    "nothing to do draws far less. But each chip can so far only talk "
                    "to its own tray. The thing that will join them is the dark band "
                    "in the middle, not switched on yet: the NVLink switch trays. "
                    "NVLink is NVIDIA's fast link between graphics chips. The switch "
                    "trays sit in the middle of the rack on purpose, so the copper "
                    "cable to even the farthest tray stays short. Short copper means "
                    "no need to convert to light, and copper is cheaper, cooler and "
                    "more reliable."
                ),
                standard=(
                    "All 72 Blackwell GPUs now come out of reset on their cold "
                    "plates. It is the largest power step in the trace because this "
                    "twin wakes each GPU into a self-test under load, roughly a "
                    "kilowatt each (illustrative); an idle GPU draws far less. Yet "
                    "each can so far talk only to its own tray. What will join them "
                    "is the band in the middle, still dark: the NVLink switch trays, "
                    "carrying NVSwitch chips that cross-connect every GPU. They sit "
                    "at mid-rack on purpose, so the copper run to the farthest tray "
                    "stays short enough to skip optics. Copper is cheaper, cooler and "
                    "more reliable at this scale."
                ),
                expert=(
                    "GPUs out of reset: largest power step, modelled as self-test "
                    "under load (~1 kW each, illustrative; idle draw is far lower); "
                    "unfused. NVSwitch trays (still dark) mid-rack bound copper run "
                    "length, so no optics."
                ),
            ),
            # The middle of the rack: trays 2 and 3 either side of the switches.
            camera=CameraTarget(x=0, y=16, w=74, h=64),
            region_ids=gpus,
            layer_reveal=_TRAY,
            trace_cursor=4,
            duration_ms=30_000,
        ),
        TourStep(
            id="fabric-training",
            title="Five thousand cables, every link trained",
            script=L(
                novice=(
                    "This is the slowest part of the whole start-up, so the timeline "
                    "lingers here. The switch trays start up, and then the links "
                    "between chips are trained: 1,296 links, carried by more than "
                    "five thousand copper cables in the bundle at the back of the "
                    "rack. Training means the two ends of a link agree on a speed, "
                    "tune their signals and check for errors. The links train side by "
                    "side, and the stage is slow because everything waits for the "
                    "last one. Until it is ready there is no shared network at all, "
                    "just chips and switches testing their connections with each "
                    "other. The right-hand switch block, partly out of view, does the "
                    "same as the left."
                ),
                standard=(
                    "The single longest stage, which is why playback dwells here. The "
                    "switch trays boot their NVSwitch chips, and then the fabric "
                    "trains: 1,296 NVLink links, 18 per GPU, carried by more than "
                    "5,000 copper cables in the cartridge at the back of the rack, "
                    "each negotiated, tuned and error-checked at 200 Gb/s per lane. "
                    "They train in parallel; the wait is for the last one. Until it "
                    "trains there is no domain, only GPUs and switches exchanging "
                    "link-training patterns. The right-hand switch block, cut off at "
                    "the edge, mirrors the left."
                ),
                expert=(
                    "Max dwell: NVSwitch trays up; 1,296 NVLink5 links (72 x 18) "
                    "train in parallel over >5,000 copper cables at 200 Gb/s/lane "
                    "through the rear cartridge. No domain until the last link."
                ),
            ),
            camera=CameraTarget(x=0, y=24, w=60, h=52),
            region_ids=switches,
            layer_reveal=_TRAY,
            trace_cursor=5,
            duration_ms=30_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Seventy-two GPUs, one domain",
            script=L(
                novice=(
                    "This is the moment the rack exists for. The software that runs "
                    "the switch network stitches every trained link into one network "
                    "where every graphics chip reaches every other chip directly. All "
                    "72 can now read and write each other's memory at enormous speed. "
                    "Programs still see 72 chips, but the chips share work and memory "
                    "so closely that NVIDIA describes the rack as one giant chip. "
                    "Watch the counter of joined chips: it goes straight from zero to "
                    "72. There is never a moment when some are joined and some are "
                    "not. A model too large for any single chip can now spread across "
                    "all of them. In the XE9680 twin the same kind of link stops at "
                    "eight chips, at the wall of one server."
                ),
                standard=(
                    "The signature moment. The fabric manager stitches every trained "
                    "link into a single all-to-all NVLink domain. All 72 GPUs can "
                    "read and write each other's memory at 1.8 TB/s each, about 130 "
                    "TB/s in total, across 13.4 TB of HBM3e (high-bandwidth memory, "
                    "the DRAM stacked beside each GPU). Those are NVIDIA's figures. "
                    "Software still sees 72 GPUs on 18 hosts; NVIDIA markets the "
                    "domain as one enormous GPU. The GPUs-in-domain counter goes from "
                    "0 to 72 in one step: the fuse is atomic, and no partial domain "
                    "ever exists. The XE9680 twin keeps this wall at eight GPUs and "
                    "the chassis; here it is the rack."
                ),
                expert=(
                    "Signature: atomic fuse. One 72-GPU all-to-all NVLink domain: 72 "
                    "CUDA devices, 18 hosts, 1.8 TB/s per GPU, ~130 TB/s aggregate, "
                    "13.4 TB HBM3e total (NVIDIA's figures); marketed as a single "
                    "GPU. gpusInDomain in {0, 72}, never partial."
                ),
            ),
            camera=camera_around(anatomy, gpus + switches, pad=2.0),
            region_ids=gpus + switches,
            layer_reveal=_TRAY,
            trace_cursor=6,
            duration_ms=40_000,
        ),
        TourStep(
            id="ready",
            title="One rack, one domain, ready",
            script=L(
                novice=(
                    "The last stage is a full check-up. Health checks and a test workload "
                    "exercise every chip, every link and every memory stack while "
                    "the cooling holds steady. Then the rack joins the job "
                    "scheduler and starts taking work. At full load it draws around "
                    "120 kilowatts, an illustrative figure: several hundred "
                    "gaming laptops running flat out. One rack is rarely alone: a separate "
                    "outside network joins it to other racks, and the SN6000 and "
                    "Quantum-X800 twins show that network."
                ),
                standard=(
                    "Burn-in, then work. Health checks and a burn-in workload "
                    "sweep every GPU, NVLink path and HBM stack while the CDU holds "
                    "the loop at temperature, and the rack joins the cluster "
                    "scheduler. At full load it draws on the order of 120 kW "
                    "(illustrative). NVLink stops at the rack wall; the scale-out "
                    "network, InfiniBand or Spectrum-X Ethernet, joins this rack to "
                    "its neighbours, which is where the SN6000 and Quantum-X800 "
                    "twins pick up."
                ),
                expert=(
                    "Burn-in passed; rack joins the scheduler. ~120 kW "
                    "(illustrative). Scale-out (IB / Spectrum-X) beyond the rack "
                    "wall: see SN6000, Quantum-X800."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_OUTSIDE,
            trace_cursor=7,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="xe9712-tour",
        title="Inside an XE9712, as 72 GPUs become one",
        intro=L(
            novice=(
                "A guided walk through the rack as it starts up, narrated beat by "
                "beat. Sit back and watch, or pause and click anything to look "
                "closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through the rack while it powers on. Watch it "
                "play, or pause and explore; Resume tour brings the camera back."
            ),
            expert="Narrated power-on walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: RackAnatomy) -> TourResponse:
    """The ``GET /api/tour`` payload: the tour plus the layer map and bounds."""
    return TourResponse(
        tour=build_tour(anatomy),
        layers=layer_map(anatomy),
        map_width=anatomy.width,
        map_height=anatomy.height,
    )


# Built once at import, like ANATOMY: importing the module registers the
# narration's reading-level variants, which tests/test_leveling.py relies on.
from .anatomy import ANATOMY  # noqa: E402  (after the builders it feeds)

TOUR_RESPONSE = build_response(ANATOMY)
