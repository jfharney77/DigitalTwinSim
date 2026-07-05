"""Interior-anatomy data: annotated floorplans of Alienware 18-inch laptops.

Like the GPU and R760 apps, the anatomy is data, not code. Each ``Anatomy``
describes the laptop opened from below — bottom cover off, battery and
motherboard exposed — as regions in a normalized 100×62 coordinate space
the frontend renders as SVG. Rear (hinge) edge is at y=0; the palm-rest
edge at y=62. Dual fans sit in the top corners, the motherboard with the
CPU and GPU dies spans the center, and the battery fills the bottom third.

Geometry is stylized, traced from Dell's service photo of the m18 interior
(frontend/public/alienware-interior.jpg). Per the project's scope
guardrails: favor a correct mental model over exact mm placement.
"""

from __future__ import annotations

from .models import Anatomy, Photo, Region, SourceLink, Stat

P_M18_INTERIOR = Photo(
    url="/alienware-interior.jpg",
    caption=(
        "Inside the Alienware m18 with the bottom cover removed: dual "
        "fans in the rear corners, the copper heat-pipe and vapor-chamber "
        "assembly bridging the CPU and GPU, and the 97 Wh battery spanning "
        "the front third of the chassis."
    ),
    credit="Dell Alienware service photo",
)

_FAN_DESC = (
    "One of the two main fans. High-blade-count blowers pull air through "
    "the bottom intake, push it across the fin stacks at the heat-pipe "
    "ends, and exhaust it out the rear and sides. Fan curves follow the "
    "AWCC (Alienware Command Center) thermal mode — from 'Quiet' up to "
    "'Full Speed', which pins them at 100%. The brief full-speed blip at "
    "power-on is a documented self-test, not a fault."
)

_IO_DESC = (
    "A side port cluster: USB-A, USB-C, and audio on the chassis edge, "
    "wired back to the motherboard. Bus-powered peripherals hanging off "
    "these ports count against the same adapter power budget as the CPU "
    "and GPU — Dell's hybrid-power KB calls out 'gaming with USB devices "
    "attached' as a load that can push total demand past the adapter."
)


