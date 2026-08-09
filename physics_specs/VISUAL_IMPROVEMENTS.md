# Physics suite — visual improvement specs (V1–V10)

Ten proposed visual upgrades for the sixteen physics apps
(`PhysicsClient` … `PhysicsLifecycle`, plus the spec-10 eight). Drafted
2026-08-09 for review before implementation; nothing here is built yet.

**Imagery ground rules** (from `RESEARCH_ASSETS.md` + house precedent —
these bind every idea below that shows a product picture):

1. **Ship-safe local assets first**: `DellAlienware/frontend/public/alienware-interior.jpg`
   and `DellPowerStore/frontend/public/powerstore{1..4}.webp` are already
   licensed-in and reusable by the physics apps.
2. **Wikimedia Commons hotlinks second**, with the `credit` line *always
   rendered* in the UI — the GPU anatomy pattern. Backend carries
   `{url, credit, license}`; a test fails if a photo ships without credit.
3. **Credited SVG facsimiles third** — house-made, self-contained,
   photorealistic-ish illustrations explicitly labeled "illustration,
   not a Dell product photo" (the `e3200-front.svg` / `xe9712-rack.svg`
   precedent). This is the only channel for products with no ship-safe
   photo (most of them, per the RESEARCH_ASSETS matrix).
4. Never an uncredited Dell marketing image; never a hotlink to a
   bot-blocked/press URL; `test_anatomy`-style tests enforce credit
   presence wherever a `photo` field is non-null.

Effort scale: S = one sitting, M = a day-ish, L = multi-day.

---

## V1 — Product hero panel (photo + credit, every app)

**What.** Each app's product selector gains a hero strip: a real product
image (channel 1/2) or credited facsimile (channel 3) of the currently
selected personality, its generation line, and the mandatory credit
caption. Swapping products swaps the hero.

**Where.** All 16 apps; the backend `anatomy`/map model grows an
optional `photo: {url, credit, license, kind: "photo"|"illustration"}`
field (wire-compatible: optional, defaults null).

**Assets.** PowerStore webps (PhysicsStorage), alienware-interior.jpg
(PhysicsClient), Wikimedia server/switch photos where the GPU-twin
pattern already found licensable ones; facsimile SVGs for XE9712,
SN6000, X800, and the SaaS products (a stylized console screenshot
facsimile for CloudIQ/AIOps).

**Tests.** Photo present ⇒ credit non-empty; `kind: illustration` ⇒
label rendered; external URLs allowed only for Wikimedia hosts.
**Effort.** M (mostly asset curation).

## V2 — Photo-underlay maps ("the overlay sits on the machine")

**What.** Where a ship-safe interior photo exists, render it *under* the
region overlay: regions become semi-transparent tinted panes over the
actual machine, with an opacity slider (0 = pure schematic, 1 = pure
photo). The temperature/load tint reads against real sheet metal.

**Where.** PhysicsClient laptop map (alienware-interior.jpg — the
regions were already traced from this photo's geometry in the
DellAlienware twin); PhysicsStorage PowerStore map (powerstore webps).
Explicitly *not* attempted where no ship-safe photo exists — the
schematic remains the primary and only view there.

**Implementation.** `<image>` element under the region `<g>` in the
view component; region fills get `fill-opacity` ~0.55; the legend gains
an opacity slider. Backend map carries `underlay: {src, credit}`.
**Tests.** Underlay present ⇒ credit rendered; region geometry
unchanged (same ids/bounds).
**Effort.** M.

## V3 — Animated flow particles (air, coolant, bytes, packets)

**What.** Replace/augment the static dashed flow lines with animated
particle streams whose speed and density bind to live trace values:
airflow particles scale with fan rpm (PhysicsClient/Compute), coolant
loop dots circulate supply→plates→return at the flow rate with color =
local coolant temp (PhysicsCompute rack, PhysicsCDU), data droplets
move stage-to-stage sized by throughput and pile up at the bottleneck
(PhysicsData), packet dots cross the fabric mesh with drops visibly
falling off lossy links (PhysicsFabric).

