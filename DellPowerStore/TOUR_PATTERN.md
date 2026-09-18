# Adding a narrated tour to a twin

This is the recipe the PowerStore pilot was built with. Follow it to give any
narrative twin (a `simulate()` trace plus an anatomy map) a `#tour` page: a
camera that moves across and into the map, layers that peel away, regions that
light, captions, and optional browser speech, synchronized with the existing
trace cursor. The design comes from `ACTIVE_TWIN_SPEC.md` sections 3–6. Where
this file and the spec disagree, this file wins, because the spec was written
before twinkit and twin-ui existed.

The shared pieces do most of the work. The backend models, the pure camera
helpers and the invariant test live in `twinkit` (`twinkit.tour`,
`twinkit.testing.assert_tour_invariants`); the player lives in
`packages/twin-ui` and is imported as `@twinsim/twin-ui`. A twin writes only
its tour as data, its own tests, two props on its map component, and the
route wiring.

The pilot's files, for reference:

```
twinkit/tour.py                                   shared models + pure helpers
twinkit/testing.py::assert_tour_invariants        shared test (spec section 6)
twinkit/tests/test_tour.py                        tests of the shared pieces
DellPowerStore/backend/app/tour.py                the tour, as data
DellPowerStore/backend/app/main.py                GET /api/tour
DellPowerStore/backend/tests/test_tour.py         the twin's tour tests
packages/twin-ui/src/components/tour/             the player (exported from @twinsim/twin-ui)
packages/twin-ui/gallery/Gallery.tsx              the player on a toy map (npm run gallery)
DellPowerStore/frontend/src/components/ChassisView.tsx   camera + regionLook props
DellPowerStore/frontend/src/App.tsx               #tour route, cursor wiring
DellPowerStore/frontend/smoke.json                #tour routes
```

## 1. Backend: `backend/app/tour.py`

Create one module that is pure data. It imports only `twinkit.tour`, the
twin's own `.leveling`, `.models` and `.anatomy`: no fastapi, no time, no IO.
The test AST-checks it the same way it checks the engine.

```python
from twinkit.tour import CameraTarget, Tour, TourPhoto, TourResponse, TourSource, TourStep, camera_around, whole_map
from .leveling import L
from .models import <YourAnatomy>

SIGNATURE_STEP_ID = "<id from ACTIVE_TWIN_SPEC.md section 8>"

def layer_map(anatomy) -> dict[str, int]: ...     # every region id -> 0..N
def build_tour(anatomy) -> Tour: ...
def build_response(anatomy) -> TourResponse:
    return TourResponse(tour=build_tour(anatomy), layers=layer_map(anatomy),
                        map_width=anatomy.width, map_height=anatomy.height)

from .anatomy import ANATOMY  # noqa: E402
TOUR_RESPONSE = build_response(ANATOMY)   # built at import, like ANATOMY
```

**Layers.** Do not add a `layer` field to the anatomy model. `layer_map`
returns `{region id: layer}`: 0 is what you see from outside, and each higher
number is one level further in. Two or three layers is plenty. Derive the map
from `region.kind` where you can, so a new region lands on a sensible layer
without an edit. It must cover every region id and nothing else (tested).

**Steps.** Aim for 6–9 beats that follow the storyboard row in spec section 8.
Each `TourStep` has:

| field | rule |
|---|---|
| `id` | kebab-case and stable. Deep links (`#tour/<id>`) key on it. One of the steps must be `SIGNATURE_STEP_ID`. |
| `title` | A short beat title for the step list. Never numbered. Leave it unwrapped. |
| `script` | **Wrap in `L(novice=..., standard=..., expert=...)`**, with at least levels 1, 3 and 5 authored. Novice must be longer than expert. It is both the caption and the speech. Spell out vocabulary on first use and label numbers as illustrative. |
| `camera` | A box in the anatomy's own coordinates (no renderer margin). It must lie inside `[0,width]×[0,height]`. Use `whole_map(anatomy)` for the first and last beats, and `camera_around(anatomy, ids, pad=...)` or an explicit `CameraTarget` for the others. |
| `region_ids` | The regions to light. They must exist on the map. For A/B twins, light both halves. |
| `layer_reveal` | Non-decreasing. It may drop only on the final "reassemble" beat, usually back to 0. Lit regions are never ghosted, whatever their layer. |
| `trace_cursor` | The index into `simulate()` that the beat pins. It must never decrease across beats (the tour never runs the sim backwards). Point it at the trace step whose description makes the same claim as the script. |
| `duration_ms` | The steps must total 120,000–360,000 ms. About 25 s for a 70-word standard script. Give the signature beat longer. |
| `photo_id` | Optional. It points into `Tour.photos`, which must be local `/file.webp` in `frontend/public/` and credited. |

