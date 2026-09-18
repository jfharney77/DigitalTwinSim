# DellCircularDesign

## What's missing

- The root `CLAUDE.md` has no DellCircularDesign section yet.
- No `CustomerSetup/` page uses the twin yet.

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

The trace endpoint is `GET /api/lifecycle`. Trace prose is authored at all
five reading levels. A narrated guided tour lives at `#tour` (`GET /api/tour`,
`backend/app/tour.py`); its signature beat, `#tour/disassembly`, pins the
recover step, where the mass ledger opens.

## Test and build

```bash
pytest DellCircularDesign                     # from the repo root
cd DellCircularDesign/frontend && npm run build
```
