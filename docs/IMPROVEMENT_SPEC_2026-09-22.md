# Improvement Spec — DigitalTwinSim

**Status:** proposed (2026-09-22)

Twenty-five improvements, found by six parallel read-only surveys of the repo on
2026-09-22: backend architecture, test and physics quality, frontend and
accessibility, docs and CI, teaching quality, and content coverage. Every item
below carries the evidence it was found by. Counts were measured, not estimated.

The repo at the time of the survey: 49 components (3 `reference`, 38 `built`,
1–2 `partial`, 7 `scaffold`), 6,446 tests running in 113 s, 42 React frontends
over one shared skin, a 19-module course in `Learn/`, 25 narrated tours, 54
graded labs, and a static-hosting build that runs the real Python engines in the
browser under Pyodide.

**A caveat on the measurements.** A workflow was mid-edit during the survey
(`compose/` untracked, ~158 untracked files, four failing `compose/` tests).
Findings that touch in-flight work are marked. Re-measure before acting on
items 9, 11 and 25.

**A correction carried forward.** One survey reported `CustomerSetup`'s research
and the seven scaffold specs as "14 months" old. They are dated 2026-07-24/31,
so as of today they are about **eight weeks** old. The staleness argument in
items 24 and 25 rests on renamed products, not on elapsed time.

Ordering is by tier, and within a tier by impact against effort. Tier 1 is
"something here is wrong"; the rest is "something here could be better".

---

## Tier 1 — Things that are wrong now

### 1. PhysicsCDU's headline identity is a tautology — S