**Truth.** Before writing a script, read the trace step it pins and the
descriptions of the regions it lights. The tour may *rephrase* what the engine
and anatomy say, but it may not say anything they do not. Unit-test the
pairing: the PowerStore test asserts that the signature step's `trace_cursor`
is the trace step labeled "NVRAM write cache initializes".

**Tour-level prose.** Also wrap `Tour.intro` in `L(...)`. `Tour.sources` can
reuse `anatomy.sources`.

## 2. Backend: the endpoint

In `main.py`:

```python
from twinkit.tour import TourResponse
from .tour import TOUR_RESPONSE

@app.get("/api/tour", response_model=TourResponse)
def get_tour(level: int = Level) -> TourResponse:
    return leveled(TOUR_RESPONSE, level)
```

Wire shape (camelCase):
`{ tour: { id, title, intro, steps: [{ id, title, script, camera: {x,y,w,h}, regionIds, layerReveal, traceCursor, durationMs, photoId, audioUrl }], photos: [{id,url,caption,credit}], sources: [{label,url}] }, layers: {regionId: n}, mapWidth, mapHeight }`.

If the twin has a route-snapshot test (the GPU pattern), add `/api/tour` to it.
If `CustomerSetup/tests/test_links.py` checks `data-twin-trace` endpoints, the
tour does not affect it.

## 3. Backend: `tests/test_tour.py`

The shared rules take one call:

```python
import pathlib, app.tour
from app.anatomy import ANATOMY
from app.engine import simulate
from app.tour import SIGNATURE_STEP_ID, TOUR_RESPONSE
from twinkit.testing import assert_tour_invariants

PUBLIC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "public"

def test_tour_invariants():
    assert_tour_invariants(TOUR_RESPONSE, ANATOMY, simulate(), SIGNATURE_STEP_ID,
                           module=app.tour, public_dir=PUBLIC)
```

That call covers these rules: regions resolve; cameras are inside the map
with positive area; consecutive cameras overlap or move at most
`(W+H)/2` (pan plus zoom; override with `max_travel=`); `layer_reveal` is
monotonic except for one drop at the final step; layers cover the map; the
trace cursor is valid and monotonic; ids are unique and kebab-case; scripts
and titles are non-empty; the total is 2–6 minutes; the signature step
exists; photos are local, credited and present on disk; and the module is
pure.

Then add the twin's own checks. Copy these from
`DellPowerStore/backend/tests/test_tour.py` and adapt them:

- `assert_deterministic(lambda: build_tour(ANATOMY))`
- storyboard shape: 6–9 beats, the first at layer 0 with a whole-map camera,
  the second peeling, the last at layer 0
- the signature step lights the regions that carry the idea, and its camera
  frames all of them
- the signature step's `trace_cursor` is the matching trace step (compare
  the trace label)
- the trace's longest stage (unique max `cycle_cost`) has a beat, where the
  twin has one
- any structural symmetry the twin already enforces (PowerStore: every lit
  `-a` has its `-b`)
- every script is registered with levels {1, 3, 5}, and novice is longer
  than expert
- the endpoint answers at every level, level 3 is byte-identical to the
  data, and 1 differs from 5

**Leveling.** Add `import app.tour  # noqa: F401` to `tests/test_leveling.py`.
The registry only holds what has been imported. Because `TOUR_RESPONSE` is
built at import, the generic leveling checks then cover the narration.

Run `cd <Twin>/backend && .venv/bin/python -m pytest -q` and, from the repo
root, `<Twin>/backend/.venv/bin/python -m pytest -q twinkit <Twin>`.

## 4. Frontend: import the player

The player lives in `packages/twin-ui` and every twin frontend already
resolves that package (the `@twinsim/twin-ui` alias in `vite.config.ts` and
the matching `paths` entry in `tsconfig.json`). Do not copy it:

```ts
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";   // in api.ts too
```

The player imports its own stylesheet, so there is nothing to add to
`main.tsx`. The wire types (`Tour`, `TourStep`, `TourPhoto`, `TourSource`,
`TourResponse`, `CameraBox`) mirror `twinkit/tour.py`; the render types
(`TourStage`, `TourRegion`, `RegionLook`) and the motion helpers
(`useCameraTween`, `useReducedMotion`, `makeRegionLook`) are exported too. To
see the player with no twin behind it, run `npm run gallery` in
`packages/twin-ui`. If a twin needs the player to behave differently, change
it there, for every twin, and rebuild every frontend that imports twin-ui.

