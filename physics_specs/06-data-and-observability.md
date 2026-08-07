# 06 — Data & Observability: Dell AI Data Platform, CloudIQ / APEX AIOps

## Dell AI Data Platform (with NVIDIA) — Archetype B + D hybrid
- **What it is (per Dell 2026):** the umbrella data architecture feeding Dell AI Factory: Dell storage engines (Exascale Storage: PowerScale, ObjectScale, Lightning FS, PowerFlex roadmap) plus data services — GPU-accelerated processing, a data analytics engine (Starburst-powered SQL), KV-cache offload to shared storage (NVIDIA CMX support), unstructured-data pipelines that make data "AI-ready."
- **Sim design — a data pipeline simulator** (distinct from file 02's raw-performance sims): the unit of simulation is a **dataset's journey**: Raw sources (files/objects/tables with volume sliders) → ingest → process/clean (GPU-accelerated toggle: hours vs minutes, estimates) → index/embed → serve to training or inference.
  - **The GPU-utilization payoff loop:** the served-data throughput feeds the XE9680 sim's data-starvation slider (file 01) conceptually; instrument "GPU idle % due to data" as the platform's north-star metric.
  - **KV-cache offload toggle (inference side):** ON = long-context sessions spill KV cache from GPU memory to fast shared storage — model as: max concurrent long-context sessions jumps (GPU memory freed) at the cost of a small per-token latency tax (estimates). This is the most 2026-current concept in the suite; keep the model simple: two bars (GPU-memory sessions vs offloaded sessions) and a latency readout.
  - **Analytics engine:** a query-demand dial served at X TB/s scan with GPU acceleration on/off (6× class speedup claim: `verify`, cite Dell).
- **Instruments:** pipeline throughput per stage (find the bottleneck stage — classic theory-of-constraints teaching), GPU idle-due-to-data %, dataset freshness lag, concurrent inference sessions.
- **Scenarios:** "Find the bottleneck" (one stage always binds; fix it, the bottleneck moves); "The KV-cache trick"; "Stale data, confident model" (freshness lag grows when ingest is under-provisioned).
- **Explain-mode equations:** pipeline throughput = min(stage rates), Little's Law for in-flight data, session-capacity math for KV offload.

## CloudIQ / APEX AIOps — fleet observability & AIOps
- **Naming note:** CloudIQ has been folded into the APEX AIOps umbrella in Dell's current branding; keep both names visible. `verify` current naming at build time.
- **Sim design — the meta-instrument:** this product IS a dashboard, so the sim is a **simulated CloudIQ console observing the other simulators** (or a synthetic fleet if run standalone: 20 servers, 3 arrays, 4 switches with scripted behaviors). Panels: fleet health scores, capacity forecasting, anomaly feed.
- **Mechanics that teach observability itself:**
  - **Health score:** a composed metric (capacity risk + performance risk + config risk, weighted — show the formula in explain mode; let the user re-weight and watch rankings shuffle: scores are opinions, not facts).
  - **Capacity forecasting:** linear + seasonality fit on each array's fill curve → "full in N days" predictions with confidence bands; inject a demand change and watch the forecast take time to catch up (forecast lag as a lesson).
  - **Anomaly detection:** per-metric rolling baseline (mean ± kσ); the user tunes k — sensitivity vs false-alarm trade again (deliberately rhyming with Cyber Detect's slider in file 05; note the rhyme in a scenario).
  - **The gray-failure payoff:** run file 03's silent-packet-loss toggle or a slow-drifting fan from file 01; the anomaly feed catches what the device's own red/green status misses — the argument for fleet telemetry, demonstrated.
- **Instruments:** alert precision/recall scoreboard (the sim knows ground truth of injected issues — score the user's tuning), mean-time-to-detect, forecast error.
- **Scenarios:** "Tune the anomaly detector" (scored); "Days-to-full" (act on a forecast: expand before the outage); "Green but sick" (gray failure caught by trend, missed by status light); "From dashboards to twins" (closing scenario for the whole suite: CloudIQ's live-fleet view is the data layer a digital twin binds to — connect back to the original R760 twin discussion).
