# 02 — Storage: PowerStore, PowerMax, PowerScale, ObjectScale, PowerFlex, Exascale Storage

All are **Archetype B (Capacity/Performance)**. Build ONE storage engine, then parameterize per product. The engine below is shared; per-product sections define personality, config space, and scenarios.

## Shared storage engine
- **Workload generator:** dials for IOPS demand, throughput demand (GB/s), block size (4K–1M), read/write mix, random/sequential mix, working-set size (drives cache-hit rate), client/host count. Presets: OLTP database, VDI, backup target, media streaming, AI training read, analytics scan.
- **Performance model (legible, not benchmark-accurate):** service latency = media latency (NVMe ~0.1 ms, SSD ~0.3 ms, HDD ~8 ms, estimates) adjusted by cache-hit rate, plus **queueing growth**: latency multiplies as utilization → saturation using an M/M/1-style curve (latency ∝ 1/(1−ρ)). The knee of that curve is the core lesson of every storage sim. Cap and clamp; show "saturated" state clearly.
- **Capacity model:** raw → usable after protection overhead (RAID/erasure/mirror per product) → effective after data reduction (dedupe+compression ratio slider per workload preset; label all ratios `estimate`). Time-based growth: data-ingest rate fills capacity over sim-months; snapshot schedule adds overhead; alert at 80/90/95%.
- **Failure/resilience:** drive-failure toggle → rebuild traffic competes with host I/O (latency rises during rebuild; rebuild time scales with drive size and free bandwidth); controller/node failure per product's HA model; **rebuild-window risk readout** (exposure to second failure).
- **Instruments:** latency (avg/p99 proxy), IOPS delivered vs demanded, cache-hit %, utilization ρ, usable/effective capacity gauge, data-reduction ratio, rebuild progress. Strip charts share a time axis.
- **Explain-mode equations minimum:** queueing latency curve, usable-capacity math, effective-capacity math, rebuild-time estimate.

## PowerStore — unified mid-range all-NVMe array
- **Config:** 1–4 appliances in a cluster; drive count/size per appliance; NVMe vs NVMe+expansion; block vs block+file serving.
- **Personality:** dual-controller active/active per appliance; controller-failure toggle halves front-end capability (watch latency knee move left); inline dedupe+compression always-on.
- **Scenarios:** "Find the knee" (raise IOPS until latency explodes); "Controller failover under load"; "The snapshot bill" (aggressive snapshot schedule eats effective capacity over sim-months).
- Sanity: hundreds of thousands of IOPS class per appliance at sub-ms until the knee (estimate).

## PowerMax — high-end enterprise array
- **Config:** engine/"brick" count; capacity per brick; SRDF replication toggle (sync vs async) to a second simulated array.
- **Personality:** extreme-availability model — component failures produce latency blips, not outages; teach **synchronous replication distance penalty**: sync SRDF adds round-trip latency = distance_km × ~0.01 ms/km × 2 (estimate) to every write. Distance slider 0–1000 km.
- **Scenarios:** "Why sync replication has a distance limit"; "Async RPO" (async mode: watch RPO grow under heavy write bursts); "Six-nines mindset" (kill components repeatedly, observe degraded-not-down).
- Note: Cyber Detect integration for PowerMax is roadmap per Dell (2H 2026) — mention in footnote, don't model.

## PowerScale — scale-out NAS (file)
- **Config:** node count (3–50+), node classes (all-flash F-series / hybrid H / archive A — capacity+performance per class, `verify`), erasure-coding protection level (e.g., +2n vs +3n style — express as "survives N failures" with overhead %).
- **Personality:** scale-OUT: adding nodes adds both capacity and performance (near-linear with a small coordination tax, ~2%/node beyond 10, estimate). Single namespace; per-node failure → data stays available, rebuild is cluster-wide and faster with more nodes (opposite of monolithic arrays — key lesson).
- **Scenarios:** "Scale-up vs scale-out" (compare with PowerStore behavior); "Protection-level trade" (higher protection = more overhead, slower fills, better survival); "AI read storm" (sequential read demand from the XE9680 sim's data-starvation concept).

## ObjectScale — S3-compatible object storage
- **Config:** node count, HDD-dense vs all-flash nodes, erasure-coding scheme, bucket count, optional multi-site replication.
- **Personality:** throughput- and capacity-oriented, latency measured in ms–tens-of-ms and mostly irrelevant; object size distribution slider (small-object metadata tax vs large-object streaming); versioning/immutability toggle (object lock) — ties into the security suite (file 05) as backup/vault target.
- **Scenarios:** "Small-object tax"; "Erasure coding across sites" (site-failure toggle with cross-site rebuild traffic); "Immutable bucket" (attempted delete events bounce — logged, teaches WORM).

## PowerFlex — software-defined block storage
- **Config:** node count (4–100+), storage+compute converged vs storage-only layout, network bandwidth per node (this is the constraint that matters), mirror-based protection.
- **Personality:** performance aggregates across ALL nodes over the network — model per-node NIC bandwidth as the ceiling; rebuilds are massively parallel (fast, brief, wide impact). Elasticity: add/remove nodes live with automatic rebalance traffic.
- **Scenarios:** "The network IS the array" (throttle NIC speed, watch aggregate IOPS cap); "60-second rebuild" (vs PowerStore's hours — why: parallelism); "Elastic expansion" (add 5 nodes, watch rebalance then new plateau).

## Exascale Storage — software-defined extreme-scale engine (Dell AI Data Platform)
- **What it is (per Dell, 2026):** the software-first storage architecture under the Dell AI Data Platform; a common platform on which PowerScale, ObjectScale, Lightning File System (parallel FS), and — per Dell's 2026 roadmap — PowerFlex resources are allocated; headline read performance up to ~6 TB/s per rack with 800GbE-class networking. Treat all figures `verify`.
- **Sim design:** a **meta-simulator** composing the engines above: user partitions a rack's node pool among File (PowerScale), Parallel-FS (Lightning — model as PowerScale-like but with much higher per-node sequential throughput and client-side parallelism, `estimate`), Object (ObjectScale), and Block (PowerFlex, flagged "roadmap 1H 2027"). One AI-workload demand profile (from the XE9680 sim's needs: checkpoint writes, dataset reads, KV-cache offload toggle) is served by the mix.
- **Scenarios:** "Right-size the mix" (re-partition until the GPU data-starvation slider in file 01 would read near-zero); "Checkpoint stampede" (periodic massive write bursts from training — watch each engine absorb it differently).
- This sim is the capstone linking storage to the GPU servers; build it last.
