"""Device maps for the client-device simulator — three stylized interior
views (Alienware laptop, Alienware desktop tower, Pro Max Plus), each a
set of thermal zones keyed to the engine's ``region_temps``. Same idiom
as the R760 thermal twin: the geometry is a mental model traced from
service imagery, not a service manual. The laptop maps are bottom-up
service views (bottom cover off); the tower is a side-panel view.
"""

from __future__ import annotations

from .leveling import L
from .models import DeviceMap, DeviceRegion


def _common_laptop_regions(npu: bool) -> list[DeviceRegion]:
    """Shared laptop interior: fans in the rear corners, CPU/GPU on the
    shared heat-pipe spine, battery across the front. The Pro Max Plus
    variant carves an NPU card bay out of the board area."""
    regions = [
        DeviceRegion(
            id="fan-0", kind="cooling", label="Fan L",
            x=2, y=2, w=16, h=14,
            description=(
                "Left blower of the pair. Laptop fans are small and "
                "high-pitched: noise rises roughly with the square of "
                "speed, and quiet mode works by capping this fan's "
                "ceiling — a cap you pay for in silicon temperature and, "
                "under load, in frames."
            ),
        ),
        DeviceRegion(
            id="fan-1", kind="cooling", label="Fan R",
            x=82, y=2, w=16, h=14,
            description=(
                "Right blower. The two fans pull air through the bottom "
                "intake and push it out the rear vents — which is why "
                "setting the machine on a lap or duvet chokes it: the "
                "intake is the surface it is resting on."
            ),
        ),
        DeviceRegion(
            id="cpu", kind="cpu", label="CPU",
            x=24, y=4, w=22, h=13,
            description=(
                "The mobile CPU package. It lives under power limits, not "
                "a TDP: PL2 for bursts (a boost window of tens of "
                "seconds), PL1 sustained, and below both whenever the "
                "skin cap or the shared thermal budget binds. The "
                "burst-then-fade shape this produces is the defining "
                "curve of laptop performance."
            ),
        ),
        DeviceRegion(
            id="gpu", kind="gpu", label="GPU",
            x=52, y=4, w=24, h=13,
            description=(
                "The discrete GPU die, sharing heat pipes with the CPU — "
                "one thermal budget, two claimants. Under game load the "
                "power-shift logic favors this die; the CPU gets clipped "
                "first. Frame rate in this simulator is a proxy computed "
                "from the watts this die actually receives."
            ),
        ),
        DeviceRegion(
            id="dimm", kind="memory", label="RAM",
            x=30, y=21, w=18, h=12,
            description=(
                "SO-DIMM slots. A few watts — memory matters here for "
                "capacity, not heat."
            ),
        ),
        DeviceRegion(
            id="nvme", kind="storage", label="NVMe",
            x=52, y=21, w=18, h=12,
            description=(
                "M.2 NVMe slots under their shields. A sustained write "
                "can warm them, but in this model they are a small, "
                "steady term."
            ),
        ),
        DeviceRegion(
            id="battery", kind="battery", label="Battery",
            x=14, y=38, w=54, h=15,
            description=(
                "The Li-ion pack — the front third of the machine. "
                "Runtime is arithmetic: watt-hours times discharge "
                "efficiency over system watts. Charging adds heat "
                "(~10% of charge power), and a worn pack adds internal-"
                "resistance heat on top. When the charger is too small "
                "for the load, the deficit comes from here — plugged in "
                "or not."
            ),
        ),
        DeviceRegion(
            id="board", kind="board", label="Board / VR",
            x=74, y=21, w=24, h=12,
            description=(
                "Motherboard and voltage regulation — the fixed platform "
                "power (display included in the model's base term)."
            ),
        ),
        DeviceRegion(
            id="skin", kind="skin", label="Skin (palm rest / underside)",
            x=2, y=56, w=96, h=6,
            description=(
                "The zone servers do not have: the surface a human "
                "touches. It follows total internal heat with a slow "
                "time constant (metal is patient), and it carries a hard "
                "cap — when the skin reaches the contact limit, power "
                "limits fall no matter what the fans could do. Sustained "
                "performance in a laptop is a skin-temperature problem "
                "before it is a silicon one."
            ),
        ),
    ]
    if npu:
        # Carve the NPU bay out of the board strip.
        for r in regions:
            if r.id == "board":
                r.w = 10.0
        regions.append(DeviceRegion(
            id="npu", kind="npu", label="NPU card",
            x=86, y=21, w=12, h=12,
            description=(
                "The discrete NPU (Qualcomm AI-100-class) — a third "
                "compute engine competing for the same shared thermal "
                "budget. Its pitch is not speed but efficiency: tokens "
                "per joule several times the GPU's, which is the "
                "difference between inference that spins the fans and "
                "inference the meeting room cannot hear."
            ),
        ))
    return regions


