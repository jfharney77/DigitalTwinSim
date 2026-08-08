"""Data & observability maps — one shared diagram: the dataset's
left-to-right journey across the top (sources → ingest → process →
index → serve → GPUs), the KV-cache and analytics blocks midway, and
the CloudIQ console band along the bottom watching all of it. Two
product overviews over one geometry, because the console's whole
argument is that it observes the same pipeline the other half runs."""

from __future__ import annotations

from .leveling import L
from .models import DataMap, MapRegion


def _regions() -> list[MapRegion]:
    return [
        MapRegion(
            id="sources", kind="source", label="Raw sources",
            x=2, y=1, w=14, h=16,
            description=(
                "Files, objects, tables — the unstructured mess the "
                "platform exists to make AI-ready."
            ),
        ),
        MapRegion(
            id="ingest", kind="stage", label="Ingest",
            x=18, y=1, w=14, h=16,
            description=(
                "First stage of the journey. Colored by load against "
                "its rate — when it's the bottleneck, everything "
                "downstream starves and freshness lags."
            ),
        ),
        MapRegion(
            id="process", kind="stage", label="Process / clean",
            x=34, y=1, w=14, h=16,
            description=(
                "The usual bottleneck: cleaning and transforming. The "
                "GPU-processing toggle multiplies its rate ~6× (Dell's "
                "claim, labeled) — and moves the bottleneck rather "
                "than removing it."
            ),
        ),
        MapRegion(
            id="index", kind="stage", label="Index / embed",
            x=50, y=1, w=14, h=16,
            description="Embedding and indexing — the stage fixes usually reveal.",
        ),
        MapRegion(
            id="serve", kind="stage", label="Serve",
            x=66, y=1, w=14, h=16,
            description=(
                "Delivery to training and inference. Its rate against "
                "GPU read demand sets the north-star gauge."
            ),
        ),
        MapRegion(
            id="gpus", kind="gpu", label="GPU cluster",
            x=82, y=1, w=16, h=16,
            description=(
                "PhysicsCompute's XE9680s, colored by idle-due-to-data "
                "— the percentage this platform exists to hold at "
                "zero."
            ),
        ),
        MapRegion(
            id="kvcache", kind="kvcache", label="KV-cache offload",
            x=2, y=21, w=46, h=10,
            description=(
                "Long-context sessions spill their KV cache to fast "
                "shared storage: ~4× the concurrent sessions for a "
                "~12% per-token tax. The most 2026-current concept in "
                "the suite, kept deliberately simple."
            ),
        ),
        MapRegion(
            id="analytics", kind="analytics", label="Analytics engine",
            x=52, y=21, w=46, h=10,
            description=(
                "The Starburst-powered SQL layer; the GPU toggle is a "
                "~6×-class scan speedup (labeled a claim to verify)."
            ),
        ),
        MapRegion(
            id="fleet", kind="fleet", label="Fleet (20 servers · 3 arrays · 4 switches)",
            x=2, y=35, w=46, h=12,
            description=(
                "The synthetic estate the console observes, colored by "
                "composed risk. Its device status lights never admit "
                "the injected issues — that gap is the console's "
                "reason to exist."
            ),
        ),
        MapRegion(
            id="detector", kind="detector", label="Anomaly detector",
            x=52, y=35, w=22, h=12,
            description=(
                "Rolling baseline ± k·σ. The k-knob is scored against "
                "known ground truth: precision, recall, time-to-"
                "detect. The same trade as Cyber Detect's sensitivity "
                "slider — the rhyme is deliberate."
            ),
        ),
        MapRegion(
            id="forecast", kind="forecast", label="Capacity forecast",
            x=78, y=35, w=20, h=12,
            description=(
                "Days-to-full from a week-long linear fit. Change the "
                "demand and watch it be confidently wrong until the "
                "window relearns — forecast lag as a lesson."
            ),
        ),
        MapRegion(
            id="console", kind="console", label="CloudIQ / APEX AIOps console",
            x=2, y=51, w=96, h=8,
            description=(
                "The health scores, the feed, the forecasts — opinions "
                "composed from weighted risks, and honest about being "
                "opinions: re-weight them and watch rankings shuffle."
            ),
        ),
    ]


