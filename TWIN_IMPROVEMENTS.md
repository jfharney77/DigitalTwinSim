# DigitalTwinSim — Improvement Plan (2026-07-24)

Improvements for every twin except `GPU/`. Each entry states why it matters, what
concretely changes (in the repo's established pattern: pure engine, data-driven
anatomy, invariant tests, frontend-owned clock), and an effort tag — S (an
afternoon), M (a day or two), L (a week-scale build). Nothing here relaxes an
existing invariant; where an idea brushes against one, the entry says how it
stays inside it. Community citations live in `RESEARCH_ASSETS.md`.

## Top 10 next actions

Ordered by impact against effort:

1. **Tour mode in DellPowerStore** (L) — the `ACTIVE_TWIN_SPEC.md` pilot; proves
   the pattern every other twin will copy, using the one twin that already ships
   local photos.
2. **Port registry** (S) — two collisions already exist; cheapest structural fix
   in the repo.
3. **Landing hub `index.html`** (S) — 25 twins have no front door; a static page
   makes the whole repo demoable in one link.
4. **iDRAC firmware-update lifecycle scenario** (M) — the loudest community pain
   across all research; the twin exists and the scenario slots into its pattern.
5. **PowerProtect cleaning/GC beat** (M) — "free space is decreasing constantly"
   is the classic Data Domain confusion and the twin already renders the dedupe
   arithmetic it extends.
6. **VxRail node-add trace with the version-mismatch failure path** (M) — the
   dominant VxRail community theme, and the repo's first day-2-operations trace.
7. **Alienware diagnostic mode + charge-taper beat** (M) — three separate real
   thread genres map onto one twin; highest community-validation density.
8. **Cross-twin contract linter `tools/check_twins.py`** (M) — locks in the
   shared invariant patterns before twin #19 forgets one.
9. **SVG/stencil export** (S per twin) — users literally ask for Visio stencils;
   the floorplans are already SVG.
10. **Build DellPowerScale** (L) — completes the storage family, and the OneFS
    simulator-demand thread makes it the most-wanted twin not yet built.

## Repo-wide

1. **Active tour mode** — full spec in `ACTIVE_TWIN_SPEC.md`; the headline
   improvement. Rollout starts with PowerStore, then the AI Factory quartet as a
   connected mini-series. (L for the pilot, M per twin after.)
2. **Port registry** — ports are assigned in prose across CLAUDE.md and have
   collided twice (8005/5178, 8006/5179). Add `ports.json` at the repo root as
   the source of truth; every `start_backend.sh`/`start_frontend.sh` reads it and
   fails loudly on conflict; CLAUDE.md keeps only a pointer. (S)
3. **Landing hub** — static `index.html` at the repo root listing every twin
   (name, one-idea line, ports, run command, screenshot), grouped as CLAUDE.md
   groups them: chassis twins, subsystem/SaaS twins, the AI Factory quartet, the
   adversarial pair, spec-only. No backend; plain HTML in the Dell clean-design
   skin. (S)
4. **Shared-pattern lint** — the twins deliberately share no code but do share
   contract patterns: AST-checked engine purity, resolvable region ids, credit
   required when a photo is present, unique longest-stage `cycleCost`, monotonic
   phase order. Add `tools/check_twins.py` that walks every `backend/` and
   re-asserts the common contract, so a new twin can't silently drop one. Run it
   in each twin's test suite or standalone. (M)
