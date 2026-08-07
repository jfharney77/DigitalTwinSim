# 05 — Security & Resilience: PowerProtect, Cyber Detect, MDR, Fort Zero

All are **Archetype E (Adversary/Defense timeline)** plus B (backup capacity) for PowerProtect.

**Hard scope boundary (bake into the app footer):** these simulators teach *defensive architecture* — backup topology, detection placement, recovery mechanics, zero-trust structure. The "attack" is an abstract scripted event ("ransomware detonates at T+0, encrypts X GB/hour") with zero technique detail. No exploit content, no evasion, no offensive realism. If a scenario can't be expressed as abstract data-corruption/exfil rates and timestamps, it doesn't belong.

## Shared resilience engine
- **World:** a small simulated estate (borrow from file 04's fleet: some VMs, a PowerStore, file shares) with a data-change rate (GB/day).
- **Timeline scrubber:** the central UI element. Sim-days tick; backups occur per policy; an incident script fires at a chosen T; the user scrubs time to inspect state at any point.
- **Core metrics as first-class instruments:** **RPO** (data lost = time since last clean recovery point), **RTO** (time to restore = data volume ÷ restore throughput + decision/validation time), backup storage consumed, detection latency (incident start → first alert).
- **Explain-mode equations:** RPO from schedule + last-clean-point, RTO composition, backup capacity math (fulls + incrementals + retention + dedupe), 3-2-1 rule as a checklist rule-engine output.

## PowerProtect — backup & Cyber Vault
- **Config:** backup policy (frequency, full/incremental, retention), dedupe ratio (`estimate`, workload-dependent), target: standard repository vs **Cyber Vault** (air-gapped: replication window opens briefly on schedule, data locked immutable inside), restore-throughput budget.
- **Personality mechanics:** the vault's **operational air gap** — the connection is closed except during sync windows; incident script that tries to corrupt backups reaches the standard repository (backups encrypted too — a devastating, common real pattern, shown abstractly) but not vaulted, locked copies.
- **Scenarios:** "Backups aren't enough" (repository-only vs vault under the same incident: compare recoverable data); "Retention vs capacity" (extend retention, watch dedupe save you — to a point); "The RTO surprise" (restoring 200 TB at N GB/s takes days — do the math live).

## Cyber Detect — AI-driven corruption detection (PowerStore + PowerProtect Cyber Vault)
- **What it is (per Dell 2026):** AI-powered ransomware/data-corruption detection across primary storage (PowerStore today; PowerMax planned 2H 2026) and backup (Cyber Vault), analyzing content statistics to flag corruption and identify clean recovery points.
- **Sim design:** a **detection layer toggle on the PowerProtect/PowerStore timeline.** Model abstractly: each backup/scan gets a corruption-score; when the incident script begins low-and-slow corruption at T+0, detection fires after the score crosses threshold — detection latency slider (hours vs days) is the experiment variable. Detector output = the **last-known-clean point**, which becomes the recovery point (vs. without Cyber Detect: the user restores the latest backup, discovers it's corrupt — event log shows a failed recovery and a second, older attempt, doubling RTO).
- **Sensitivity/false-positive slider:** stricter threshold → earlier detection but occasional false alarms (each costs investigation admin-hours) — the classic ROC trade-off, taught by knob.
- **Scenarios:** "Slow burn" (2-week quiet corruption: with vs without detection, compare RPO); "Trust but verify the backup" (clean-point identification vs restore-and-pray).

## MDR — Managed Detection & Response (service)
- **Sim design:** an **alert-queue operations game** layered on the timeline. Alerts stream in (mostly benign noise + the incident's real signals); response model toggle: (a) in-house team — capacity of N alerts/day, business hours only; (b) MDR — 24/7 triage with mean-time-to-triage in minutes (estimates). Incident fires at 2 a.m. Saturday; measure detection→containment gap under each model. Containment = an abstract action that stops the corruption spread rate.
- **Instruments:** alert backlog depth, mean time to acknowledge/contain, incident blast radius (GB affected = spread rate × time-to-containment).
- **Scenarios:** "The 2 a.m. problem" (the headline lesson — same detection, different response clocks); "Alert fatigue" (raise noise volume; in-house backlog grows until the real alert waits in queue).

## Fort Zero — zero-trust private cloud
- **What it is:** Dell's zero-trust architecture offering (advanced-maturity zero trust, DoD-aligned reference design). Specific control lists: `verify`; model the *principles*.
- **Sim design:** an **access-graph simulator**, not a timeline: nodes = users, devices, apps, data stores; edges = allowed access. Two architecture toggles: (a) perimeter model — inside = broadly connected; (b) zero-trust — every edge requires identity + device-health + policy check (visualized as gates on edges). "Compromise" script marks one user/device as hostile (abstractly); the sim floods reachable nodes: **blast radius = reachable set**, counted and highlighted. Micro-segmentation slider shrinks segment sizes and visibly shrinks the flood.
- **Instruments:** reachable-asset count from any selected start node, policy-check count per session (the usability cost — zero trust isn't free), segment count.
- **Scenarios:** "One stolen laptop" (perimeter vs zero-trust flood, side by side); "Segment until it hurts" (blast radius vs friction trade); "Least privilege decay" (unused edges accumulate over sim-months unless a review action prunes them — access entropy as a maintenance problem).
