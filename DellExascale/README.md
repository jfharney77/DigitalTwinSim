# DellExascale — parallel-storage digital twin (thirteenth component)

A digital twin of **Dell Exascale Storage** and the **Lightning File
System**. Exascale (announced March 2026) runs PowerScale (file),
ObjectScale (object) and the Lightning File System (parallel file) as
software personalities on common PowerEdge servers; Dell targets PowerFlex
(block) for 1H 2027 and claims up to 6 TB/s of reads per rack on the
Lightning personality. Project Lightning produced two parallel paths:
pNFS (parallel NFS) with a metadata server and Flex Files layouts inside
PowerScale's OneFS 9.15, and the Lightning File System itself, which is a
separate file system (not OneFS) with its own client and distributed
metadata. The trace narrates the pNFS form, because the protocol is public
and names its parts; both paths share the one idea below.

The **data** pillar of the AI Factory quartet in this repo — compute
(XE9712), cooling (IR7000), data (this), fabric (SN6000).

## The one idea

The controller arrays here, PowerStore and PowerMax, move every byte
through a controller, and that controller's ceiling is the system's
ceiling. PowerFlex and PowerScale make the sibling refusals; a parallel
file system refuses that bargain this way: the client asks the metadata server **one** question
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
Lightning and Exascale material (see anatomy `sources`); the 6 TB/s, 6×
and "fastest" figures are Dell's own claims and are labeled so in the UI.
The PowerFlex block region is drawn but planned (it never lights). A real rack holds
many more data servers than the four drawn.
