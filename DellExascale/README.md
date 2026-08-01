# DellExascale — parallel-storage digital twin (thirteenth component)

A digital twin of **Dell Exascale Storage** and the **Lightning File
System** — the production form of Project Lightning, a parallel file system
built on PowerScale's OneFS using pNFS (parallel NFS) with a metadata
server and Flex Files layouts. Exascale is the rack that unifies the
engines: PowerFlex (block), PowerScale and Lightning (file), ObjectScale
(object), at roughly 6 TB/s per rack.

The **data** pillar of the AI Factory quartet in this repo — compute
(XE9712), cooling (IR7000), data (this), fabric (SN6000).

## The one idea

Every other storage twin here moves bytes through a controller, and that
controller's ceiling is the system's ceiling. A parallel file system
refuses that bargain: the client asks the metadata server **one** question
— where do this file's stripes live? — gets a layout, and then reads
straight from every data server at once with the metadata server out of the
path. Throughput becomes the *sum* of the servers rather than the *maximum*
of one. `test_engine.py` enforces exactly that, and `test_anatomy.py` even
pins the metadata server's geometry above the data-server band, because the
diagram is the lesson.

## What it shows

- **Data path** (`/`) — an AI job's data: mount, layout, parallel stripe
  fan-out, GPUs saturated at ~6 TB/s, checkpoint burst, tiering to object,
  steady training loop.
- **Inside the rack** (`/#anatomy`) — clients, fabric, the metadata server
  drawn above the path, four data servers with their NVMe, and the file /
  object / block protocol engines.
- **Components & options** (`/#components`) — platform, Lightning, data
  servers, media, object, block, client paths (GPUDirect, pNFS), fabric,
  management, services.
- **Use cases** (`/#usecases`) — feeding an eight-rack AI factory,
  replacing a legacy parallel file system at an HPC centre, consolidating
  three storage silos.

## Run

```
./DellExascale/scripts/start_all.sh   # backend :8011, frontend :5184
./DellExascale/scripts/stop_all.sh
```

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

## Key invariants (backend/tests/)

- Engine purity (AST-checked); the playback clock lives in `App.tsx`.
- Phase order `idle→mount→layout→stripe→feed→checkpoint→tier→steady` never
  regresses.
- **Metadata leaves the data path**: the `metadata` region is absent from
  every bulk-data phase, and active in exactly `mount` and `layout`.
- **Layout precedes data**: nothing streams before the client holds a
  layout, and the layout is never lost mid-job.
- **Throughput requires fan-out**: any nonzero throughput means all four
  data servers are streaming; zero servers means zero throughput.
- Data servers light in lockstep, each with its media; peak reaches
  48,000 Gbps (~6 TB/s); the checkpoint burst is the longest stage.

Counts, bandwidths, and timings are illustrative, anchored to Dell's
Lightning and Exascale material (see anatomy `sources`). A real rack holds
many more data servers than the four drawn.