**Problem.** The app exists to show that "a CDU is a device for making three
numbers equal", and `PhysicsCDU/backend/tests/test_engine.py:53
test_heat_balance_both_loops_every_tick` cannot fail for any reason except a
rounding change. All three assertions restate the engine's own algebra:
`engine.py:210` computes `sec_ret = supply + q_it / (m_dot_sec * cp_pg)` and the
test divides it straight back out, so `cp_pg25`, `rho_pg25` and the `/60.0`
unit conversion all cancel; `engine.py:310` sets `heat_removed_kw = q_it`, and
line 73 compares that value to itself. A wrong specific heat, a wrong density
or a dropped unit conversion all pass. Contrast `DellIR7000`'s version of the
same law, which asserts it with no tolerance over hand-written literal states
and is therefore a real arithmetic check.

**Do.** Assert against numbers the engine does not compute the same way:
accumulate the energy budget over the run from the trace's *reported* flow and
temperatures; pin one hand-computed operating point as a literal (220 kW at a
6 K design ΔT is 8.76 kg/s ≈ 527 L/min); and check the secondary ΔT lands in
the 8–12 K band the `flow_nominal_lpm` constant claims.

**Done when.** Deleting the `/60.0` in `engine.py:210` makes the test fail.

### 2. PhysicsCDU trips silicon at 65 °C, and the app's whole lesson pivots on it — M

**Problem.** `PhysicsCDU/backend/app/constants.py:132` sets `chip_trip_c = 65`
and `:126` sets `chip_target_c = 63`. Real GB200-class silicon runs to roughly
90–105 °C. The cause is upstream: `:113 r_chip_k_per_kw = 0.18` gives only 7.2 K
of junction-to-coolant rise across a 40 kW bank where a cold plate and TIM stack
is 25–35 K, so silicon lands near 44 °C and the trip line had to be dragged down
to make the story work. That story — coordinated control versus an uncoordinated
trip cascade — is the app's flagship lesson and its two acceptance tests. Both
constants are correctly labelled `estimated=True`, which is the point worth
sitting with: the honesty labelling is intact and the number is still wrong and
still load-bearing. `DellPowerEdgeR760Thermal` uses a realistic 98 °C.

**Do.** Raise `r_chip_k_per_kw` to ~0.7 (≈28 K at 40 kW), move target/trip to
~85/90 °C, re-tune `cap_kp` so the coordinated and uncoordinated acceptance
tests still separate, and update the guided-scenario prose that quotes them.
Add the plausibility test the physics suite currently lacks anywhere.

**Done when.** A new test pins peak silicon into 70–95 °C at full tilt, and both
acceptance tests still pass.

### 3. Two apps enforce opposite rules on the same class of constant — S

**Problem.** Both cite "the Circular Design rule: no invented sustainability
numbers". `PhysicsDisplay/backend/tests/test_model_data.py:42` asserts carbon
constants must **not** be estimates ("must be sourced, not invented").
`PhysicsLifecycle/backend/tests/test_engine.py:54` asserts they **must** be
estimates. A constant moved between the two apps fails one by construction. The
filters are also wrong in both directions: Display matches `unit == "kgCO2e"`
exactly, so `"kgCO2e/yr"` slips past; Lifecycle matches `"kg" in unit`, which
sweeps in masses like `battery_part_kg`.

**Do.** One helper in `twinkit` — every carbon figure must either cite a PCF
document or declare itself an estimate, never neither — with a normalised unit
predicate. Call it from both apps.

**Done when.** Moving a carbon constant between the two apps does not change
whether the suite passes.

### 4. Tests that check less than their names claim — M

**Problem.** Three cases, all in headline identities.

- 17 scenario-driven apps declare a bare `TraceProfile()`
  (`grep -c "TraceProfile()" */backend/tests/*.py` → 17 files). With no phases,
  no anatomy and no cycle field, `twinkit/testing.py:129
  assert_trace_invariants` collapses from six checks to two: the trace is
  non-empty and time increases. The docstring advertises "the six invariants
  every trace in this repo has"; for 40% of components it enforces one.
- Consequently **`PhysicsME5` has no engine-to-diagram contract test at all**.
  It declares `region_states` and `ArrayRegion`, and `grep -rl region
  PhysicsME5/backend/tests/` returns nothing. Rename a region id and it goes
  silently unpainted, with no frontend test to catch it either.
- `PhysicsLifecycle/backend/tests/test_engine.py:92
  test_the_ledger_closes_every_tick` iterates `trace[::37]` — 79 of 2,920 ticks,
  2.7%. `DellPowerEdgeR760Thermal/backend/tests/test_engine.py:74
  test_heat_balance_at_steady_state` checks `trace[-1]` of one scenario, and its
  comment claims the mass flow is derived from the scenario's altitude while the
  code uses the sea-level density constant unconditionally.

**Do.** Add a `TraceProfile.physics(...)` constructor that keeps the region
check alive for scenario apps, and make an empty profile an explicit
`TraceProfile.minimal()` so it is a decision rather than a default. Add the
missing PhysicsME5 region test. Drop the stride and the single-index probe —
2,920 subtractions cost microseconds against a 113 s suite — and run the heat
balance at altitude with density derived from the scenario.

**Done when.** `grep -c "TraceProfile()"` is 0; renaming a PhysicsME5 region id
fails a test; neither conservation test contains a stride or a single index.

### 5. The lab invariants — 150 lines behind 36 call sites — have no negative coverage — S

**Problem.** `twinkit/testing.py:441-600 assert_lab_invariants` is what makes
the 54 graded labs trustworthy: reference solutions must pass, naive defaults
must fail, gaming attempts must not succeed. Its two siblings are properly
self-tested with `pytest.raises` (`twinkit/tests/test_twinkit.py:161`,
`twinkit/tests/test_tour.py:147`). `twinkit/tests/test_labs.py` tests only
`twinkit.labs.grade` and contains **no** `pytest.raises` against the helper. If
the anti-gaming check were inverted or short-circuited, all 282 collected lab
tests would pass while checking nothing. The `gaming_attempts is not None` guard
is the sharpest edge: omit the argument and the whole block is skipped. All 35
apps pass it today by convention, enforced by nothing.

**Do.** Mirror the existing break-it-one-at-a-time pattern: drop the
`guards_work` criterion, make the start scenario already pass, make the
reference fail, remove the level-5 prose, add a passing gaming attempt, omit
`gaming_attempts` — each must raise with a named message. Make `gaming_attempts`
required.

**Done when.** `test_labs.py` has ≥6 `pytest.raises(..., match=...)` cases, and
calling the helper without `gaming_attempts` raises.

### 6. The purity check never follows the engine's own imports — S

**Problem.** `twinkit/testing.py:220` skips relative imports by construction
(`node.level == 0`), so the 86 sibling edges out of the 42 engines
(`from .models`, `from .constants`, `from .leveling`, …) are never inspected.
`constants.py` could `import time` and every purity test would stay green.
`IMPURE_MODULES` also omits `datetime`, `pathlib`, `subprocess`, `urllib`,
`requests`, `socket`, `secrets` and `uuid`, and nothing checks for `open(`,
`__import__`, `eval` or `exec`. There are zero live violations today — this is
a guard-rail gap, not a bug, and the guard rail is one of the repo's
load-bearing invariants.

**Do.** Follow relative imports to the sibling file and recurse with a visited
set; extend the module list; add an `ast.Call` check for the dynamic-execution
builtins.

**Done when.** A deliberate `import time` in any component's `constants.py`
fails that component's engine test.

### 7. 258 warnings go to a stream nobody reads — S

**Problem.** The suite ends `6442 passed, 258 warnings` and `pytest.ini` has no
`filterwarnings`. Among them, 72 instances across 16 components of
`UnsupportedFieldAttributeWarning: The 'alias' attribute ... has no effect in
the context it was used`, fired at request time by the `POST /api/simulate` and
`POST /api/labs/{id}/grade` routes taking a camelCase scenario model. That is
precisely the failure class CLAUDE.md's "Cross-cutting gotcha" section warns
about — a wire alias silently not applied — and pydantic is announcing it into
silence.

**Do.** Turn the pydantic alias and deprecation warnings into errors in
`pytest.ini`, then triage the remainder to zero or to named `ignore` entries
with a stated reason.

**Done when.** `pytest -q` reports 0 warnings, or every survivor has a comment
saying why it is allowed.

---

## Tier 2 — Verification that does not verify

### 8. CI does not check what CI claims to check — M

**Problem.** Three findings, confirmed directly:

- `.gitlab-ci.yml:84` runs `cd frontend` at the repo root. **There is no root
  `frontend/` directory** — the 42 frontends live at `<Component>/frontend/`.
  The job fails on every pipeline and always has, and `deploy-frontend` `needs:`
  it, so that has never run either. Net effect: **no frontend is typechecked or
  built in CI**, though CLAUDE.md documents `npm run build` as the gate.
- The `Learn` shard passes **vacuously**. `Learn/tests/test_links.py` returns
  `None` from its trace helper when a twin's `.venv` is absent, and three call
  sites (`:213`, `:399`, `:538`) respond with `continue`, not `pytest.skip`. CI
  has no venvs, so the two tests that verify the course's quoted numbers and
  step links against the engines check **zero** pins and report green.
- `scripts/gen_root_pytest.py:44 missing_ci_shards()` only enumerates
  `*/backend/tests`, so a new top-level test directory is invisible to it. The
  in-flight `compose/tests/` is exactly that case.
- `e2e-smoke` is `allow_failure: true` on the stated grounds that "only GPU and
  DellPowerEdgeR760 have manifests yet". There are now 42 manifests.

**Do.** Replace the two dead jobs with a real frontend build (the root
`package.json` already declares the workspaces, so `npm run build --workspaces`
may be one job). Make the trace helper `pytest.skip` with a reason — a skip is
honest, a vacuous pass is not — and add a job that builds venvs for the twins
the course pins. Broaden shard detection to any top-level `tests/` directory.
Refresh the `e2e-smoke` comment and drop `allow_failure` once green.

**Done when.** A deliberate type error in any `App.tsx` fails a job; the `Learn`
job reports a nonzero checked-pin count or explicit skips; no job references a
path that `ls` cannot resolve; a test asserts that last property.

### 9. The suite tests a stack nobody serves — S

**Problem.** All 42 `requirements.txt` are byte-identical and every line is a
floor (`fastapi>=0.110`, `pydantic>=2.6`, …). What is actually installed across
the 42 venvs: **five FastAPI versions** (0.138.1 through 0.141.1) and six
uvicorn versions. Meanwhile the root suite runs on the system Python with
FastAPI 0.115 — roughly 25 minors behind what `uvicorn` actually serves. Every
`start_backend.sh` re-runs `pip install` on each launch, so twins drift forward
silently, and CI resolves fresh in each of 34 shards, so one upstream release
can redden the pipeline with no repo change. The 42 venvs total 3.0 GB.

**Do.** A repo-root `constraints.txt` with exact versions, passed by
`start_backend.sh` and CI; skip the reinstall when a stamp matches the
constraints hash; run the root suite inside that pinned environment. Consider
one shared dev venv for testing, since per-component venvs are only needed to
*run* a twin.

**Done when.** Scanning the venvs yields one FastAPI, one pydantic and one
uvicorn version, and a cold start needs no network.

### 10. No frontend test of any kind beyond a liveness check — M

**Problem.** `find */frontend -name "*.test.*" -o -name "*.spec.*"` → 0. No
frontend declares vitest, jest or testing-library. The only verification is the
Playwright smoke suite, which collects page errors and screenshots — it cannot
catch a wrong number rendered, a mislabelled axis, a chart drawn from the wrong
field, or the `coresPerSM` alias mismatch CLAUDE.md explicitly warns about. The
page renders cleanly and passes. Meanwhile ~1,100 backend tests assert the
values, so the wire contract is tested on exactly one side. The type layer is
otherwise in good shape: `strict: true` with `noUnusedLocals` in all 42, and
exactly one `any` in the whole frontend tree.

**Do.** Add `tsc --noEmit` per component (this catches the alias-drift class for
free), then vitest on the pure TS modules that compute things: twin-ui's
`Timeline` band arithmetic, `staticApi.ts`'s `bodyKey` hash — which must stay
byte-compatible with two Python implementations, and whose own comment says
"change one side, change the other" — `level.ts` fallback ties, and a
key-equality fixture checked against the backend's `model_dump(by_alias=True)`.
That last one is the highest-yield frontend test in the repo.

**Done when.** `npm test` runs green at the root, and renaming a backend field
whose camelCase key changes fails a frontend test.

---

## Tier 3 — Who can use it

### 11. The diagrams are invisible to assistive technology and unreachable by keyboard — M

**Problem.** The SVG floorplan *is* the content — CLAUDE.md says "geometry
carries the lesson" a dozen times. Measured: 44 diagram components, **2** with
`role="img"`, and exactly **one file in the repo** with `tabIndex`. There are 83
click handlers inside SVGs and one keyboard equivalent. A typical region is a
`<g>` with `onClick`/`onMouseMove` and no role, label, tabindex or key handler;
its only `<title>` is conditional on failure, so in the normal case a screen
reader gets one `aria-label` on the svg root and nothing else. `aria-live`
appears 5 times repo-wide, 3 of them in the tour player, so playback
auto-advances announcing nothing. No `<main>` in any of the 42 `App.tsx`, and
619 `<h2>` render as a flat list of peers. Separately, `animation: region-pulse
... infinite` appears 43 times — an infinite pulse on the primary content of
every twin — and `prefers-reduced-motion` is honoured in 5 stylesheets, each for
one unrelated selector. That is also WCAG 2.2.2.

The fix is already written, twice: `GPU/frontend/src/components/AnatomyView.tsx:99`
does regions correctly (`role="button"`, `tabIndex`, `aria-label`,
`aria-pressed`, Enter/Space, focus-visible CSS), and twin-ui's `TourPlayer` is
the most accessible component in the repo.

**Do.** Lift the GPU region pattern into a shared twin-ui `<Region>` wrapper;
give each diagram `role="img"`, an `aria-label` and a `<desc>` built from the
anatomy overview that is already authored at five reading levels, so the alt
text is free; add an `aria-live` region that announces phase and step as
playback advances; add `<main>`, a skip link and a heading hierarchy to
`TwinLayout`; and put one `prefers-reduced-motion` block in the shared skin.

**Done when.** Every diagram has `role="img"` and keyboard-reachable regions; a
screen reader reads region name and state on focus and announces each step once;
with reduced motion on, no infinite animation runs anywhere.

### 12. When a backend is down, the user gets a JavaScript error at 2.4:1 contrast — S

**Problem.** Two defects that meet on the same line of the page. `.an-error` is
defined identically in **all 42** stylesheets as `#ff7a3c` — a *diagram* token —
rendered on the light page chrome, giving **2.40:1** where AA needs 4.5:1. The
skin already defines `--dell-error` at 5.63:1 and already uses it for failed
regions. Into that div, all 42 apps render `setError(String(e))`, so with
uvicorn stopped the user reads `TypeError: Failed to fetch`, with no retry and
no hint — while CustomerSetup's plain-JS pages already do better, showing the
start command when a port does not answer. There is 1 `ErrorBoundary` in 42
frontends, so a render-time throw whitescreens the other 41.

