"""Pipeline map for the dedupe simulator — the "anatomy" here is the data
path, drawn left → right the way the CloudIQ and PowerProtect twins draw
theirs: backup streams in, physical containers out. Regions are keyed to
the engine's ``region_load`` dict; the frontend lights them by activity.
Stylized — a mental model of DDOS's ingest path, not a block diagram from
the source tree.
"""

from __future__ import annotations

from .leveling import L
from .models import PipelineMap, PipelineRegion

ANATOMY = PipelineMap(
    id="dd-dedupe-path",
    name="Data Domain · deduplication data path",
    vendor="Dell Technologies",
    form_factor="Purpose-built backup appliance — ingest-path view",
    generation="DDOS variable-length deduplication (DD series / All-Flash)",
    year=2025,
    width=100,
    height=54,
    overview=L(
        novice=(
            "This is the path a backup takes through a Data Domain "
            "appliance, drawn left to right. Backup streams arrive from "
            "the servers being protected. The chunker slices each stream "
            "into small variable-size pieces. For every piece, the "
            "fingerprint index answers one question: have we seen these "
            "exact bytes before? Pieces already in the store are simply "
            "referenced — they cost nothing. Only never-seen pieces get "
            "compressed and written to disk. That is the whole trick, and "
            "everything this simulator shows follows from it: back up the "
            "same data thirty times and you store it roughly once, but "
            "back up encrypted data — which looks different every time — "
            "and the trick stops working entirely. The dedupe ratio you "
            "see is never configured anywhere. It simply happens, or "
            "fails to."
        ),
        plain=(
            "The DDOS ingest path, left to right: streams → DD Boost "
            "(client-side dedupe: only novel segments cross the wire) → "
            "variable-length chunker → fingerprint index (RAM-resident "
            "sample, the ingest bottleneck when it outgrows memory) → "
            "compressed container store → cleaning. The dedupe ratio is "
            "emergent: it falls out of change rate, retention, and "
            "entropy. Encrypted or high-entropy data defeats both "
            "compression and — with fresh session keys — deduplication."
        ),
        standard=(
            "The ingest path of a deduplicating backup appliance, drawn "
            "as the simulator models it. Streams arrive (DD Boost pushes "
            "part of the dedupe to the client, so mostly-novel data is "
            "what crosses the wire); the segmenter cuts variable-length "
            "chunks (~8 KB average) so that shifted data still lines up; "
            "the fingerprint index decides novel-or-seen — the one lookup "
            "whose RAM residency sets ingest speed; novel chunks are "
            "locally compressed and packed into containers; cleaning "
            "reclaims chunks no retained generation references. Every "
            "instrument in this app is a property of this path: the "
            "dedupe ratio is logical ÷ physical of the store, the ingest "
            "knee is the index outgrowing RAM, and the entropy alarm is "
            "the chunker noticing that today's changed data reads as "
            "random — which is what ransomware's writes look like, the "
            "same physics the Cyber Detect twin reads from the other "
            "side."
        ),
        technical=(
            "Analytic model of the DDOS path: variable-length segmenting "
            "(µ ≈ 8 KB), fingerprint lookup with a RAM-resident sample "
            "(SISL-style; pressure = index/RAM knees ingest), lz on novel "
            "segments (cf = f(entropy)), container store with metadata "
            "overhead, retention-driven GC. Ledger identity per day: "
            "physical(t) = physical(t−1) + novel − reclaimed; ratio = "
            "logical/physical, emergent. Chunk novelty closed-form from "
            "change rate, entropy, encryption state."
        ),
        expert=(
            "Stream → Boost → segmenter → fingerprint index → containers "
            "→ GC. Ratio = Σ logical / ledger physical; novelty analytic; "
            "cf(entropy); knee at index > RAM. Ciphertext: novelty → 1, "
            "cf → 1. The alarm is d(entropy of deltas), not capacity."
        ),
    ),
    regions=[
        PipelineRegion(
            id="streams", kind="source", label="Backup streams",
            x=0.5, y=14, w=13, h=26,
            description=(
                "The protected estate's backup jobs — logically, a full "
                "backup of everything, every day. The stream's own "
                "properties (change rate, entropy) are the entire input "
                "to this machine; the simulator's dials edit them."
            ),
        ),
        PipelineRegion(
            id="boost", kind="transport", label="DD Boost",
            x=16, y=14, w=12, h=26,
            description=(
                "Client-side deduplication: the backup client learns "
                "which segments the appliance already holds, so only "
                "never-seen data crosses the wire. This region's activity "
                "is today's novelty fraction — near zero on a quiet "
                "estate, saturated when an encrypted source makes "
                "everything novel."
            ),
        ),
        PipelineRegion(
            id="chunker", kind="chunk", label="Variable-length chunker",
            x=31, y=14, w=14, h=26,
            description=(
                "Cuts the stream into variable-size segments (~8 KB "
                "average) at content-defined boundaries, so data that "
                "shifts by a byte still produces the same chunks — the "
                "reason dedupe survives file edits. Fixed-block chunking "
                "would break on every shift."
            ),
        ),
        PipelineRegion(
            id="index", kind="index", label="Fingerprint index",
            x=48, y=2, w=22, h=20,
            description=(
                "Every unique chunk's fingerprint, sampled into RAM. This "
                "lookup — seen or novel? — happens for every chunk of "
                "every backup, which makes its RAM residency the ingest "
                "throughput's governor: once the index outgrows memory, "
                "lookups spill and ingest degrades past a knee. Watch "
                "this region heat up as unique data accumulates."
            ),
        ),
        PipelineRegion(
            id="store", kind="store", label="Container store",
            x=48, y=26, w=22, h=26,
            description=(
                "Novel chunks, locally compressed and packed into "
                "containers on disk or flash. Physical capacity lives "
                "here — the denominator of the dedupe ratio. The gap "
                "between logical protected data and this region's "
                "occupancy is the product."
            ),
        ),
        PipelineRegion(
            id="cleaner", kind="clean", label="Cleaning (GC)",
            x=74, y=14, w=25, h=26,
            description=(
                "Garbage collection: when a generation ages out of "
                "retention, the chunks only it referenced become garbage, "
                "and cleaning reclaims them. Until the retention window "
                "first fills, this region is dark — nothing has expired "
                "yet — and the store only grows."
            ),
        ),
    ],
    sources=[
        {"label": "Dell PowerProtect Data Domain family data sheet",
         "url": "https://www.delltechnologies.com/asset/en-us/products/data-protection/technical-support/h16867-powerprotect-dd-series-appliances-ds.pdf"},
        {"label": "DellPowerProtect narrative twin (this repo) — vault-side companion",
         "url": "../DellPowerProtect/README.md"},
        {"label": "Expansion-roster spec (this repo), product #4",
         "url": "../physics_specs/10-additional-products.md"},
    ],
)
