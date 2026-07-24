# DellAIDataPlatform — AI data platform / Data Lakehouse digital twin (spec)

Status: **spec only.** Chosen in loop iteration 1 as one of the top three
untwinned Dell products; the Pro Max Plus was built first. Build this one
by following the pattern in `DellExascale/` and `DellCloudIQ/`.

## Subject

**Dell AI Data Platform** and the **Dell Data Lakehouse** — announced at
Dell Technologies World and expanded with NVIDIA in March 2026
("breakthrough data orchestration and storage innovations"; orchestration
and search advancements available Q2 2026). The Lakehouse adds native
vector search, built-in large-language-model functions, hybrid search, and
automated Apache Iceberg table management.

## The one idea

**The bottleneck moved from storage to meaning.**

The `DellExascale` twin already answers the throughput question: a parallel
file system that refuses the controller ceiling and streams ~6 TB/s to a
GPU fleet. It ends by feeding an AI factory, and in doing so exposes the
next problem. Bandwidth is not what stops most enterprise AI. What stops it
is that the data is *undiscoverable* — spread across file shares, object
buckets, and databases, described inconsistently, and impossible to ask a
question of without knowing in advance where the answer lives.

So this twin is about a different kind of path. Exascale's story is bytes
moving fast; this one's is a question becoming an answer: a corpus
ingested, catalogued, chunked, embedded into vectors, indexed, and then
retrieved *by meaning* rather than by path — and finally handed to a model
as grounded context.

The invariant that carries it: **an answer is never produced without the
sources it came from.** `citations` is on every state that produces output
and is never empty, because retrieval-augmented generation whose provenance
you cannot check is just a confident guess with extra steps.

## Metaphor mapping

Following CloudIQ and Exascale (software and data paths, not boxes):

- **"Anatomy"** → a left→right data-path diagram: source systems (file,
  object, database) → ingest and Iceberg table management → catalog and
  metadata → chunking and embedding → vector index → hybrid retrieval →
  LLM functions and grounding → the answer. Storage sits *beneath* the
  path as a band, the way Exascale draws its media under the data servers,
  with a geometry test pinning that the vector index lies strictly between
  embedding and retrieval — the pipeline's order is the lesson.
- **"Power-on trace"** → the life of a question: from a corpus at rest to
  a grounded, cited answer.

## Proposed model shapes

`PlatformAnatomy` / `PlatformRegion` / **`QueryState`**.

```
RegionKind = source | ingest | catalog | embedding | vectorindex
           | retrieval | llm | governance | storage
```

`QueryState` carries:

- `documents_indexed: int` — the corpus, growing during ingest
- `vectors_millions: int` — the embedded index
- `candidates_retrieved: int` — how many chunks the hybrid search returned
- `citations: int` — **never zero once an answer exists**
- `latency_ms: int`
- plus the standard `step / phase / label / description / active_regions /
  elapsed_seconds / cycle_cost`

## Proposed phases

`idle → ingest → catalog → chunk → embed → index → query → retrieve → ground → answer`

- `ingest` — source systems land in Iceberg tables, managed automatically
- `catalog` — metadata extracted; the estate becomes describable
- `chunk` — documents split into retrievable units (the decision that
  quietly determines answer quality more than model choice does)
- `embed` — chunks become vectors: coordinates in a space where nearness
  means similar meaning
- `index` — the vector index is built
- `query` — a question arrives
- `retrieve` — hybrid search: vector similarity *and* keyword matching,
  because each fails in ways the other catches
- `ground` — retrieved context assembled and handed to the model
- `answer` — generated, with citations

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_no_answer_without_citations`** — any step with an answer has
   `citations >= 1`. The twin's reason for existing.
2. **`test_citations_never_exceed_retrieved_candidates`** — you cannot cite
   what you did not retrieve. Catches the failure mode that matters:
   plausible provenance invented after the fact.
3. **`test_nothing_is_retrievable_before_it_is_indexed`** —
   `candidates_retrieved > 0` implies `vectors_millions > 0`.
4. **`test_the_index_is_never_queried_while_being_built`** — the query
   phases come strictly after `index`; the pipeline order is real.
5. **`test_embedding_is_the_longest_stage`** — unique max `cycle_cost`.
   Embedding a corpus is the expensive, one-time act, and — like the
   Pro Max Plus twin's model load — its cost is paid per corpus, not per
   question. Retrieval afterwards is milliseconds.
6. **`test_governance_is_active_on_every_step_that_touches_data`** — the
   governance region is not an optional stage bolted on at the end; if a
   step touches source data or produces an answer, governance is lit.
7. Standard: phase order never regresses, monotonic counters, active
   regions exist, engine purity (AST-checked).

## Catalog (~10 categories, backend data)

Platform (AI Data Platform / Data Lakehouse), storage foundation
(PowerScale, ObjectScale, Exascale), Iceberg table management, catalog and
metadata discovery, embedding models and vector search, hybrid and
keyword search, LLM functions in the query layer, data orchestration and
pipelines, governance/lineage/access control, NVIDIA integration
(NeMo Retriever, NIM microservices) and validated designs.

## Use cases (3)

1. An enterprise making twenty years of engineering documents askable —
   the classic retrieval-augmented-generation build, where the hard part
   is chunking and provenance, not the model.
2. Feeding an agent fleet with grounded context, where every tool call
   needs an auditable source.
3. Consolidating three data silos (file, object, warehouse) into one
   queryable surface without physically moving the data first.

## Cross-references to keep intact

- **DellExascale** — the layer beneath. Exascale delivers ~6 TB/s to the
  GPUs; this twin is what makes those bytes *findable*. Exascale's story
  ends where this one starts, and both should say so.
- **DellPowerEdgeXE9712** — the compute that consumes the grounded
  context.
- **DellCloudIQ** — the same "telemetry becomes an insight" shape, applied
  to enterprise data rather than infrastructure health.
- **DellProMaxPlus** — its agent-development use case runs an embedding
  model locally for exactly this retrieval step, at laptop scale.

## Ports

Backend **:8015**, frontend **:5188** (after DellNativeEdge's 8014/5187).
Trace endpoint `GET /api/query` returning `QueryResponse`.

## Sources

- <https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~03~dell-ai-data-platform-with-nvidia-supercharges-enterprise-ai-with-breakthrough-data-orchestration-and-storage-innovations.htm>
- <https://www.dell.com/en-us/blog/elevating-innovation-with-dell-s-ai-data-platform/>
- <https://www.dell.com/en-us/blog/accelerate-ai-workflows-new-dell-data-lakehouse-features/>
- <https://www.dell.com/en-us/blog/how-dell-storage-powers-ai-factories/>
- <https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~05~dell-technologies-closes-the-gap-between-ai-ambition-and-ai-outcomes.htm>