**Where.** PhysicsClient, PhysicsCompute, PhysicsCDU, PhysicsData,
PhysicsFabric, PhysicsStorage (rebuild traffic between nodes).

**Implementation.** Pure SVG/CSS: `stroke-dasharray` + `animation-duration`
driven by state (no JS animation loop; the R760Thermal `flow-fast/mid/slow`
class pattern generalized to a continuous `--flow-speed` CSS var).
Respect `prefers-reduced-motion`.
**Tests.** Frontend-only; snapshot of class/var derivation logic.
**Effort.** M.

## V4 — Real drawn topology for PhysicsFabric

**What.** The fabric map currently shows tier *bands*; replace with an
actual drawn leaf/spine mesh — every leaf connected to every spine,
links as individual lines colored by their modeled utilization, the
worst link drawn thick with a flame marker, dead spines grayed with
their links slack. The campus map becomes a real tree with the PoE
devices as icon rows that visibly go dark when shed.

**Where.** PhysicsFabric (all three personalities). Mirrors the
narrative SN6000 twin's data-driven mesh so a bigger fabric stays data.

**Implementation.** The engine already computes worst/mean utilization;
add a per-link utilization vector to `SimState.region_load` (or a new
`link_load` dict) so each drawn line has its own color. Backend change
is additive.
**Tests.** Link count = leaves × spines; worst-link line's value equals
the `worst_link_pct` instrument.
**Effort.** L (the one backend-touching visual).

## V5 — Photorealistic rack/chassis facsimile strips

**What.** For the rack-scale apps, swap the flat rectangles for a
front-elevation facsimile with bezel detail: tray faceplates with
handles and status LEDs (LED color = region state), the CDU's grille,
busbar shelf fins, blinking NIC lights scaled to traffic. Explicitly
labeled illustrations (channel 3). The point: a viewer should recognize
the machine from the Dell photo they've seen, while the overlay stays
honest about being a model.

**Where.** PhysicsCompute (XE9712 rack + XE9680/XE7745 chassis),
PhysicsRackPower, PhysicsMX7000 (chassis with sleds), PhysicsAIFactory
(rack rows).

**Implementation.** Hand-built SVG symbol library
(`frontend/src/components/bezels.tsx`): `<TrayFace>`, `<PsuFace>`,
`<SledFace>`, `<CduFace>` symbols parameterized by state; region
click/hover behavior unchanged.
**Tests.** Region ids/geometry contract unchanged; illustration label
present.
**Effort.** L.

## V6 — Cockpit gauges for the hero instruments

**What.** Each app's 2–3 *hero* numbers (the ones its tests pin) become
SVG dial/arc gauges with marked redlines instead of text rows: skin-cap
arc with the 46 °C line (Client), coolant-return dial with 65/75 °C
marks (Compute), ρ dial with the knee shaded (Storage/Fabric), RPO/RTO
twin dials (Resilience), carbon-per-useful-year dial (Lifecycle).
Everything else stays as text — gauges only where a threshold exists.

**Where.** All 16 apps via one shared `Gauge.tsx` (copied per app, house
rule).

**Implementation.** One ~80-line arc-gauge component: value, bands
(ok/warn/redline), needle, threshold ticks; color ramp reuses each
app's existing palette.
**Tests.** Frontend-only.
**Effort.** M.

## V7 — Annotated timeline scrubber

**What.** The playback slider becomes a true timeline: colored phase
bands under the track (boost window, throttle intervals, incident
active, rebuild window, update rolling, exposure window), event pins
with icons at their timestamps (⚡ fault, 🌡 heatwave, 🛰 WAN-down…),
hover tooltips quoting the log line, click-to-jump. The scrubber
becomes the narrative spine spec 05 says it should be.

**Where.** All 16 apps; richest payoff in PhysicsResilience (incident
timeline), PhysicsFleet (release waves), PhysicsLifecycle (the battery
year).

**Implementation.** Derive bands/pins from the existing trace + events
+ log (no backend change); one shared `Timeline.tsx` replacing the bare
`<input type=range>`.
**Tests.** Band derivation unit-tested against a canned trace.
**Effort.** M.

## V8 — A/B compare mode (two runs, one screen)

