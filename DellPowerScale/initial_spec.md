# DellPowerScale — scale-out NAS digital twin (spec)

Status: **spec only.** Chosen in loop iteration 4 as one of the top three
untwinned Dell products; Project Fort Zero was built first. Build this one
by following the pattern in `DellPowerFlex/` and `DellExascale/`.

## Subject

**Dell PowerScale** running **OneFS** — scale-out network-attached storage
where every node contributes compute, memory, networking, and storage to a
cluster that presents **one file system, one volume, one namespace**. Data
is striped across all nodes; clients reach it over NFS, SMB, S3, HTTP, and
HDFS. Adding a node grows the single volume and rebalances data onto it
non-disruptively.

## The one idea

**There are no volumes.**

The PowerFlex twin in this repo removed the controller. This one removes
something subtler and, for anyone who has administered traditional NAS, more
viscerally annoying: the *volume*.

Conventional storage makes you carve capacity into fixed containers before
you know what you will need. Then reality diverges from the guess, and the
rest of the system's life is spent on the consequences — this volume is
95% full while that one is empty, and moving capacity between them means a
migration, a maintenance window, and a conversation with whoever owns the
data. The administrative work is not caused by the storage being full; it is
caused by capacity having been partitioned into containers that cannot be
resized as fast as the world changes.

OneFS declines to partition. One file system spans every node in the
cluster. Capacity is added by adding a node, at which point the single
volume simply becomes larger and the cluster redistributes data onto the new
hardware while clients keep reading. There is no volume to be full, so there
is no migration to plan, and — the part that compounds — there is no
capacity-planning ritual that has to be repeated every quarter forever.

The trace should therefore make its point by *not* having a step that other
storage would need. A conventional NAS trace would include "provision a
volume", "volume fills", "migrate data". This one has an `expand` phase and
nothing else, and the tests should assert that the namespace count stays at
one no matter how much the cluster grows.

## Metaphor mapping

- **"Anatomy"** → a cluster map: a band of identical nodes (each with
  compute, memory, and storage), the multi-protocol access layer above them,
  the internal cluster network between them, and — drawn as **one continuous
  shape spanning every node** — the single namespace. That last region is
  the lesson, and it should be drawn as the only thing in the diagram that
  crosses node boundaries.
- **"Power-on trace"** → the life of a cluster: formed, striped, serving,
  outgrown, expanded, rebalanced, and serving again at larger scale with the
  same single namespace.

## Proposed model shapes

`ClusterAnatomy` / `ClusterRegion` / **`NamespaceState`**.

```
RegionKind = node | media | protocol | interconnect | namespace | management
```

`NamespaceState` carries:

- `nodes: int` — 4, then 6 after expansion
- `namespaces: int` — **exists to be 1**, at every cluster size. This twin's
  `droppedPackets`.
- `capacity_tb: int` — grows with nodes
- `used_percent: int` — rises toward the expansion, falls after
- `migrations_required: int` — **also exists to be zero**
- `rebalancing: bool`
- plus the standard `step / phase / label / description / active_regions /
  elapsed_seconds / cycle_cost`

## Proposed phases

`off → form → stripe → serve → fill → addnode → rebalance → served`

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_there_is_only_ever_one_namespace`** — `namespaces == 1` on every
   step, at four nodes and at six. THE invariant.
2. **`test_growing_the_cluster_requires_no_migration`** —
   `migrations_required == 0` throughout, including across the expansion.
   This is the administrative cost that conventional NAS pays forever and
   this architecture does not pay at all.
3. **`test_capacity_grows_with_nodes_not_with_planning`** — `capacity_tb`
   increases only at the `addnode` step, and `used_percent` falls as a
   consequence rather than because anything was deleted or moved by hand.
4. **`test_service_continues_during_rebalance`** — clients are served on
   every step from `serve` onward, including while `rebalancing` is true.
   Expansion is a background task, not an outage.
5. **`test_all_nodes_serve_all_protocols`** — no node is the "NFS node" or
   the "SMB head"; every protocol region is reachable from every node, which
   is what makes the single namespace usable rather than merely true.
6. **`test_nodes_are_never_partitioned`** — no step lights a strict subset
   of nodes for data placement; striping spans the cluster.
7. **`test_rebalancing_is_the_longest_stage`** — unique max `cycle_cost`.
   Redistributing data onto a new node is genuinely slow, and it is the
   price of never having to migrate.
8. Standard: phase order, monotonic capacity, active regions exist, engine
   purity (AST-checked).

## Geometry invariant

`test_the_namespace_spans_every_node` — the namespace region's horizontal
extent must cover every node region, and it must be the only region in the
map that does. Every other region belongs to a node or sits in a band; the
namespace is the one thing that refuses to be partitioned, and the drawing
has to say so.

## Catalog (~10 categories, backend data)

Node platform (all-flash, hybrid, archive tiers), OneFS operating system,
protocols (NFS, SMB, S3, HDFS — multi-protocol access to the same data),
data protection and erasure coding, tiering and policy-driven placement,
cluster networking, scale limits and node pools, snapshots and replication,
security and immutability, management and AIOps.

## Use cases (3)

1. A media organization whose archive grows unpredictably and can never be
   taken offline.
2. Genomics or research data with mixed protocol access to the same files —
   written by an instrument over SMB, read by a pipeline over NFS, published
   over S3.
3. An AI training corpus, cross-referencing the Exascale twin: PowerScale
   with the Lightning file system is the file tier of that rack, and this
   twin explains the namespace underneath it.

## Cross-references to keep intact

- **DellExascale** — Lightning File System runs on OneFS; that twin covers
  parallel throughput, this one covers the namespace beneath it. Both should
  name each other.
- **DellPowerFlex** — the sibling refusal. PowerFlex removed the controller,
  OneFS removed the volume; both let a system's shape change while running.
- **DellObjectScale** (spec, iteration 2) — the object tier, and the sharper
  version of the same trade: object storage gave up the *tree*, OneFS kept
  the tree and gave up the *volume*. The two specs should point at each
  other, because read together they are a much better lesson than either
  alone.
- **DellCloudIQ** — watching a cluster of interchangeable nodes.

## Ports

Backend **:8023**, frontend **:5196** (after DellFortZero's 8022/5195).
Trace endpoint `GET /api/namespace` returning `NamespaceResponse`.

## Sources

- <https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/powerscale>
- <https://www.delltechnologies.com/asset/en-us/products/storage/industry-market/h8202-wp-powerscale-onefs-product-overview.pdf>
- <https://infohub.delltechnologies.com/en-us/l/dell-powerscale-onefs-operating-system/scalability-96/>
- <https://infohub.delltechnologies.com/en-us/l/high-availability-and-data-protection-with-dell-powerscale-scale-out-nas/onefs-architectural-overview-1/>