def _regions_18_inch() -> list[Region]:
    """The shared 18-inch floorplan; both dies use the same physical layout.

    Region ids are the vocabulary ``PowerState.activeRegions`` speaks, so
    the set (and ids) must stay in sync with engine.py.
    """
    return [
        Region(
            id="fan-left",
            kind="cooling",
            label="Fan · left",
            x=2, y=2, w=16, h=14,
            description=_FAN_DESC,
        ),
        Region(
            id="fan-right",
            kind="cooling",
            label="Fan · right",
            x=82, y=2, w=16, h=14,
            description=_FAN_DESC,
        ),
        Region(
            id="heatpipes",
            kind="cooling",
            label="Vapor chamber · heat pipes",
            x=20, y=4, w=42, h=6,
            description=(
                "The copper thermal assembly bridging the CPU and GPU dies "
                "to both fans' fin stacks. On this class of machine it "
                "combines heat pipes with a vapor chamber — a flat, sealed "
                "plate in which a working fluid evaporates over the die and "
                "condenses at the cool end, spreading heat far faster than "
                "solid copper. Dell brands the stack 'Cryo-tech'; on the "
                "highest trims a gallium-based liquid-metal compound "
                "(Element 31) replaces conventional paste on the CPU die."
            ),
        ),
        Region(
            id="dc-in",
            kind="power",
            label="DC-in jack",
            x=74, y=2, w=6, h=5,
            description=(
                "The rear power jack: a 7.4 mm outer / 5.1 mm inner coaxial "
                "barrel carrying 19.5 V DC, plus a third center pin that is "
                "a 1-Wire data line. Over that pin the laptop reads the "
                "adapter's PSID (power supply ID) EEPROM to learn its "
                "wattage before trusting it — a bent center pin is the "
                "classic cause of BIOS reporting the adapter as 'Unknown'."
            ),
        ),
        Region(
            id="cpu",
            kind="board",
            label="CPU",
            x=26, y=12, w=14, h=10,
            description=(
                "The processor die, soldered to the motherboard under the "
                "thermal assembly. It can burst far above its sustained "
                "power, and package temperatures touching 99–100 °C under "
                "load are documented as normal: Intel's thermal control "
                "circuit trims a few hundred MHz at the limit rather than "
                "shutting down. A BIOS 'TCC offset' can move that trigger "
                "up to 15 °C lower for a cooler, slightly slower machine."
            ),
        ),
        Region(
            id="gpu",
            kind="board",
            label="GPU die",
            x=48, y=12, w=16, h=12,
            description=(
                "The discrete GPU, soldered alongside the CPU and sharing "
                "the same thermal assembly. Its power budget is the TGP "
                "(total graphics power) — the sustained wattage the "
                "platform lets it draw, 175 W here, which the GPU only "
                "gets on AC with a recognized full-wattage adapter. On "
                "battery or an 'Unknown' adapter the platform cuts this "
                "limit sharply."
            ),
        ),
        Region(
            id="vram",
            kind="memory",
            label="GDDR6 VRAM",
            x=48, y=25, w=16, h=4,
            description=(
                "The GPU's dedicated graphics memory: GDDR6 packages "
                "arranged around the GPU die to keep trace lengths short. "
                "They share the GPU's thermal solution via pads to the "
                "vapor-chamber plate, and their power draw is accounted "
                "inside the GPU's TGP budget."
            ),
        ),
        Region(
            id="ec",
            kind="board",
            label="Embedded controller",
            x=20, y=24, w=8, h=6,
            description=(
                "The EC (embedded controller): a small always-on "
                "microcontroller that runs even when the laptop is 'off', "
                "drawing a few watts from battery or standby power. It "
                "owns the power button, the keyboard, the fans, the "
                "adapter PSID handshake, and the power-budget decision — "
                "the whole plug-in sequence in this simulator is the EC's "
                "state machine."
            ),
        ),
        Region(
            id="charger",
            kind="power",
            label="Charger · power path",
            x=66, y=12, w=10, h=8,
            description=(
                "The charging and power-path stage near the DC-in jack: "
                "the circuitry that decides whether the system runs from "
                "the adapter, the battery, or both at once (hybrid power), "
                "and that steps 19.5 V down to the pack's charge voltage "
                "through the precharge, constant-current, and constant-"
                "voltage stages of a Li-ion charge cycle."
            ),
        ),
        Region(
            id="dimm",
            kind="memory",
            label="SO-DIMM slots",
            x=30, y=25, w=14, h=8,
            description=(
                "Two user-accessible SO-DIMM slots for DDR5 system memory "
                "— one of the reasons the m-series chassis is thick where "
                "thin-and-light designs solder RAM. Memory is checked "
                "during POST; the power LED blinking a red/blue 2,3 code "
                "means no memory was detected."
            ),
        ),
        Region(
            id="ssd",
            kind="storage",
            label="M.2 SSD slots",
            x=66, y=22, w=10, h=8,
            description=(
                "M.2 slots for NVMe SSDs, under thermal pads that sink "
                "into the chassis. The OS loads from here during boot; "
                "sustained transfers add a handful of watts to the system "
                "power the adapter budget must cover."
            ),
        ),
        Region(
            id="wlan",
            kind="wireless",
            label="Wi-Fi module",
            x=8, y=20, w=8, h=6,
            description=(
                "The M.2 2230 wireless module (Wi-Fi + Bluetooth), with "
                "antenna leads running up into the display lid. A "
                "single-digit-watt consumer, but one that stays powered "
                "in modern-standby sleep states."
            ),
        ),
        Region(
            id="io-left",
            kind="io",
            label="I/O · left",
            x=0.5, y=18, w=5, h=24,
            description=_IO_DESC,
        ),
        Region(
            id="io-right",
            kind="io",
            label="I/O · right",
            x=94.5, y=18, w=5, h=24,
            description=_IO_DESC,
        ),
        Region(
            id="battery",
            kind="battery",
            label="Battery · 6-cell Li-ion",
            x=14, y=42, w=72, h=18,
            description=(
                "The 6-cell lithium-ion pack spanning the front of the "
                "chassis, with its own battery management system. It is "
                "not just a backup: under peak load the platform "
                "deliberately discharges it in parallel with the AC "
                "adapter (hybrid power), and its firmware enforces the "
                "94–100% hold band, the precharge rules for a deeply "
                "drained pack, and the under-voltage protection that "
                "hard-stops everything if a weak adapter lets it run dry."
            ),
        ),
    ]