Related, and cheap to fix in the same pass: `twin.simSettings` and
`twin.sessionName` are generically named `localStorage` keys owned by the GPU
twin alone, read without try/catch. Under static hosting all 42 apps share one
origin, so the second twin to adopt the documented "sim settings persist"
pattern silently restores another twin's state. (`twin-reading-level` is shared
deliberately and correctly; the 18 lab keys are properly namespaced.)

**Do.** Point `.an-error` at `--dell-error` in the shared skin. Add a twin-ui
`<BackendDown>` that distinguishes a network failure from an HTTP status, names
the port, shows the start command, offers Retry, and knows when the page is a
static build. Promote `ErrorBoundary` to twin-ui and wrap all 42. Add a
`twinStorage(component)` helper that prefixes keys and wraps access in
try/catch.

**Done when.** Error text measures ≥4.5:1; stopping a backend shows a sentence
a reader can act on plus a working Retry; every storage key is either
`twin-reading-level` or component-prefixed, asserted by a test.

---

## Tier 4 — The cost of 42 copies

### 13. Finish the twinkit consolidation: models, routes, and the leveling test — M

**Problem.** `twinkit` has already absorbed leveling, the app factory and the
trace invariants, and done it well — all 42 `leveling.py` are 47-line shims with
one hash. Three large seams remain.