**What.** A "Compare" toggle runs a second scenario (the natural foil:
manual vs automated, DIY vs Blocks, sealed vs serviceable, perimeter vs
zero-trust, static vs adaptive, sync vs async) and renders both: strip
charts overlay the B-run as dashed ghosts, the two maps sit
side-by-side half-width, and a delta ribbon states the headline gap
("automation saved 1,240 h", "the vault saved 200 TB"). Every app
already has tests comparing exactly these pairs — this makes the
comparison a picture.

**Where.** All 16; each app declares its canonical foil pairs in
presets (`comparePresetId` on ConfigPreset — additive backend field).

**Implementation.** Second `simulate()` POST; chart components accept
`ghostTrace`; deltas computed from the two summaries.
**Tests.** Foil-pair declarations resolve to real presets.
**Effort.** L.

## V9 — Photo-card product picker

**What.** Replace the product `<select>` with a card row: each card =
thumbnail (V1's asset, cropped), product name, and its one-line
personality ("the network IS the array"), selected card highlighted in
Dell blue. Makes the multi-personality architecture visible at a
glance and gives the photos a second home.

**Where.** The 8 multi-product apps (Client, Compute, Storage, Fabric,
Fleet, Resilience, Data, Lifecycle).

**Implementation.** Pure frontend on top of V1's photo metadata; cards
fall back to the app accent color + product initial where no asset
exists.
**Tests.** Every card's product id ∈ the Product literal; credit shown
on hover/tooltip.
**Effort.** S (after V1).

## V10 — X-ray toggle (photo ↔ schematic crossfade)

**What.** Where V2's underlay exists, add an "X-ray" button that
crossfades between three states: *photo* (the machine as your eyes see
it), *hybrid* (photo + tinted overlay), *schematic* (the current dark
diagram). A caption explains what the schematic abstracts away ("the
model sees nine thermal zones where the camera sees four hundred
parts"). Teaches the map-vs-territory point that every twin footnotes,
visually.

**Where.** PhysicsClient (laptop), PhysicsStorage (PowerStore), and
any map that later gains a ship-safe underlay; grayed-out (with the
honest "no licensable photo exists" tooltip) elsewhere.

**Implementation.** Extends V2: a three-state toggle animating
`fill-opacity`/`image-opacity`; caption text lives in the backend map
model so it levels with the reading-level system.
**Tests.** Toggle only offered when an underlay exists; caption leveled.
**Effort.** S (after V2).

---

## Summary table

| # | Idea | Pictures? | Apps | Backend change | Effort | Depends on |
|---|---|---|---|---|---|---|
| V1 | Product hero panel with credited photo/facsimile | **Yes** — all 3 channels | all 16 | optional `photo` field | M | — |
| V2 | Photo-underlay maps (overlay on the real machine) | **Yes** — ship-safe assets only | Client, Storage | optional `underlay` field | M | — |
| V3 | Animated flow particles (air/coolant/bytes/packets) | no | 6 apps | none | M | — |
| V4 | Real drawn leaf/spine mesh + campus tree | no | Fabric | additive `link_load` | L | — |
| V5 | Photorealistic rack/chassis facsimile strips (LEDs, bezels) | **Yes** — facsimile channel | Compute, RackPower, MX7000, AIFactory | none | L | — |
| V6 | Cockpit gauges with redlines for hero metrics | no | all 16 | none | M | — |
| V7 | Annotated timeline scrubber (phase bands + event pins) | no | all 16 | none | M | — |
| V8 | A/B compare mode with ghost traces + delta ribbon | no | all 16 | additive `comparePresetId` | L | — |
| V9 | Photo-card product picker | **Yes** — reuses V1 assets | 8 multi-product apps | none | S | V1 |
| V10 | X-ray toggle: photo ↔ hybrid ↔ schematic crossfade | **Yes** — reuses V2 assets | Client, Storage | caption field (leveled) | S | V2 |

**Suggested order** if all approved: V1 → V9 (assets once, two payoffs),
V2 → V10 (same), then V7, V6, V3 (shared components, no backend risk),
then V4, V8, V5 (the three L-effort items).
