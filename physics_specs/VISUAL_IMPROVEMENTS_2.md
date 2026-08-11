# Physics suite — visual improvement specs, round two (W1–W10)

Drafted 2026-08-11 for review; nothing here is built yet. Round one
(V1–V10, `VISUAL_IMPROVEMENTS.md`) delivered the media pipeline (hero
panels, photo cards, underlays, x-ray), the annotated timeline, gauges,
flow particles, the drawn fabric mesh, A/B compare, and the rack
bezels. Round two deepens the imagery and adds the presentation layer
around the sims.

**Imagery ground rules carry over unchanged** (see round one): ship-safe
local assets → Wikimedia Commons hotlinks with rendered credit +
license → labeled repo-drawn facsimiles. Tests enforce credits.

Effort: S = one sitting, M = a day-ish, L = multi-day.

---

## W1 — Per-product facsimile library v2 (real front bezels)

**What.** Replace the seven generic silhouettes (laptop/server/rack…)
with *per-product* facsimile SVGs that read as the actual machine: the
XE9680's 6U face with its drive strip and PSU quad, PowerMax's
brick-and-DME rack face, the SN6000's 128-port OSFP grid, the E3200's
48-port + 4-SFP campus face, the PowerStore bezel wave, the Pro Max
Plus keyboard deck. Static SVG files in each app's `frontend/public/`,
`kind: "illustration"` with the mandatory label; the generic shapes
remain the fallback.

**Where.** All 16 apps' media tables (files referenced by `src`, so no
component changes — the ProductGallery already renders file-backed
entries).
**Tests.** Existing media tests already verify referenced files exist;
add: every facsimile SVG contains a `<title>` naming it an illustration.
**Effort.** L (it's drawing — ~20 SVGs done well).

## W2 — Wikimedia photo research pass

**What.** A sourcing pass in the GPU twin's channel: search Wikimedia
Commons for licensable photos of the modeled products or close kin
(Dell rack servers, EMC-era arrays, Alienware machines, data-center
aisles for the facility apps), and wire the finds into the media
tables as hotlinks with **credit AND license** rendered ("Photo: X, CC
BY-SA 4.0, via Wikimedia Commons"). Products with no find keep their
facsimile. Extends `ProductMedia` with a `license` field; the media
test requires `license` non-empty whenever the src is external, and
restricts external hosts to `upload.wikimedia.org`.

**Where.** All 16 media tables; RESEARCH_ASSETS.md gains a physics-suite
section recording every search (found or not) so the pass is auditable.
**Tests.** License-required rule; host allowlist.
**Effort.** M (mostly research; wiring is data).

## W3 — Live hero: status badges on the product image

**What.** The hero panel stops being static: a badge strip renders *on*
the photo/facsimile — a fan glyph spinning at the live rpm class, a
thermometer chip with the hot-zone temperature, a red "INCIDENT" ribbon
while corruption spreads, a coverage chip on the telecom hero, LED dots
that go amber when the sim throttles. The product picture becomes a
one-glance summary of the machine's current condition.

**Where.** All 16 apps; `ProductGallery` gains an optional `status`
prop (2–3 {icon, text, tone} chips) computed per app from the cursor
state — the same derivations the gauges already use.
**Tests.** Frontend-only.
**Effort.** M.

## W4 — Region close-up drawer (component portraits)

**What.** Clicking a region currently shows a text card; upgrade it to
a drawer with a **component portrait** — a small facsimile illustration
of that part (a cold plate with its microchannels, a DIMM bank, an OSFP
cage, a BBU, a tape-less vault glyph) — beside the live values for that
region and the existing leveled description. A shared portrait library
keyed by region *kind* (cpu, gpu, media, coldplate, manifold, spine…)
serves all apps, so ~18 drawings cover all 16 apps.

**Where.** All 16 apps; `RegionCard` shared component + `Portraits.tsx`
library.
**Tests.** Every region kind used by an app's maps has a portrait (or
the explicit generic fallback).
**Effort.** L.

## W5 — Scenario storyboard filmstrip

**What.** Each guided scenario gains a filmstrip: 3–5 auto-chosen key
moments (its events' timestamps plus the trace's extremum of the
headline metric) rendered as clickable chips — "t=120 the load lands",
"t=300 on-lap", "t=840 skin-limited" — that jump the cursor. A visual
table of contents for the story the narration tells.

**Where.** All 16 apps; moments derived frontend-side from
`scenario.events` + the band derivations V7 already computes (no
backend change).
**Tests.** Moment derivation unit-testable against a canned scenario.
**Effort.** M.

## W6 — State theatrics (heat haze, incident vignette, power-off fade)

**What.** Three subtle SVG/CSS post-effects tied to state: a heat-haze
shimmer (feTurbulence displacement) over any region past its throttle
line; a soft red edge-vignette on the whole map while an incident is
active/uncontained; a desaturate+dim when the machine is powered off
or recycled. All gated behind `prefers-reduced-motion` and a "calm
mode" toggle.

**Where.** The 8 core apps' view components (shared `effects.tsx`
filter defs).
**Tests.** Frontend-only; calm-mode default honored.
**Effort.** M.