- **Models.** 17 physics components each redeclare `Constant`, `Validation`,
  `SimEvent`, `LogEntry` (identical but for the tick field name), and 9 redeclare
  `Explain`, 7 `GuidedScenario`. `def value(name)` is verbatim in all 17
  `constants.py`. Separately, 24 narrative twins each redeclare `Photo` and
  `SourceLink` (byte-identical), and 23 redeclare `CatalogOption`,
  `CatalogCategory` and `UseCase` — the category hashes differ only by a
  trailing comment. That is ~120 duplicate class definitions.
- **Routes.** `make_app` stops one step short of what components hand-write:
  `/api/anatomy` 41 times, `/api/scenarios` 27, `/api/catalog` 24,
  `/api/usecases` 24, `/api/explain` 18. `/api/tour` is byte-identical in 24 of
  25. The lab grader `grade_scenario` is byte-identical from `def` to EOF in 17
  of 18.
- **The leveling test.** 42 near-copies, 5,073 lines, 33 hashes; eight test
  function names appear in all 42; two components differ by a single trailing
  comment.

**Do.** Add `twinkit/physics.py` and `twinkit/catalog.py` for the model layer;
extend `make_app` with optional `anatomy=`, `catalog=`, `usecases=`, `explain=`,
`scenarios=`, `tour=`, `labs=` kwargs following the existing `profiles=` pattern,
plus `twinkit.labs.make_grader(...)`; and add
`assert_leveling_invariants(leveling, surfaces=[...])` so each component keeps a
~15-line file naming its surfaces. Do it as three mechanical commits, not one.

