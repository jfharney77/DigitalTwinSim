# DellPowerScale

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

## Guided tour

`#tour` is a narrated walk through the cluster (`GET /api/tour`, built in
`backend/app/tour.py` following `DellPowerStore/TOUR_PATTERN.md`). It has nine
beats: the protocol band over six identical nodes, the cluster forming, the
namespace as the only shape that spans every node, the signature beat
`onefs-stripe` (every node holds part of every file), serving, filling, two
nodes joining with no migration, the live rebalance, and the reassembled
six-node cluster. Every script is authored at reading levels 1, 3 and 5.
Deep links such as `#tour/onefs-stripe` open the tour on that beat.

## Test and build

```bash
pytest DellPowerScale                         # from the repo root
cd DellPowerScale/frontend && npm run build
```
