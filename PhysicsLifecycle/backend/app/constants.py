"""Every model constant with units and a source. Spec 08's rule is
absolute here: sustainability numbers are never invented — everything
carbon-related below is a labeled literature estimate, and the real
calibration source is Dell's published per-product PCF reports."""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Telecom integration (the product's reason to exist) --------------
    "diy_validate_h_site": Constant(
        value=10, unit="h/site",
        source="estimate — separately validate server + OS + RAN software",
        estimated=True,
        blurb="Integration hours per DIY site (the compatibility matrix, worked by hand).",
    ),
    "blocks_deploy_h_site": Constant(
        value=1.5, unit="h/site",
        source="estimate — one validated bundle version per site", estimated=True,
        blurb="Integration hours per Blocks site.",
    ),
    "diy_mismatch_every_n": Constant(
        value=12, unit="sites",
        source="estimate — A×B×C version combinations fail somewhere, deterministically here",
        estimated=True,
        blurb="Every Nth DIY site hits a version mismatch (outage + penalty hours).",
    ),
    "mismatch_penalty_h": Constant(
        value=16, unit="h", source="estimate — debug a site that failed validation",
        estimated=True,
        blurb="Extra hours when a DIY site's version combination fails.",
    ),
    "mismatch_outage_h": Constant(
        value=8, unit="h", source="estimate", estimated=True,
        blurb="Site outage while a mismatch is repaired.",
    ),
    "standard_temp_limit_c": Constant(
        value=40, unit="°C",
        source="estimate — standard commercial ambient ceiling", estimated=True,
        blurb="Ambient above which standard-temp sites shut down.",
    ),
    "extended_temp_limit_c": Constant(
        value=55, unit="°C",
        source="estimate — XR-class extended envelope; verify against Dell XR spec sheets",
        estimated=True,
        blurb="Ambient ceiling for extended-temperature (XR-class) sites.",
    ),
    "heatwave_site_fraction": Constant(
        value=0.3, unit="fraction",
        source="estimate — share of sites past the standard ceiling on a 48 °C day",
        estimated=True,
        blurb="Fraction of standard-temp sites lost during a heatwave day.",
    ),
    "site_mttr_remote_h": Constant(
        value=4, unit="h", source="estimate — remote remediation", estimated=True,
        blurb="Site repair time with remote remediation.",
    ),
    "site_mttr_truck_h": Constant(
        value=24, unit="h", source="estimate — a drive to a hilltop", estimated=True,
        blurb="Site repair time requiring a visit.",
    ),
    # --- Circular Design (ALL estimates; calibrate from Dell PCF PDFs) ----
    "embodied_kg": Constant(
        value=280, unit="kgCO2e",
        source="estimate — laptop-class embodied carbon, literature range 200–350; calibrate from Dell PCF reports",
        estimated=True,
        blurb="Embodied carbon of manufacturing one laptop.",
    ),
    "recycled_chassis_saving": Constant(
        value=0.12, unit="fraction of embodied",
        source="estimate — recycled-content aluminum saving", estimated=True,
        blurb="Embodied-carbon saving from a recycled-content chassis.",
    ),
    "battery_part_kg": Constant(
        value=12, unit="kgCO2e", source="estimate — replacement pack, made and shipped",
        estimated=True,
        blurb="Carbon of one replacement battery.",
    ),
    "ram_part_kg": Constant(
        value=8, unit="kgCO2e", source="estimate — a SO-DIMM upgrade", estimated=True,
        blurb="Carbon of a RAM upgrade.",
    ),
    "repair_part_kg": Constant(
        value=6, unit="kgCO2e", source="estimate — a modular port/board part",
        estimated=True,
        blurb="Carbon of the mid-life repair part.",
    ),
    "grid_clean_kg_kwh": Constant(
        value=0.05, unit="kgCO2e/kWh",
        source="estimate — hydro/nuclear-heavy grid", estimated=True,
        blurb="Grid intensity, clean.",
    ),
    "grid_average_kg_kwh": Constant(
        value=0.35, unit="kgCO2e/kWh", source="estimate — world-average grid",
        estimated=True,
        blurb="Grid intensity, average.",
    ),
    "grid_coal_kg_kwh": Constant(
        value=0.85, unit="kgCO2e/kWh", source="estimate — coal-heavy grid",
        estimated=True,
        blurb="Grid intensity, coal-heavy.",
    ),
    "laptop_mass_kg": Constant(
        value=2.0, unit="kg", source="estimate — 16-inch-class device mass",
        estimated=True,
        blurb="Device mass, for the e-waste ledger.",
    ),
    "device_cost_usd": Constant(
        value=1800, unit="$", source="estimate — the lesson is the ratio, not the price",
        estimated=True,
        blurb="Purchase cost of one device.",
    ),
    "part_cost_usd": Constant(
        value=120, unit="$", source="estimate — battery/RAM/repair part average",
        estimated=True,
        blurb="Cost of one replaceable part.",
    ),
    # Lifecycle event schedule (deterministic, spec 08's year ranges).
    "battery_wear_day": Constant(
        value=1278, unit="day (~3.5 y)",
        source="estimate — spec 08: battery wears out year 3–4", estimated=True,
        blurb="Day the battery no longer holds charge.",
    ),
    "ram_short_day": Constant(
        value=1642, unit="day (~4.5 y)",
        source="estimate — spec 08: RAM becomes insufficient year 4–5", estimated=True,
        blurb="Day the RAM stops being enough.",
    ),
    "repair_day": Constant(
        value=912, unit="day (~2.5 y)",
        source="estimate — spec 08's random repair need, made deterministic",
        estimated=True,
        blurb="Day something breaks (a port, a hinge).",
    ),
    "refurb_base_success": Constant(
        value=0.35, unit="fraction",
        source="estimate — refurb economics of a sealed device", estimated=True,
        blurb="Second-life success probability floor (sealed design).",
    ),
    "refurb_modular_bonus": Constant(
        value=0.15, unit="fraction per modular choice",
        source="estimate — easier disassembly = viable refurb", estimated=True,
        blurb="Refurb-success bonus per repair-friendly design choice.",
    ),
}


def value(name: str) -> float:
    return CONSTANTS[name].value
