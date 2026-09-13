# DellPowerScale

## What's missing

- The 8 trace steps in `backend/app/engine.py` are not wrapped in `L(...)`, so they read the same at every reading level (the anatomy overview is leveled).
- There was no README until this one; the design notes live in `initial_spec.md` and the DellPowerScale section of the root `CLAUDE.md`.
- No product photos: the chassis map carries no `photo`, and none have been sourced with clean licensing.

Status in `components.json`: **partial**. See [`docs/LIFECYCLE.md`](../docs/LIFECYCLE.md).

A digital twin of Dell PowerScale running OneFS: scale-out NAS where every node
adds compute, networking and storage, and the cluster presents one file system
over NFS, SMB, S3 and HDFS. The one idea is that there are no volumes. Growing
the cluster means adding a node, never planning a migration, so the trace's
hero counters are `namespaces` (always 1) and `migrationsRequired` (always 0).

## Run it

```bash
scripts/dev.sh DellPowerScale                 # from the repo root
# or
./DellPowerScale/scripts/start_all.sh         # backend :8023, frontend :5196
```

The trace endpoint is `GET /api/namespace`.

## Test and build

```bash
pytest DellPowerScale                         # from the repo root
cd DellPowerScale/frontend && npm run build
```