**Done when.** Those class definitions exist once; `*/backend/app/main.py` drops
~600 lines; `cat */backend/tests/test_leveling.py | wc -l` is under 900; the
suite is still green at 6,446 tests. Verify the leveling helper by un-leveling
one component and watching it fail.

### 14. Finish the twin-ui migration and collapse 42 stylesheets — M

**Problem.** The shared shell exists and is barely adopted: `TwinLayout` is used
by **2 of 42** apps, `Timeline` and `MetricReadout` by 3 each, `ControlPanel` by
15 — leaving 25 hand-written `*Controls.tsx` and 26 `*Counters.tsx`. Meanwhile
`level.ts` and `LevelControl.tsx` are byte-identical across all 42 (one hash
each) and twin-ui does not even export them. The stylesheets are 27,510 lines
across 42 files; a rule-block analysis found **101 blocks identical in ≥35 of
the 42 files — 4,133 duplicated rule copies**, including every base rule from
`body` to `.btnrow`. `shell.css:3` already names this as "the next step rather
than this one".

Adjacent and cheap: 42 per-frontend `package-lock.json` files and 42 real
(unhoisted) `node_modules` totalling **2.9 GB**, all pinning the same React,
Vite and TypeScript; and each hosted twin bundles its own React, so a visitor
browsing five twins on one origin downloads React five times.

**Do.** Move `level.ts` and `LevelControl.tsx` into twin-ui verbatim and delete
the 84 copies. Promote the ≥35-file rule blocks into `skin.css`. Migrate the
remaining 40 `App.tsx` onto `TwinLayout` (which also delivers item 11's
landmarks for free). Delete the per-frontend lockfiles and install once from the
root. Emit React as one shared vendor chunk at the site root.

**Done when.** No `level.ts` or `LevelControl.tsx` under `*/frontend/src`; no
rule block is identical across more than ~5 stylesheets; total stylesheet lines
under ~10k; `site/` contains one React chunk.

---

## Tier 5 — Teaching

### 15. The 54 graded labs are invisible to the course — M

**Problem.** 18 apps ship labs with scoring, hints and reference solutions, and
the course links **none of them**. `course.js` has link kinds `tour`, `phase`,
`scenario`, `step`, `root`, `setup` and `lesson` — there is no `lab` kind at
all. So a learner finishes the liquid-cooling module having *watched* PhysicsCDU
run a warm-water day, and is never told that PhysicsCDU will grade them on
building a loop that survives one. This is the largest gap between what exists
and what a learner is offered.

**Do.** Add a `lab` link kind rendering a "now do it" block after the checks,
pointing at the `#lab=<id>` deep link the panel already honours. Extend
`Learn/tests/test_links.py` to pin lab ids by AST, exactly as it already pins
scenario ids. Carry the lab's best score into the progress object so a module
can be "watched" or "passed".

**Done when.** Every module whose twins include a labs-bearing app links at
least one lab; the course home distinguishes watched from passed.

### 16. Nothing is graded, and progress dies with the browser profile — M

**Problem.** `Learn/README.md:97` states "Nothing is graded" as a design choice.
The only self-check is a pair of self-marked `Got it` / `Missed it` buttons, so
a learner can complete all 12 modules by clicking Reveal twelve times and
Got-it forty times. The predict questions already carry options and an answer
index, so the data for real scoring is already in `course.js` — it is thrown
away. Separately, all state lives in `localStorage` with no export and no
import, in a course its own design doc sizes at 6–8 hours. A learner who starts
at work and continues at home starts over.

