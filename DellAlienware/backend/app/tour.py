"""The narrated tour of the Alienware m18's AC power path — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: seven beats that
move a camera across the m18 R2 interior map, peel it from the edges you can
touch down to the motherboard, pin the power-path trace at the moments that
carry the story, and narrate each one. The frontend player owns the clock;
nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The storyboard is ACTIVE_TWIN_SPEC.md section 8's Alienware row, and the
signature beat is ``psid-handshake``: the adapter has to prove what it is over
the 1-Wire center pin before the embedded controller will budget a single watt
of it. Every claim the scripts make is one the engine and the anatomy already
make — each beat pins the trace step whose description says the same thing.

**The trace is scenario-driven** (``POST /api/simulate`` takes a
:class:`Scenario`), so the tour narrates one fixed scenario,
:data:`TOUR_SCENARIO`: the m18 R2 on its 280 W barrel adapter, starting at 30%,
Full Speed thermal mode, a gaming load. That is the headline hybrid-power case
``test_m18_280w_fullspeed_goes_hybrid`` pins, and the frontend switches its
scenario controls to the same values when the tour page opens. Trace cursors
index *that* trace. The charge ramp runs before boot in this engine (the pack
charges lid-closed first), and the tour never runs the trace backwards, so the
charge beat precedes the hybrid beat.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``Anatomy`` is unchanged:

    0  what you can touch with the machine closed: the side ports, the DC-in jack
    1  under the bottom cover: battery, fans, vapor chamber, memory, SSD, Wi-Fi
    2  on the motherboard: CPU, GPU, embedded controller, charger stage
"""

from __future__ import annotations

from twinkit.tour import (
    CameraTarget,
    Tour,
    TourPhoto,
    TourResponse,
    TourSource,
    TourStep,
    camera_around,
    whole_map,
)

from .leveling import L
from .models import Anatomy, Scenario

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "psid-handshake"

#: The one scenario the tour narrates; trace cursors index its trace. The
#: frontend's ``TOUR_SCENARIO`` in App.tsx must match (tested).
TOUR_SCENARIO = Scenario(
    profile_id="m18-r2",
    adapter_id="barrel-280",
    start_battery_pct=30,
    thermal_mode="fullSpeed",
    workload="gaming",
)

#: The interior map the tour is framed against.
TOUR_ANATOMY_ID = "m18-r2"

_OUTSIDE = 0
_UNDER_COVER = 1
_BOARD = 2


