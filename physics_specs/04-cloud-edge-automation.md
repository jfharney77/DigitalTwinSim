# 04 — Cloud, Edge & Automation: VxRail, Private Cloud, APEX, NativeEdge (Distributed Private Cloud), Automation Studio

All are **Archetype D (Fleet/Orchestration)**, some with F (economics). Build one fleet engine.

## Shared fleet engine
- **World model:** N sites, each with M nodes; each node has capacity (vCPU, RAM GB, storage TB) and a software stack version. Workloads (VMs/containers) with resource demands get placed on nodes.
- **Time dynamics (sim-days/weeks):** workload demand grows; updates are released monthly; hardware faults arrive randomly (MTBF-based, ~1 fault per 100 node-months, estimate); config drift accumulates on any node not centrally managed.
- **Operations model — the teaching core:** every action (deploy site, patch node, remediate fault, fix drift) costs **admin-hours**. Central automation vs manual toggle changes the cost per action by an order of magnitude and changes failure windows. Instruments: total admin-hours/month, fleet availability %, version spread histogram, drift count, capacity headroom per site.
- **Placement & HA mechanics:** node failure → workloads restart on surviving nodes if headroom exists (N+1 math); no headroom → outage event. Maintenance mode drains a node first.
- **Explain-mode equations:** N+1 headroom math, availability from MTBF/MTTR, admin-hours model, capacity forecast (demand growth vs installed).

## VxRail — VMware-integrated HCI appliance
- **Config:** one site, 3–16 node cluster; node classes (compute-heavy/storage-heavy/GPU); vSAN-style storage policy (FTT=1 mirror vs FTT=2 — capacity overhead vs failures tolerated).
- **Personality:** the **lifecycle-management bundle** is the product: one-click cluster update as a single orchestrated action (rolling: drain → patch → return, watch it proceed node by node with N+1 protecting workloads) vs "manual mode" where the user patches ESXi/firmware/drivers as separate per-node actions with a compatibility-matrix rule that errors on mismatched combinations.
- **Scenarios:** "Rolling upgrade under load"; "FTT trade-off"; "The 3-node trap" (one node down in a 3-node FTT=1 cluster = no rebuild target — why minimums matter).

## Dell Private Cloud — on-prem cloud (Automation Platform-delivered)
- **What it is:** Dell's private cloud offering delivered via Dell Automation Platform; supports customer-chosen stacks (VMware vSphere, Red Hat OpenShift, etc.) with centralized catalog-based deployment. 
- **Config:** choose cloud OS stack per cluster; cluster sizes; self-service catalog of workload blueprints.
- **Personality:** **stack pluralism** — run two clusters with different stacks under one control plane; deploying from catalog = minutes of admin-time vs manual stack install = days (estimates). Model "bring your own license" as a cost line (Archetype F lite): subscription vs perpetual license cost accumulation over sim-months.
- **Scenarios:** "Two stacks, one pane"; "Catalog vs artisanal" (same outcome, two admin-hour bills).

## APEX — as-a-Service consumption
- **Personality:** pure **Archetype F economics layered on any fleet**: instead of buying capacity, commit to a base + buffer; usage above base bills per unit; under-use still pays base. Sliders: committed base, buffer %, demand curve (steady/seasonal/spiky). Instruments: monthly bill, utilization of commitment, cost per delivered VM-hour vs a simulated CapEx purchase amortized over 4 years (all rates `estimate` — the lesson is the shape, not the price).
- **Scenarios:** "Spiky demand" (as-a-service wins); "Flat demand" (owned capacity wins); "The buffer decision" (too small = capacity outage events, too big = paying for air).

## NativeEdge / Dell Distributed Private Cloud — edge fleet operations
- **Naming note (2026):** Dell has rebranded NativeEdge as **Dell Distributed Private Cloud** within Dell Automation Platform; keep both names in the UI.
- **Config:** 10–1,000 sites, 1–2 nodes each (2-node HA with witness supported); site classes (factory, store, clinic); intermittent WAN connectivity slider per site class.
- **Personality:** **zero-touch onboarding** — "ship a box" action: device arrives, authenticates, pulls its blueprint, joins fleet with zero local admin-hours vs manual mode (site visit = 8 admin-hours + travel, estimate). **Blueprints**: declarative app+config bundles pushed fleet-wide; a blueprint change rolls to 1,000 sites as one action. Connectivity loss → site runs autonomously, reconciles on reconnect (show drift accumulating then resolving).
- **Scenarios:** "Roll out to 500 stores" (manual vs zero-touch admin-hour bill — the headline lesson); "The disconnected factory"; "2-node HA at the edge" (node fault at a remote site: HA failover vs single-node outage + truck roll).

## Automation Studio — CI/CD-native infrastructure orchestration
- **What it is (per Dell 2026):** a premium Dell Automation Platform capability letting teams build AI-driven compute/storage/network automation workflows with familiar DevOps tools; CI/CD-native, blueprint-driven.
- **Sim design:** a **visual workflow builder ON TOP of the other sims in this file** (and files 01–03 if present): drag steps (provision cluster → configure network → deploy storage policy → deploy app → validate) into a pipeline; "run pipeline" executes against the fleet engine with a test→prod promotion gate. Failure injection mid-pipeline → rollback step behavior. Instruments: pipeline duration, success rate, drift eliminated (pipelines re-run = enforcement).
- **Scenarios:** "Pipeline vs clicks" (same environment built twice); "Failed in test, saved in prod" (gate catches an intentionally bad config change).
- Build last in this file; it's the integrator.