**Do.** Record correct-on-first-try for the predict question that already grades
itself. Give the check questions the same options/answer shape. Add a per-track
assessment drawn from the modules' own items with a pass threshold, and a
completion page naming the track, date, modules and lab scores, generated
client-side and printable. Add "copy my progress" / "paste progress" — one
versioned blob covering the course key, reading level and lab bests.

**Done when.** A track shows a score rather than a count; a learner who reveals
without answering cannot reach a pass; exporting on one machine and pasting on
another reproduces module status, lab scores and reading level.

### 17. Ask a question inside each tour — M

**Problem.** 25 twins ship tours, and `TourStep` has no field for a question:
`grep -E "question|quiz|predict|choice" twinkit/tour.py` returns nothing. The
spec frames a tour as "a video-like experience", and the course does the
predicting elsewhere — but most people who arrive via `scripts/dev.sh <name>`
meet the tour directly, where the signature beat plays past without the viewer
ever committing to an answer.

**Do.** One optional field on `TourStep`: a prompt, options, an answer and the
reveal, honoured by the player as a pause. Author it only on each twin's
signature step — 25 questions, and the prose largely exists already as that
module's predict question in `course.js`.

**Done when.** Every twin's signature step carries a prompt; the player blocks
advance until the viewer commits; the tour test pins it.

### 18. No glossary, no search, and no way to carry a concept out of the building — M

**Problem.** Two halves of one gap. First, `find -iname "*glossar*"` returns
nothing and nothing in `Learn/` searches. CLAUDE.md commits per twin to
"spelling out vocabulary on first use" — but *first use* is scoped per twin, so
a learner meets "incast" in three modules with no single place to look it up.
Second, and more consequential: a grep across every `.md`, `.py`, `.tsx` and
`.html` finds **zero** mentions of NetApp, Pure Storage, Ceph, VAST, Weka,
Arista, Juniper or HPE. The only competitor name is Nutanix, and every instance
is inside `DellPrivateCloud` because Dell resells it. So a learner finishes able
to say "PowerScale has one namespace" with no handle on *scale-out NAS* as a
category and no vocabulary that survives leaving Dell's website. The twins
already do the hard half — every "one idea" in the collection is a concept, not
a SKU. They are just filed under product names.

**Do.** Generate a glossary from the twins' own prose, keyed by the twin that
introduces each term, with a filter box and a test that every term the course
uses is defined. Add `docs/CONCEPTS.md` and a `#concepts` page: per row, the
vendor-neutral name, the twin that teaches it with a deep link to the exact
step, two or three named non-Dell systems making the same or the opposite
trade, and one sentence on why a vendor would disagree. Add an honest framing
line to the README and root index: this is one vendor's catalog, chosen because
Dell publishes enough detail to simulate.

Do **not** attempt multi-vendor simulation. Competitors' internals cannot be
sourced to the standard this repo holds itself to, and trying would break the
"every constant carries a source" discipline that makes the collection
trustworthy.

**Done when.** Every built twin's one idea appears in the concept table with a
generic name and ≥1 named non-Dell counterpart; a glossary term is one click
from any module; a test fails on an undefined course term.

### 19. A foundations track — the reasoning under the hardware — L

**Problem.** Counted in `course.js`: "capacity planning" 0, "virtualiz*" 0,
"subnet" 0, "TCP" 0, "troubleshoot" 0, "TCO" 1, "container" 2. Against "IOPS"
18 and "packet" 16 — so the vocabulary is present and the fundamentals under it
are assumed. The sharpest case: PhysicsAIFactory computes `$/Mtok` as one of six
headline instruments, and the course never teaches cost reasoning, so the
capstone's most decision-relevant number arrives unexplained. The
`what-goes-wrong` track is now ten failure stops with no *method* taught.

