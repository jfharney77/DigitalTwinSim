# Twin-discovery loop log

A self-paced loop: each iteration researches Dell product lines not yet
twinned in this repo, picks the three most interesting, writes a spec for
each, and fully builds one. Five iterations planned.

Each iteration must pick products not already listed here.

## Already twinned before the loop started (14)

GPU, DellPowerEdgeR760, DellPowerStore, DellAlienware, DellIDRAC,
DellPowerMax, DellPowerSwitchE3200, DellVxRail, DellCloudIQ,
DellPowerEdgeXE9712, DellIR7000, DellPowerProtect, DellExascale,
DellPowerSwitchSN6000.

---

## Iteration 1 — 2026-07-24

**Research**: dell.com newsroom and product pages (AI Factory 2026
announcements, NativeEdge, Data Lakehouse, APEX), corroborated with the
Qualcomm Cloud AI SDK architecture docs, arXiv 2507.00418 (Cloud AI 100
Ultra vs NVIDIA data-center GPUs), and trade coverage of the Pro Max Plus
launch.

**Top three picks**

| Pick | Product | The one idea | Outcome |
|---|---|---|---|
| 1 | **Dell Pro Max 16 Plus** + Qualcomm AI 100 PC Inference Card | The weights never move — a 109B model crosses PCIe once and stays resident | **Built** → `DellProMaxPlus/`, ports 8013/5186 |
| 2 | **Dell NativeEdge** | Nobody touches the device — the endpoint provisions itself | Spec → `DellNativeEdge/initial_spec.md`, ports 8014/5187 |
| 3 | **Dell AI Data Platform / Data Lakehouse** | The bottleneck moved from storage to meaning | Spec → `DellAIDataPlatform/initial_spec.md`, ports 8015/5188 |

**Why the Pro Max Plus was built first**: it is the sharpest contrast with
everything already in the repo. Thirteen of the fourteen existing twins are
datacenter infrastructure whose subject is moving data quickly; this one's
subject is refusing to move data at all, which makes it the cleanest new
idea rather than a variation on an existing one. It also completes a pair
with the GPU twin's roofline analysis (decode is exactly that twin's
memory-bound regime, reached from the opposite direction) and with the
Alienware twin's laptop power path.

**Result**: 36 backend tests pass, frontend builds clean, all four API
endpoints verified serving.

**Ports taken so far**: 8013/5186 (built). Reserved by spec: 8014/5187,
8015/5188.

---

## Iteration 2 — 2026-07-24

**Research**: dell.com May 2026 newsroom ("Reimagines the Modern Data
Center for the AI Era"), the PowerFlex product page and Dell's technical
overview of rebuild, WWT's PowerFlex 5.0 Ultra write-up, and Dell's
Telecom Infrastructure Blocks pages plus RCR Wireless' Cloud Core
coverage.

**Top three picks**

| Pick | Product | The one idea | Outcome |
|---|---|---|---|
| 1 | **Dell PowerFlex 5.0 Ultra** | There is no controller — every survivor rebuilds a sliver at once | **Built** → `DellPowerFlex/`, ports 8016/5189 |
| 2 | **Dell Telecom Infrastructure Blocks (Open RAN)** | The deadline is the product, not the rate | Spec → `DellTelecomBlocks/initial_spec.md`, ports 8017/5190 |
| 3 | **Dell ObjectScale** | It scales because it gave up the tree | Spec → `DellObjectScale/initial_spec.md`, ports 8018/5191 |

**Why PowerFlex was built first**: it argues directly with two twins
already here. PowerStore and PowerMax are controller architectures whose
engineering is about making centrality survivable; PowerFlex deletes the
centre. That gives the repo a genuine three-way comparison rather than a
third storage twin. It also let this twin deliberately invert the repo's
usual `cycleCost` pattern — every other twin dwells on a recovery-ish
stage, and this one dwells on *setup*, because scattering chunks in
advance is exactly what makes the repair short.

**Result**: 37 backend tests pass, frontend builds clean, all four API
endpoints verified serving.

**Ports taken so far**: 8013/5186, 8016/5189 (built). Reserved by spec:
8014/5187, 8015/5188, 8017/5190, 8018/5191.

**Next iteration should avoid**: everything in the pre-loop list, plus
Pro Max Plus, NativeEdge, AI Data Platform / Data Lakehouse, PowerFlex,
Telecom Infrastructure Blocks / Open RAN, ObjectScale. Candidate areas
still unexplored: PowerScale / OneFS as its own subject, APEX cloud
platforms and APEX File Storage for Azure, Dell Automation Platform and
Automation Studio (June 2026), Dell Cyber Detect for PowerStore/PowerMax
(Q3 2026 — in-array ransomware detection, distinct from the PowerProtect
vault twin), PowerProtect One, Precision fixed workstations, PowerVault
entry storage, PowerEdge XE7745 and other AI server SKUs, Dell Managed
Detection and Response, and Dell's sustainability/circular-design
programs.
