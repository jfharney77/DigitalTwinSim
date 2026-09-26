"""Every model constant in one place, each with units and a source — the
suite's honesty rule (BUILD_PLAN: constants discipline). Values marked
``estimated=False`` trace to Dell's published spec pages, the EPREL energy
label, or Dell's Product Carbon Footprint datasheets; everything else says
``estimate`` and the UI badges readouts that derive from estimates.

The two panel personalities are deliberately concrete classes rather than
exact SKUs: "edge-27" is a U2723QE-class 27-inch 4K edge-lit IPS Black
panel; "miniled-32" is a UP3221Q-class 32-inch 4K panel with 2,000
mini-LED local-dimming zones. Where a class value is derived from one
model's datasheet, the source says which.
"""

from __future__ import annotations

from .models import Constant

CONSTANTS: dict[str, Constant] = {
    # --- Shared electronics ------------------------------------------------
    "psu_efficiency": Constant(
        value=0.88, unit="fraction",
        source="estimate — small internal AC/DC boards run 85–90%",
        estimated=True,
        blurb="Internal power-supply efficiency: AC in = DC loads ÷ this.",
    ),
    "standby_w": Constant(
        value=0.3, unit="W",
        source="Dell U2723QE product page tech specs — standby 0.3 W "
        "(off mode 0.2 W); the UP3221Q user's guide lists 0.2 W standby, "
        "shared here as one class value",
        estimated=False,
        blurb="Standby draw with the panel asleep and USB wake armed.",
    ),
    "hub_efficiency": Constant(
        value=0.90, unit="fraction",
        source="estimate — USB-C PD conversion stage", estimated=True,
        blurb="Delivered laptop watts ÷ watts the hub stage consumes; the "
              "rest is heat inside the monitor.",
    ),
    "hub_max_w": Constant(
        value=90, unit="W",
        source="Dell U2723QE product page — USB-C upstream power delivery "
        "up to 90 W; the UP3221Q's Thunderbolt 3 upstream is also 90 W",
        estimated=False,
        blurb="Maximum USB-C power delivery to a docked laptop.",
    ),
    "zone_floor_fraction": Constant(
        value=0.04, unit="fraction", source="estimate", estimated=True,
        blurb="Mini-LED zones never fully extinguish while the panel is on "
              "(halo control, zone electronics): the dimming floor.",
    ),
    "hdr_boost": Constant(
        value=2.5, unit="× SDR backlight max", source="estimate — the "
        "UP3221Q's 1000 cd/m² DisplayHDR 1000 peak (Dell product page) over "
        "an assumed ~400 cd/m² SDR working ceiling, as a "
        "luminance-proportional LED power ratio; the 400 is the model's "
        "assumption, not a Dell figure",
        estimated=True,
        blurb="How far the lit zones overdrive during an HDR highlight.",
    ),
    "hdr_boost_edge": Constant(
        value=1.15, unit="× SDR backlight max",
        source="estimate — DisplayHDR 400 class headroom on the edge-lit panel",
        estimated=True,
        blurb="Edge-lit HDR headroom: the whole strip brightens a little; "
              "there are no zones to overdrive selectively.",
    ),
    # --- edge-27 (U2723QE-class) --------------------------------------------
    "edge_electronics_w": Constant(
        value=9.0, unit="W", source="estimate — scaler, USB hub idle, logic",
        estimated=True,
        blurb="Panel-independent electronics power, edge-lit 27-inch class.",
    ),
    "edge_backlight_max_w": Constant(
        value=29.0, unit="W",
        source="estimate — sized so electronics + backlight reach ~38 W "
        "at 100% brightness. Dell publishes 25.9 W on-mode for the U2723QE, "
        "measured at the test luminance rather than full brightness; the "
        "~38 W full-brightness figure is the model's, not Dell's",
        estimated=True,
        blurb="Edge-lit LED strip power at 100% brightness.",
    ),
    "edge_max_ac_w": Constant(
        value=220, unit="W",
        source="Dell U2723QE spec — 220 W maximum (panel + full 90 W hub load)",
        estimated=False,
        blurb="Nameplate maximum wall draw with every port loaded.",
    ),
    # --- miniled-32 (UP3221Q-class) -------------------------------------------
    "mini_electronics_w": Constant(
        value=15.0, unit="W",
        source="estimate — larger scaler, zone drivers, colorimeter logic",
        estimated=True,
        blurb="Panel-independent electronics power, mini-LED 32-inch class.",
    ),
    "mini_backlight_max_w": Constant(
        value=55.0, unit="W",
        source="estimate — derived so electronics + full-field backlight ≈ "
        "the UP3221Q's 68.3 W on-mode figure (Dell UP3221Q user's guide; "
        "its nameplate maximum is 380 W with every port loaded)",
        estimated=True,
        blurb="Full-array mini-LED power with every zone at 100%.",
    ),
    "mini_zones": Constant(
        value=2000, unit="zones",
        source="Dell UP3221Q product page — 2,000 mini-LED local-dimming "
        "zones, VESA DisplayHDR 1000",
        estimated=False,
        blurb="Independently dimmable backlight zones.",
    ),
    # --- Content lit fractions (what share of the field is actually bright) --
    "lit_dark": Constant(
        value=0.12, unit="fraction", source="estimate — dark-UI/terminal mix",
        estimated=True, blurb="Average backlight demand of dark content.",
    ),
    "lit_mixed": Constant(
        value=0.50, unit="fraction", source="estimate — documents + web mix",
        estimated=True, blurb="Average backlight demand of mixed content.",
    ),
    "lit_bright": Constant(
        value=0.90, unit="fraction", source="estimate — white documents, CAD",
        estimated=True, blurb="Average backlight demand of bright content.",
    ),
    "lit_hdr": Constant(
        value=0.45, unit="fraction",
        source="estimate — HDR mastering: extreme highlights over mid-bright "
        "fields",
        estimated=True,
        blurb="Average lit share of HDR mastering content (the highlights "
              "are extreme but not the whole field).",
    ),
    # --- Lifetime carbon ------------------------------------------------------
    "embodied_edge_kg": Constant(
        value=422, unit="kgCO2e",
        source="Dell S2722QC PCF datasheet (Sept 2022) — mean 638 kgCO2e "
        "± 167, use phase 33.8%; the non-use remainder (manufacturing 57.8% "
        "+ transport 7.5% + EoL 0.9%) as a 27-inch 4K class proxy. "
        "https://www.delltechnologies.com/asset/en-us/products/electronics-and-accessories/technical-support/dell-s2722qc-monitor-pcf-datasheet.pdf",
        estimated=False,
        blurb="Embodied carbon (manufacturing + transport + end-of-life), "
              "27-inch class.",
    ),
    "embodied_mini_kg": Constant(
        value=516, unit="kgCO2e",
        source="Dell P3424WE PCF datasheet (Nov 2022) — mean 777 kgCO2e "
        "± 198, use phase 33.6%, 6-year life; non-use remainder as the "
        "large-premium-panel proxy. The P3424WE is a 34-inch curved "
        "ultrawide, not a mini-LED panel — Dell publishes no PCF for the "
        "UP3221Q, so this is the nearest class, not the SKU. "
        "https://www.delltechnologies.com/asset/en-us/products/electronics-and-accessories/technical-support/dell-p3424we-monitor-pcf-datasheet.pdf",
        estimated=False,
        blurb="Embodied carbon (manufacturing + transport + end-of-life), "
              "32-inch mini-LED class.",
    ),
    "laptop_total_kg": Constant(
        value=241, unit="kgCO2e",
        source="Dell Latitude 7490 carbon footprint datasheet — 241 kgCO2e "
        "± 53, 4-year life. "
        "https://i.dell.com/sites/csdocuments/CorpComm_Docs/en/carbon-footprint-latitude-7490.pdf",
        estimated=False,
        blurb="A business laptop's lifetime footprint, for the contrast.",
    ),
    "laptop_use_pct": Constant(
        value=12, unit="%",
        source="Dell Latitude E7440 carbon footprint whitepaper — use 12%, "
        "manufacturing 78%, transport 10% of 276 kgCO2e. "
        "https://i.dell.com/sites/doccontent/corporate/corp-comm/en/Documents/PCF-WP-E7440.pdf",
        estimated=False,
        blurb="Share of a business laptop's footprint that is use-phase.",
    ),
    "grid_default_kgco2_per_kwh": Constant(
        value=0.4, unit="kgCO2e/kWh",
        source="estimate — order of a world-average grid; slide it for "
        "your region",
        estimated=True,
        blurb="Grid carbon intensity used unless the scenario overrides it.",
    ),
}


def value(name: str) -> float:
    """Shorthand the engine uses; keeps call sites terse."""
    return CONSTANTS[name].value
