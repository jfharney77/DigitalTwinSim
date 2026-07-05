"""The laptop catalog: machines and adapters as data, not code.

Like the R760's catalog.py, everything here is model instances a frontend
can render directly. Wattages, connector geometry, and battery figures come
from Dell's owner's manuals and support KBs (see the research notes and the
source links in anatomy.py); descriptions are written for a technically
expert reader who has never owned an Alienware, so Dell-specific jargon
(PSID, EC, TGP, ExpressCharge) is spelled out where it first matters.
"""

from __future__ import annotations

from .models import AdapterOption, Battery, LaptopProfile

# ---------------------------------------------------------------------------
# Alienware m18 R2 — the 18-inch flagship of the m-series era (2024)
# ---------------------------------------------------------------------------

M18_R2 = LaptopProfile(
    id="m18-r2",
    name="Alienware m18 R2",
    family="m-series",
    cpu="Intel Core i9-14900HX",
    cpu_max_w=157,
    gpu="GeForce RTX 4090 Laptop",
    gpu_tgp_w=175,
    battery=Battery(wh=97.0, cells=6, voltage=11.4, express_charge=True),
    default_adapter_id="barrel-280",
    idle_w=25,
    anatomy_id="m18-r2",
    description=(
        "Dell's performance-first 18-inch gaming laptop, the last m-series "
        "flagship before the 2025 rebrand. The chassis is deliberately "
        "thick: it exists to hold a 175 W TGP (total graphics power — the "
        "sustained power budget NVIDIA lets the GPU draw) RTX 4090 Laptop "
        "and a 157 W-peak i9 at full tilt, which is why it ships with 280 W "
        "or 360 W adapters where an ultrabook ships with 65 W. The 97 Wh "
        "battery is the largest US airlines allow in the cabin."
    ),
    adapters=[
        AdapterOption(
            id="barrel-280",
            name="280 W barrel (7.4 mm)",
            watts=280,
            connector="barrel",
            voltage=19.5,
            amps=14.36,
            recognized=True,
            description=(
                "The standard m18 R2 brick: 19.5 V at 14.36 A through a "
                "7.4 mm outer / 5.1 mm inner coaxial barrel plug. A third "
                "conductor — a center pin inside the inner barrel — carries "
                "a 1-Wire data signal from an ID chip (the PSID, power "
                "supply ID) so the laptop knows exactly what it is plugged "
                "into. 280 W covers most gaming loads, but a full CPU+GPU "
                "burn can exceed it, at which point the battery quietly "
                "makes up the difference (hybrid power)."
            ),
        ),
        AdapterOption(
            id="barrel-360",
            name="360 W SFF barrel (7.4 mm)",
            watts=360,
            connector="barrel",
            voltage=19.5,
            amps=18.46,
            recognized=True,
            description=(
                "The uprated small-form-factor brick: 19.5 V at 18.46 A, "
                "same 7.4 mm connector and PSID handshake. Its extra 80 W "
                "of headroom keeps a sustained all-core CPU plus 175 W GPU "
                "workload entirely on wall power, so the battery never has "
                "to supplement — the adapter to buy for multi-hour "
                "unattended compute runs."
            ),
        ),
        AdapterOption(
            id="usbc-100",
            name="100 W USB-C PD (budget-limited)",
            watts=100,
            connector="usbc",
            voltage=20.0,
            amps=5.0,
            recognized=True,
            description=(
                "A 100 W USB Power Delivery charger on the Thunderbolt "
                "port. USB-C negotiates its contract digitally (no PSID "
                "pin needed), so the laptop recognizes it — but 100 W is "
                "under half what even light gaming draws on this machine. "
                "It will trickle-charge an idle laptop; under load the "
                "battery carries most of the deficit and drains while "
                "plugged in. Travel fallback, not a power supply."
            ),
        ),
        AdapterOption(
            id="barrel-unknown",
            name="280 W barrel · damaged ID pin",
            watts=280,
            connector="barrel",
            voltage=19.5,
            amps=14.36,
            recognized=False,
            description=(
                "The same 280 W brick with a bent or broken center ID pin, "
                "so the embedded controller cannot read the PSID chip. The "
                "adapter still delivers 19.5 V, but BIOS reports it as "
                "'Unknown' and the platform refuses to trust it: battery "
                "charging is disabled and CPU/GPU power limits are capped "
                "hard. This is also what a cheap third-party replacement "
                "without the ID chip looks like to the machine."
            ),
        ),
    ],
)

# ---------------------------------------------------------------------------
# Alienware 18 Area-51 — the post-rebrand 18-inch flagship (2025)
# ---------------------------------------------------------------------------
# Dell retired the m-/x-series names in the 2025 rebrand; the 18 Area-51 is
# the m18's successor. CPU/GPU wattages and the battery figure below are
# representative of the class ([inferred] where Dell hasn't published the
# exact number) — per the project's scope guardrails, mental model over
# spec-sheet precision.

AREA51_18 = LaptopProfile(
    id="area51-18",
    name="Alienware 18 Area-51",
    family="Area-51",
    cpu="Intel Core Ultra 9 275HX",
    cpu_max_w=160,
    gpu="GeForce RTX 5090 Laptop",
    gpu_tgp_w=175,
    battery=Battery(wh=96.0, cells=6, voltage=11.4, express_charge=True),
    default_adapter_id="barrel-360",
    idle_w=28,
    anatomy_id="area51-18",
    description=(
        "The 2025 flagship that replaced the m18 when Dell retired the "
        "m-/x-series names. Same recipe, new generation: Intel Core Ultra "
        "200HX silicon, RTX 50-series graphics up to a 175 W TGP RTX 5090, "
        "and 'Cryo-chamber' cooling — the rebrand's evolution of the "
        "vapor-chamber-plus-heat-pipe stack. The AC power path is "
        "unchanged: 19.5 V barrel input, 1-Wire adapter identification, "
        "and hybrid battery supplement under peak load."
    ),
    adapters=[
        AdapterOption(
            id="barrel-360",
            name="360 W barrel (7.4 mm)",
            watts=360,
            connector="barrel",
            voltage=19.5,
            amps=18.46,
            recognized=True,
            description=(
                "The default brick for the 18 Area-51: 19.5 V at 18.46 A "
                "with the PSID center-pin handshake. Sized so that CPU and "
                "GPU can both hold their full power limits with margin for "
                "charging and peripherals."
            ),
        ),
        AdapterOption(
            id="barrel-280",
            name="280 W barrel (7.4 mm)",
            watts=280,
            connector="barrel",
            voltage=19.5,
            amps=14.36,
            recognized=True,
            description=(
                "A recognized but smaller Dell brick — the m18 R2's "
                "standard adapter. It runs the machine, but a combined "
                "CPU+GPU burn overshoots its budget and the battery "
                "supplements the difference, draining slowly while "
                "plugged in."
            ),
        ),
        AdapterOption(
            id="barrel-unknown",
            name="360 W barrel · damaged ID pin",
            watts=360,
            connector="barrel",
            voltage=19.5,
            amps=18.46,
            recognized=False,
            description=(
                "A full-wattage brick whose PSID chip can no longer be "
                "read over the center pin. Plenty of power on the rail, "
                "but the EC reports 'Unknown', disables charging, and caps "
                "performance — wattage the platform can't verify is "
                "wattage it won't budget for."
            ),
        ),
    ],
)

PROFILES: dict[str, LaptopProfile] = {p.id: p for p in (M18_R2, AREA51_18)}
DEFAULT_PROFILE = M18_R2
