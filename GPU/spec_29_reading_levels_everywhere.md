# spec_29 — reading levels everywhere

**Goal:** the GPU app pioneered the reading-level mechanism and then leveled the
least of it. `leveling.py`, the `LevelControl`, `?level=` plumbing, and
`test_leveling.py` all ship — but only the 8 die-anatomy **overviews** are
authored at all five registers. The lesson tour (the designated beginner path),
every die-region description, and the simulator page's explainer copy read
identically at every level, so the control the header promises works on exactly
one kind of paragraph. Close the gap. No new mechanism: every change is `L(...)`
wrappers, `leveled(...)` at the transport edge, and `lv()` on one more fetch.

## Inventory (counted, current state)

| Surface | Blocks | Leveled today |
|---|---|---|
| Anatomy overviews (`anatomy.py`) | 8 dies | **yes — all 5 levels** |
| Die-region descriptions (`anatomy.py`) | 51 regions, ~50 `description=` call sites, **28 unique strings** | no |
| Die stats / region names / titles | — | no, and stays no (see scope) |
| Tour intro (`tour.py`) | 1 | no |
| Tour step scripts (`tour.py`) | 8 | no |
| Tour experiments (`tour.py`) | 6 (steps 04 and 06 carry none) | no |
| InfoDot/Controls + LiveViz explainers (frontend JSX) | ~9 modals | no — scoped out below |

Registry before: 8 blocks (ends coverage 8/8). After: **51 blocks** — 8
overviews + 28 unique region descriptions + 1 intro + 8 scripts + 6 experiments.

## 1. The lesson tour (highest value — it is the beginner path)

- Wrap `intro`, every step's `script`, and every `experiment` in `L(...)` with
  **all five registers authored** — no fallback-only levels here. Titles and
  ids stay plain strings (names, not prose).
- Purity is not threatened: `test_tour.py`'s AST check allows relative imports,
  and `leveling` imports nothing but `typing` — `from .leveling import L` in
  `tour.py` passes, exactly as it does in the 18 engine modules repo-wide.
  **Resolution never happens in `tour.py`**: `build_tour()` keeps returning the
  level-3 tour; `main.py`'s `get_tour` grows `level: int = Level` and returns
  `leveled(build_tour(), level)`. `/api/tour/recordings/*` is untouched —
  recordings are events, not prose.
- Register content guidance: level 1 opens "grid of thread blocks", "SM",
  "occupancy", "%smid" on the spot and drops the cross-references (spec_03,
  NV-HBI, XE9712 asides); level 5 keeps the numbers and cuts the explanations —
  the Blackwell step at level 5 is roughly "320 blocks, 160 SMs, smids 0–159,
  no seam: NV-HBI presents one logical GPU."

## 2. Die-region descriptions (the deduplication is the effort-saver)

- Wrap each region `description` in `L(...)`. Because registration keys on the
  level-3 text, the repeated memory-subsystem blocks **author once and serve
  everywhere**: the 4× GB200 L2-slice text, 3× GDDR6X and 3× GDDR7 controller
  blocks, 2× HBM3, 2× HBM2e, 2× H100 L2 strings collapse ~50 call sites to
  **28 authoring jobs**. Wrap every call site anyway (identical `L(...)` calls
  under one key are legal); only *differing* variants under one key raise
  `LevelingConflict` — so if one die ever needs a die-specific novice line for
  a shared block, **change its level-3 text first** (e.g. append the die name),
  never fork the variants alone. Extract each shared block to a module-level
  `_HBM3_DESC = L(...)` constant so the five variants exist in one place.
- Authoring priority, in order: (1) the shared memory blocks — biggest yield
  per paragraph; (2) AD102's regions — it is the default profile's family and
  the die a 4060 owner opens first; (3) GH100/GB200/GB300 (the tour's step 7–8
  point at them); (4) the rest. Levels 1/3/5 authored minimum; 2/4 optional —
  the tie-break-away-from-standard rule makes a {1,3,5} block resolve sensibly
  at 2 and 4.
- **Stats, region names, source titles, photo credits stay unleveled** on
  purpose: they are labels and citations, not prose — five registers of "L2
  cache: 96 MB" would be noise, and credits must never be paraphrased.

## 3. Simulator-page explainers: scoped out, deliberately

The InfoDot bodies (`Controls.tsx` ×8, `LiveViz.tsx`) stay in the frontend and
out of the leveling system. Decision, defended:

- They are **structured JSX** — lists, `<code>`, emphasis, sometimes values
  interpolated from live state. `resolve()` swaps flat strings in a dumped
  payload; it cannot carry markup, so a backend route would mean flattening the
  copy or inventing an HTML-fragment protocol. Both are worse than the gap.
- The modals are already written for the reader who clicked "what is this?" —
  they are novice-register by construction, the one surface whose audience is
  self-selecting.
