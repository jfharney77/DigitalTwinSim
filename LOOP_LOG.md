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

**Next iteration should avoid**: Pro Max Plus, NativeEdge, AI Data
Platform / Data Lakehouse, and everything in the pre-loop list. Candidate
areas not yet explored: APEX cloud platforms and APEX File Storage for
Azure, PowerFlex software-defined block, ObjectScale, PowerScale as its own
subject, Dell Automation Platform, Precision workstations, Dell Managed
Detection and Response / security portfolio, PowerVault entry storage,
Dell Telecom/Open RAN infrastructure, XE7745 and other AI server SKUs.