### Player props (exact API)

```ts
interface TourPlayerProps {
  tour: Tour;                                        // GET /api/tour → .tour
  layers: Record<string, number>;                    // GET /api/tour → .layers
  bounds: { width: number; height: number };         // { width: mapWidth, height: mapHeight }
  regions: TourRegion[];                             // anatomy.regions (any {id,x,y,w,h}[])
  renderStage: (stage: TourStage) => ReactNode;      // draw the twin's own diagram
  onTraceCursor?: (index: number) => void;           // move the host's trace cursor
  initialStepId?: string | null;                     // from #tour/<stepId>
  onStepChange?: (stepId: string) => void;           // rewrite the hash
  aside?: ReactNode;                                  // extra side-column content
  stageAspect?: number;                               // width ÷ height of the diagram box
}

interface TourStage {
  viewBox: CameraBox;                                 // tweened camera, map coords
  lit: Set<string>;                                   // the step's regionIds
  regionLook: (id: string) => { opacity: number; dx: number; dy: number };
  onRegionClick: (id: string) => void;                // call on region click → take-over
  takenOver: boolean;
  reducedMotion: boolean;
}
```

The player owns one `requestAnimationFrame` clock, the transport
(Previous / Play / Next, a scrubber with one tick per step, speed 0.75–2×),
the step list (titles only), captions (always shown, below the diagram or on
it), speech (muted until the viewer turns it on, rate = playback speed), the
X-ray photo toggle, take-over (a region click or a hidden tab pauses; "Resume
tour" restores the framing; "Show the whole map" frees the camera), and the
keyboard (space, left/right arrows, ignored while focus is in a control).

**`stageAspect`.** The stage's SVG box has a fixed aspect ratio so the page
does not change height while the camera tweens. It defaults to
`bounds.width / bounds.height`. If the map component draws a margin or labels
around the map, pass its own ratio: PowerStore's `ChassisView` draws
100 × (46 + margin + labels), so it passes `stageAspect={2}`.

## 5. Frontend: teach the diagram two props

The twin's map component (`ChassisView`, `RackView`, `FabricView`, ...) needs
two optional props. Without them it draws exactly as before.

```tsx
camera?: { x: number; y: number; w: number; h: number };        // map coords
regionLook?: (id: string) => { opacity: number; dx: number; dy: number };
```

- **viewBox.** Map the camera box to the renderer's own frame so that
  `whole_map` reproduces the default viewBox *exactly* (otherwise the first
  tween jumps). With the chassis pattern (outline margin `M` and 4 units of
  orientation labels below):
  `viewBox = camera ? \`${c.x} ${c.y} ${c.w + 2*M} ${c.h + (2*M + 4) * (c.h / anatomy.height)}\` : \`0 0 ${W} ${H + 4}\``.
  Work the equivalent out for any other margin scheme, and check it at the
  whole-map box.
- **regionLook.** On each region's `<g>`, set
  `style={{ opacity, transform: \`translate(${dx}px, ${dy}px)\` }}`. In SVG,
  CSS `px` are user units, so the offset is in map units. Add the transition
  in the twin's `styles.css`:
  `.tour-stage .an-region { transition: opacity .6s ease, transform .8s ease }`
  and `.tour-reduced .an-region { transition: opacity .3s linear }`.

## 6. Frontend: `App.tsx`

1. Add `"tour"` to `Page`. In `pageFromHash` add `if (h.startsWith("#tour")) return "tour";`,
   and add `tour: "tour"` to `PAGE_HASH`.
2. Read the deep link once:
   `const tourStart = useRef(window.location.hash.match(/^#tour\/([a-z0-9-]+)$/i)?.[1] ?? null)`.
3. Fetch lazily and refetch on level: add `fetchTour()` to `api.ts` (same
   `url()` helper, so `?level=` rides along) and run
   `useEffect(() => { if (tourWanted) fetchTour().then(setTour) }, [level, tourWanted])`,
   where `tourWanted = page === "tour" || tour !== null`.
4. Add a `Guided tour` nav button and a `Guided tour` button (`className="primary"`)
   on the sim page's hero.
5. Listen for `hashchange` and set the page from the hash, so back/forward
   and in-page links that assign `location.hash` switch pages
   (`useEffect(() => { const f = () => setPage(pageFromHash()); addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, [])`).
   The pilot shipped without this; every other twin already had it.
6. Render the page. It spans both grid columns
   (`.tour-page { grid-column: 1 / -1 }`, plus `grid-row: 2 / -1` under `.app.dell`):

```tsx
<TourPlayer
  tour={tour.tour} layers={tour.layers}
  bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
  stageAspect={2}                                        // only if the diagram adds a margin
  regions={anatomy.regions}
  initialStepId={tourStart.current}
  onStepChange={(id) => { tourStart.current = id; history.replaceState(null, "", `#tour/${id}`); }}
  onTraceCursor={(i) => { stop(); setCursor(i); }}      // the EXISTING cursor
  renderStage={(stage) => (
    <ChassisView anatomy={anatomy} active={stage.lit} selected={regionId}
      onSelect={(id) => { setRegionId(id); if (id) stage.onRegionClick(id); }}
      camera={stage.viewBox} regionLook={stage.regionLook} />
  )}
  aside={<>{state && <p className="tour-trace">Power-on trace: <strong>{state.label}</strong> …</p>}</>}
/>
```

Use `history.replaceState` instead of assigning `location.hash`. That way the
URL follows the tour without firing `hashchange` or growing the history.

## 7. `frontend/smoke.json`

Add these routes. The tour opens paused, so the interaction check clicks
`Next`:

```json
{ "hash": "#tour", "name": "tour", "svg": true, "visible": [".tour-caption"],
  "text": ["<a step title>"],
  "play": { "click": "button:text-is('Next')", "watch": ".tour-caption", "times": 2 } },
{ "hash": "#tour/<signature-id>", "name": "tour-signature", "svg": true,
  "visible": [".tour-caption", ".tour-step-current"],
  "text": ["<the pinned trace label>", "<a phrase from the standard script>"],
  "play": { "click": "button:text-is('Previous')", "watch": ".tour-caption", "times": 1 } }
```

Do not require `Resume tour` text. It only appears after a take-over. Then run
`scripts/smoke.sh <Twin>`; `scripts/smoke.sh <Twin> -- --grep tour` runs just
the tour routes.

## 8. Pitfalls hit in the pilot

- **Wide maps barely zoom.** Most maps are about 2:1 (PowerStore is
  100×46), and `camera_around` keeps the map's aspect, so any frame that
  holds both a top and a bottom region comes out as nearly the whole map. For
  a real close-up, frame one half with an explicit `CameraTarget` and say in
  the script that the other half mirrors it. Keep the signature beat framing
  every region it lights, and test that.
- **Skin specificity.** `.app.dell button` is (0,2,1) and restyles every
  button. The player's step-list buttons use
  `.tour .tour-steps button.tour-step` (0,3,1) to stay flat. Any new button
  style in the player (`packages/twin-ui/src/components/tour/tour.css`) needs
  at least that specificity.
- **Chrome speech drops long utterances.** An utterance longer than about 15
  seconds can stop without firing `onend`, which would hang a "wait for the
  narrator" rule. `narration.ts` speaks one utterance per sentence, and the
  clock waits for speech at most one extra step length.
- **StrictMode and the clock.** Dev mode runs state updaters twice. Keep the
  timeline in refs (`pos`, `hold`), advance them in the rAF callback, and
  only mirror them into state. An updater that adds `dt` would double time.
- **Hash effect.** App's page effect used ``hash.startsWith(`#${PAGE_HASH[page]}`)``,
  and with `poweron: ""` that is always true, so leaving `#tour/<id>` for
  the sim page kept the tour hash. The pilot checks the landing page
  explicitly with `!/^#(anatomy|components|usecases|tour)/.test(h)`. Copy
  that fix, with the twin's own page names.
- **Leveling registers on import only.** Build `TOUR_RESPONSE` at module
  import and import `app.tour` in `test_leveling.py`. Otherwise the tour's
  variants are invisible to the generic leveling tests. Two scripts whose
  standard text is byte-identical share one registry key. If their other
  levels differ, the result is a `LevelingConflict`.
- **`resolve()` swaps any string equal to a registered standard text**,
  wherever it appears in the payload. Never reuse a script's exact text as a
  title or id.
- **Lit beats ghost.** A step that peels to layer 2 but narrates a layer-0
  part (PowerStore's NVRAM slots) still shows that part at full opacity,
  because lit regions are never ghosted. Don't lower `layer_reveal` to show
  it. That would break monotonicity.
- **Stopping servers.** `pkill -f "<pattern>"` matches the shell that runs
  it and kills it. Kill your own server processes by PID. Other agents'
  `smoke.sh --keep` runs hold other twins' ports.