## W7 — Live small-multiples overview strip

**What.** A "All personalities" toggle renders the app's other products
as live mini-maps (thumbnail views running the default scenario,
fetched once, animated by the same cursor) in a strip above the main
map — the multi-product architecture made scannable, each mini captioned
by its photo card. Click a mini to switch products.

**Where.** The 8 multi-product apps; reuses each view component at
thumbnail scale (the views are already pure props-in/SVG-out).
**Tests.** Frontend-only; fetches cached per product.
**Effort.** L (N extra simulate calls need caching care).

## W8 — Header sparkline chips

**What.** The header's text readout ("t+300s · 1.2 kW · 87%") becomes
2–3 sparkline chips: a 60-px inline chart of the metric's trailing
window with the current value — the header shows *trajectory*, not
just position, everywhere including when the user has scrolled the
strip charts off-screen.

**Where.** All 16 apps; shared `SparkChip.tsx`.
**Tests.** Frontend-only.
**Effort.** S.

## W9 — Exploded-view toggle

**What.** For the physical maps (rack, chassis, laptop), an "Explode"
toggle animates the regions apart along the airflow/loop axis with
thin connector lines and sequence numbers — the front-to-back airflow
order, the supply→plates→return loop order, the intake→battery
stack — then collapses back. Teaches the *ordering* the flat map only
implies. Pairs with the x-ray toggle (photo mode disables explode).

**Where.** PhysicsClient, PhysicsCompute (both server + rack maps),
PhysicsStorage's PowerStore map.
**Tests.** Frontend-only; region ids/click behavior unchanged.
**Effort.** M.

## W10 — Suite gallery page (the sixteen-app front door)

**What.** A static `PhysicsSuite/index.html` (CustomerSetup-style, no
build step) presenting all 16 physics apps as cards: hero image or
facsimile, the one-line idea, port, and a liveness chip (ping the
backend, show the start command when down — the CustomerSetup shared-JS
pattern). The suite's front door, with the product pictures doing the
wayfinding. Registered in `ports.json` reserved block; served by the
CustomerSetup static server or `python -m http.server`.

**Where.** New top-level `PhysicsSuite/` (index.html + a small css/js,
assets copied from the apps' public dirs with credits).
**Tests.** A link-check added to `CustomerSetup/tests/test_links.py`
style: every card's port matches ports.json; every image credited.
**Effort.** M.

---

## Summary table

| # | Idea | Pictures? | Apps | Backend change | Effort | Depends on |
|---|---|---|---|---|---|---|
| W1 | Per-product facsimile bezels replacing generic silhouettes | **Yes** — facsimile files | all 16 | none (media data) | L | — |
| W2 | Wikimedia photo research pass (credit + license enforced) | **Yes** — real photos | all 16 | `license` field | M | — |
| W3 | Live hero: status badges/LEDs on the product image | **Yes** — animates V1's images | all 16 | none | M | — |
| W4 | Region close-up drawer with component portraits | **Yes** — portrait library | all 16 | none | L | — |
| W5 | Scenario storyboard filmstrip (key-moment chips) | no | all 16 | none | M | — |
| W6 | State theatrics: heat haze, incident vignette, power-off fade | no | 8 core | none | M | — |
| W7 | Live small-multiples strip of all personalities | **Yes** — captioned by cards | 8 multi-product | none | L | — |
| W8 | Header sparkline chips (trajectory, not position) | no | all 16 | none | S | — |
| W9 | Exploded-view toggle (airflow/loop order animated) | no | Client, Compute, Storage | none | M | — |
| W10 | Suite gallery front door with hero images + liveness chips | **Yes** — reuses all assets | new static page | ports.json reserved entry | M | — |

**Suggested order** if all approved: W8 (cheap, universal) → W2 → W1
(sourcing before drawing — only draw what the research pass can't
find) → W3 → W10 (the assets' third payoff) → W5 → W9 → W6 → W4 → W7
(the two heaviest last).
