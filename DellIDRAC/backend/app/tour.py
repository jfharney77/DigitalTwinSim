"""The narrated tour of the iDRAC9 service processor — pure data.

``build_tour(anatomy)`` returns a :class:`twinkit.tour.Tour`: nine beats that
move a camera across the BMC block diagram, peel it from the parts you can
reach from outside to the Root of Trust underneath, pin the bring-up trace at
the moments that carry the story, and narrate each one. The frontend player
owns the clock; nothing here knows about time, IO or the web (AST-checked in
``tests/test_tour.py``, the same rule as ``engine.py``).

The storyboard is ACTIVE_TWIN_SPEC.md section 8's iDRAC row, and the
signature beat is ``always-on``: the management plane is up, watching and
reachable while the host it manages has never been powered on. Every claim
the scripts make is one the engine and the anatomy already make — the trace
index named in each beat is the step whose description says the same thing,
and ``tests/test_engine.py::test_host_never_powers_on`` is the fact the whole
tour narrates.

Layers (region id -> layer) ride with the tour rather than on the anatomy
model, so ``SubsystemMap`` is unchanged:

    0  what touches the outside: standby power, the sideband buses into the
       host, the management NIC, console, virtual media, front-panel access
    1  the controller core: the SoC, its DRAM and flash, the monitoring engine
    2  the trust anchor: the silicon Root of Trust
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
from .models import SubsystemMap

#: The step the tests pin: the product's one idea lives here.
SIGNATURE_STEP_ID = "always-on"

_OUTSIDE = 0
_CORE = 1
_TRUST = 2


def layer_map(anatomy: SubsystemMap) -> dict[str, int]:
    """Every block's layer, derived from its kind so a new block lands
    somewhere sensible without an edit here."""
    core = {"soc", "memory", "sensor"}
    layers: dict[str, int] = {}
    for block in anatomy.regions:
        if block.kind == "security":
            layers[block.id] = _TRUST
        elif block.kind in core:
            layers[block.id] = _CORE
        else:
            layers[block.id] = _OUTSIDE
    return layers


def _photos() -> list[TourPhoto]:
    return [
        TourPhoto(
            id="console",
            url="/idrac9-console.svg",
            caption=(
                "The management plane as an administrator meets it: web console, "
                "Redfish, RACADM and IPMI, all served by the controller on this map."
            ),
            credit="Illustration for this teaching tool; not a Dell product image.",
        ),
    ]


def build_tour(anatomy: SubsystemMap) -> Tour:
    """The iDRAC9 tour, framed against ``anatomy``."""

    def frame(*ids: str, pad: float = 3.0) -> CameraTarget:
        return camera_around(anatomy, ids, pad=pad)

    steps = [
        TourStep(
            id="host-off",
            title="A server that is switched off",
            script=L(
                novice=(
                    "Picture a Dell PowerEdge R760, a rack server, sitting in a "
                    "data centre with its power cords unplugged. Everything inside "
                    "it is dark. This map does not show the whole server. It shows "
                    "one small part of it: the iDRAC, short for integrated Dell "
                    "Remote Access Controller, a tiny separate computer built into "
                    "the server whose only job is to look after the big one. Here "
                    "is how to read the map. The big block in the middle is the "
                    "iDRAC's own processor. The three blocks on the left are slow "
                    "wires that reach into the server to read its sensors and talk "
                    "to its processors. The blocks on the right face the outside "
                    "world: a network port, and tools for seeing the server's "
                    "screen from far away. For now nothing on this map has power, "
                    "so there is nothing here anyone could reach, from anywhere."
                ),
                standard=(
                    "Picture a Dell PowerEdge R760 in a rack, cords unplugged, "
                    "completely dark. This map is not the server; it is one "
                    "subsystem inside it, the iDRAC9 (integrated Dell Remote Access "
                    "Controller), the baseboard management controller, or BMC, that "
                    "every PowerEdge carries: a complete small computer on the "
                    "system board. Read it left to right. The sideband buses on the "
                    "left reach into the host's sensors, CPUs and network ports; "
                    "the system-on-chip (SoC) in the centre is the service "
                    "processor; the dedicated NIC, virtual console and virtual "
                    "media on the right face the outside world. With no AC, none of "
                    "it is reachable."
                ),
                expert=(
                    "PowerEdge R760, no AC. Map: the iDRAC9 BMC as a logical block "
                    "diagram, host-side sideband buses left, SoC centre, external "
                    "interfaces right. All dark, nothing reachable."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_OUTSIDE,
            trace_cursor=0,
            duration_ms=36_000,
        ),
        TourStep(
            id="one-warm-corner",
            title="The one warm corner",
            script=L(
                novice=(
                    "Now the power cords go in, but nobody presses the power "
                    "button. Even so, one small corner of the server wakes up. The "
                    "power supply sends out a trickle of electricity, a few watts "
                    "(the numbers in this tour are rough examples), on a separate "
                    "line called the standby rail. It feeds only the iDRAC's own "
                    "little computer, its memory and its network port. The "
                    "server's main processors get nothing and stay off. That "
                    "trickle is why a server that is plugged in is never truly off."
                ),
                standard=(
                    "The cords go in and nobody touches the power button. The power "
                    "supply brings up a standby rail, a few watts (the figures here "
                    "are illustrative), that feeds only the iDRAC's power island: "
                    "the SoC, its memory and the management NIC. The host's main "
                    "rails stay off. This one warm corner is why a plugged-in server "
                    "is never truly off, and why you can reach iDRAC before anyone "
                    "presses power."
                ),
                expert=(
                    "AC applied, no power button. Standby rail, a few watts "
                    "(illustrative), feeds only the BMC island: SoC, DRAM, NIC. "
                    "Host rails off."
                ),
            ),
            camera=frame("pwr", pad=6.0),
            region_ids=["pwr"],
            layer_reveal=_CORE,
            trace_cursor=1,
            duration_ms=26_000,
        ),
        TourStep(
            id="boot-rom",
            title="The one piece of code that cannot change",
            script=L(
                novice=(
                    "With its trickle of power steady, the iDRAC's processor is let "
                    "out of reset, which just means it is allowed to start. That "
                    "processor is a system on a chip, or SoC: a whole computer "
                    "squeezed onto one chip. The first thing it runs is a tiny "
                    "program built into the chip itself, called the boot ROM. "
                    "Nobody can ever change or replace that program. Its only job "
                    "is to find the iDRAC's main start-up software in its storage "
                    "chip and hand over to it."
                ),
                standard=(
                    "With standby power stable, the iDRAC SoC is released from "
                    "reset. Its on-chip boot ROM runs first, the one piece of code "
                    "in the BMC that cannot be reflashed, and its only job is to "
                    "find iDRAC's first-stage firmware in flash and hand off to it."
                ),
                expert=(
                    "SoC out of reset. Immutable on-chip boot ROM executes; its "
                    "sole job is locating the first-stage image in flash."
                ),
            ),
            camera=frame("soc", "pwr", pad=3.0),
            region_ids=["pwr", "soc"],
            layer_reveal=_CORE,
            trace_cursor=2,
            duration_ms=24_000,
        ),
        TourStep(
            id="root-of-trust",
            title="Nothing runs until it is signed",
            script=L(
                novice=(
                    "Before that start-up software may run, the iDRAC checks "
                    "that nobody has tampered with it. A block of security "
                    "circuitry called the Root of Trust checks the software's "
                    "digital signature, a kind of tamper-proof seal, against a key "
                    "burned into the chip at the factory. If the software has been "
                    "altered or damaged, it is refused right here, before it can do "
                    "anything. Only software that passes gets to run, and this "
                    "first check starts a chain of checks that later covers the "
                    "server's own start-up firmware too. Two Dell security "
                    "features rest on it: System Lockdown, which freezes a "
                    "server's settings and firmware against changes, and Secured "
                    "Component Verification, which checks that the parts inside "
                    "are the ones that left the factory."
                ),
                standard=(
                    "Before the first-stage firmware in flash may execute, the "
                    "silicon Root of Trust checks its cryptographic signature "
                    "against a key fused into the chip. Tampered or corrupt "
                    "firmware is rejected here, at the very bottom of the stack; "
                    "only a valid image proceeds, and it anchors the chain that "
                    "goes on to validate BIOS and other firmware. System Lockdown "
                    "and Secured Component Verification rest on this step. The Fort "
                    "Zero twin calls it the hardware root of trust."
                ),
                expert=(
                    "Silicon RoT verifies the flash image against a fused key "
                    "before execution. Reject at the bottom of the stack; anchors "
                    "BIOS validation, System Lockdown, SCV."
                ),
            ),
            camera=frame("soc", "rot", "flash", pad=2.0),
            region_ids=["soc", "rot", "flash"],
            layer_reveal=_TRUST,
            trace_cursor=3,
            duration_ms=30_000,
        ),
        TourStep(
            id="sideband-buses",
            title="Reaching into a host that is off",
            script=L(
                novice=(
                    "The chip has loaded its memory and started its own operating "
                    "system, a small version of Linux. Now it switches on the three "
                    "buses on the left. One reads temperature sensors, power "
                    "supplies and memory sticks. One talks to the server's main "
                    "processors and its start-up firmware. One lets the iDRAC "
                    "borrow one of the server's own network ports. These links are "
                    "called out-of-band, because they work even while the main "
                    "processors are switched off, which is exactly how they are "
                    "right now."
                ),
                standard=(
                    "The bootloader has initialized the iDRAC's own DDR4 and "
                    "embedded Linux is up. Now the kernel binds drivers to the "
                    "sideband buses: I2C and PMBus (its power-management variant) "
                    "for sensors, PSUs and DIMMs; eSPI and PECI (the Enhanced "
                    "Serial Peripheral Interface and Platform Environment Control "
                    "Interface) for the host CPUs and BIOS; NC-SI (Network "
                    "Controller Sideband Interface), the shared-LOM path through "
                    "which iDRAC can borrow a host LAN-on-motherboard port. These "
                    "are out-of-band links: they work with the host CPUs powered "
                    "off, which is the state the host is in right now."
                ),
                expert=(
                    "Linux up in dedicated DDR4. Sideband drivers bound: I2C/PMBus, "
                    "eSPI/PECI, NC-SI. Out-of-band; host CPUs still off."
                ),
            ),
            camera=frame("soc", "sb-espi", "sb-i2c", "sb-ncsi", pad=2.0),
            region_ids=["soc", "sb-espi", "sb-i2c", "sb-ncsi"],
            layer_reveal=_TRUST,
            trace_cursor=6,
            duration_ms=32_000,
        ),
        TourStep(
            id="lifecycle-controller",
            title="The longest stage",
            script=L(
                novice=(
                    "This is the slowest part of the whole start-up, so the "
                    "timeline lingers here. The iDRAC is waking up the Lifecycle "
                    "Controller, a set-up tool kept in the same storage chip as the "
                    "iDRAC's own software. It compares "
                    "its saved list of the server's parts with what the buses are "
                    "reporting right now, and gets its tools ready for installing "
                    "software, updating firmware and changing settings. Because "
                    "this tool lives inside the iDRAC, a brand new server with no "
                    "operating system and no install disk can still have one "
                    "installed. "
                    "It is what runs when someone presses F10 as the server starts."
                ),
                standard=(
                    "The longest stage in the trace, so playback dwells here. The "
                    "embedded Lifecycle Controller mounts its repository from "
                    "flash, reconciles its stored hardware inventory against what "
                    "the sideband buses report, and readies its deployment, "
                    "firmware-update and configuration services. It is the "
                    "machinery behind pressing F10 at boot and behind zero-touch "
                    "provisioning: a bare server with no OS and no media can deploy "
                    "one, because this engine lives in flash."
                ),
                expert=(
                    "Longest stage (max cycleCost): Lifecycle Controller mounts its "
                    "flash repository, reconciles inventory, readies deploy, update "
                    "and config services. F10; zero-touch."
                ),
            ),
            camera=frame("soc", "flash", "dram", pad=3.0),
            region_ids=["soc", "flash", "dram"],
            layer_reveal=_TRUST,
            trace_cursor=8,
            duration_ms=34_000,
        ),
        TourStep(
            id="front-door",
            title="A front door with its own address",
            script=L(
                novice=(
                    "Now the iDRAC's own network port gets an address on the "
                    "network, either handed out automatically or typed in by an "
                    "administrator. This port is separate from all of the "
                    "server's normal network ports and carries only management "
                    "traffic. The moment it has an address, someone at a desk "
                    "anywhere on the management network can open the iDRAC's web "
                    "page, even though the server's main processors still have "
                    "not been switched on. Instead of its own port, the iDRAC "
                    "could borrow one of the server's normal ports through the "
                    "bottom-left link on the map, but its own port keeps "
                    "management traffic physically apart."
                ),
                standard=(
                    "The dedicated 1GbE management port acquires its IP address, "
                    "by DHCP (automatic address assignment) by default or a static "
                    "address set in iDRAC Settings or the "
                    "Lifecycle Controller. It is its own RJ-45, separate from every "
                    "host NIC, carrying only management traffic; the NC-SI path on "
                    "the left could borrow a host port instead. The moment it has an "
                    "address, an administrator can open the web console, though "
                    "the host is still off."
                ),
                expert=(
                    "Dedicated 1GbE NIC gets its IP (DHCP or static); NC-SI shared "
                    "LOM is the alternative. Reachable now; host still off."
                ),
            ),
            camera=frame("sb-ncsi", "soc", "nic", pad=2.0),
            region_ids=["soc", "nic", "sb-ncsi"],
            layer_reveal=_TRUST,
            trace_cursor=9,
            duration_ms=26_000,
        ),
        TourStep(
            id=SIGNATURE_STEP_ID,
            title="Ready and watching, host still off",
            script=L(
                novice=(
                    "This is the most important moment in the tour. The iDRAC is "
                    "fully awake. Its monitoring engine reads every sensor over "
                    "the buses on the left, keeps a log of everything that "
                    "happens, and controls the fan speeds from the temperatures "
                    "it reads. Its network port on the right stays open, waiting "
                    "for an administrator to ask it to switch the server on, "
                    "update its firmware or install an operating system. The big "
                    "server has still never been switched on. The whole time, the "
                    "iDRAC has used only a few watts, and it keeps watching like "
                    "this for as long as the server stays plugged in. (The watt "
                    "figures are rough examples, not measurements.)"
                ),
                standard=(
                    "This is the idea the whole twin exists to show. Bring-up is "
                    "complete and the management plane settles into what it does "
                    "forever after: watching. The monitoring engine samples every "
                    "sensor over the sideband buses, keeps the Lifecycle Log and "
                    "owns the fan loop, while the NIC holds the web console, "
                    "Redfish (the standard REST API for server management) and "
                    "virtual media open for a command. The host has never powered "
                    "on, and the BMC domain has drawn only a few watts throughout "
                    "(illustrative). It never stops while the server is plugged "
                    "in."
                ),
                expert=(
                    "Signature: always-on, out-of-band. Steady-state watch: "
                    "sensors, Lifecycle Log, fan loop, NIC open. Host never "
                    "powered; BMC draw single-digit watts (illustrative). Runs "
                    "while AC is present."
                ),
            ),
            camera=frame("soc", "monitor", "sb-i2c", "sb-espi", "nic", pad=2.0),
            region_ids=["soc", "monitor", "sb-i2c", "sb-espi", "nic"],
            layer_reveal=_TRUST,
            trace_cursor=13,
            duration_ms=40_000,
        ),
        TourStep(
            id="reassemble",
            title="The power button is just another input",
            script=L(
                novice=(
                    "Step back and look at the whole map again. From plugging in "
                    "to ready took under a minute and a half on this illustrative "
                    "timeline, and the server itself is still off. From here, even "
                    "the power button is just one more request the iDRAC handles. "
                    "When someone presses it, or clicks it from far away, the "
                    "iDRAC starts the server, and that start-up is the story told "
                    "by the R760 power-on twin. The R760 thermal twin shows the fan "
                    "control this controller runs once the server is working."
                ),
                standard=(
                    "The whole map again. Cords-in to ready took under a minute and "
                    "a half on this illustrative timeline, and the host is still "
                    "dark. From here the power button is just another input to "
                    "iDRAC: an administrator can power the host on from anywhere, "
                    "and everything the R760 power-on twin shows begins from a "
                    "signal sent here. The R760 thermal twin shows the fan loop "
                    "this controller runs once the host is working."
                ),
                expert=(
                    "Ready in under 90 s (illustrative), host dark. Power button is "
                    "an iDRAC input; the R760 power-on twin starts from this "
                    "signal. Fan loop: R760 thermal twin."
                ),
            ),
            camera=whole_map(anatomy),
            region_ids=[],
            layer_reveal=_OUTSIDE,
            trace_cursor=13,
            duration_ms=26_000,
            photo_id="console",
        ),
    ]

    return Tour(
        id="idrac-tour",
        title="Inside iDRAC9, while the server sleeps",
        intro=L(
            novice=(
                "A guided walk through the small management computer inside every "
                "PowerEdge server as it starts up, narrated beat by beat. Sit back "
                "and watch, or pause and click any block to look closer; the tour "
                "waits for you."
            ),
            standard=(
                "A narrated walk through iDRAC9's own bring-up, with the host "
                "powered off throughout. Watch it play, or pause and explore; "
                "Resume tour brings the camera back."
            ),
            expert="Narrated BMC bring-up, host off. Pause to explore; resume restores framing.",
        ),
        steps=steps,
        photos=_photos(),
        sources=[TourSource(label=s.label, url=s.url) for s in anatomy.sources],
    )


def build_response(anatomy: SubsystemMap) -> TourResponse:
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
