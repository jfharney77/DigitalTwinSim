# DellCircularDesign

## What's missing

- The trace steps in `backend/app/engine.py` are not wrapped in `L(...)`, so they read the same at every reading level (the anatomy overview is leveled).
- `initial_spec.md` still opens with "Status: spec only", and the root `CLAUDE.md` has no DellCircularDesign section, although the backend and frontend are built.
- There was no README until this one, and no `CustomerSetup/` page uses the twin yet.

Status in `components.json`: **partial**. See [`docs/LIFECYCLE.md`](../docs/LIFECYCLE.md).

A digital twin of Dell's circular design and Asset Recovery Services. Every
other twin's trace ends at a steady state. This one closes: a product's
materials go through manufacture, service, repair and recovery, and come back
as the input to the next generation. The conservation invariant is the IR7000
heat balance applied to matter. Every kilogram entering the loop is accounted
for as reused, reclaimed or lost, and `tests/test_engine.py` asserts it.

Phase order: `materials → manufacture → ship → deploy → serve → repair → extend → recover → sort → reborn`.

## Run it

```bash
scripts/dev.sh DellCircularDesign             # from the repo root
# or
./DellCircularDesign/scripts/start_all.sh     # backend :8024, frontend :5197
```

The trace endpoint is `GET /api/lifecycle`.

## Test and build

```bash
pytest DellCircularDesign                     # from the repo root
cd DellCircularDesign/frontend && npm run build
```