LAPTOP_OVERVIEW = L(
    novice=(
        "You are looking up into an open gaming laptop — the bottom cover "
        "is off. Two fans sit in the rear corners; between them are the "
        "two chips that do the work, the processor and the graphics chip, "
        "joined by shared copper heat pipes. The battery fills the front. "
        "The strip along the bottom edge of the picture stands for the "
        "surface your hands touch. That strip is the real limit: a "
        "laptop must stay comfortable to touch, so when the case gets "
        "too warm the machine quietly turns its own performance down — "
        "no matter how fast the fans could spin. Everything this "
        "simulator teaches follows from three facts: the two big chips "
        "share one cooling system, the case touches a person, and the "
        "battery is a bucket of watt-hours that drains by arithmetic."
    ),
    standard=(
        "The laptop interior as thermal zones, service view (bottom cover "
        "off): blower pair in the rear corners, CPU and GPU on a shared "
        "heat-pipe spine — one dissipation budget, two claimants — RAM, "
        "NVMe, and the voltage regulation midboard, the battery across "
        "the front, and the skin zone drawn along the bottom edge. The "
        "skin is the constraint servers never meet: it follows total "
        "internal heat on a slow time constant and carries a hard "
        "contact cap that overrides fan logic and forces power limits "
        "down. Add the PL2→PL1 burst window and the battery's "
        "Wh × η ÷ W arithmetic and you have the three mechanics that "
        "make client devices different from the rack hardware elsewhere "
        "in this repo."
    ),
    expert=(
        "Bottom-service view. Blower pair; CPU+GPU on one heat-pipe "
        "budget (allocator favors GPU); skin zone, τ≈120 s, hard cap "
        "overriding fan control; PL2 τ≈28 s → PL1; battery Wh·η/W with "
        "charge-heat and IR-loss terms. The client trinity: shared "
        "budget, skin cap, battery arithmetic."
    ),
)


ALIENWARE_LAPTOP = DeviceMap(
    id="aw-laptop",
    name="Alienware 16/18-class gaming laptop · power & thermal model",
    vendor="Dell Technologies",
    form_factor="Gaming laptop — interior service view",
    generation="Alienware m-series class",
    year=2025,
    width=100,
    height=64,
    overview=LAPTOP_OVERVIEW,
    regions=_common_laptop_regions(npu=False),
    sources=[
        {"label": "physics_specs/07-client-devices.md (this repo)",
         "url": "../physics_specs/07-client-devices.md"},
        {"label": "DellAlienware twin — the AC power path of the same machine",
         "url": "http://localhost:5176/"},
    ],
)


PROMAX = DeviceMap(
    id="promax",
    name="Dell Pro Max Plus mobile workstation · power & thermal model",
    vendor="Dell Technologies",
    form_factor="Mobile workstation — interior service view",
    generation="Pro Max Plus (discrete-NPU option)",
    year=2025,
    width=100,
    height=64,
    overview=L(
        novice=(
            "This is the same kind of picture as the gaming laptop — "
            "bottom cover off, fans at the back, battery at the front — "
            "but this machine is built for eight-hour renders rather "
            "than eight-minute benchmarks, and it has one part the "
            "gaming machine lacks: a dedicated AI chip (an NPU) on its "
            "own small card. The NPU is not the fastest way to run an "
            "AI model here — the graphics chip is faster — but it does "
            "far more work per unit of battery, and it does it almost "
            "silently. This simulator lets you run the same AI job on "
            "all three engines and watch speed, heat, noise, and "
            "battery drain differ."
        ),
        standard=(
            "The Pro Max Plus interior: the gaming laptop's layout with "
            "a workstation's priorities — sustained (PL1) performance "
            "and acoustics over burst — plus the discrete NPU card, a "
            "third claimant on the shared thermal budget. The teaching "
            "instrument is tokens per joule: run the local-LLM preset "
            "on CPU, GPU, or NPU and compare speed, heat, noise, and "
            "battery drain. The NPU loses the speed race to the GPU "
            "and wins efficiency by a wide margin — which is the whole "
            "argument for putting a dedicated inference engine in a "
            "portable machine."
        ),
        expert=(
            "Workstation register: PL1-sustained + acoustics over "
            "burst. Discrete AI-100-class NPU as third budget claimant; "
            "tokens/joule is the instrument. NPU: slower than GPU, "
            "several× better per joule, near-silent. Same skin/battery "
            "mechanics as the gaming chassis."
        ),
    ),
    regions=_common_laptop_regions(npu=True),
    sources=[
        {"label": "physics_specs/07-client-devices.md (this repo)",
         "url": "../physics_specs/07-client-devices.md"},
        {"label": "DellProMaxPlus twin — the on-device inference data path",
         "url": "http://localhost:5186/"},
    ],
)


