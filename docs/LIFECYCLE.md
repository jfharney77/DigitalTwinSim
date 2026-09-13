# Component lifecycle

Every top-level component directory has a `status` in `components.json`. The
status tells a reader, human or agent, whether a directory is something to
demo, something to finish, or something to leave alone. `scripts/dev.sh --list`
prints it, and the component tables in `CLAUDE.md` and `README.md` are sorted
by it.

The status is editorial: it lives in the `EDITORIAL` table in
`scripts/gen_components.py`, because reading the source cannot tell you whether
a component is the pattern the others follow or an experiment nobody finished.
Change it there, then run:

```bash
python3 scripts/gen_components.py   # rewrites components.json
python3 scripts/gen_docs.py         # rewrites the tables in CLAUDE.md and README.md
```

CI runs both with `--check`, so a status change that skips this step fails the
`component-index` job.

## The five statuses

| Status | Meaning | Rule |
|---|---|---|
| `reference` | Fully built, and the pattern new components copy. | Changes here should be made deliberately, because they propagate by imitation. |
| `built` | Fully built: backend, frontend, tests, reading levels, documentation. Demo-ready. | Its suite is green in the root `pytest`, and its frontend builds. |
| `partial` | Runs, but something a `built` component has is missing. | Its `README.md` opens with a `## What's missing` block of about three lines. `gen_components.py` refuses to write `components.json` otherwise. |
| `scaffold` | A spec with reserved ports and no code. | `scripts/dev.sh <name>` says so and points at the spec instead of failing. |
| `archived` | No longer maintained or demoed. | Lives under `archive/<name>/`, not at the top level. `gen_components.py` scans `archive/` and refuses a mismatch in either direction. |

## Where things stand

As of this document: 3 `reference`, 37 `built`, 2 `partial`, 7 `scaffold`,
0 `archived`. `components.json` is the live count.

The references are `GPU` (the pure-engine and trace pattern),
`DellPowerEdgeR760` (the chassis twin) and `DellPowerEdgeR760Thermal` (the
scenario-driven physics simulator).

The two `partial` components:

- `DellPowerScale`: built after the reading-level pass, so its trace steps
  read the same at every level.
- `DellCircularDesign`: built from its spec, but its trace steps are
  unleveled, its spec still says "spec only", and `CLAUDE.md` has no section
  for it.

The seven `scaffold` components are the specs the twin-discovery loop left
behind (`LOOP_LOG.md` has the table): `DellAIDataPlatform`, `DellAPEX`,
`DellAutomationStudio`, `DellMDR`, `DellObjectScale`, `DellPowerEdgeXE7745`,
`DellTelecomBlocks`. They are future work, not abandoned work. They stay at
the top level until someone builds them or decides not to, and in the second
case they become `archived` and move under `archive/`.

Nothing is `archived` yet, so no directory has moved. The procedure for
archiving a component, and the loose files at the top level that are not
components, are listed in `DEFERRED_ACTIONS.md` at the repo root. Moving
directories breaks relative links and port registrations, so every move there
is a reviewed step, not something a script does on its own.

## Changing a status

- `scaffold` to `built`: build it, add its `ports.json` entry, set the status,
  regenerate. The root `pytest` picks up its tests once
  `scripts/gen_root_pytest.py` has written its `backend/conftest.py`. Add it to
  the `SHARD` list in `.gitlab-ci.yml`; `gen_root_pytest.py --check` fails
  until you do.
- `built` to `partial`: add the `## What's missing` block to the top of the
  README first, or the generator will refuse.
- `partial` to `built`: close the gaps, delete the block, set the status.
- anything to `archived`: follow the archive steps in `DEFERRED_ACTIONS.md`.
