# Graded labs — the recipe

A guided scenario is watch-mode: the app sets the dials and narrates. A **lab**
is do-mode: a goal, constraints, the learner builds a `Scenario` with the
app's existing controls, the pure engine runs it, and a **pure scoring
function** grades the trace.

Pilot: `DellPowerEdgeR760Thermal/` (three labs). Shared code: `twinkit/labs.py`
(models + `grade()`), `twinkit.testing.assert_lab_invariants`. This document is
the exact recipe for every other scenario-driven physics app (`Physics*/`).

## The split

| Piece | Lives in | Knows about |
|---|---|---|
| `Lab`, `LabGoal`, `Criterion`, `Objective`, `LabResult`, `grade(lab, metrics)` | `twinkit/labs.py` | nothing app-specific; no FastAPI |
| `measure(scenario, trace, summary, validations) -> dict[str, float]` | `<App>/backend/app/labs.py` | the app's `SimState` |
| `LABS`, `REFERENCE_SOLUTIONS`, `GAMING_ATTEMPTS`, `grade_scenario(lab_id, scenario)` | `<App>/backend/app/labs.py` | the app's presets and Explain ids |
| `GET /api/labs`, `POST /api/labs/{id}/grade` | `<App>/backend/app/main.py` | HTTP, reading level |
| `labs.ts`, `labs.css`, `components/LabPanel.tsx`, six small edits to `App.tsx` | `<App>/frontend/src/` | rendering only — no rules |

`app/labs.py` is pure exactly like `engine.py`: no FastAPI, no IO, no clock,
no randomness, AST-checked by the invariants helper. A `Lab` dumped to JSON
plus a metrics dict is the whole grading specification, so a static-hosting
build can grade in the browser: port `measure()` (one loop over the trace) and
`grade()` (forty lines) and feed them the same `GET /api/labs` JSON.
`test_grading_a_lab_needs_only_data` pins that contract.

## The two rules that keep a lab honest

1. **Delivered work is always a criterion.** "Hold the CPU under 90 °C" is
   passed by an idle server. Every lab carries at least one criterion with
   `guards_work=True` — a floor on useful output — and that metric must go to
   zero when the system is idle, throttled, tripped or dark. Make it a **rate
   averaged over the whole run** (dark ticks count as zero), never a total: a
   total is gamed by a long run at low load. In the pilot,
   `workRateW = mean(util × (1 − throttle loss) × sockets × TDP)`. Label the
   proxy illustrative.
2. **Every constraint is a criterion.** "At 35 °C inlet" is not a locked
   control, it is `minInletC >= 35`, measured from the trace. The grader never
   trusts the client about what the learner did. The same goes for run length
   (`durationS >= N`), "a fan must fail early" (`firstFanFailureS <= 100`),
   "keep the redundant pair", "do not strip the build" and "no validation
   errors".

## Scoring

`grade()` is fixed across apps. All criteria pass → `score = 70 + 30 × f`,
where `f` is how far the lab's `Objective` metric sits between `worst` (0) and
`par` (1), linear, clamped. Any criterion fails → `score = floor(69 × passed
weight / total weight)`. So `score >= 70` iff `passed`, and the objective never
rescues a failed run. Set `par` at the reference solution's value (the helper
requires the reference to earn ≥ 0.9 of the band) and `worst` near where a
just-passing run lands.

## Backend steps

1. **Choose three lessons, rising difficulty (1, 2, 3).** Each needs a genuine
   tension between two equations the app already explains, and an "aha" a
   learner finds with the existing controls. Pilot: PSU sizing vs the
   one-survivor peak; airflow vs watts per unit of work at 35 °C; the turbo
   boost as the thing that throttles on five fans (99% beats 100%).
2. **Explore before you author.** Script the engine over a grid of configs and
   print the candidate metrics. Pick thresholds the naive start fails, the
   obvious greedy attempt fails *for the instructive reason*, and at least one
   reasonable solution passes with margin.
3. **Write `measure()`.** Return camelCase keys (they go over the wire in
   `LabResult.metrics`). Replay timed `set-workload` events exactly as the
   engine does when computing work. Round to instrument precision.
4. **Write the labs.** Every `Criterion` and the `Objective` cite an
   `explain_id` from the app's Explain entries and carry that entry's
   `equation` **verbatim** (the pilot tests the equality). `why`, the goal
   statement, each constraint, `delivered_work` and each hint go through the
   app's `L(standard=, novice=, expert=)` — levels 1, 3 and 5 authored, novice
   longer than expert, numbers identical at every level. Two to four hints,
   progressive: where to look → what the tension is → the move.