ALIENWARE_DESKTOP = DeviceMap(
    id="aw-desktop",
    name="Alienware desktop tower · power & thermal model",
    vendor="Dell Technologies",
    form_factor="Gaming desktop — side-panel view",
    generation="Alienware Aurora class",
    year=2025,
    width=100,
    height=64,
    overview=L(
        novice=(
            "A gaming tower with the side panel off. The graphics card "
            "is the big block in the middle — in a machine like this it "
            "draws more power than everything else combined. Unlike the "
            "laptop, nothing here shares a cooler: the processor has its "
            "own, the graphics card has its own, and the case has room "
            "for enough airflow that neither is likely to slow down. "
            "The limits that remain are electrical — the power supply "
            "at the bottom has a rating, and pushing past it for long "
            "trips its protection — and acoustic, since four fans at "
            "full speed are not subtle. There is no battery and no "
            "skin-temperature worry: this is what performance looks "
            "like when the constraints are removed."
        ),
        standard=(
            "The tower, side-panel view: PSU at the bottom, the "
            "double-wide GPU dominating the midboard, tower-cooled CPU "
            "above it, four case fans. The desktop is this app's "
            "control group — no shared heat-pipe budget, no skin cap, "
            "no battery — so the burst-then-fade curve the laptop "
            "cannot escape simply does not appear. What remains is the "
            "R760's electrical physics at consumer scale: a PSU "
            "efficiency curve (80 Plus Gold class), an overcurrent "
            "trip if the build outdraws its supply, and the cubic fan "
            "law priced in dB(A) instead of rack noise nobody hears."
        ),
        expert=(
            "Control group: no shared budget, no skin cap, no battery. "
            "PSU η-curve + overcurrent trip; per-part throttle only; "
            "cubic fans → dB(A). Laptop-vs-desktop A/B is the lesson."
        ),
    ),
    regions=[
        DeviceRegion(
            id="fan-0", kind="cooling", label="Front intake",
            x=2, y=6, w=8, h=22,
            description="Front intake fan — cool room air in.",
        ),
        DeviceRegion(
            id="fan-1", kind="cooling", label="Front intake",
            x=2, y=32, w=8, h=22,
            description="Second front intake.",
        ),
        DeviceRegion(
            id="fan-2", kind="cooling", label="Top exhaust",
            x=40, y=2, w=22, h=6,
            description="Top exhaust fan — heat rises, help it leave.",
        ),
        DeviceRegion(
            id="fan-3", kind="cooling", label="Rear exhaust",
            x=90, y=6, w=8, h=18,
            description="Rear exhaust behind the CPU cooler.",
        ),
        DeviceRegion(
            id="cpu", kind="cpu", label="CPU + tower cooler",
            x=52, y=10, w=26, h=16,
            description=(
                "Desktop CPU under its own tower cooler. Same power "
                "curve as the laptop but with limits it rarely meets: "
                "the burst window exists, yet the cooler usually holds "
                "the die below throttle indefinitely — sustained equals "
                "burst, which is the desktop's whole personality."
            ),
        ),
        DeviceRegion(
            id="dimm", kind="memory", label="RAM",
            x=82, y=28, w=6, h=20,
            description="DIMM slots beside the socket.",
        ),
        DeviceRegion(
            id="gpu", kind="gpu", label="GPU (double-wide)",
            x=24, y=30, w=48, h=16,
            description=(
                "The double-wide graphics card — 200 to 450 W, the "
                "biggest consumer in the case by a wide margin. It has "
                "its own fans and fin stack; the case fans only need to "
                "hand it cool air and take away what it exhausts."
            ),
        ),
        DeviceRegion(
            id="nvme", kind="storage", label="NVMe",
            x=24, y=50, w=14, h=8,
            description="M.2 slots under the GPU.",
        ),
        DeviceRegion(
            id="board", kind="board", label="Board / VR",
            x=42, y=50, w=18, h=8,
            description="Motherboard, VRs, lighting — the fixed platform term.",
        ),
        DeviceRegion(
            id="psu", kind="power", label="PSU",
            x=66, y=50, w=32, h=12,
            description=(
                "The tower PSU (750–1500 W, 80 Plus Gold-class curve in "
                "this model). Wall watts exceed DC watts by the "
                "efficiency margin, and a build that outdraws the "
                "rating trips protection after a sustained overload — "
                "warn, then simulate the consequence, same as the R760."
            ),
        ),
        DeviceRegion(
            id="skin", kind="skin", label="Side panel",
            x=12, y=6, w=8, h=48,
            description=(
                "The side panel — drawn for symmetry with the laptops, "
                "but nobody types on a tower: the skin cap does not "
                "bind here, and that absence is itself the lesson."
            ),
        ),
    ],
    sources=[
        {"label": "physics_specs/07-client-devices.md (this repo)",
         "url": "../physics_specs/07-client-devices.md"},
    ],
)


MAPS: dict[str, DeviceMap] = {
    "aw-laptop": ALIENWARE_LAPTOP,
    "aw-desktop": ALIENWARE_DESKTOP,
    "promax": PROMAX,
}


def map_for(product: str, form_factor: str) -> DeviceMap:
    if product == "promax":
        return PROMAX
    return ALIENWARE_DESKTOP if form_factor == "desktop" else ALIENWARE_LAPTOP
