"""Presets and the teaching layer — model presets, guided scenarios, and
Explain entries. The scenario prose carries reading levels (1/3/5
authored), per the suite rule."""

from __future__ import annotations

from .leveling import L
from .models import (
    DisplayConfig,
    Explain,
    GuidedScenario,
    Lifecycle,
    ModelPreset,
    Scenario,
    SimEvent,
)

EDGE = DisplayConfig(model="edge-27", brightness_pct=75, content="mixed",
                     local_dimming=False, hub_laptop_w=0)
MINILED = DisplayConfig(model="miniled-32", brightness_pct=75, content="mixed",
                        local_dimming=True, hub_laptop_w=0)

MODEL_PRESETS = [
    ModelPreset(
        id="edge-27", name="Edge-lit 27\" 4K",
        blurb="U2723QE-class: one LED strip lights the whole field — "
              "content cannot save watts here.",
        config=EDGE,
    ),
    ModelPreset(
        id="miniled-32", name="Mini-LED 32\" 4K",
        blurb="UP3221Q-class: 2,000 local-dimming zones — the picture "
              "decides the power.",
        config=MINILED,
    ),
]

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="dark-mode",
        title="Dark mode actually saves power (on the right panel)",
        narration=[
            L(
                novice=(
                    "People say switching your apps to dark mode saves "
                    "electricity. On this monitor, whether that is true "
                    "depends entirely on how the light behind the screen "
                    "is built. This run starts on the fancy panel, whose "
                    "backlight is 2,000 tiny zones that dim one by one. "
                    "Halfway through, the content switches from a bright "
                    "white document to a dark editor — watch the power "
                    "gauge drop, because most of those 2,000 zones just "
                    "went nearly dark. Now try the same run on the "
                    "27-inch edge-lit preset: the drop almost vanishes, "
                    "because its single light strip cannot dim only part "
                    "of the screen. Same trick, different hardware, "
                    "different bill."
                ),
                standard=(
                    "Bright content to dark content at t=120 s on the "
                    "mini-LED panel: the lit fraction falls from ~0.9 to "
                    "~0.12 and the backlight watts follow. Re-run on the "
                    "edge-lit preset and the same content switch barely "
                    "moves the needle — the strip lights the full field "
                    "regardless. Dark mode is a hardware question wearing "
                    "a software costume."
                ),
                expert=(
                    "bright→dark @120 s. FALD: lit 0.9→0.12, W follows. "
                    "Edge: lit pinned 1.0, ΔW≈0. Dark mode is a backlight "
                    "architecture question."
                ),
            ),
        ],
        question="How many watts does the bright-to-dark switch save on each panel class?",
        scenario=Scenario(
            config=DisplayConfig(model="miniled-32", brightness_pct=75,
                                 content="bright", local_dimming=True),
            duration_s=300,
            events=[SimEvent(at_s=120, action="set-content", content="dark")],
        ),
    ),
    GuidedScenario(
        id="brightness-bill",
        title="Brightness is the whole bill",
        narration=[
            L(
                novice=(
                    "This run leaves everything alone except the "
                    "brightness slider: 25%, then 50%, then 100%. Watch "
                    "the power gauge step up each time. Almost everything "
                    "a monitor spends goes into making light, and the "
                    "brightness setting is the tap. The small remainder — "
                    "the monitor's own electronics — never changes, which "
                    "is why even a very dim screen never reaches zero."
                ),
                standard=(
                    "Brightness steps 25 → 50 → 100% at fixed mixed "
                    "content. Backlight watts scale linearly with the "
                    "slider while the electronics floor stays put — the "
                    "power line is the brightness line plus a constant. "
                    "One slider owns the operating bill; the annual-kWh "
                    "readout on the right prices it."
                ),
                expert=(
                    "25/50/100% steps, mixed content. P = floor + "
                    "max_W·b·lit; linear in b. The slider is the bill."
                ),
            ),
        ],
        question="Roughly what fraction of full-brightness power remains at 25% brightness?",
        scenario=Scenario(
            config=DisplayConfig(model="edge-27", brightness_pct=25,
                                 content="mixed", local_dimming=False),
            duration_s=300,
            events=[
                SimEvent(at_s=100, action="set-brightness", value=50),
                SimEvent(at_s=200, action="set-brightness", value=100),
            ],
        ),
    ),
    GuidedScenario(
        id="hdr-burst",
        title="The HDR burst",
        narration=[
            L(
                novice=(
                    "HDR pictures have highlights far brighter than a "
                    "normal desktop — a sun glint, a lamp in a dark room. "
                    "At two minutes this run switches to HDR grading "
                    "content: small, very bright highlights on dark "
                    "fields. On the zone-dimming panel only the zones "
                    "under the highlights fire, but they fire much harder "
                    "than normal — so peak power rises above anything the "
                    "normal desktop could ask for, even though most of "
                    "the screen is dark."
                ),
                standard=(
                    "SDR mixed to HDR mastering at t=120 s: the lit "
                    "fraction drops (highlights are small) while the lit "
                    "zones overdrive to ~1.8× the SDR maximum — and the "
                    "product of the two still exceeds the SDR bright-field "
                    "peak. HDR power is a burst regime: higher peaks, "
                    "content-dependent averages."
                ),
                expert=(
                    "SDR→HDR @120 s: lit↓, drive×1.8; product > SDR peak. "
                    "Burst regime — peak up, average content-dependent."
                ),
            ),
        ],
        question="Does the HDR peak exceed the SDR bright-content peak on both panel classes?",
        scenario=Scenario(
            config=DisplayConfig(model="miniled-32", brightness_pct=100,
                                 content="bright", local_dimming=True),
            duration_s=300,
            events=[SimEvent(at_s=120, action="set-content", content="hdr")],
        ),
    ),
    GuidedScenario(
        id="hub-meter",
        title="The 220-watt monitor that isn't",
        narration=[
            L(
                novice=(
                    "The spec sheet says this 38-watt-ish monitor can draw "
                    "220 watts. Where would those go? At ninety seconds a "
                    "laptop docks over the single USB-C cable and starts "
                    "charging at 90 watts. The wall meter leaps — but "
                    "almost all of those watts pass straight through the "
                    "monitor and out the cable into the laptop. Only a "
                    "small conversion loss stays behind as warmth. The "
                    "monitor became a power adapter with a screen "
                    "attached."
                ),
                standard=(
                    "Laptop docks at t=90 s drawing 90 W over USB-C PD. "
                    "Wall power jumps by the delivery plus ~10% conversion "
                    "loss, while the heat readout barely moves — delivered "
                    "watts leave over the cable. The nameplate 220 W "
                    "maximum is mostly hub, not display: the panel's own "
                    "budget never changed."
                ),
                expert=(
                    "PD 90 W @90 s: AC += 90/η_hub; heat += 90(1/η−1)≈10 W. "
                    "Nameplate 220 W ≈ hub + panel, not panel."
                ),
            ),
        ],
        question="Of the wall-power jump when the laptop docks, how many watts stay in the monitor as heat?",
        scenario=Scenario(
            config=DisplayConfig(model="edge-27", brightness_pct=75,
                                 content="mixed", local_dimming=False),
            duration_s=300,
            events=[
                SimEvent(at_s=90, action="hub-plug", value=90),
                SimEvent(at_s=240, action="hub-unplug"),
            ],
        ),
    ),
    GuidedScenario(
        id="embodied-surprise",
        title="The embodied-carbon surprise",
        narration=[
            L(
                novice=(
                    "Here is the question the carbon bar answers: over "
                    "this monitor's whole life, which cost more — building "
                    "it, or running it? For a laptop the answer is "
                    "lopsided: making it is roughly three-quarters of its "
                    "lifetime footprint, because it sips power on a "
                    "battery. A monitor sits plugged in with a big light "
                    "behind the glass, so running it counts for much more "
                    "— roughly a third at desk duty, and more the longer "
                    "it stays on. This run uses heavy signage-style hours; "
                    "watch the use slice of the bar swell past what any "
                    "laptop's would be."
                ),
                standard=(
                    "Dell's PCF datasheets put a business laptop's "
                    "use-phase near 20% of lifetime carbon — manufacturing "
                    "dominates. Monitors invert toward the middle: ~34% "
                    "use-phase at standard assumptions, because the "
                    "backlight burns wall power for a decade. This run "
                    "sets 16 h/day duty; watch the use share overtake the "
                    "monitor's desk-duty split. Same methodology, "
                    "different physics, different lever: for the laptop "
                    "you extend its life, for the monitor you also mind "
                    "the brightness. The Circular Design spec carries the "
                    "portfolio version of this ledger."
                ),
                expert=(
                    "Laptop PCF: use ≈20%. Monitor: ≈34% at desk duty; "
                    "16 h/day pushes higher. Lever differs: lifetime vs "
                    "brightness. See Circular Design spec."
                ),
            ),
        ],
        question="At these hours, does use-phase carbon overtake the embodied share?",
        scenario=Scenario(
            config=DisplayConfig(model="edge-27", brightness_pct=90,
                                 content="bright", local_dimming=False),
            lifecycle=Lifecycle(hours_per_day=16, days_per_year=360,
                                service_years=8, grid_kgco2_per_kwh=0.4),
            duration_s=120,
            events=[],
        ),
    ),
]

