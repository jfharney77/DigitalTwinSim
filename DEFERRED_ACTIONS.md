# Deferred actions

The improvement spec (`IMPROVEMENT_SPEC_2026-09-11.md`) asks for some things
that delete or move files, or change deployment config. This pass was run
under a "stage, don't destroy" rule, so those steps were not taken. Everything
safe that leads up to them is done and committed. Each item below says what
the action is, why the spec wants it, the commands, and what to check first.

Run the whole suite before and after any of these:

```bash
pytest                                        # repo root, ~30 s
python3 scripts/gen_components.py --check
python3 scripts/gen_docs.py --check
python3 scripts/gen_root_pytest.py --check
```

## 1. Delete the per-component copies of shared frontend code (spec #2)

**What.** `packages/twin-ui` holds the tokens, the skin and the four shell
components, and all 42 frontends import it. Some whole files are still copied
per component:

- `src/level.ts` and `src/components/LevelControl.tsx`: byte-identical in all
  42 frontends.
- `src/components/Timeline.tsx`: byte-identical in 8 physics apps
  (`PhysicsClient`, `PhysicsCompute`, `PhysicsData`, `PhysicsFabric`,
  `PhysicsFleet`, `PhysicsLifecycle`, `PhysicsResilience`, `PhysicsStorage`).
  It is not the same component as twin-ui's `Timeline`.
- Playback controls that do not use twin-ui's `ControlPanel` yet (12):
  `DellAlienware` `PowerControls`, `DellCyberDetect` `DetectControls`,
  `DellExascale` `DataControls`, `DellIR7000` `ThermalControls`,
  `DellNativeEdge` `OnboardControls`, `DellPowerEdgeXE9680` and
  `DellPowerEdgeXE9712` `PowerOnControls`, `DellPowerProtect`
  `LifecycleControls`, `DellPowerSwitchSN6000` and `DellQuantumX800`
  `FabricControls`, `DellVxRail` `FirstRunControls`, `GPU` `Controls`.

**Why.** Spec #2: "delete the per-project copies". A copied file drifts the
same way the copied CSS did.

**Commands.** Move first, then delete. For `level.ts` and `LevelControl.tsx`:

```bash
cp DellPowerMax/frontend/src/level.ts packages/twin-ui/src/level.ts
cp DellPowerMax/frontend/src/components/LevelControl.tsx packages/twin-ui/src/components/LevelControl.tsx
# export useLevel / LevelControl from packages/twin-ui/src/index.ts and fix the
# relative import inside LevelControl.tsx, then repoint every consumer:
grep -rl --include=*.tsx --include=*.ts -E "from \"(\./|\.\./)(components/)?(level|LevelControl)\"" */frontend/src
# after each file imports from "@twinsim/twin-ui" instead:
git rm */frontend/src/level.ts */frontend/src/components/LevelControl.tsx
for d in */frontend; do (cd "$d" && npm run build) || echo "BUILD FAILED: $d"; done
```

Follow the same pattern for the 8 physics `Timeline.tsx` copies, under a
different export name (for example `ScrubberTimeline`) so it does not collide
with the shell `Timeline`. The 12 controls are wrappers to rewrite, not files
to delete. The 13 that already wrap `ControlPanel` show the shape.

**Check first.** `level.ts` holds module-level state and a `localStorage` key
(`twin-reading-level`) that `CustomerSetup/shared/setup.js` also reads. One
shared module keeps one store per page, which is the same as today, but check
that the key name does not change. Build all 42 frontends, not a sample.

## 2. Move archived components under `archive/` (spec #5)

**What.** Spec #5 wants archived components out of the top level.
`components.json` has no `archived` component today, so nothing needs to move
now. The seven `scaffold` components (spec-only directories) are the likely
candidates if the owner decides not to build them: `DellAIDataPlatform`,
`DellAPEX`, `DellAutomationStudio`, `DellMDR`, `DellObjectScale`,
`DellPowerEdgeXE7745`, `DellTelecomBlocks`.

**Why.** "The top level of the repo is a list of components someone would
actually demo."

**Commands**, per component, for example `DellMDR`:

```bash
mkdir -p archive
git mv DellMDR archive/DellMDR
# in scripts/gen_components.py, EDITORIAL["DellMDR"] status -> "archived"
python3 scripts/gen_components.py && python3 scripts/gen_docs.py
grep -rn "DellMDR/" --include=*.md --include=*.html --include=*.py . | grep -v node_modules
pytest
```

**Check first.**
- `gen_components.py` scans `archive/` and refuses a status/location mismatch,
  so change the status in the same commit as the move.
- References by path: all seven are named in `CLAUDE.md` and `LOOP_LOG.md`,
  and `DellTelecomBlocks/` in `PhysicsXR/README.md`. Update those links.
- Ports: scaffolds have no `ports.json` entry, so
  `CustomerSetup/tests/test_links.py::test_ports_registry` is unaffected. For
  a built component, that test scans top-level directories only. Remove the
  component's `ports.json` entry, and add `archive/` handling to the test if
  its ports should stay reserved.
- An archived backend that still has tests: the root `pytest` would still
  collect it under `archive/`, but `scripts/gen_root_pytest.py` only covers
  `*/backend`, so it would run without a claiming conftest and collide on
  `app`. Add `archive` to `norecursedirs` in `pytest.ini` and remove it from
  the `SHARD` list in `.gitlab-ci.yml`.

## 3. Tidy the loose files at the repo root (spec #5)

**What.** Seven files at the top level are not components: `alienware.jpg`
(2.2 MB), `poweredger760.webp`, `powerstore1.webp` through `powerstore4.webp`,
and `dell-clean-design.tar.gz`. The tarball is an archive of a Claude skill
directory (`home/john/.claude/skills/dell-clean-design/`), not project code.

**Why.** Same goal as item 2: the top level should show live work.

**Commands.**

```bash
mkdir -p docs/assets
git mv alienware.jpg poweredger760.webp powerstore1.webp powerstore2.webp \
       powerstore3.webp powerstore4.webp docs/assets/
# the tarball: keep it outside the repo if you still want it, then
git rm dell-clean-design.tar.gz
```

**Check first.** `RESEARCH_ASSETS.md` refers to `alienware.jpg` by name.
`DellPowerStore/backend/app/anatomy.py` and
`PhysicsStorage/backend/app/media.py` use `/powerstore1.webp`, but that URL is
served from each frontend's own `public/` copy, not the root file. Confirm
with `ls DellPowerStore/frontend/public` before moving anything. Keep the
tarball if the skill is not saved anywhere else.

## 4. Repair or remove the frontend deploy jobs in `.gitlab-ci.yml`

**What.** `validate-frontend` runs `cd frontend` at the repo root, and
`deploy-frontend` pushes to Railway. The repo root has no `frontend/`
directory, so `validate-frontend` fails on every pipeline, and the deploy
never runs. These jobs predate this pass. The new `component-index`,
`root-pytest-conftests` and `pytest` jobs are in the same stage and do not
depend on them.

**Why.** The spec asks for CI that runs the suite. A stage that always goes
red hides whether the new jobs pass.

**Commands.** Either point the jobs at a real frontend, for example
`cd GPU/frontend`, or remove both jobs:

```bash
# edit .gitlab-ci.yml: delete the validate-frontend and deploy-frontend jobs,
# and drop "deploy" from stages if nothing else uses it
```

**Check first.** Whether the Railway service `DigitalTwinSim-frontend` is
still live and what it was deploying. Removing the job stops future deploys.
Do not touch the Railway service itself from here.
