# spec_30 — cross-navigation: three tabs, one atlas

The app has three tabs that describe the same silicon and never point at each
other. The simulator's `H100-SXM` profile and the anatomy page's `gh100`
floorplan are the same die, but the correspondence lives only in the reader's
head; a lesson-07 recording says "NVIDIA H100" and the UI shrugs. This spec
makes the correspondences data and turns them into links — the three tabs
become one connected atlas. No new pages; every feature is a link or a badge
riding data the backend already owns or gains here.

## The mapping (backend data)

1. **`die_id` on `GpuProfile`** — a nullable field naming the `DieAnatomy` id
   the profile draws (`dieId` on the wire; plain camelization, no alias
   gotcha). Nulls are honest and allowed in both directions:
   - mapped: `H100-SXM↔gh100`, `B300-Blackwell-Ultra↔gb300`,
     `RTX-5090↔gb202`, `MI300X↔mi300x`.
   - profile without a die: `RTX-4060-Laptop` (there is **no AD107 entry** in
     `anatomy.py` — the machine's own die is the one we cannot show),
     `Generic-128`, `Generic-512` (deliberate: they are teaching abstractions,
     not silicon).
   - die without a profile: `ga100`, `ad102`, `navi31`, `gb200` (anatomy is a
     museum; the simulator is a bench — the museum is allowed to be bigger).
   The reverse map is derived from `PROFILES` at import time, never authored
   twice. Recommend authoring an AD107 die as a follow-up spec to close the
   4060's gap — it is the only *machine-present* die missing — but this spec
   does not include the die itself.
2. **`GET /api/atlas`** — the profile↔die pairs plus per-mapping
   `deviceMatch` substrings (e.g. `"H100"`, `"B300"`, `"GB300"`) used by item
   6, served as data so the frontend hardcodes nothing. This is a **new
   route**: `test_api_surface_snapshot` pins all 23 `/api` routes by name and
   must be updated to 24, deliberately, in the same commit.

## Simulator → anatomy

3. **"See this die's anatomy"** next to the profile picker in `Controls.tsx`,
   rendered only when the selected profile carries a `dieId`; it navigates to
   the existing `#anatomy/<dieId>` deep link. Unmapped profiles show nothing —
   no disabled button apologizing for the generic dies.

## Anatomy → simulator

4. **"Simulate this die"** on the anatomy page when the shown die has a
   profile, writing the profile name into the persisted
   `twin.simSettings` (spec_21 #2 — add a `profileName` key the simulator
   honors on load, falling back to the first profile as today) and navigating
   to `#`. The reader's N / tile size / dtype survive; only the die changes.

## Anatomy die-compare

5. **`#anatomy/<dieA>/vs/<dieB>`** — the deep-link grammar grows one form:
   two floorplans side by side with an aligned stats table (SMs/CUs, cache,
   memory, process, area — the fields `DieAnatomy.stats` already carries).
   `vs` becomes a reserved region id (assert no die ever uses it,
   `test_anatomy.py`). The payoffs the picker should offer as one-click
   presets, as data: **gb200 vs gb300** (the Blackwell refresh — same
   floorplan, more HBM) and **gh100 vs gb200** (the Hopper→Blackwell
   generation step). Compare view is derived from two ordinary die fetches;
   no new endpoint.

## Tour → everywhere

6. **`link` on `TourStep`** — an optional hash URL (`#anatomy/gh100/nvlink`,
   `#live`, `#anatomy/gb200/vs/gb300`) that `LessonTour.tsx` renders as a
   real button beside the `experiment` prose, which today names tabs in
   words the reader must retype. Links are authored in `backend/tours/`,
   not in component code; steps without one render exactly as now.

## Live → anatomy

7. **Die badge on `device_info`** — when a session's device name matches a
   `deviceMatch` substring from the atlas (the lesson-07 H100 and B300
   golden recordings are the motivating cases), the Live tab's device line
   gains a small "die anatomy →" badge linking to `#anatomy/<dieId>`. The
   local 4060 gets no badge until the AD107 follow-up lands — the gap stays
   visible rather than papered over.

## Invariant

**Every existing deep link keeps meaning what it meant.** `#anatomy`,
`#anatomy/<die>`, `#anatomy/<die>/<region>`, `#live`, and bare `#` parse
exactly as before; the `vs` form is additive and unreachable by accident
because `vs` is a reserved, never-authored region id.

## Test plan

- `test_atlas.py` (new): every non-null `die_id` resolves in `ANATOMIES`;
  the derived reverse map is injective (no two profiles claim one die); the
  known-unmapped sets on both sides are pinned by name, so closing a gap
  (or opening one) is a deliberate test edit; every `deviceMatch` substring
  is nonempty and maps to a resolvable pair.
- vs-grammar: parse and round-trip tests in the frontend build's typecheck
  path plus a `test_anatomy.py` assertion that no region id equals `vs`.
- `test_tour.py` grows: every authored `link` is a well-formed hash whose
  die/region segments resolve against `ANATOMIES` (tour links must never
  404 into a blank floorplan).
- `test_api_surface_snapshot` updated 23 → 24 routes for `/api/atlas` —
  called out above; the only snapshot change this spec is allowed to make.
- Frontend: `npm run build` stays green; no other API shape changes.

## Implementation notes

Landed 2026-08 against the post-spec_22–28 codebase (suite 470 → 486). Where
the spec's guesses differed from code reality, the code won:

- **`twin.simSettings` was the real key** — the spec's guess was right.
  `App.tsx` now persists a `profileName` alongside the existing settings and
  honors it on load (falling back to the first profile as before); "simulate
  this die" works by setting the profile through App state, so the same
  persistence effect writes the key — no second writer.
- **The app never listened to `hashchange`** — tabs only *wrote* the hash.
  Cross-navigation links (Controls' anatomy link, tour-step buttons, live
  badges) change the hash directly, so `App.tsx` gained a `hashchange` →
  page-state sync listener. Additive: every pre-existing deep link
  (`#anatomy`, `#anatomy/<die>`, `#anatomy/<die>/<region>`, `#live`,
  `#live/tour`, bare `#`) parses exactly as before.
- **No frontend test runner exists**, so the vs-grammar "parse and
  round-trip tests in the typecheck path" are `src/anatomyHash.ts`: pure
  typed `parseAnatomyHash`/`buildAnatomyHash` used by `AnatomyPage`, held by
  `tsc` plus hand verification of all four hash forms and their round-trips.
  The backend halves are real pytest: `test_anatomy.py` reserves `vs` as an
  id, `test_tour.py` resolves every authored link against `ANATOMIES`.
- **deviceMatch substrings** are authored against what devices actually
  report (`"H100"`, `"B300"`/`"GB300"`, `"RTX 5090"` with the space,
  `"MI300X"`); `test_atlas.py::test_lesson_07_goldens_match_the_atlas` pins
  the two golden recordings' device names to gh100/gb300.
- **The live badge rides the folded frame's `device` info** (which carries
  forward across a session's frames), shown on the device/kernel line —
  sessions in the recordings list carry no device name until a summary is
  fetched, so the badge lives where the device name actually is. It also
  appears in the lesson tour, where the lesson-07 recordings are actually
  watched.
- Tour links authored: `the-roof` → `#` (simulator), `the-die-is-a-parameter`
  → `#anatomy/gh100`, `blackwell-two-dies-one-gpu` →
  `#anatomy/gb300/vs/gb200`. Steps without links render exactly as before
  (`link` defaults to null).
- The route snapshot moved 23 → 24 for `/api/atlas`, with a comment, as the
  only snapshot change — per the test plan.
- The compare view is derived from the anatomy list the page already fetches
  (no per-die refetch, no new endpoint); clicking a block in compare drops
  into that die's ordinary single view with the region pinned.
