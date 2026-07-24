# DellObjectScale — object storage digital twin (spec)

Status: **spec only.** Chosen in loop iteration 2 as one of the top three
untwinned Dell products; PowerFlex was built first. Build this one by
following the pattern in `DellExascale/` and `DellPowerFlex/`.

## Subject

**Dell ObjectScale** — Dell's software-defined object storage, the object
tier of the Exascale rack and the Dell AI Data Platform. NVIDIA-Certified
Storage validation arriving Q2 2026; **AI-Optimized Search** globally
available from the second half of 2026.

## The one idea

**It scales because it gave up the tree.**

A file system's central promise is a hierarchy: directories inside
directories, a path that means something, rename and move as cheap
metadata operations. That promise is also its ceiling. Every path lookup
walks a tree, every rename takes a lock, and the namespace becomes a
structure that must be kept globally consistent — which is precisely the
thing that stops being possible somewhere past a few billion entries.

Object storage made a trade that looks like a loss and is the whole point.
There are no directories, only a flat namespace of keys. A key that *looks*
like a path is just a string with slashes in it. Nothing is nested, so
nothing has to be walked, so there is no tree to keep consistent — and the
namespace becomes something you can shard across as many nodes as you like.
The price is paid at the API: no rename, no move, no partial update, and no
listing that is cheap when a bucket holds a hundred million keys.

Which sets up the second half of the story, and the reason this is
interesting *now*. Having given up the hierarchy, object storage has spent
two decades being hard to find things in. AI-optimized search is the answer
finally arriving: instead of navigating a structure, you ask for what you
want and metadata indexing finds it. The tree was a navigation aid; search
replaces it.

## Metaphor mapping

Following Exascale and PowerFlex (data paths, not boxes):

- **"Anatomy"** → a left→right map: clients and the object API, the
  request router, the flat namespace / metadata index, the erasure-coded
  data nodes beneath it, plus lifecycle/tiering and the search index.
  Geometry should carry the lesson: draw the namespace as **one wide flat
  band** with no nesting and no depth, and pin it — a
  `test_anatomy.py::test_the_namespace_is_flat` asserting that the
  namespace region is wider than it is tall by a large factor, and that no
  region is drawn *inside* another (which the existing non-overlap test
  already gives, but the docstring should say why it matters here).
- **"Power-on trace"** → the life of an object: written, sharded,
  erasure-coded, indexed, listed (expensively), searched (cheaply), tiered,
  and read back years later.

## Proposed model shapes

`PlatformAnatomy` / `PlatformRegion` / **`ObjectState`**.

```
RegionKind = client | api | router | namespace | datanode
           | erasure | search | lifecycle | management
```

`ObjectState` carries:

- `objects_millions: int` — namespace size
- `namespace_depth: int` — **exists to be 1**, at every scale. This twin's
  `droppedPackets`.
- `list_latency_ms: int` — grows with bucket size; the honest cost
- `search_latency_ms: int` — flat, whatever the bucket size; the payoff
- `durability_nines: int` — from erasure coding
- plus the standard `step / phase / label / description / active_regions /
  elapsed_seconds / cycle_cost`

## Proposed phases

`idle → put → shard → encode → index → grow → list → search → tier → get`

- `put` — a client writes an object through the S3-compatible API
- `shard` — the key is hashed; no directory is consulted, because there
  isn't one
- `encode` — erasure coding writes fragments across nodes
- `index` — the key lands in the flat namespace
- `grow` — the bucket reaches a hundred million objects, and nothing about
  the write path changes
- `list` — a listing is requested, and is *expensive*; the trace should be
  honest about this rather than skipping it
- `search` — AI-optimized search answers the same question cheaply, by
  metadata rather than enumeration
- `tier` — lifecycle policy moves cold objects to a cheaper tier, without
  the key changing
- `get` — the object is read back, still by key, still in one hop

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_the_namespace_never_gains_depth`** — `namespace_depth == 1` on
   every step, including after the bucket grows to a hundred million
   objects. The twin's reason for existing: keys with slashes in them are
   not directories.
2. **`test_growth_does_not_change_the_write_path`** — the set of active
   regions during `put`/`shard`/`encode` is identical before and after the
   `grow` phase, and the per-object write cost does not increase. A tree
   would deepen; this does not.
3. **`test_listing_is_honestly_expensive`** — `list_latency_ms` rises with
   `objects_millions`. The twin must not pretend the trade was free.
4. **`test_search_beats_listing_at_scale`** — at the grown scale,
   `search_latency_ms` is dramatically lower than `list_latency_ms`, and
   search latency does not scale with object count. This is the 2026 story
   and the resolution of the trade.
5. **`test_a_key_never_changes`** — tiering moves data between media
   without the key changing; assert the `get` phase succeeds after `tier`
   with the same addressing, and that no phase re-encodes or renames.
6. **`test_durability_never_regresses`** — `durability_nines` is
   non-decreasing once erasure coding is applied.
7. **`test_erasure_coding_is_the_longest_stage`** — unique max
   `cycle_cost`.
8. Standard: phase order never regresses, active regions exist, engine
   purity (AST-checked).

## Catalog (~10 categories, backend data)

Deployment form (software-defined, appliance, or as the object tier of the
Exascale rack), the S3-compatible API and compatibility surface, erasure
coding and protection, flat-namespace scale limits, AI-optimized search and
metadata indexing, lifecycle and tiering, object lock / immutability
(cross-referencing PowerProtect), multi-site replication, GPU-adjacent
access and NVIDIA-Certified Storage validation, management and AIOps.

## Use cases (3)

1. A petabyte-scale training-data lake feeding an AI factory, where the
   corpus is addressed by key and searched by metadata.
2. Long-term retention with immutability for regulatory compliance.
3. Replacing a file-server estate that has outgrown its own directory
   tree — the migration where the hardest part is that applications expect
   rename to exist.

## Cross-references to keep intact

- **DellExascale** — ObjectScale is the object tier of the same rack;
  Exascale's file path and this object path are two answers to different
  access patterns, and the Exascale twin already names ObjectScale.
- **DellPowerFlex** — the block tier of that rack, and the same
  refuse-the-controller instinct in a different shape. Both spread data and
  let clients address it directly.
- **DellAIDataPlatform** (spec, iteration 1) — its search/embedding path
  is what sits on top of this; the two specs should point at each other,
  since "make the data findable" is the shared subject.
- **DellPowerProtect** — object lock and immutability are the same
  retention idea the vault twin models.

## Ports

Backend **:8018**, frontend **:5191** (after DellTelecomBlocks' 8017/5190).
Trace endpoint `GET /api/object` returning `ObjectResponse`.

## Sources

- <https://www.dell.com/en-us/blog/powerscale-objectscale-innovation-storage-that-delivers/>
- <https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~05~dell-technologies-reimagines-the-modern-data-center-for-the-ai-era.htm>
- <https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~03~dell-ai-data-platform-with-nvidia-supercharges-enterprise-ai-with-breakthrough-data-orchestration-and-storage-innovations.htm>
- <https://www.dell.com/en-us/blog/dell-ai-data-platform-introduces-only-4-in-1-storage-for-ai/>
