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

---

## Iteration 3 — 2026-07-24 (fired early at the user's request)

**Research**: Dell's Cyber Detect product page and the "recovery starts on
primary storage" blog, the May 2026 data-center announcement, Dell's
PowerMax cybersecurity info hub, the XE7745 spec sheet, and the Automation
Platform / Automation Studio pages.

**Top three picks**

| Pick | Product | The one idea | Outcome |
|---|---|---|---|
| 1 | **Dell Cyber Detect** | It reads the data, not the metadata — and the answer is a date, not an alert | **Built** → `DellCyberDetect/`, ports 8019/5192 |
| 2 | **Dell PowerEdge XE7745** | The same watts, spent two ways (8×600 W or 16×75 W) | Spec → `DellPowerEdgeXE7745/initial_spec.md`, ports 8020/5193 |
| 3 | **Dell Automation Studio** | The gap between the drawing and the rack | Spec → `DellAutomationStudio/initial_spec.md`, ports 8021/5194 |

**Why Cyber Detect was built first**: it closes a question the
PowerProtect twin deliberately leaves open. That twin models the isolated
vault and answers "will a copy survive?"; it cannot answer "which copy?",
and a vault full of faithfully replicated, immutably locked corruption has
protected nothing. Cyber Detect is also the first twin here whose subject
is *adversarial* — the attack is designed against the detector — which let
the trace carry an invariant no other twin could: a counter that stays at
zero not because the system is healthy but because it is being fooled.

**Novel technique in this twin**: `TimelineView.tsx` takes a `revealed`
prop, so corrupted snapshots are drawn identically to clean ones until
content analysis has run. Pausing on the blind step shows a timeline a
viewer genuinely cannot read — which is the administrator's actual
position. Marking corruption early would have undone the lesson.

**Result**: 37 backend tests pass, frontend builds clean, all four API
endpoints verified serving.

**Ports taken so far**: 8013/5186, 8016/5189, 8019/5192 (built). Reserved
by spec: 8014/5187, 8015/5188, 8017/5190, 8018/5191, 8020/5193,
8021/5194.

**Next iteration should avoid**: everything in the pre-loop list, plus
Pro Max Plus, NativeEdge, AI Data Platform / Data Lakehouse, PowerFlex,
Telecom Infrastructure Blocks / Open RAN, ObjectScale, Cyber Detect,
XE7745, Automation Studio.

---

## Iteration 4 — 2026-07-24 (fired early at the user's request)

**Research**: Dell's April 2025 DoD zero-trust validation announcement and
the Zero Trust landing page, the PowerScale/OneFS product overview and
scalability docs, and Dell's circular-economy and sustainable-devices
pages.

**Top three picks**

| Pick | Product | The one idea | Outcome |
|---|---|---|---|
| 1 | **Dell Project Fort Zero** | There is no inside | **Built** → `DellFortZero/`, ports 8022/5195 |
| 2 | **Dell PowerScale / OneFS** | There are no volumes | Spec → `DellPowerScale/initial_spec.md`, ports 8023/5196 |
| 3 | **Dell circular design & Asset Recovery** | Every other twin ends at "steady"; this one doesn't end | Spec → `DellCircularDesign/initial_spec.md`, ports 8024/5197 |

**Why Fort Zero was built first**: it inverts the repo's dominant idiom.
Seventeen twins carry their lesson in a boundary — a PCIe strip, an air
gap, a band of nodes with nothing above it — and this one carries its
lesson in the *absence* of one, with a geometry test forbidding any region
large enough to act as a perimeter. It is also the second adversarial twin
(after Cyber Detect) and fails differently: there, detection is defeated;
here, lateral movement is.

**Note on the runner-up**: the circular-design spec is the structurally
most novel thing found so far — the only twin whose trace would *close*
rather than end, with a mass-conservation invariant deliberately modelled
on the IR7000's heat balance. It was not built first only because Fort
Zero is a harder, more technical subject. It carries an explicit tone
guard in its spec, because it is the twin most at risk of reading as a
brochure.

**Result**: 37 backend tests pass, frontend builds clean, all four API
endpoints verified serving.

**Ports taken so far**: 8013/5186, 8016/5189, 8019/5192, 8022/5195
(built). Reserved by spec: 8014/5187, 8015/5188, 8017/5190, 8018/5191,
8020/5193, 8021/5194, 8023/5196, 8024/5197.

**Next iteration (5 of 5, the last) should avoid**: everything above,
plus Fort Zero, PowerScale/OneFS, and circular design. Candidate areas
still unexplored: APEX cloud platforms and APEX File Storage for Azure,
PowerProtect One, Precision fixed workstations, PowerVault entry storage,
Dell Managed Detection and Response, Dell Private Cloud, the Dell Pro /
Latitude commercial-client line, Dell's services and residency programs,
and Dell displays/peripherals. Iteration 5 should also close the loop:
summarize what the five iterations produced and which specs remain
unbuilt.