5. **Real product photos where licensing allows** — only PowerStore and
   Alienware ship local photos today. Work through `RESEARCH_ASSETS.md`: Dell's
   own service-manual figures (Alienware m18 R2, on Dell's CDN) and spec-sheet
   diagrams are the safest additions; editorial photos (STH, StorageReview) need
   permission before shipping in anything public. Keep the honest-SVG rule where
   licensing fails. Every added photo keeps the credit-required test. (S per
   twin)
6. **Glossary endpoint** — every twin spells out vocabulary on first use in
   copy; also expose it as data (`GET /api/glossary`, a static list in a new
   `glossary.py`) and render hover definitions. The tour scripts (§4 of the tour
   spec) then share one glossary source with page copy. (M repo-wide)
7. **Cross-twin links in the UI** — CLAUDE.md documents rich cross-references
   (the quartet, PowerProtect↔CyberDetect, iDRAC↔R760, ProMaxPlus↔GPU roofline).
   Put them on screen: a small "related twins" footer per app, driven by a
   per-twin static list. (S per twin)
8. **SVG/stencil export** — a "Download floorplan" button that serializes the
   anatomy SVG (with credits baked in) to a standalone file. Users ask for Visio
   stencils of exactly these machines. (S per twin)
9. **Build the eight spec-only twins** — NativeEdge, AIDataPlatform,
   TelecomBlocks, ObjectScale, XE7745, AutomationStudio, PowerScale,
   CircularDesign. Recommended order below. (L each)

## Per-twin

Pattern note for every "new scenario/trace" item below: scenarios are new
`Workload`/`Scenario` inputs to the pure engine producing a different trace —
never runtime mutation of a playing trace, never a timer in the engine. The
frontend keeps the clock; tests pin the new trace's invariants the same way the
existing ones do.

### DellPowerEdgeR760
- **Airflow overlay** — why: fanPercent is currently a bare counter; geometry
  can teach it. What: `anatomy.py` gains an airflow path (front→rear vectors as
  data); `ChassisView` animates flow intensity from `fanPercent`; no engine
  change. (M)
- **Failure-injection scenarios** — why: community threads ask about failure
  modes (PSU, DIMM, VCCIO PG voltage faults at POST) and Dell publishes no MTBF.
  What: `simulate()` takes an optional `fault` input; a faulted trace still
  respects phase order but ends degraded (e.g., POST halts with the fault region
  lit); `test_engine.py` gains faulted-trace invariants. (M)
- **Storage-topology view** — why: HBA355-vs-PERC and mixed HDD/NVMe RAID
  confusion is a top thread genre. What: catalog gains controller/backplane
  wiring data; a small diagram on the components page shows which bays route to
  which controller. (M)
- **iDRAC deep link** — why: the twins are companions by design. What: the
  iDRAC region's info popup links to the DellIDRAC twin. (S)

### DellPowerStore
- **Write-path workload** — why: the twin only models power-on; the product's
  signature behavior is the mirrored-NVRAM write ack. What: second trace
  endpoint (`/api/write`) from the same pure engine: host write → both NVRAMs →
  ack → destage; dual-node symmetry test extends to it. (M)
- **Controller failover scenario** — why: community threads on node reboots and
  upgrades dropping a node into service mode. What: scenario input kills node A
  mid-trace; B takes both personalities; symmetry test is *deliberately* relaxed
  for this trace only (the asymmetry is the lesson) with its own invariant: I/O
  never stops. (M)
- **Replication/Metro trace** — why: the top conceptual wall in community
  threads. What: a two-appliance mini-map (like PowerProtect's two sites) with a
  Metro Volume write straddling both; async replication as a second scenario. (L)
- **X-ray photo toggle** — why: four local photos already ship. What: tour-spec
  §7 overlay wiring in `ChassisView`. (S)

### DellAlienware
- **Battery-degradation scenario** — why: "battery lasts 50 minutes" threads;
  an aged pack changes the energy identity's terms. What: `Scenario` gains pack
  health; hybrid kicks in earlier; energy-conservation test still holds exactly
  (the identity is the point). (S)
- **240 W USB-C vs 330 W barrel** — why: real boot-time PD-error threads. What:
  catalog's adapter options gain the USB-C PD path with its lower budget and
  different handshake; the unrecognized-adapter path stays reachable. (S)
- **Probe-the-node diagnostic mode** — why: "plugged in, not charging" threads
  can't distinguish adapter vs DC-in vs battery vs deliberate taper. What: a UI
  mode where clicking a power-path region shows what a multimeter/BIOS would
  report at that node for the current trace state; pure presentation, no engine
  change. (M)
- **Charge-taper beat** — why: "brick stays cool" thread — tapering *is* the
  answer. What: the charge phase's `chargeW` curve tapers near full; copy
  explains it; energy test unchanged. (S)
- **Software-controlled fans** — why: threads where AWCC conflicts stop fans —
  fan control is an EC/software path. What: anatomy notes the EC's role; a
  scenario models a stuck fan-control handoff (thermal mode ignored) without
  breaking the phase machine. (M)

### DellIDRAC
- **Firmware-update lifecycle scenario** — why: the loudest community pain:
  updates regenerate certs (7.00), break FQDN access (5.10), strand sessions.
  What: second trace (`/api/update`): stage → verify → flash → reboot → cert
  regen → recovery path; longest stage is the flash; host stays off; ≤20 W
  invariant carries over. (M)
- **Host power-on epilogue** — why: iDRAC is the R760's brain; the handoff is
  the relationship. What: final tour/trace beat lights the host-facing sideband
  buses and links to the R760 twin; no merged engines — a link, not a
  dependency. (S)
- **License-tier visual diff** — why: capabilities-by-license is the twin's
  catalog thesis; show it. What: tier selector greys blocks/features in and out
  from existing catalog `regionIds`; frontend only. (S)
- **Constrained-BMC scenario** — why: SupportAssist collections hang real
  iDRACs. What: a scenario where a collection saturates the SoC block and the
  UI's responsiveness meter degrades; progressPercent stays monotonic. (M)

### DellPowerMax
- **Credited local images** — why: roadmap note already in CLAUDE.md; research
  found interior/DME material (see `RESEARCH_ASSETS.md`, licensing pending for
  editorial shots; Dell spec-sheet renders are safer). What: local files +
  credit lines; `test_anatomy.py`'s credit-when-photo-present rule applies. (S)
- **Vault drill scenario** — why: vault-to-flash is the twin's signature; let
  the user pull the plug. What: scenario yanks AC mid-I/O; SPS carries the
  flush; the `vault` phase invariants replay under failure. (M)
- **SRDF/Metro mini-map** — why: the zero-RPO use case is text-only today.
  What: second array drawn small beside the first; a write straddles both; new
  invariant: no ack before both arrays hold the write. (L)
- **MMCS/management-topology overlay** — why: "how do I find MMCS IPs" threads.
  What: management network drawn as an overlay layer from anatomy data. (S)

### DellPowerSwitchE3200
- **PoE budget interactive** — why: the "1683 W average" spec-sheet misreading
  thread — the twin's poe-peak invariant answers it; make it manipulable. What:
  UI lets the user plug loads port-by-port until the budget trips; the trace's
  power arithmetic recomputes per scenario; poe-peak test extends. (M)
- **VLT/MLAG HA-pair beat** — why: ex-N2000 admins expect stacking; E3200
  doesn't stack. What: catalog gains an HA topology category (VLT on OS10, MLAG
  on SONiC); a second switch appears in the use-case page's diagram. (M)
- **NOS-swap scenario** — why: the `-ON` disaggregation is the twin's thesis;
  ONIE reinstall proves it. What: scenario reruns the boot trace with the other
  NOS; identical phase order, different `nos` labels — the invariance across the
  swap *is* the lesson. (S)

### DellVxRail
- **Node-add expansion trace with the failure path** — why: the dominant VxRail
  community theme is expansion blocked by version mismatch, plus IPv6-multicast
  discovery failures. What: `/api/nodeadd` trace: discovery → version check →
  (fail: level-set/reimage, the longest stage) → join → rebalance; lockstep
  invariants apply to the surviving four while node five progresses alone. (L)
- **Stretched-cluster view** — why: topology is a catalog line today. What:
  use-case page draws two sites + witness from data. (M)
- **ESA vs OSA visual** — why: the catalog names them; the difference is
  architectural. What: side-by-side datastore internals diagram (data-driven,
  two small anatomies). (M)
- **Licensing note** — why: "what VMware software is included" confusion. What:
  one catalog category clarifying bundled entitlements. (S)

### DellCloudIQ
- **Broken-gateway scenario** — why: "connected but no data" is the top AIOps
  thread type. What: scenario where `transmit` never completes; healthScore
  stays flat at 100 (nothing is being seen — the false-calm is the lesson);
  one-way-flow invariant holds. (M)
- **Lineage in beat one** — why: CloudIQ→APEX AIOps→Dell AIOps rebrand
  confusion is its own thread genre. What: copy edit on the landing page. (S)
- **Observe the fleet** — why: the observability twin observing the simulator
  fleet is the best demo in the repo. What: optional mode where source regions
  poll the other twins' `/api/health`; falls back to canned data when none run;
  the *trace* stays pure — live data feeds the idle dashboard only. (M)
- **Mock REST endpoint** — why: API-discoverability threads. What: `/api/mock`
  serving a small alerts/events payload with a docs panel. (S)

### DellPowerEdgeXE9712
- **Domain-partition scenario** — why: the atomic fuse means more when you see
  the alternative. What: scenario fusing 2×36 instead of 1×72; the atomic-fuse
  invariant applies per-domain (0 → 36, never partial). (M)
- **Power-jump annotation** — why: the gpuinit step's kW leap is the trace's
  biggest number; label it. What: a live watts graph beside the counters with
  the jump annotated; frontend only. (S)
- **IR7000 cross-link** — why: "liquid before silicon" waits on the IR7000's
  verify phase by design. What: the coolant phase's info popup links there. (S)

### DellIR7000
- **Leak-response scenario** — why: leak fear is the visceral objection to
  liquid cooling (even consumer AIO threads show it). What: scenario where a
  sensor trips → branch isolates → its bay's heat rebalances to air; the
  no-tolerance heat-balance identity holds on every step, which is exactly why
  the scenario is convincing. (M)
- **Heat-reuse meter** — why: facility integration is a catalog line; make it a
  number. What: steady phase shows kW recovered to the facility loop. (S)
- **Warm-water economization toggle** — why: supply temperature is the
  operating lever. What: scenario input for supply temp; liquid-share invariant
  (≥85 %) still enforced. (S)

### DellPowerProtect
- **Cleaning/GC beat** — why: "free space is decreasing constantly" is the
  classic Data Domain confusion; deleting ≠ freeing until cleaning runs. What:
  the lifecycle trace gains a `clean` stage; `storedTb` falls only there; a new
  invariant: stored never falls outside a clean stage. Copy explains
  cleanable-vs-freed and the replication interaction. (M)
- **Failed-recovery counterexample** — why: motivates CyberDetect — restoring
  the attack from a copy nobody verified. What: an alternate ending scenario
  restoring a corrupt copy, clearly labeled a counterexample, ending on a link
  to the CyberDetect twin. (M)
- **Retention Lock countdown** — why: immutability is a claim; a timer even
  admins can't shorten is a picture. What: vault region shows the lock clock
  from trace data. (S)

### DellExascale
- **Per-server throughput bars** — why: the fan-out arithmetic is the story;
  show all four addends. What: bars per data server during `feed`; sums match
  `throughputGbps` (asserted in a frontend-consumed field, tested in the
  engine). (S)
- **Straggler scenario** — why: ties to SN6000's incast story. What: one slow
  server drags aggregate throughput; the throughput-requires-fan-out invariant
  gets a degraded-mode variant; cross-link to SN6000's congestion step. (M)

### DellPowerSwitchSN6000
- **Congestion micro-view** — why: "zero drops under stress" earns belief at
  packet level. What: a zoom panel during the congestion step (queue depth, ECN
  marks, PFC pauses) driven by new per-step fields from the pure engine. (M)
- **Fabric-scale slider** — why: `FabricView` already derives the mesh from
  data; prove it. What: 4-leaf vs 8-leaf vs 16-leaf anatomies as data; the
  tier-ordering and matched-count tests run over all of them. (M)
- **CPO vs pluggable beat** — why: the 5× power / 10× reliability CPO claims
  are themselves twin content (community has no coverage yet). What: optics
  catalog category gains the comparison; copy carries the numbers as Dell's. (S)

### DellProMaxPlus
- **Token-stream panel** — why: tokens/sec is the product's felt experience.
  What: a fake generation stream in the UI clocked off the trace cursor
  (frontend-owned clock, unchanged). (S)
- **Three-way contrast mode** — why: the honest comparison (integrated NPU vs
  GPU vs AI-100) is already in the catalog; make it visual. What: side-by-side
  sustained-tokens/sec and watts curves from three canned traces. (M)
- **Quantization arithmetic beat** — why: the 64 GB / 109 B-parameter ≈ 4-bit
  math is the twin's sharpest honest point. What: an on-screen worked example
  in the load phase. (S)

### DellPowerFlex
- **Scale slider** — why: rebuild-gets-faster-with-scale is the product claim;
  let the user move N. What: 6/12/24-node anatomies as data; the
  every-survivor-rebuilds invariant runs at each N; rebuild `cycleCost` falls
  as N rises (new test). (M)
- **Fault-set grouping** — why: rack-aware placement is the catalog's
  protection story. What: nodes gain fault-set bands in the anatomy; mirror
  placement respects them (test). (M)

### DellCyberDetect
- **Guess-the-snapshot game** — why: the blind step's lesson lands hardest
  when the viewer commits to a guess first. What: UI-only interlude at the
  blind step; score revealed at the verdict; `TimelineView`'s `revealed` prop
  discipline is untouched. (S)
- **Dwell-time slider** — why: if dwell exceeds retention there is no clean
  copy — the honest failure. What: scenario input shifts the attack date; one
  setting yields `lastCleanSnapshot = -1` at the verdict, with copy that says
  so plainly. (M)

### DellFortZero
- **Perimeter counterfactual** — why: the absence-of-perimeter argument needs
  its control group. What: a *separate* comparison view (not the Fort Zero map
  — `test_nothing_is_drawn_as_a_perimeter` stays inviolate) replaying the same
  breach against a drawn perimeter and watching it succeed. (M)
- **Policy-latency slider** — why: the catalog already names slow decisions as
  the honest failure mode. What: scenario input; high latency shows requests
  queuing and exceptions accumulating; implicit-trust-grants stays zero. (M)

## Spec-only twins

Add a Tour section to each `initial_spec.md` (storyboards in
`ACTIVE_TWIN_SPEC.md` §8) so each is born tour-capable. Build order, with the
reason:

1. **PowerScale** — completes the storage family; the OneFS-simulator-demand
   thread makes it the most-wanted unbuilt twin.
2. **CircularDesign** — the Concept Luna disassembly is the best possible
   showcase of tour mode; Engadget teardown imagery exists.
3. **ObjectScale** — active community, free Community Edition audience, and
   Dell's own data-path diagrams to trace.
4. **XE7745** — pairs with the XE9712 as the air-cooled contrast; model the
   firmware-power-cap lesson (see community item 12).
5. **NativeEdge** — center the zero-touch onboarding trust chain and its two
   real failure modes (community item 9).
6. **TelecomBlocks** — cluster topology/dimensioning fills a genuine
   documentation vacuum.
7. **AIDataPlatform** — redraw the layer stack the press releases only
   describe in prose.
8. **AutomationStudio** — youngest product; wait for the platform to settle.

## Community-informed additions

From the Dell Community research in `RESEARCH_ASSETS.md` (thread URLs there).
Each item is a real, recurring user confusion that maps to a scenario a twin
should teach:

1. **Validated demand.** A Jan 2026 thread literally asks "Can I get a PowerScale
   OneFS simulator download?" — users want hands-on practice environments. Frame
   and publish the twins as exactly that. Users also repeatedly request Visio
   stencils (R760, ObjectScale threads): add SVG/stencil export of every twin's
   floorplan.
2. **Alienware twin is confirmed on-target.** Real threads show the exact modeled
   behaviors: battery draining to 45% while plugged in under gaming load (hybrid
   supplement), and BIOS reporting the adapter as "Unknown" when the ID pin fails
   (the unrecognized-adapter throttle path). Add: charge-taper explainer ("brick
   stays cool" thread), a probe-the-node "plugged in, not charging" diagnostic
   mode, and software-controlled fans (AWCC conflicts stopping fans).
3. **iDRAC twin: add the firmware-update lifecycle.** The loudest iDRAC theme is
   updates breaking access (cert regeneration at 7.00, FQDN/DNS breakage at 5.10,
   sluggishness after SupportAssist collections). Model update → cert regen →
   recovery (racreset), and the BMC as a resource-constrained subsystem.
4. **PowerProtect twin: add a cleaning/GC beat.** "Free space is decreasing
   constantly" is the classic Data Domain confusion — deleting backups doesn't
   free space until cleaning cycles run, and cleaning interacts with replication.
   The dedupe arithmetic panel should grow a "cleanable vs freed" stage.
5. **VxRail twin: node-add must include the failure path.** The dominant VxRail
   thread is expansion blocked by node/cluster version mismatch (plus IPv6
   multicast discovery failures). The planned node-add trace should model
   discovery → version check → level-set/reimage → join.
6. **E3200 twin: the PoE invariant answers a real thread.** Users misread the
   spec sheet's "1683 W average" as switch draw when it's the PoE budget — the
   twin's poe-peak step should cite this directly. Add a VLT/MLAG HA-pair beat
   (E3200 doesn't stack; ex-N2000 admins expect it to).
7. **PowerStore/PowerFlex: replication is the conceptual wall.** Metro Volume,
   RCG-with-snapshots, and cross-platform (Unity→PowerStore) replication dominate
   questions → add replication traces, not just use-case text.
8. **CloudIQ twin: model the onboarding failure.** "Connected but no data" (OME
   plugin, gateway) is the top AIOps thread type; add a broken-gateway scenario.
   Name the CloudIQ→APEX AIOps→Dell AIOps lineage in beat one — rebrand
   confusion is its own thread genre.
9. **NativeEdge (when built): the trust chain is the story.** Real failures are
   onboarding voucher key mismatch and MTLS/SZTP cert errors — model zero-touch
   onboarding with those two failure modes.
10. **CircularDesign (when built): the trust gap is the story.** Community
    presence of the circular program is trade-in complaints (quote $658 → paid
    $298, device unreturnable) — add a transparent valuation/chain-of-custody
    walkthrough beside the Concept Luna disassembly.
11. **The vacuum products are the highest-value twins.** XE9712, IR7000, Fort
    Zero, SN6000, Lightning/Exascale, TIB, AI Data Platform have essentially zero
    community presence — learners have only press and PDFs. The twins fill a
    genuine education gap; prioritize polishing those and consider publishing
    them.
12. **XE7745 spec should model firmware power caps.** A sibling-server thread
    (R7725 capping the 600 W RTX Pro 6000 at 450 W) is exactly the
    power-budget-vs-GPU lesson the XE7745 twin should teach.