5. **`start`** is `Scenario(...).model_dump(by_alias=True)`: it sets the stage
   (room, duration — useful where the UI has no duration control) and is the
   **naive default, which must fail**.
6. **`REFERENCE_SOLUTIONS`** (one passing scenario per lab) and
   **`GAMING_ATTEMPTS`** (named scenarios that must fail; a zero-load attempt
   is mandatory; add one per constraint a learner might dodge: cool the room,
   short run, long run at low load, single PSU, strip the build, do the hard
   part at the last tick, idle first and load later). Both stay server-side.
7. **`grade_scenario(lab_id, scenario)`**: `simulate` → `validate` →
   `measure` → `twinkit.labs.grade`. `KeyError` on an unknown id.
8. **Routes** (append to `main.py`; resolution to a reading level happens here
   and only here):

   ```python
   @app.get("/api/labs", response_model=list[Lab])
   def get_labs(level: int = Level): return leveled_all(LABS, level)

   @app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
   def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level):
       if lab_id not in LABS_BY_ID: raise HTTPException(404, ...)
       return leveled(grade_scenario(lab_id, scenario), level)
   ```

   If the app pins its API surface in a snapshot test, update it deliberately.
9. **Tests** — `backend/tests/test_labs.py`:

   ```python
   assert_lab_invariants(
       LABS, grade_scenario, REFERENCE_SOLUTIONS,
       explain_ids=[e.id for e in EXPLAINS], registry=registry(),
       parse_start=Scenario.model_validate,
       gaming_attempts=GAMING_ATTEMPTS, module=labs_module,
   )
   ```

   It pins: kebab-case unique ids, rising difficulty, a `guards_work`
   criterion, a real explain id + equation on every line, objective par/worst
   on the right sides, prose registered at levels 1/3/5, ≥ 2 distinct hints,
   reference passes (and earns ≥ 90% of the objective), `start` fails, score
   agrees with `passed`, grading deterministic, every gaming attempt fails,
   module pure. Add the app's own: work is zero at idle, a tripped system
   stops earning, every named metric is measured, the lab's specific "aha"
   stays true in the engine (pilot: 100% throttles, 99% passes, and the *only*
   failing line is `no-throttle`), the JSON round-trip, and the API (labs
   listed, grade works, 404, no solutions leaked).

## Frontend steps

Copy from the pilot and rename the localStorage key (`<app>-lab-best`):

- `src/labs.ts` — wire types, `fetchLabs()`, `gradeLab()`, `labFromHash()`,
  guarded `readBest()`/`recordBest()`.
- `src/labs.css` — scoped under `.app.dell`; no dividers, eyebrows, numbering
  or highlights.
- `src/components/LabPanel.tsx` — lab list with difficulty dots and best
  score, goal card, **Run and grade**, **Reset to the lab's start**,
  progressive hints, results (score, verdict, objective bar, one `<details>`
  per criterion showing measured vs needed, the equation, the leveled `why`,
  and a button into Explain mode). Failed lines open by default. A reading
  level change re-grades the same scenario (deterministic, so only the words
  change). A "scenario has changed since this grade" note marks a stale result.
- `App.tsx` — labs state held by id; `fetchLabs()` in a `[level]` effect; a
  **Labs** nav button; `#labs` and `#lab=<id>` deep links (apply once on
  arrival, follow `hashchange`); `loadLabStart()` writes the lab's start into
  the *ordinary* scenario state; render `<LabPanel>` above the normal grid so
  the normal controls are the lab's controls. The playback clock stays where
  it was.
- `frontend/smoke.json` — two routes: `#labs` (panel and lab titles visible)
  and `#lab=<first id>` with `play: {click: ".lab-run", watch: ".lab-results"}`.

## Checklist

- [ ] `pytest <App>` and `pytest twinkit` green; `npm run build` clean
- [ ] `scripts/smoke.sh <App>` green, including the two lab routes
- [ ] start fails, reference passes at ~100, every gaming attempt < 70
- [ ] every criterion cites an Explain entry and its equation verbatim
- [ ] levels 1/3/5 on every prose block; thresholds identical across levels
- [ ] the work proxy and the scores are labeled illustrative in the UI
- [ ] reference solutions never appear in any API response