**Do.** Not new twins — a short track built from twins that already demonstrate
the idea: queueing and latency (PhysicsStorage's 1/(1−ρ) knee, already pinned),
cost and TCO (PhysicsAIFactory's `$/Mtok`, PhysicsFleet's consumption
crossover, PhysicsLifecycle's carbon ledger), capacity planning (PowerScale's
`usedPercent` fall at node-add, PhysicsDataDomain's forecast), and a
troubleshooting method that the ten failure stops then exercise — form a
hypothesis, find the instrument that discriminates, check it.

**Done when.** A `foundations` track exists with modules for queueing, cost and
capacity; the failure track opens with an explicit method.

### 20. Give the narrative twins something to do — L

**Problem.** Of the 25 twins with tours, exactly one (`DellAlienware`) also has
labs. The other 24 — PowerStore, PowerFlex, CyberDetect, FortZero, XE9712,
IR7000, the whole narrative spine — are watch-only. This is structural: they
serve a fixed trace with no scenario to build, so there is no input surface to
grade. But Alienware proves it is not impossible, and the R760 pair shows the
shape.

**Do.** Two tiers. Cheap and broad: a "read the trace" activity — the learner is
asked to find the step where an invariant is established ("find where the vault
is sealed relative to the attack") and answers with a step number, graded
against the engine's own trace, using the `#step=N` machinery that already
exists. Expensive and deep: give the highest-value narrative twins a scenario
surface following the Alienware precedent, after which the existing lab recipe
applies unchanged.

**Done when.** Every core-spine module has at least one gradeable activity, and
a test pins each graded step number against the engine's trace.

---

## Tier 6 — Reach

### 21. Nothing is published — L

**Problem.** The collection is localhost-only. No `.github/`, no `pages` job in
`.gitlab-ci.yml`, `/site/` is gitignored on purpose, the README has zero images
and zero badges, and there is **no LICENSE**, so even a visitor who finds the
repo has no permission to use it. The machinery is built and half-rolled-out:
the static build runs the real engines under Pyodide with byte-identical
answers, and it is piloted on 2 of 42 components. Meanwhile the root
`index.html` catalog — the project's front door — lists 27 Dell components and
**zero** of the 16 physics apps, and its prose says "eight" specs where
`components.json` says seven. Every other catalog in the repo is generated from
`components.json`; this one is hand-typed.

**Do.** Finish the static conversion across all 42, add a Pages job on both
remotes, commit a LICENSE (paired with a NOTICE: trademarks belong to their
owners, figures are illustrative and not vendor-measured, photos are credited
per `RESEARCH_ASSETS.md`), generate the index's card list from `components.json`
with a status filter, and put three screenshots and the live link at the top of
the README.

**Done when.** A public URL serves the root index, the course, the CustomerSetup
pages and ≥30 twins with working traces; a test asserts the index card count
equals the non-archived component count; CI publishes on merge.

### 22. Triage the seven scaffolds and build the two that fill concept gaps — M

**Problem.** Seven `initial_spec.md` files with reserved ports, written
2026-07-24/25, none built. They inflate the component count to 49 when 42 are
real and show seven rows of `—` in every generated table. Four of them describe
ideas that later work shipped under another name: XE7745 is already a selectable
personality inside PhysicsCompute; AutomationStudio's blueprints overlap
NativeEdge's blueprint pillar; MDR is a sixth resilience twin beside
PhysicsResilience's decision-time model; TelecomBlocks is covered by
PhysicsLifecycle and PhysicsXR. `components.json` already declares an `archived`
status with no members.

Two are worth building. **DellAPEX** is the only spec that fills a *concept* gap
rather than a product gap: no catalog model in 49 components has a price field,
and case-sensitive `grep "TCO"` finds exactly one real mention repo-wide. The
collection teaches how every machine works and never why anyone buys one.
**DellObjectScale** completes the Exascale rack (block ✓, file ✓, object ✗) and
argues rather than repeats. **DellAIDataPlatform** is genuinely uncovered but
its real product has moved fastest since July, so re-research before building.

**Do.** Build APEX (hero counter: the crossover month; identity: the two curves
cross exactly once) and ObjectScale. Archive the four with a one-paragraph
"superseded by" header in each spec and release their port reservations. Hold
AIDataPlatform.

**Done when.** `components.json` has ≥4 `archived` rows, each archived spec says
where its idea now lives, and a built APEX asserts its crossover in both
directions.

### 23. Rebalance what the collection teaches about — M

**Problem.** By family: storage is 9 of 49, and counting storage-adjacent
resilience it is 12 of 49 — 24% — with five twins arguing variants of the same
argument (controller, no controller, no volume, no tree). Against that, `client`
is 4 and two of those are physics modules, so Dell's actual commercial client
line (Dell Pro, Latitude, OptiPlex, Precision workstations) has zero twins and
zero specs. **Services is a total absence**: ten named service families on
Dell's site, zero components — despite services being where the real failure
modes live (ProDeploy is literally NativeEdge's trace performed by humans). VDI,
a top-level Dell family, is absent entirely. `LOOP_LOG.md`'s own closing note
flags all of this.

**Do.** A moratorium on new storage twins, and spend the next two builds on a
commercial-client twin whose one idea is *service life, not performance* (it
pairs with PhysicsDisplay's embodied-versus-use carbon test), and a
deployment-services twin: the same rack drawn as a project plan, whose hero
counter is **weeks of calendar time** — the thing no twin measures and every
buyer does.

**Done when.** No family exceeds 15% of built components, and client plus a new
services family hold ≥6 built components between them.

---

## Tier 7 — Legibility

### 24. CLAUDE.md has outgrown its job — M

**Problem.** 1,248 lines, ~50,000 tokens, read in full at the start of every
agent session. **981 of those lines (79%) are per-component prose** — and every
one of those 42 components also has its own README. The text is not duplicated
verbatim, which is worse: two independently worded descriptions of each twin
must be kept true in parallel. Structurally it is a wall, with ordinal section
titles ("twenty-second component") that do not help lookup and section 53 at
line 1224. Three subsystems that now exist on disk — static hosting, labs, and
`compose/` — appear in it **zero** times.

**Do.** Make it a router of ~300 lines: the generated component table, the
invariants, the testing approach, reading levels, tours, failure scenarios,
smoke tests, static hosting, labs, compose, the port registry, repository state,
and an index of `docs/`. Move each per-component section into that twin's README
under a consistent `## For agents` heading, leaving a pointer in the table.
Extend `gen_docs.py` to verify the pointers so the router cannot drift. Add a
"where to look" block at the top.

**Done when.** CLAUDE.md is under 320 lines; every removed section is one link
away; `gen_docs.py --check` passes; each of the three new subsystems is
mentioned.

### 25. Land the work: main, the docs' truth, and the junk — S

**Problem.** Four small things that together decide whether anyone else can pick
this up.

- **`main` is 61 commits and ~40 components behind.** Its tip is "Add CloudIQ
  and PowerMax digital twins" — component #9 of 49. Anyone cloning either remote
  gets a nine-component snapshot matching no documentation, and
  `deploy-frontend` is gated on the default branch, so it could never have run.
- **Planning docs describe finished work as future.** All five items of
  `IMPROVEMENT_SPEC_2026-09-11.md` are done and it still reads in the
  imperative. `TWIN_IMPROVEMENTS.md` has item 1 struck through while items 2–7
  and 10 also shipped. `ACTIVE_TWIN_SPEC.md` gets it right with a `**Status:**`
  header — that is the pattern to copy.
- **`docs/LIFECYCLE.md` disagrees with the generated table** about whether
  PowerScale is `partial`, because its counts are hand-written prose outside the
  generated markers.
- **Junk at the root:** a 2.1 MB `alienware.jpg`, a 340 KB skill tarball,
  untracked screenshots, a root `test-results/`, and an `undefined/` directory
  holding one PNG — a tool was handed a literal JavaScript `undefined` as its
  output path, and `.gitignore` covers none of them.

**Do.** Land the in-flight work as commits, run the full gate, then fast-forward
`main` on both remotes and make it the working branch — a 61-commit, 747-file
PR would not be meaningfully reviewed, so the fast-forward is the honest option.
Give every planning doc a `**Status:**` header and move the finished ones under
`docs/history/`. Generate LIFECYCLE's counts. Move the images to `docs/assets/`,
delete the tarball and the junk directories, extend `.gitignore`, and find
whatever writes `undefined/`. Add `LICENSE`, `CONTRIBUTING.md` (the four
`--check` generators, root `pytest`, `dev.sh`, picking ports, the `L(...)` rule,
engines stay pure, branch policy), issue templates, and a "first 10 minutes"
block plus a `scripts/bootstrap.sh` so a clean clone reaches a running twin in
two commands.

**Done when.** Both remotes' `main` equals the work tip; `head -5` of every
planning doc shows a status; no two files state different statuses for one
component; `git status --porcelain` shows only real source files; a newcomer
reaches a running twin from the top of the README alone.

---

## Considered and not included

- **Refresh `CustomerSetup`.** Seven deployments, all researched on one day
  eight weeks ago, all large-scale, none in healthcare, manufacturing, retail or
  telecom, and none midmarket. Two already hedge renamed products (CyberSense,
  CloudIQ). Worth doing; it just ranks below everything above.
- **Extend `RESEARCH_ASSETS.md` to the physics suite.** It covers 25 of 42
  components and stopped at the end of the discovery loop. Its "pain points"
  sections are the only record of real operator complaints in the repo and
  nothing else reproduces them.
- **A component scaffolder.** Adding a component means 88 files plus three
  registrations that only fail later. Worth building *after* items 13 and 14
  shrink the per-component surface — and possibly not at all, if item 23's
  moratorium holds.
- **An instructor kit and a learner feedback link.** No facilitator notes, no
  timing, no preflight that checks which twins a module needs before the session
  stalls; and no way for a learner to report an ambiguous question.
- **Recorded tour narration.** Browser speech synthesis is serviceable; audio
  files are a polish item.