def layer_map(anatomy: Anatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.kind == "io" or region.id == "dc-in":
            layers[region.id] = _OUTSIDE
        elif region.kind in {"board", "power"}:
            layers[region.id] = _BOARD
        else:
            layers[region.id] = _UNDER_COVER
    return layers


def _photos(anatomy: Anatomy) -> list[TourPhoto]:
    if anatomy.photo is None:
        return []
    return [
        TourPhoto(
            id="interior",
            url=anatomy.photo.url,
            caption=anatomy.photo.caption,
            credit=anatomy.photo.credit,
        )
    ]


def build_tour(anatomy: Anatomy) -> Tour:
    """The Alienware m18 tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    photos = _photos(anatomy)
    interior_photo = photos[0].id if photos else None

    steps = [
        TourStep(
            id="closed-laptop",
            title="A laptop, a brick, and a cord between them",
            script=L(
                novice=(
                    "This is an Alienware m18, a large gaming laptop, drawn as if "
                    "we were looking up at it from underneath. The rear edge, where "
                    "the hinge is, runs along the top of the picture. Right now it "
                    "is switched off and running on its own battery, and the power "
                    "adapter, the heavy brick on the cord, is not plugged in yet. "
                    "For the moment, only the outside edges matter: the ports along "
                    "each side and the round power socket at the back, called the "
                    "DC-in jack. Everything this tour shows happens in the first "
                    "moments after that plug goes in."
                ),
                standard=(
                    "This is the Alienware m18 R2, drawn from below with the rear "
                    "hinge edge along the top. It is shut down and on its own "
                    "battery; the only thing awake inside is a small always-on "
                    "chip we will meet shortly. The 280 W adapter brick sits beside "
                    "it, unplugged. For now only the edges you can touch matter: "
                    "the side port clusters and the round DC-in (direct current "
                    "input) jack at the rear right. This tour follows what happens after the plug goes in."
                ),
                expert=(
                    "Alienware m18 R2, bottom view, rear edge up. Off, on pack "
                    "power. 280 W barrel adapter unplugged. Exterior: side I/O, "
                    "rear-right DC-in."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["dc-in", "io-left", "io-right"],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="adapter-brick",
            title="Inside the brick: 19.5 volts, and a name tag",
            script=L(
                novice=(
                    "The adapter goes into the wall. Inside the brick, electricity "
                    "from the socket, which constantly reverses direction, is "
                    "turned into a steady 19.5 volts flowing one way, up to about "
                    "14 amps, which works out to 280 watts. A ring of light on the "
                    "plug comes on, showing the brick is working before the laptop "
                    "is even involved. The brick also carries something small and "
                    "important: a tiny memory chip that stores what kind of adapter "
                    "it is. We have taken the bottom cover off now, and the plug "
                    "is about to go into that socket at the back."
                ),
                standard=(
                    "The adapter meets the wall. Inside the brick, mains AC "
                    "(alternating current) is rectified to a regulated 19.5 V DC "
                    "(direct current) at up to 14.36 A, which is its 280 W rating. "
                    "The LED ring on the plug lights, confirming output before the "
                    "laptop is involved; the laptop's controller is still on "
                    "battery. The brick also holds a PSID (power supply ID) chip, "
                    "and that chip is the next beat. The bottom cover is off now."
                ),
                expert=(
                    "Adapter: mains AC to regulated 19.5 V DC, 14.36 A max, "
                    "280 W. Plug LED confirms output host-independently. PSID "
                    "EEPROM in the brick. Cover off."
                ),
            ),
            camera=frame("dc-in", pad=10.0),
            region_ids=["dc-in"],
            layer_reveal=_UNDER_COVER,
            trace_cursor=1,
            duration_ms=28_000,
            photo_id=interior_photo,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Prove what you are first",
            script=L(
                novice=(
                    "This is the most important moment in the tour. The plug has "
                    "three contacts. The outer sleeve and the inner sleeve carry "
                    "the power. A thin pin in the very centre carries a single "
                    "data wire. Over that wire, a small always-on chip on the "
                    "motherboard, called the embedded controller, reads the name "
                    "tag inside the brick: its family, its wattage, its voltage and "
                    "current, with a check number to catch any errors. The chip is "
                    "powered by the data wire itself. The read is slow by computer "
                    "standards, so the timeline pauses here on purpose. If the "
                    "read fails, perhaps because that centre pin is bent or a "
                    "cheap replacement brick has no chip, the laptop calls the "
                    "adapter Unknown. It still takes power from it, but it will "
                    "not charge the battery, and it holds the processor and "
                    "graphics chip to about 35 watts between them. Power it cannot "
                    "check is power it will not plan around."
                ),
                standard=(
                    "This is the idea the whole power path rests on. The plug has "
                    "three conductors: ground on the outer barrel, +19.5 V on the "
                    "inner, and a center pin carrying a 1-Wire data line. Over that "
                    "pin the EC (embedded controller) reads the PSID, a tiny EEPROM "
                    "(a small rewritable memory chip) powered by the data line "
                    "itself, encoding the adapter's family, wattage, voltage and "
                    "current behind a CRC (cyclic redundancy check) checksum. "
                    "The read is slow by silicon standards, so the trace stalls "
                    "here. If it fails, from a bent pin or a brick with no PSID "
                    "chip, BIOS reports the adapter as Unknown: the EC still draws "
                    "from the rail but disables charging and caps CPU and GPU near "
                    "35 W combined. Wattage the platform cannot verify is wattage "
                    "it will not budget for."
                ),
                expert=(
                    "PSID read over the 1-Wire center pin. Parasite-"
                    "powered EEPROM, family/wattage/V/A, CRC. Trace stalls here. "
                    "Read fails: Unknown adapter, charging off, CPU+GPU capped "
                    "~35 W, boot still completes."
                ),
            ),
            camera=frame("dc-in", "ec", "charger", pad=3.0),
            region_ids=["dc-in", "ec"],
            layer_reveal=_BOARD,
            trace_cursor=3,
            duration_ms=46_000,
        ),
        TourStep(
            id="power-budget",
            title="A budget smaller than the silicon",
            script=L(
                novice=(
                    "The check number matches, so the embedded controller now "
                    "trusts that this really is a 280 watt adapter. It sets the "
                    "laptop's power budget from that number: how much the "
                    "processor, the graphics chip and the battery charger are "
                    "allowed to draw. Here is the catch. The processor can pull up "
                    "to about 157 watts and the graphics chip about 175, plus "
                    "roughly 25 for everything else. Added up, that is more than "
                    "280, so if both chips work flat out at once, the adapter alone "
                    "cannot keep up. These wattages are illustrative. Then the "
                    "charging circuit moves the whole laptop onto adapter power."
                ),
                standard=(
                    "The CRC checks out, so the EC knows it has a genuine 280 W "
                    "supply and sets the platform power budget: full charge rate "
                    "and full CPU and GPU limits are on the table. The budget is "
                    "real but modest for this silicon. The CPU can burst to about "
                    "157 W and the GPU's TGP (total graphics power) is 175 W, with "
                    "some 25 W for the rest of the board, all illustrative. That "
                    "sum beats 280 W. Next the charger chip moves the system load "
                    "onto the adapter rail."
                ),
                expert=(
                    "CRC valid: 280 W budget, full charge rate, full CPU/GPU "
                    "limits. CPU ~157 W + GPU TGP 175 W + ~25 W platform exceeds "
                    "280 W (illustrative)."
                ),
            ),
            camera=frame("ec", "cpu", "gpu", "charger", pad=3.0),
            region_ids=["ec", "charger", "cpu", "gpu"],
            layer_reveal=_BOARD,
            trace_cursor=4,
            duration_ms=30_000,
        ),
        TourStep(
            id="charge-ramp",
            title="Ninety watts into the pack",
            script=L(
                novice=(
                    "Before the laptop is even switched on, the adapter starts "
                    "filling the battery, a 97 watt-hour pack of six lithium-ion "
                    "cells across the front of the machine. The charging circuit "
                    "pushes a steady 90 watts or so into it, and this is where the "
                    "battery percentage climbs quickly. Dell calls this "
                    "ExpressCharge. Near the top it changes approach: it holds the "
                    "voltage steady and lets the flow shrink, which is why the last "
                    "fifth of any charge takes so long. A nearly empty battery "
                    "would first get a gentle trickle. The rates here are "
                    "illustrative."
                ),
                standard=(
                    "With the machine still off, the charger fills the 97 Wh "
                    "six-cell lithium-ion pack. This is the constant-current bulk "
                    "stage: a steady ~90 W while cell voltage rises, the regime "
                    "Dell sells as ExpressCharge and rates at roughly 80% in an "
                    "hour with the computer off. "
                    "Near the top the charger switches to constant voltage and the "
                    "current tapers, which is why the last 20% is slow; a deeply "
                    "drained pack gets a gentle precharge first. Rates are "
                    "illustrative."
                ),
                expert=(
                    "Powered-off charge, 97 Wh 6-cell pack: CC bulk ~90 W "
                    "(ExpressCharge, ~80% in 1 h), then CV taper; precharge only "
                    "below 10%. Illustrative."
                ),
            ),
            camera=frame("charger", "battery", pad=2.0),
            region_ids=["charger", "battery"],
            layer_reveal=_BOARD,
            trace_cursor=6,
            duration_ms=30_000,
        ),
        TourStep(
            id="hybrid-power",
            title="Plugged in, and the battery still drains",
            script=L(
                novice=(
                    "Now the laptop is on and a game is running in Full Speed "
                    "mode, which spins both fans flat out and lets both chips run "
                    "to their full limits. The processor and graphics chip together with "
                    "the rest of the machine want about 294 watts, and the adapter "
                    "only has 280. Instead of slowing the game down, the laptop "
                    "takes the missing 14 watts from the battery, at the same time "
                    "as it draws the full 280 from the wall. This is called hybrid "
                    "power, and it is deliberate. Windows shows the battery slowly "
                    "dropping even though it is plugged in. If the battery falls "
                    "below about 20%, the laptop stops doing this and slows the "
                    "chips instead, to protect the battery."
                ),
                standard=(
                    "The OS is up and a game is running in Full Speed mode (fans "
                    "pinned at 100%, CPU and GPU allowed their full limits), and "
                    "combined demand reaches about 294 W against the 280 W "
                    "adapter. Rather than throttle, the charger runs the battery "
                    "in parallel with the wall and it supplies the missing ~14 W. "
                    "This is hybrid power, by design: Windows shows the pack "
                    "draining while plugged in. The books still balance on every "
                    "step, AC plus battery equals system plus charge. Below about "
                    "20% the EC disables hybrid and throttles instead."
                ),
                expert=(
                    "Hybrid: ~294 W demand vs 280 W adapter; pack supplies ~14 W "
                    "in parallel. acW + batteryW == systemW + chargeW holds every "
                    "step. Disabled below ~20%; throttle instead."
                ),
            ),
            camera=frame("cpu", "gpu", "vram", "charger", "battery", pad=2.0),
            region_ids=["cpu", "gpu", "vram", "charger", "battery"],
            layer_reveal=_BOARD,
            trace_cursor=13,
            duration_ms=34_000,
        ),
        TourStep(
            id="steady-state",
            title="Two ways to stop the drain",
            script=L(
                novice=(
                    "The cover goes back on. The laptop has settled down, and the "
                    "battery is still covering the gap between what the game wants "
                    "and what the adapter can give. Over a long session the battery "
                    "keeps slowly dropping. There are two ways out. Switching down "
                    "to Performance mode keeps this game inside the adapter's 280 "
                    "watts, at the cost of some speed. Keeping Full Speed without "
                    "touching the battery takes a bigger adapter, the 360 watt "
                    "brick, which covers the whole load by itself. Everything here "
                    "started with one small chip being read through one thin pin. The companion physics app, "
                    "PhysicsClient, runs the same power balance second by second. "
                    "Press play on the power path page to walk it step by step."
                ),
                standard=(
                    "Reassembled, at thermal and electrical equilibrium, with the "
                    "battery still making up the difference between demand and "
                    "the adapter. On a long run the pack keeps draining. There are "
                    "two exits: a lower thermal mode (Performance holds this game "
                    "near 254 W, inside the adapter, at some cost in speed), or "
                    "adapter headroom, the 360 W brick, which keeps Full Speed "
                    "entirely on wall power. All "
                    "of it traces back to one EEPROM read over one center pin. "
                    "PhysicsClient carries the same supply identity into a "
                    "second-by-second physics model, and the power path page walks "
                    "this trace one step at a time."
                ),
                expert=(
                    "Steady state, still hybrid; pack drains. Exits: Performance "
                    "mode (~254 W, fits 280 W, slower) or the 360 W adapter (Full "
                    "Speed on wall power). Same supply identity in PhysicsClient."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_OUTSIDE,
            trace_cursor=14,
            duration_ms=26_000,
        ),
    ]

    return Tour(
        id="alienware-tour",
        title="Inside an Alienware m18, as it plugs in",
        intro=L(
            novice=(
                "A guided walk through what happens inside the laptop when you "
                "plug in its power adapter, narrated beat by beat. Sit back and "
                "watch, or pause and click anything to look closer; the tour "
                "waits for you."
            ),
            standard=(
                "A narrated walk through the m18's AC power path, from plug-in "
                "to a gaming load. Watch it play, or pause and explore; Resume "
                "tour brings the camera back."
            ),
            expert="Narrated plug-in walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=photos,
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: Anatomy) -> TourResponse:
    """The ``GET /api/tour`` payload: the tour plus the layer map and bounds."""
    return TourResponse(
        tour=build_tour(anatomy),
        layers=layer_map(anatomy),
        map_width=anatomy.width,
        map_height=anatomy.height,
    )


# Built once at import, like ANATOMIES: importing the module registers the
# narration's reading-level variants, which tests/test_leveling.py relies on.
from .anatomy import ANATOMIES  # noqa: E402  (after the builders it feeds)

TOUR_ANATOMY = ANATOMIES[TOUR_ANATOMY_ID]
TOUR_RESPONSE = build_response(TOUR_ANATOMY)