- If these strings ever gain live-value substitution, the right move is the
  R760Thermal **explain-endpoint pattern** (`/api/explain`, leveled like
  everything else), which is a spec of its own — record that as the follow-up,
  don't half-build it here.

## 4. Frontend

- `api.ts`: `fetchLessonTour()` appends `lv()` (the anatomy fetch already
  does). No other fetch changes — sim traces and live sessions carry no prose.
- `LessonTour.tsx`: `const level = useLevel()`; `level` joins the tour-fetch
  effect's dependency array. The recording-fetch effect keys on `lessonId`
  only and must **not** re-run on a level change.
- **House rule, pinned:** a level change never resets the reader's place. The
  tour keeps its current step index across the refetch (step count is
  level-invariant), exactly as the anatomy page keeps its selected die/region
  and the sim keeps its cursor.

## Authoring requirements (the gotchas, as rules)

- Levels 1–2 are a **change of register, not a paraphrase** — the light-edit
  approach collapses into byte-identical neighbors, and
  `test_every_variant_is_nonempty_and_distinct_from_its_neighbours` has caught
  that 21 times repo-wide. Rewrite, don't sand.
- Where 1 and 5 both exist, **novice must be longer than expert**
  (`test_the_scale_runs_the_right_way` — an inverted scale is a bug).
- Level 3 stays byte-identical to today's text: `L(standard=<existing>)`, never
  a rewrite in the same commit (that would silently re-key shared blocks and
  invalidate the dedup).

## Tests

- The whole existing `test_leveling.py` suite is the guard and runs unchanged —
  including `test_levels_actually_differ_for_every_die`, which now bites on
  region descriptions too.
- New, in `test_leveling.py` (or `test_tour.py`):
  - `test_every_tour_script_is_registered_at_the_ends` — intro, all 8 scripts,
    and all 6 experiments present in `registry()` with levels 1 **and** 5
    authored (fallback is fine for regions; the beginner path gets no
    fallbacks).
  - `test_tour_endpoint_levels` — `GET /api/tour?level=3` byte-identical to
    unparameterized; `?level=1` ≠ `?level=5` for every step script.
  - Coverage floor: `coverage()[1] >= 40` and `coverage()[5] >= 40` (from
    today's 8/8), so the registry can't quietly regress to overviews-only.
- Frontend: `npm run build` (no type changes expected — leveling is invisible
  to `types.ts` by design).

## Sizing

Mechanism work is a day: two `L` imports, one `leveled()` call, one `lv()`, one
dependency array, three tests. The real cost is authoring — 43 new blocks × up
to 5 registers, concentrated in 15 tour blocks at full depth and 28 region
descriptions at 1/3/5. Land it in two commits: tour first (small, highest
value, exercises the whole path end to end), regions second.

## Implementation notes

Landed 2026-08-16. Where the spec differed from code reality, code reality won:

- **Inventory recount.** The spec was authored before specs 22–28/30 landed
  GB202, GB300, and MI300X (and the two lesson-07 tour steps). Reality: 8 dies,
  167 region call sites, **40 unique description strings** (not 51/~50/28), and
  a tour of 1 intro + **8** scripts + **6** experiments (steps 04
  `matmul-uncached` and 06 `the-roof` carry none — the table's counts were
  right, the §"Registry after" arithmetic wasn't). Registry after: **63**
  blocks (8 overviews + 40 regions + 15 tour), not 51.
- **Coverage floor** set at `>= 60` for levels 1 and 5 (actual: 63), not the
  spec's `>= 40` — recounted per the spec's own instruction.
- **`test_tour.py`'s AST purity check does not "allow relative imports"** as
  the spec claimed: it checks the module name against an allowlist
  (`{__future__, typing, "", models}`). `"leveling"` was added to that set —
  legitimate because `leveling` imports nothing but `typing`, exactly the
  argument the spec makes.
- Dedup landed as planned: every unique region description is a module-level
  `_*_DESC = L(...)` constant; the GB200/GB300-shared io and L2 strings
  (`_IO_DESC_GB`, `_L2_DESC_GB`) author once and serve both dies. Regions are
  authored at 1/3/5 (2/4 resolve by the tie-break rule); all 15 tour blocks
  carry all five registers.
- Frontend: `fetchLessonTour()` appends `lv()`; `LessonTour.tsx` refetches the
  tour on `level` while the recording effect keys on `lessonId` only, and
  `stepIdx` survives the refetch (house rule). The spec_30 `link` fields are
  untouched — names and hashes, not prose.
- Tests 486 → **489**: `test_every_tour_script_is_registered_at_the_ends` and
  `test_tour_endpoint_levels` (in `test_tour.py`),
  `test_coverage_floor_after_spec_29` (in `test_leveling.py`).