EXPLAINS = [
    Explain(
        id="backlight-power",
        title="Backlight power",
        equation="P_bl = P_max × brightness × lit",
        inputs=["backlight max W", "brightness setting", "content lit fraction"],
        explanation=L(
            novice=(
                "The backlight's power is its maximum, scaled down by two "
                "dials: how bright you set it, and — only on the zone-"
                "dimming panel — how much of the picture actually needs "
                "light. On the edge-lit panel that second dial is stuck at "
                "'all of it'."
            ),
            standard=(
                "Maximum backlight watts scaled by the brightness setting "
                "and the lit fraction. On the mini-LED class the lit "
                "fraction is the content's (dark ≈ 0.12, bright ≈ 0.9); on "
                "the edge-lit class it is pinned at 1.0 — the strip cannot "
                "light half a field."
            ),
            expert="P_max·b·lit; FALD lit=f(content), edge lit≡1.0.",
        ),
    ),
    Explain(
        id="wall-power",
        title="Wall power",
        equation="P_ac = (P_elec + P_bl + P_hub/η_hub) / η_psu",
        inputs=["electronics W", "backlight W", "hub delivery W", "PSU efficiency"],
        explanation=L(
            novice=(
                "Add up everything inside — the electronics, the light, "
                "and any laptop charging passing through — then add the "
                "little the power supply wastes converting wall power. "
                "That total is what the wall meter reads."
            ),
            standard=(
                "DC loads (electronics + backlight + hub delivery with its "
                "conversion loss) divided by supply efficiency. The same "
                "identity every server twin asserts per tick, at desk "
                "scale — and the tests assert it here too."
            ),
            expert="AC = ΣDC/η_psu; hub adds out/η_hub. Asserted per tick.",
        ),
    ),
    Explain(
        id="heat",
        title="Heat vs delivery",
        equation="Q = P_dc − P_hub_out",
        inputs=["DC power W", "hub delivered W"],
        explanation=L(
            novice=(
                "Almost every watt a monitor uses becomes warmth in the "
                "room — except the watts it hands to a charging laptop, "
                "which leave through the cable and warm the laptop "
                "instead."
            ),
            standard=(
                "Everything the monitor consumes becomes room heat except "
                "the watts delivered downstream over USB-C, which exit on "
                "the cable. Silently: there is no fan to move this heat — "
                "the chassis convects it, which is the whole acoustics "
                "model."
            ),
            expert="Q = DC − PD_out; passive convection, 0 dBA by construction.",
        ),
    ),
    Explain(
        id="use-carbon",
        title="Use-phase carbon",
        equation="CO2_use = kWh/yr × years × grid",
        inputs=["average on-power W", "duty hours", "service years", "grid intensity"],
        explanation=L(
            novice=(
                "Running cost in carbon: the power it draws, times the "
                "hours it runs over its whole life, times how dirty the "
                "local electricity is. Added to the fixed cost of building "
                "it, that is the monitor's lifetime footprint."
            ),
            standard=(
                "Average on-power integrated over the duty cycle and "
                "service life, priced at grid intensity, then added to the "
                "PCF-sourced embodied figure. The closure — embodied + use "
                "= lifetime, shares summing to 100 — is a test, the "
                "Circular Design rule applied to one product."
            ),
            expert="∫P·duty·years×grid + embodied(PCF); closure asserted.",
        ),
    ),
]