M18_R2_ANATOMY = Anatomy(
    id="m18-r2",
    name="Alienware m18 R2",
    vendor="Dell (Alienware)",
    platform="18″ gaming laptop · Intel HX + RTX 40-series",
    year=2024,
    width=100,
    height=62,
    overview=(
        "The m18 R2 opened from below. The layout is the power path made "
        "visible: 19.5 V enters at the DC-in jack (rear right), the "
        "charger and power-path stage beside it routes energy between "
        "adapter, battery, and system, and the EC on the motherboard "
        "referees the whole exchange. The CPU and GPU dies sit under a "
        "shared vapor-chamber-and-heat-pipe assembly flanked by two fans "
        "— together they can demand more than the 280 W adapter supplies, "
        "which is exactly why the 97 Wh battery across the front third is "
        "wired to supplement the wall, not just replace it."
    ),
    regions=_regions_18_inch(),
    stats=[
        Stat(label="Adapter", value="280 W or 360 W SFF · 19.5 V barrel"),
        Stat(label="Adapter ID", value="1-Wire PSID chip, center pin"),
        Stat(label="Battery", value="6-cell 97 Wh · 11.4 V"),
        Stat(label="ExpressCharge", value="~80% in 1 h (lid closed)"),
        Stat(label="GPU power", value="RTX 4090 Laptop · 175 W TGP"),
        Stat(label="CPU", value="i9-14900HX · up to 157 W"),
        Stat(label="Hybrid power", value="Battery supplements AC at peak"),
    ],
    sources=[
        SourceLink(
            label="Dell — m18 R2 power adapter specs",
            url="https://www.dell.com/support/manuals/en-us/alienware-m18-r2-laptop/alienware-m18-r2-owners-manual/power-adapter",
        ),
        SourceLink(
            label="Dell — m18 R1 battery specs",
            url="https://www.dell.com/support/manuals/en-us/alienware-m18-r1-laptop/alienware-m18-r1-setup-and-specifications/battery",
        ),
        SourceLink(
            label="Dell KB — battery drain on AC is hybrid power by design",
            url="https://www.dell.com/support/kbdoc/en-us/000143915/alienware-15-r3-15-r4-17-r4-17-r5-m15-m17-performance-issue-or-battery-drain-while-ac-adapter-is-connected",
        ),
        SourceLink(
            label="Dell KB — wrong/unknown AC adapter on Alienware laptops",
            url="https://www.dell.com/support/kbdoc/en-us/000218837/no-power-after-shut-down-using-the-incorrect-ac-adapter-on-alienware-gaming-laptops",
        ),
        SourceLink(
            label="Dell — m18 R2 diagnostic LED codes",
            url="https://www.dell.com/support/manuals/en-us/alienware-m18-r2-laptop/alienware-m18-r2-owners-manual/system-diagnostic-lights",
        ),
    ],
    photo=P_M18_INTERIOR,
)

AREA51_18_ANATOMY = Anatomy(
    id="area51-18",
    name="Alienware 18 Area-51",
    vendor="Dell (Alienware)",
    platform="18″ gaming laptop · Core Ultra 200HX + RTX 50-series",
    year=2025,
    width=100,
    height=62,
    overview=(
        "The 18 Area-51 is the m18's successor from the 2025 rebrand that "
        "retired the m-/x-series names. The interior follows the same "
        "18-inch recipe — dual fans, a shared CPU/GPU thermal assembly "
        "(now branded 'Cryo-chamber'), battery across the front, 19.5 V "
        "barrel input with the 1-Wire PSID handshake — so this floorplan "
        "reuses the m18 layout as its mental model. What changed is the "
        "silicon on top of it: Core Ultra 200HX and RTX 50-series GPUs up "
        "to a 175 W TGP RTX 5090."
    ),
    regions=_regions_18_inch(),
    stats=[
        Stat(label="Adapter", value="360 W · 19.5 V barrel"),
        Stat(label="Adapter ID", value="1-Wire PSID chip, center pin"),
        Stat(label="Battery", value="6-cell ~96 Wh"),
        Stat(label="GPU power", value="RTX 5090 Laptop · 175 W TGP"),
        Stat(label="CPU", value="Core Ultra 9 275HX"),
        Stat(label="Cooling", value="Cryo-chamber (vapor chamber + pipes)"),
    ],
    sources=[
        SourceLink(
            label="Dell KB — adapter wattage requirements by model",
            url="https://www.dell.com/support/kbdoc/en-us/000218837/no-power-after-shut-down-using-the-incorrect-ac-adapter-on-alienware-gaming-laptops",
        ),
        SourceLink(
            label="Dell KB — AC adapter troubleshooting and BIOS recognition",
            url="https://www.dell.com/support/kbdoc/en-us/000125125/how-to-troubleshoot-ac-adapter-issues",
        ),
        SourceLink(
            label="CES 2026 lineup coverage (16/18 Area-51, 16X Aurora)",
            url="https://wccftech.com/alienware-2026-laptop-16x-aurora-18-16-area-51-16-oled-brand-new-entry-level-ultra-slim-models/",
        ),
    ],
    photo=Photo(
        url="/alienware-interior.jpg",
        caption=(
            "Interior of the previous-generation m18, whose dual-fan, "
            "center-motherboard, front-battery layout the 18 Area-51 "
            "broadly carries forward."
        ),
        credit="Dell Alienware service photo",
    ),
)

ANATOMIES: dict[str, Anatomy] = {
    a.id: a for a in (M18_R2_ANATOMY, AREA51_18_ANATOMY)
}
