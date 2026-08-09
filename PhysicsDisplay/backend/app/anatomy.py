"""The panel map — a stylized front view of the monitor with the
electronics shelf drawn below the glass (in reality it sits behind it;
drawing it beside keeps every region visible and non-overlapping, the
repo's map idiom). Geometry invariants live in tests/test_model_data.py:
the panel is the largest region by area, because on a monitor the screen
*is* the product and the electronics are a footnote."""

from __future__ import annotations

from .leveling import L
from .models import PanelMap, PanelRegion

ANATOMY = PanelMap(
    id="ultrasharp",
    name="Dell UltraSharp (edge-lit 27 / mini-LED 32 classes)",
    vendor="Dell",
    form_factor="Desktop display",
    generation="UltraSharp 4K USB-C hub class",
    year=2022,
    width=100,
    height=64,
    overview=L(
        novice=(
            "This is a computer monitor drawn face-on, with the parts that "
            "normally hide behind the screen laid out along the bottom so "
            "you can see them. The big rectangle is the screen itself. "
            "Behind every screen like this sits a light source — the "
            "backlight — because the liquid-crystal layer that forms the "
            "picture makes no light of its own; it only blocks or passes "
            "the light behind it. How that backlight is built is the whole "
            "story here. A cheaper design runs a strip of LEDs along the "
            "edge and spreads their light across the back of the screen — "
            "so the backlight is either on or off as one piece. A fancier "
            "design tiles the back with thousands of tiny LEDs in zones "
            "that can each dim on their own, so dark parts of the picture "
            "genuinely use less electricity. The small boxes below the "
            "screen are the monitor's own computer (the scaler), the USB "
            "hub that can also charge a laptop, and the power supply. "
            "Notice what is missing: a fan. Monitors are silent because "
            "nothing in them moves."
        ),
        standard=(
            "A stylized front view: the panel dominates, with the "
            "backlight field drawn as a band behind-made-below it and the "
            "electronics shelf — scaler, USB-C hub, power supply — along "
            "the bottom edge where the real boards sit behind the panel's "
            "lower third. The simulator's one idea lives in the backlight "
            "region: an edge-lit strip lights the whole field regardless "
            "of content, while a mini-LED array (2,000 zones on the "
            "32-inch class) lights only what the picture needs, which is "
            "why content — not just brightness — decides the watts. There "
            "is no cooling region because there is nothing to cool "
            "actively: the display is this suite's fanless product, and "
            "its acoustics gauge would read silence forever. Lifetime "
            "carbon splits between what it took to build the monitor and "
            "what it takes to run it — see the Circular Design spec "
            "(DellCircularDesign/initial_spec.md) for the whole-portfolio "
            "version of that ledger."
        ),
        expert=(
            "Front view; panel dominant, backlight band, electronics shelf "
            "(scaler / USB-C PD hub / PSU). Edge strip: lit fraction "
            "pinned 1.0. FALD 2,000 zones: lit fraction = content. No "
            "moving parts; acoustics degenerate. Carbon: embodied vs use, "
            "PCF-sourced."
        ),
    ),
    sources=[
        {
            "label": "Dell U2723QE monitor page (27-inch 4K USB-C hub class)",
            "url": "https://www.dell.com/en-us/shop/dell-ultrasharp-27-4k-usb-c-hub-monitor-u2723qe/apd/210-bdpf/monitors-monitor-accessories",
        },
        {
            "label": "Dell UP3221Q — 2,000-zone mini-LED UltraSharp",
            "url": "https://www.dell.com/en-us/shop/dell-ultrasharp-32-hdr-premiercolor-monitor-up3221q/apd/210-ayci/monitors-monitor-accessories",
        },
        {
            "label": "Dell Product Carbon Footprint datasheets (monitors)",
            "url": "https://www.dell.com/en-us/lp/dt/product-carbon-footprints",
        },
    ],
    regions=[
        PanelRegion(
            id="panel", kind="panel", label="LCD PANEL",
            x=4, y=2, w=92, h=34,
            description=L(
                novice=(
                    "The screen: a liquid-crystal sandwich that shapes the "
                    "picture but makes no light of its own. Every watt of "
                    "light you see started in the backlight behind it."
                ),
                standard=(
                    "The LCD stack — liquid crystal, color filters, "
                    "polarizers. It modulates light rather than emitting "
                    "it; panel electronics draw a few watts, but the "
                    "picture's real energy bill is the backlight's."
                ),
                expert="LC stack; modulator, not emitter. Power is the backlight's.",
            ),
        ),
        PanelRegion(
            id="backlight", kind="backlight", label="BACKLIGHT FIELD",
            x=4, y=38, w=92, h=10,
            description=L(
                novice=(
                    "The light source behind the screen. On the 27-inch "
                    "class it is one LED strip along the edge — all on or "
                    "all off together. On the 32-inch class it is 2,000 "
                    "tiny LED zones that dim one by one, so a mostly-dark "
                    "picture really does cost less electricity."
                ),
                standard=(
                    "The simulator's protagonist. Edge-lit class: one "
                    "strip, lit fraction pinned at 1.0 — content cannot "
                    "save you watts. Mini-LED class: 2,000 local-dimming "
                    "zones; the lit fraction tracks the content, so dark "
                    "frames are nearly free and HDR highlights overdrive "
                    "only the zones that need it."
                ),
                expert=(
                    "Edge strip (lit=1.0) vs 2,000-zone FALD (lit=content; "
                    "HDR overdrives lit zones only)."
                ),
            ),
        ),
        PanelRegion(
            id="scaler", kind="electronics", label="SCALER",
            x=4, y=52, w=26, h=10,
            description=L(
                novice=(
                    "The monitor's own small computer: it takes the video "
                    "signal, resizes it to the panel's pixels, and runs "
                    "the menus. It draws a steady handful of watts whether "
                    "the picture is dark or bright."
                ),
                standard=(
                    "Scaler/timing controller: signal processing, OSD, "
                    "color pipeline. A content-independent baseline of a "
                    "few watts — the reason a black screen still isn't "
                    "zero watts."
                ),
                expert="TCON/scaler baseline; content-independent floor.",
            ),
        ),
        PanelRegion(
            id="hub", kind="hub", label="USB-C HUB",
            x=34, y=52, w=30, h=10,
            description=L(
                novice=(
                    "The docking part: one USB-C cable to a laptop carries "
                    "the picture and up to 90 watts of charging. Those "
                    "charging watts pass through the monitor and out the "
                    "cable — they show up on the wall meter but mostly "
                    "leave again, warming the laptop, not the monitor."
                ),
                standard=(
                    "USB-C PD hub: up to 90 W delivered downstream. "
                    "Pass-through power, not panel heat — the wall meter "
                    "jumps by the delivery plus a ~10% conversion loss, "
                    "and only the loss stays in the chassis. This is why "
                    "the nameplate 'maximum 220 W' is mostly not display."
                ),
                expert=(
                    "PD 90 W downstream; AC += out/η_hub, heat += out(1/η−1). "
                    "Nameplate max ≈ hub, not panel."
                ),
            ),
        ),
        PanelRegion(
            id="psu", kind="power", label="POWER SUPPLY",
            x=68, y=52, w=18, h=10,
            description=L(
                novice=(
                    "Where wall power comes in and is converted for the "
                    "electronics. A little energy is lost as warmth in the "
                    "conversion — that is why the wall always reads a bit "
                    "higher than what the parts inside use."
                ),
                standard=(
                    "Internal AC/DC conversion, ~88% efficient in the "
                    "model: wall watts = DC loads ÷ efficiency, the same "
                    "identity every server twin asserts, scaled to a desk."
                ),
                expert="AC = DC/η, η≈0.88 (est). Same identity, desk scale.",
            ),
        ),
        PanelRegion(
            id="stand", kind="chassis", label="STAND",
            x=88, y=52, w=8, h=10,
            description=L(
                novice=(
                    "The stand. It holds the monitor up and uses no power "
                    "at all — but building its metal and plastic is part "
                    "of the carbon story on the right of the dashboard."
                ),
                standard=(
                    "Zero watts forever, yet not zero carbon: the stand's "
                    "aluminum and plastic sit in the embodied column of "
                    "the lifetime ledger — the part of the footprint no "
                    "power setting can touch."
                ),
                expert="0 W; nonzero embodied kgCO2e. Settings can't reach it.",
            ),
        ),
    ],
)
