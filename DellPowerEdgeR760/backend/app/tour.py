"""The narrated tour of the PowerEdge R760 — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: seven beats that
move a camera across the chassis floorplan, peel it from the serviceable
outside to the processors and memory under the air shroud, pin the power-on
trace at the moments that carry the story, and narrate each one. The frontend
player owns the clock; nothing here knows about time, IO or the web
(AST-checked in ``tests/test_tour.py``, the same rule as ``engine.py``).

Storyboard: front bezel, drive bay, peel the lid (fans), DIMMs and CPUs, PERC
and BOSS-N1, the iDRAC corner, reassemble. The signature beat is
``memory-training``: DDR5 training is the trace's single longest stage
(``test_memory_training_is_the_longest_stage``), and the beat pins the cursor
there. Every claim the scripts make is one the engine and the anatomy already
make; each beat's ``trace_cursor`` names the step whose description says the
same thing.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``ChassisAnatomy`` is unchanged:

    0  what you can reach with the lid on: drive bay, PSUs, BOSS-N1, OCP NIC
    1  under the lid: fan wall, PERC, system board, iDRAC, risers, power board
    2  under the air shroud: the CPU sockets and their DDR5 banks
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
from .models import ChassisAnatomy

#: The step the tests pin: the longest stage of the power-on lives here.
SIGNATURE_STEP_ID = "memory-training"

#: The front of the chassis, nearly full height: drive bay, fan wall, PERC.
#: The bay and the fan column each run the whole front edge, so this is as
#: tight as the camera can go without cutting them.
_FRONT = CameraTarget(x=0, y=1.5, w=90, h=43)

_OUTSIDE = 0
_LID = 1
_SHROUD = 2


def layer_map(anatomy: ChassisAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    outside = {"backplane", "boss", "ocp"}
    layers: dict[str, int] = {}
    for region in anatomy.regions:
        if region.kind in {"cpu", "memory"}:
            layers[region.id] = _SHROUD
        elif region.id in outside or region.id.startswith("psu"):
            layers[region.id] = _OUTSIDE
        else:
            layers[region.id] = _LID
    return layers


def _photos() -> list[TourPhoto]:
    return [
        TourPhoto(
            id="interior",
            url="/r760-interior.webp",
            caption=(
                "Inside the R760 with the lid and air shroud removed: drive "
                "backplane at the front, the fan wall, two CPU heatsinks "
                "between DDR5 banks, risers and power supplies at the rear."
            ),
            credit="Dell Technologies product image",
        ),
    ]


def build_tour(anatomy: ChassisAnatomy) -> Tour:
    """The R760 tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="front-bezel",
            title="A 2U server, cords in, still dark",
            script=L(
                novice=(
                    "This is a Dell PowerEdge R760, a rack server: a computer "
                    "built to live in a data centre, two rack units tall (a "
                    "rack unit is one standard shelf height in the rack "
                    "cabinet). We are looking down on it from "
                    "above, with the front on the left and the back on the "
                    "right. Both power cords have just been plugged in. "
                    "Nothing seems to happen: the fans are still, the lights "
                    "are off. But the two power supplies at the back right "
                    "have already noticed there is electricity at the wall, "
                    "and they are about to wake the one part of this machine "
                    "that never really sleeps."
                ),
                standard=(
                    "This is the Dell PowerEdge R760, a two-socket 2U rack "
                    "server, seen from above with the front on the left and "
                    "the rear on the right. Both AC cords have just gone in. "
                    "Nothing appears to happen: fans still, LEDs dark, no "
                    "measurable draw. But the two power supplies in the rear "
                    "corner have detected line voltage, and they are about to "
                    "wake the one subsystem that never truly sleeps."
                ),
                expert=(
                    "R760, 2U two-socket, top-down, front left. AC applied, "
                    "no draw yet. PSUs have seen line voltage; standby rail "
                    "is next."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["psu1", "psu2"],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=26_000,
            photo_id="interior",
        ),
        TourStep(
            id="drive-bay",
            title="The drive bay, read before the host is on",
            script=L(
                novice=(
                    "The strip down the whole front edge is the drive bay: "
                    "24 slots for 2.5-inch drives, which can be pulled out and "
                    "replaced while the server keeps running. Behind them sits "
                    "the backplane, the circuit board every drive plugs into. "
                    "The main computer is still switched off, yet something is "
                    "already reading this bay, listing every drive it finds. "
                    "The power supplies have woken a small helper computer on "
                    "their standby power, and it is taking stock of the "
                    "machine. We meet that helper near the end of the tour."
                ),
                standard=(
                    "The front edge is the drive bay: 24 hot-swap 2.5-inch "
                    "slots for NVMe, SAS or SATA drives, plugged into a "
                    "backplane that routes each bay to the RAID controller or "
                    "straight to CPU PCIe lanes. The host is still off, yet "
                    "the backplane is already being queried. The standby rail "
                    "has woken a management controller, and it is walking the "
                    "chassis over low-speed sideband buses, taking inventory "
                    "before the host ever powers on. We meet it near the end."
                ),
                expert=(
                    "24x 2.5-inch bay, backplane to PERC or direct NVMe. "
                    "Host off; the BMC is already inventorying the backplane "
                    "over sideband."
                ),
            ),
            # The front of the chassis, nearly full height: the bay runs the whole
            # front edge, so a tighter box would cut it (and its label) in half.
            camera=_FRONT,
            region_ids=["backplane"],
            layer_reveal=_OUTSIDE,
            trace_cursor=3,
            duration_ms=26_000,
        ),
        TourStep(
            id="fan-wall",
            title="Lid off: six fans at full roar",
            script=L(
                novice=(
                    "We lift the lid. Right behind the drives stands a wall of "
                    "six fans, and they pull air from the front of the server "
                    "to the back, across everything inside. The main power "
                    "has just come on, and all six fans jump straight to full "
                    "speed with a roar anyone who works in a data centre "
                    "knows. That is on purpose. Nothing has read the "
                    "temperature sensors yet, so the safe guess is as much air "
                    "as possible. Under the fans' path, a plastic cover called "
                    "the air shroud still hides the processors and memory."
                ),
                standard=(
                    "With the lid peeled back, the fan wall sits right behind "
                    "the drive bay: six hot-swap fans pulling air front to "
                    "rear across drives, memory, CPUs and risers. The main "
                    "12 V rails have just come up, and all six fans slam to "
                    "100%. It is deliberate: until the thermal sensors have "
                    "been read, maximum airflow is the only safe assumption. "
                    "The air shroud, the plastic duct over the sockets, is "
                    "still in place."
                ),
                expert=(
                    "Lid off. Six hot-swap fans, front-to-rear airflow. Main "
                    "rails up, fans to 100% until sensors are read. Shroud "
                    "still on."
                ),
            ),
            # All six fans stand in one full-height column; keep them all in view.
            camera=_FRONT,
            region_ids=[f"fan-{i}" for i in range(6)],
            layer_reveal=_LID,
            trace_cursor=5,
            duration_ms=28_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="DDR5 memory training, the long pause",
            script=L(
                novice=(
                    "Now the air shroud comes off, and we reach the two "
                    "processors, each flanked by banks of memory sticks called "
                    "DIMMs, 32 slots in all. The processors have started and "
                    "the start-up checks have begun, but the memory cannot be "
                    "used yet. Each processor must first train every memory "
                    "stick: it tries timing and voltage settings on every "
                    "wire until it finds ones that work reliably. Modern "
                    "memory runs so fast that the right settings cannot be "
                    "fixed in advance. This is the longest stage of the whole "
                    "start-up. A fully loaded server can sit here for minutes "
                    "on its first boot, looking as if it is doing nothing. "
                    "The results are saved, so later boots go much faster."
                ),
                standard=(
                    "With the air shroud off, the two Xeon sockets sit between "
                    "their DDR5 banks, 16 slots per CPU, 32 in all. The CPUs "
                    "are out of reset and POST (Power-On Self-Test) is running "
                    "from cache, because there is no usable RAM yet. Each "
                    "CPU's memory controller now trains every DIMM, sweeping "
                    "timing and voltage per lane to find reliable settings at "
                    "4800 to 5600 MT/s, margins too fine to hardcode. It is "
                    "the single longest stage in the trace: a fully loaded "
                    "machine can sit here for minutes on first boot. Results "
                    "are cached, so later boots are faster."
                ),
                expert=(
                    "Shroud off. Two sockets, 32 DDR5 slots. POST in "
                    "cache-as-RAM; per-lane timing/Vref training at "
                    "4800-5600 MT/s. Longest stage; minutes cold, cached "
                    "after."
                ),
            ),
            camera=frame("dimm-a1", "dimm-a2", "dimm-b1", "dimm-b2", "cpu1", "cpu2", pad=1.0),
            region_ids=["dimm-a1", "dimm-a2", "dimm-b1", "dimm-b2", "cpu1", "cpu2"],
            layer_reveal=_SHROUD,
            trace_cursor=8,
            duration_ms=44_000,
            photo_id="interior",
        ),
        TourStep(
            id="perc-and-boss",
            title="Data drives on PERC, the OS on BOSS-N1",
            script=L(
                novice=(
                    "Two small parts decide where everything is stored. At the "
                    "front, beside the drive bay, is the PERC, Dell's RAID "
                    "card: it combines the front drives into protected groups "
                    "and keeps a battery-backed memory so writes survive a "
                    "power cut. It is checking that memory now, and starting "
                    "spinning disks a few at a time, because 24 motors "
                    "starting at once could overload the power supplies. At "
                    "the back is the BOSS-N1, a module with two small flash "
                    "drives that copy each other, holding only the operating "
                    "system. That keeps all 24 front slots free for data."
                ),
                standard=(
                    "Two parts decide where things live. The front-mounted "
                    "PERC (PowerEdge RAID Controller) runs its own firmware, "
                    "checks its battery-backed cache and verifies its RAID "
                    "volumes, starting spinning drives in staggered groups so "
                    "24 motors' inrush cannot trip the power budget. At the "
                    "rear, the BOSS-N1 (Boot Optimized Storage Solution) holds "
                    "two M.2 NVMe drives in a hardware RAID-1 mirror for the "
                    "operating system, keeping all 24 front bays free for "
                    "data."
                ),
                expert=(
                    "PERC: firmware up, BBU cache checked, volumes verified, "
                    "staggered spin-up. BOSS-N1: two M.2 NVMe in RAID-1 for "
                    "the OS; front bays stay data-only."
                ),
            ),
            camera=frame("perc", "backplane", "boss", pad=2.0),
            region_ids=["perc", "backplane", "boss"],
            layer_reveal=_SHROUD,
            trace_cursor=10,
            duration_ms=28_000,
        ),
        TourStep(
            id="idrac-corner",
            title="Meet the brain: iDRAC9",
            script=L(
                novice=(
                    "Here, near the back, is the helper computer from the "
                    "start of the tour: iDRAC9, short for integrated Dell "
                    "Remote Access Controller. It is a small, always-on "
                    "computer with its own software and its own network "
                    "port. It woke about ten seconds after the cords went "
                    "in, long before the main server. It listed the drives "
                    "and memory, it treats the power button as just another "
                    "request, and it sets the fan speeds. The start-up checks "
                    "have now passed, and because iDRAC finally has the full "
                    "temperature picture, the fans settle down to about a "
                    "third of full speed. This controller has its own twin in "
                    "this collection, the iDRAC twin, which follows its "
                    "start-up with the server switched off throughout."
                ),
                standard=(
                    "Near the rear sits the controller from the drive-bay "
                    "beat: iDRAC9 (integrated Dell Remote Access Controller), "
                    "a baseboard management controller with its own ARM "
                    "processor, OS, network port and web/Redfish API. It "
                    "began booting about ten seconds after AC, long before the host; "
                    "it took the inventory, the power button is just another "
                    "input to it, and it is the thermal brain. POST has now "
                    "passed, iDRAC logs the milestone, and with the thermal "
                    "picture known the fans settle to a managed 30% or so. "
                    "The iDRAC twin in this collection walks its own firmware "
                    "bring-up, with the host off throughout."
                ),
                expert=(
                    "iDRAC9 BMC: booting from t+10 s on standby, did inventory, "
                    "owns power control and fan policy. POST complete, fans "
                    "down to ~30%. See the iDRAC twin for its own bring-up."
                ),
            ),
            camera=frame("idrac", "board", "boss", pad=2.0),
            region_ids=["idrac", "board"],
            layer_reveal=_SHROUD,
            trace_cursor=11,
            duration_ms=30_000,
        ),
        TourStep(
            id="reassemble",
            title="Lid on, operating system running",
            script=L(
                novice=(
                    "The shroud and lid go back on. The server has loaded its "
                    "operating system from the BOSS module, and it is now "
                    "doing real work. Sitting idle it draws around 250 watts "
                    "with the fans near a quarter of full speed, and both "
                    "numbers climb as the work grows. All these figures are "
                    "illustrative, not measured. The iDRAC keeps watching "
                    "throughout, just as it has since the cords went in. To "
                    "see what the same server does while it works, with heat "
                    "and fans reacting to load, open the R760 thermal twin. "
                    "The power-on page walks this start-up one step at a time."
                ),
                standard=(
                    "Shroud and lid back on. The OS has loaded off the BOSS "
                    "mirror and the server is serving: a dual-socket R760 "
                    "idles around 250 W with fans near 25%, both climbing "
                    "with load under iDRAC's thermal control (illustrative "
                    "figures). iDRAC keeps watching out of band, as it has "
                    "since ten seconds after AC. The R760 thermal twin picks "
                    "up here, with what happens while it runs; the power-on "
                    "page walks this trace step by step."
                ),
                expert=(
                    "Reassembled, OS up. ~250 W idle, ~25% fans "
                    "(illustrative). BMC watching out of band. Next: the "
                    "R760 thermal twin."
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
        id="r760-tour",
        title="Inside a PowerEdge R760, from AC to OS",
        intro=L(
            novice=(
                "A guided walk through the server as it starts up, narrated "
                "beat by beat. Sit back and watch, or pause and click anything "
                "to look closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through the server while it powers on. Watch "
                "it play, or pause and explore; Resume tour brings the camera "
                "back."
            ),
            expert="Narrated AC-to-OS walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=_photos(),
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: ChassisAnatomy) -> TourResponse:
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
