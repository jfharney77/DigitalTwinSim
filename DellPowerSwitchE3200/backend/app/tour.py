"""The narrated tour of the PowerSwitch E3200-ON — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: seven beats that
move a camera across the switch floorplan, peel the lid off to show the
switching ASIC and the control-plane CPU that manages it, pin the boot trace
at the moments that carry the story, and narrate each one. The frontend player
owns the clock; nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The storyboard: the front panel, then the peel (the ASIC is the actual
switch, the CPU is its manager), ONIE, the network-OS choice, the ASIC's
tables programmed, the PoE power peak leaving through the front ports, and
line rate. The signature beat is ``poe-peak``: most of an edge switch's
wattage is not the switch at all — it is power handed to the devices plugged
into it (``test_poe_step_is_the_power_peak``). Every claim the scripts make is
one the engine and the anatomy already make.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``ChassisAnatomy`` is unchanged:

    0  what you can see and touch: ports, uplinks, console, PSUs, fans
    1  under the lid: the switching ASIC, the control-plane CPU, the PoE
       power subsystem
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
from .models import ChassisAnatomy

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "poe-peak"

_OUTSIDE = 0
_BOARD = 1


def layer_map(anatomy: ChassisAnatomy) -> dict[str, int]:
    """Every region's layer, derived from its kind so a new region lands
    somewhere sensible without an edit here."""
    inside = {"asic", "cpu", "poe"}
    return {
        region.id: _BOARD if region.kind in inside else _OUTSIDE
        for region in anatomy.regions
    }


def build_tour(anatomy: ChassisAnatomy) -> Tour:
    """The E3200-ON tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="front-panel",
            title="Forty-eight ports and a console",
            script=L(
                novice=(
                    "This is a Dell PowerSwitch E3200-ON, a network switch: the "
                    "box in a wiring closet that lets every computer, phone and "
                    "wireless access point in a building talk to the others. We "
                    "are looking down on it from above, with the front on the "
                    "left. That long column is 48 network sockets, called ports, "
                    "where cables from the building plug in. Below them sit four "
                    "faster sockets, called uplinks, that connect this switch to "
                    "the rest of the network, and the small ports an engineer "
                    "uses to manage it. Right now it is unplugged: no power, and "
                    "nothing moving through it."
                ),
                standard=(
                    "This is a Dell PowerSwitch E3200-ON, a one-rack-unit edge "
                    "switch, seen from above with the front on the left. The "
                    "front carries 48 RJ45 access ports on the PoE models (the "
                    "E3224F has 24 fiber ports instead), four SFP+/SFP28 uplink "
                    "cages, and the console, USB and out-of-band management "
                    "ports. Power supplies, fans and two 100GbE QSFP28 uplinks "
                    "sit at the rear. The AC is disconnected and nothing is "
                    "forwarding."
                ),
                expert=(
                    "E3200-ON, 1RU, top-down, front left: 48 RJ45 (24 SFP on the "
                    "E3224F), 4 SFP+/SFP28, console/OOB. Rear: 2 PSUs, 4 fans, 2x 100G "
                    "QSFP28. AC off."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["access-ports", "sfp-uplinks", "mgmt-panel"],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=26_000,
        ),
        TourStep(
            id="asic-and-cpu",
            title="The chip that switches, and the computer that manages it",
            script=L(
                novice=(
                    "Let us lift the lid. The big block in the middle is the "
                    "switching chip, called an ASIC, short for "
                    "application-specific integrated circuit: a chip built to do "
                    "one job, moving network traffic, extremely fast. That chip "
                    "is the actual switch. The thin strip above it is a small "
                    "ordinary computer, the CPU, and its job is to manage the "
                    "chip, not to carry traffic. Power is connected now, and only "
                    "the power supplies, the computer and the fans have woken up. The fans run at "
                    "full speed until the software has read the temperature "
                    "sensors. The switching chip is still asleep."
                ),
                standard=(
                    "With the lid peeled back, the switch splits in two. The big "
                    "block is the switching ASIC (application-specific "
                    "integrated circuit), the data plane: every frame is switched "
                    "or routed in its hardware. The strip above it is the control "
                    "plane, a 4-core CPU with its own memory and SSD, whose job "
                    "is to manage the ASIC. The main rails are up and the CPU is "
                    "booting; the fans run at full until firmware reads the "
                    "sensors. The ASIC has not seen a packet yet."
                ),
                expert=(
                    "Lid off. ASIC = data plane, does the switching. 4-core CPU = "
                    "control plane, manages the ASIC. Main rails up, CPU booting, "
                    "fans at 100% pending sensors; ASIC idle."
                ),
            ),
            camera=frame("asic", "cpu", pad=2.0),
            region_ids=["asic", "cpu"],
            layer_reveal=_BOARD,
            trace_cursor=2,
            duration_ms=30_000,
        ),
        TourStep(
            id="onie",
            title="ONIE, the open part of E3200-ON",
            script=L(
                novice=(
                    "The computer now runs a small starter program called ONIE, "
                    "the Open Network Install Environment. This is what the ON "
                    "in the name means: Open Networking. Many switches come with "
                    "one fixed operating system from the company that made them. "
                    "This one boots ONIE first, and ONIE either starts the "
                    "operating system already installed, or, on a brand-new "
                    "switch, downloads one and installs it. So the same hardware "
                    "can run different software."
                ),
                standard=(
                    "The CPU runs ONIE, the Open Network Install Environment, "
                    "and this is what the '-ON' (Open Networking) in the name "
                    "means. Instead of a fixed vendor OS, the switch boots a "
                    "small open installer that either launches the network OS "
                    "already in flash or, on a factory-fresh unit, fetches and "
                    "installs one over the network. It is the disaggregation "
                    "layer that lets the same silicon run different operating "
                    "systems."
                ),
                expert=(
                    "ONIE: open installer/bootloader. Launches the installed NOS "
                    "or fetches one on a fresh unit. Hardware and OS "
                    "disaggregated."
                ),
            ),
            camera=frame("cpu", pad=3.0),
            region_ids=["cpu"],
            layer_reveal=_BOARD,
            trace_cursor=4,
            duration_ms=26_000,
        ),
        TourStep(
            id="nos-choice",
            title="OS10 or SONiC",
            script=L(
                novice=(
                    "ONIE hands over to the switch's real operating system, "
                    "called the network operating system or NOS. Which one "
                    "depends on the model: Dell SmartFabric OS10 on the fiber "
                    "model, Enterprise SONiC on the two copper models. Both are "
                    "built on Linux, so what boots here is a full small "
                    "computer's worth of software. This is the slowest part of "
                    "the whole start-up, and the switch looks idle while it "
                    "happens, just as a server looks idle while it trains its "
                    "memory in the PowerEdge R760 twin. The timeline lingers "
                    "here for that reason."
                ),
                standard=(
                    "ONIE hands off to the installed network operating system "
                    "(NOS): SmartFabric OS10 on the E3224F, Enterprise SONiC on "
                    "the E3248 models. A full Linux control plane boots, kernel "
                    "then switching stack and databases. It is the longest stage "
                    "in the trace, and the switch looks idle through it, exactly "
                    "as the R760 twin's server does during memory training, so "
                    "playback dwells here."
                ),
                expert=(
                    "NOS boot: OS10 (E3224F) or Enterprise SONiC (E3248). Linux "
                    "kernel, switching stack, databases. Longest stage, max "
                    "dwell."
                ),
            ),
            camera=frame("cpu", pad=3.0),
            region_ids=["cpu"],
            layer_reveal=_BOARD,
            trace_cursor=5,
            duration_ms=30_000,
        ),
        TourStep(
            id="asic-tables",
            title="Decisions pushed into silicon",
            script=L(
                novice=(
                    "The switching chip is awake now, and the computer fills it "
                    "with lists, called forwarding tables: which device is on which "
                    "port, which way to send traffic for each network, and "
                    "which traffic to block. Once those lists live inside the "
                    "chip, it no longer needs to ask the computer anything. It "
                    "looks up where each piece of traffic goes by itself, at "
                    "full speed. A moment ago the box was just a small "
                    "computer. Now it is a switch."
                ),
                standard=(
                    "With the ASIC initialized, the OS pushes its decisions into "
                    "the hardware tables: the MAC address table for Layer 2 "
                    "switching, the IP route and next-hop tables for Layer 3 "
                    "routing, VLAN membership, and access-control lists into "
                    "TCAM (ternary content-addressable memory). Once these are "
                    "resident in silicon, forwarding no longer needs the CPU; it "
                    "happens at wire speed. Until the ASIC woke, the box was a "
                    "Linux server. Now it is a switch."
                ),
                expert=(
                    "ASIC up; tables programmed: MAC, IP route/next-hop, "
                    "VLAN, ACLs in TCAM. Forwarding leaves the CPU for wire-speed "
                    "hardware."
                ),
            ),
            # The whole board: the tables live in the ASIC, and the CPU that
            # writes them sits on the strip above it. Both stay in frame.
            camera=frame("asic", "cpu", pad=1.0),
            region_ids=["asic", "cpu"],
            layer_reveal=_BOARD,
            trace_cursor=8,
            duration_ms=28_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="The power peak leaves through the front",
            script=L(
                novice=(
                    "This is the most important moment in the tour. The ports "
                    "are connected now, and the power section, the tall block "
                    "next to the ports, starts sending electricity down "
                    "the same network cables that carry data. This is called "
                    "Power over Ethernet, or PoE. The switch first checks that a "
                    "device on the other end can take power, asks how much it "
                    "needs, and only then switches the power on: up to 30 watts "
                    "a port on one copper model, up to 90 watts on the other "
                    "(the fiber model has no PoE). This is "
                    "the moment the wireless access points, desk phones and "
                    "cameras in the building actually turn on. Look at the "
                    "watts in the boot-trace line: they jump to "
                    "the highest they will ever be, about 900 watts in this "
                    "illustrative timeline, from about 250 a moment ago. Most of that is not the switch using "
                    "power. It is power passing through the switch and out of "
                    "the front ports to other devices."
                ),
                standard=(
                    "The PoE subsystem, the Power Sourcing Equipment beside the "
                    "access ports, negotiates with each attached powered device "
                    "(detect, classify, then energize) and starts delivering DC "
                    "power over the data pairs: up to 30 W per port under "
                    "802.3at, or 90 W under 802.3bt on the E3248PXE. Access "
                    "points, phones and cameras turn on here. This is the power "
                    "peak of the whole trace, about 900 W (illustrative) against "
                    "250 W a step earlier, and most of it is not the switch's "
                    "own draw. It is the PoE budget leaving through the front "
                    "ports, which is why the rear PSUs are sized to the PoE load."
                ),
                expert=(
                    "Signature: PoE is the power peak. PSE detect, classify, "
                    "energize; 802.3at 30 W or 802.3bt 90 W per port. Draw jumps "
                    "~250 to ~900 W (illustrative), mostly PoE budget exiting "
                    "the front ports."
                ),
            ),
            camera=frame("poe-system", "access-ports", pad=1.0),
            region_ids=["poe-system", "access-ports"],
            layer_reveal=_BOARD,
            trace_cursor=10,
            duration_ms=42_000,
        ),
        TourStep(
            id="line-rate",
            title="Line rate, with the CPU out of the path",
            script=L(
                novice=(
                    "The lid goes back on. The switch has joined the rest of the "
                    "network and now simply moves traffic, as fast as every port "
                    "can carry it, up to 1,560 gigabits a second on the fastest "
                    "model. The switching chip does all of that work. The small "
                    "computer only handles the switch's own housekeeping, and "
                    "the fans spin only as hard as the heat needs. Several "
                    "switches like this joined together form a whole network "
                    "fabric, which is the PowerSwitch SN6000 twin's story. Press "
                    "play on the Boot page to walk the same start-up one step "
                    "at a time."
                ),
                standard=(
                    "Reassembled and forwarding. The control plane has formed "
                    "its adjacencies (MLAG with its partner, BGP and OSPF "
                    "neighbors), and every port forwards at line rate through "
                    "the non-blocking fabric, up to 1,560 Gb/s on the E3248PXE, "
                    "with the CPU handling only control traffic and exceptions. "
                    "The PowerSwitch SN6000 twin picks up where this one stops: "
                    "not one switch booting but the fabric several of them "
                    "form. The Boot page walks the same trace one step at a time."
                ),
                expert=(
                    "Steady state: line rate, up to 1,560 Gb/s (E3248PXE), ASIC "
                    "forwards, CPU on control and exceptions only. Fabric-scale "
                    "view: the SN6000 twin."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=["asic", "access-ports", "sfp-uplinks", "qsfp-uplinks"],
            layer_reveal=_OUTSIDE,
            trace_cursor=12,
            duration_ms=28_000,
        ),
    ]

    return Tour(
        id="e3200-tour",
        title="Inside a PowerSwitch E3200-ON, as it boots",
        intro=L(
            novice=(
                "A guided walk through the switch as it starts up, narrated beat "
                "by beat. Sit back and watch, or pause and click anything to look "
                "closer; the tour waits for you."
            ),
            standard=(
                "A narrated walk through the switch while it boots. Watch it "
                "play, or pause and explore; Resume tour brings the camera back."
            ),
            expert="Narrated boot walk-through. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=[],
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
