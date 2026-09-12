# Improvement Spec — DigitalTwinSim
**Date:** 2026-09-11

Twenty-six-plus hardware digital twins (GPU, PowerEdge, PowerMax, PhysicsFabric, …), each
a FastAPI pure-engine backend plus a React/Vite frontend in the Dell clean-design skin.
~600 Python files, ~570 TS/JS files, 461 test files, one CI workflow.

This is the largest project in the workspace, and every improvement below is about the
cost of having twenty-six copies of the same thing.

## 1. Extract the repeated backend into a shared `twinkit` package

**Problem.** Each component directory re-implements the same skeleton: `models.py`
(pydantic, camelCase JSON), `profiles.py`, `engine.py` with a pure `simulate()`,
`main.py` with `/api/health`, `/api/profiles`, `/api/simulate`. A fix to the camelCase
alias generator, the health route, or the trace-invariant test helper has to be applied
twenty-six times, and in practice is applied to three.

**Do.**
- Create `twinkit/` at the repo root: `twinkit.api.make_app(profiles, simulate)` returning
  a configured FastAPI app; `twinkit.models.CamelModel` base; `twinkit.testing.assert_trace_invariants`.
- Migrate three components first (GPU, DellPowerEdgeR760, DellPowerMax) to prove the
  abstraction, then the rest.
- A component's `backend/` should shrink to its domain model, its profiles, and its engine.

**Done when.** `/api/health` exists in exactly one place, and adding a twenty-seventh
component is a directory with an engine and a profile list.

## 2. Extract the shared frontend shell and design tokens

**Problem.** The Dell clean-design skin (flat white, `#0672CB`, `#D2D2D2` borders, Roboto,
2–4px radii, no eyebrows/numbering/dividers) is re-typed per frontend. Drift is already
visible between the older and newer components.

**Do.**
- Publish `packages/twin-ui/` as a local workspace package: the tokens as CSS custom
  properties in one stylesheet, plus `<TwinLayout>`, `<ControlPanel>`, `<Timeline>`,
  `<MetricReadout>` — the components every twin actually reuses.
- Convert the frontends to consume it via a workspace dependency; delete the per-project copies.
- Add a Storybook-or-equivalent page that renders every shared component, as the visual
  reference the design skill checks against.

**Done when.** Changing the Dell blue is a one-line edit that every component picks up.

## 3. Give the repo a component index and a single dev entry point

**Problem.** `CLAUDE.md` lists the components in prose. There is no machine-readable list,
no way to start an arbitrary twin without reading its README, and no way to see which are
finished versus scaffolded.

**Do.**
- Add `components.json`: name, directory, backend port, frontend port, status, one-line
  description, hardware family.
- Add `scripts/dev.sh <component>` that starts that component's backend and frontend on its
  declared ports, and `scripts/dev.sh --list`.
- Generate the component table in `CLAUDE.md` and `README.md` from `components.json` in CI,
  so the prose cannot drift from reality.

**Done when.** `scripts/dev.sh DellPowerMax` works from a clean checkout without reading
any documentation.

## 4. Make the 461 test files run as one suite with a shared invariant library

**Problem.** Tests are per-component and, as far as CI is concerned, mostly unrun. The
interesting property — a simulation trace is monotonic, conserves its budget, and is
deterministic under a seed — is restated per component with local helpers.

**Do.**
- One root `pytest.ini` with the component backends on the path; `pytest` at the root runs
  everything.
- Move the invariant assertions into `twinkit.testing` (see #1) and have each component's
  test file call `assert_trace_invariants(trace, profile)` plus its domain-specific checks.
- CI: run the full suite on a matrix sharded by component so wall-clock stays reasonable.

**Done when.** A single `pytest` at the root is green, and a new component gets invariant
coverage from four lines of test code.

## 5. Decide and document the lifecycle of half-built components

**Problem.** Twenty-six directories, one CI workflow, and no signal about which twins are
demo-ready. A reader — human or agent — cannot tell an abandoned experiment from the
flagship.

**Do.**
- Add a `status` field to `components.json`: `reference` (fully built, used as the pattern),
  `built`, `partial`, `scaffold`, `archived`.
- Move `archived` components under `archive/` so the top level shows only live work.
- For each `partial`, put a three-line "what's missing" block at the top of its README.

**Done when.** The top level of the repo is a list of components someone would actually
demo, and the archive is honestly labeled rather than silently rotting.