def _map(map_id: str, name: str, gen: str, overview: str) -> DataMap:
    return DataMap(
        id=map_id,
        name=name,
        vendor="Dell Technologies",
        form_factor="Data-pipeline & observability view",
        generation=gen,
        year=2026,
        width=100,
        height=61,
        overview=overview,
        regions=_regions(),
        sources=[
            {"label": "physics_specs/06-data-and-observability.md (this repo)",
             "url": "../physics_specs/06-data-and-observability.md"},
        ],
    )


AIDATAPLATFORM = _map(
    "aidataplatform",
    "Dell AI Data Platform · the dataset's journey",
    "Dell AI Data Platform (with NVIDIA)",
    L(
        novice=(
            "Follow one dataset across the top of the map: raw files "
            "arrive, get cleaned, get indexed, and get served to the "
            "expensive computers on the right. The chain moves only as "
            "fast as its slowest stage — fix that stage and a "
            "different one becomes slowest, forever. The scoreboard "
            "is on the far right: the fraction of time the GPU "
            "cluster waits for data. Everything else on this map "
            "exists to keep that number at zero. The middle row "
            "holds two clever tricks: spilling AI conversation "
            "memory to shared storage so four times as many long "
            "chats fit, and a query engine that scans six times "
            "faster with GPU help."
        ),
        standard=(
            "Theory of constraints as a sim: throughput = min(stage "
            "rates), backlog piles up ahead of the bottleneck (the "
            "map names it), freshness lag = backlog ÷ throughput, "
            "and the fix-stage event moves the constraint instead of "
            "removing it. GPU-idle-due-to-data is the north star — "
            "PhysicsCompute's feed slider and PhysicsStorage's "
            "Exascale gauge, unified. The KV-offload toggle trades a "
            "~12% token tax for ~4× long-context sessions; the "
            "analytics toggle is the labeled 6×-class claim."
        ),
        expert=(
            "min(stages); backlog pre-constraint; lag = Q/X; fixes "
            "relocate the constraint. North star: GPU idle %. KV "
            "offload: ×4 sessions / +12% token. Little's law in the "
            "explain tab."
        ),
    ),
)

CLOUDIQ = _map(
    "cloudiq",
    "CloudIQ / APEX AIOps · the meta-instrument",
    "APEX AIOps (CloudIQ name kept visible)",
    L(
        novice=(
            "This product is a dashboard, so the simulator is a "
            "dashboard watching a pretend fleet — with one honest "
            "advantage: the simulator knows exactly which problems "
            "it planted and when. That means your tuning gets "
            "graded. Set the anomaly detector touchy and it finds "
            "the planted problems fast but cries wolf between them; "
            "set it calm and the wolf-cries stop, along with some "
            "of the finding. The capacity forecast has its own "
            "flaw: it learns from the past week, so when demand "
            "suddenly doubles it stays confidently wrong for days. "
            "And the planted 'gray' failure never turns any status "
            "light red — only the trend line catches it, which is "
            "the whole argument for watching trends."
        ),
        standard=(
            "The meta-instrument, scored: injected issues are ground "
            "truth, so the k-knob earns a precision/recall/MTTD "
            "scoreboard (spec 06's 'the sim knows the truth — score "
            "the user's tuning'). Days-to-full is a rolling linear "
            "fit whose window is the lag: the demand-change event "
            "makes forecast error spike and decay. Health scores "
            "are weighted opinions (re-weight and watch rankings "
            "shuffle), and the gray failure pays off the fabric "
            "app's toggle: status green, trend caught. The closing "
            "note is the suite's: a live fleet feeding these panels "
            "is the data layer a digital twin binds to."
        ),
        expert=(
            "Ground truth → scored k (P/R/MTTD). Forecast = "
            "windowed fit → lag on slope change. Scores are "
            "weighted opinions. Green-but-sick caught by trend. "
            "Dashboards → twins, the suite's closing loop."
        ),
    ),
)


MAPS: dict[str, DataMap] = {
    "aidataplatform": AIDATAPLATFORM,
    "cloudiq": CLOUDIQ,
}
