# Active Digital Twin — Narrated Look-Inside Tour Mode

**Status:** proposed spec (2026-07-24). Applies to every twin in this repo except `GPU/`
(explicitly out of scope per the request, though nothing here prevents it from adopting
the same mode later).

## 1. The idea

Today each twin is a *reactive* simulator: the user presses Play and watches a phase
trace light regions on a schematic. The active twin adds a **guided tour** — a
video-like experience where the twin drives itself: a camera moves across and *into*
the product, layers peel away, regions light up, and a narration track (spoken audio +
captions) explains the architecture beat by beat, synchronized with the existing
simulation trace. The user can sit back and watch it like a video, or scrub, pause,
and take over at any point — which is precisely what a rendered MP4 cannot offer.

## 2. Feasibility

**Yes — and cheaply — because of three properties every twin already has:**

1. **Anatomy is data.** Every twin ships a normalized-coordinate floorplan
   (`anatomy.py`) rendered by a data-driven SVG component. A "camera" is just an
   animated SVG `viewBox`; zooming into the NVRAM module or the CDU is interpolating
   four numbers. No 3D engine, no WebGL, no assets to model.
2. **The simulation is a pure trace.** `simulate()` already emits the full
   `SimState[]`/`PowerOnState[]`/etc. up front. A tour step can therefore pin the
   trace cursor to any step ("hold on the vault flush while I explain it") with no
   engine changes at all.
3. **The clock lives in the frontend.** The repo's core invariant means the tour
   player is just a second, richer clock owner. The engine stays pure; the tour is
   one more pure-data artifact served next to the anatomy.

So the recommended build is a **real-time tour engine inside each app**, not a
pre-rendered video. A true MP4 export is a stretch goal (§9) using the same tour
data — record the SVG to canvas with `MediaRecorder` and mix the narration audio.

**Narration feasibility:** three tiers, all workable offline-first:
- Tier 0 (always on): synchronized **captions** rendered from the tour script.
- Tier 1 (zero dependencies): browser `speechSynthesis` (Web Speech API) speaking
  each step's script. Free, instant, works in Chrome/Edge/Safari; voice quality is
  adequate for a teaching tool.
- Tier 2 (best quality, optional): pre-rendered audio files (one per tour step,
  `frontend/public/tour/<stepId>.mp3`) generated once by any TTS pipeline; the tour
  data carries an optional `audioUrl` per step and the player prefers it when
  present. Step durations then come from the actual audio length.

**Layer peel / look-inside feasibility:** the schematics are flat, but "inside" can
be staged as an ordered **layer stack**: e.g. bezel → fans/airflow → boards/drives →
buses/fabric. Each anatomy region gets a `layer` index; the tour's camera steps can
set layer opacity (outer layers fade to 10–20% ghost outlines) and a small
"explode" translation per layer (outer layers slide outward a few units). This is
CSS/SVG transform animation on existing shapes — no new art required. Where we have
real interior photography (see `RESEARCH_ASSETS.md`), a step can cross-fade a
credited photo behind the schematic at the same camera framing — an "X-ray toggle"
between the real product and the mental model.

## 3. Architecture (shared across all twins)

Same split as everything else in the repo: **the tour is backend data; the frontend
owns the clock.**

```
backend/app/tour.py        pure data: build_tour(anatomy) -> Tour   (+ tests/test_tour.py)
backend/app/main.py        GET /api/tour -> TourResponse
frontend/src/components/
  TourPlayer.tsx           the second clock owner: transport bar, scrubber, step list
  CameraRig.tsx            viewBox tween (ease-in-out, honors prefers-reduced-motion)
  NarrationChannel.ts      captions always; speechSynthesis or audioUrl playback
  LayerStack support       in the existing *View components: layer opacity + explode offset props
frontend/public/tour/      optional per-step audio (tier 2)
```

Route: a fourth page/tab `#tour` (deep-linkable, like `#anatomy`), plus a
"▶ Guided tour" button on the landing sim page.

## 4. Data model

Pydantic (camelCase aliases, same conventions as everything else) mirrored in
`types.ts`:

```python
class CameraTarget(BaseModel):
    x: float; y: float; w: float; h: float   # viewBox in the anatomy's normalized space
    # must lie within the map bounds (test-enforced)

class TourStep(BaseModel):
    id: str                      # stable, kebab-case; keys the optional audio file
    title: str                   # short beat title shown in the step list
    script: str                  # narration text; also the caption text; spells out
                                 # vocabulary on first use, per repo copy rules
    camera: CameraTarget
    region_ids: list[str]        # regions to light; every id must resolve (test)
    layer_reveal: int            # 0 = whole product, N = peel to layer N
    trace_cursor: int | None     # pin the sim trace to this state while the step plays
    duration_ms: int             # tier-0/1 fallback; ignored when audio is present
    photo_id: str | None         # optional credited photo overlay (X-ray view)
    audio_url: str | None        # tier-2 pre-rendered narration

class Tour(BaseModel):
    id: str; title: str; intro: str
    steps: list[TourStep]
    sources: list[Source]        # same Source shape the anatomy pages use
```

## 5. Player behavior

- **One clock.** `TourPlayer` owns a single `requestAnimationFrame` timeline; when a
  step pins `trace_cursor`, it drives the *existing* playback cursor (the sim page's
  state is lifted or shared via App). The engine and trace are untouched.
- **Transport:** play/pause, next/prev step, scrub bar with step tick marks,
  playback speed (0.75×–2×; speechSynthesis honors `rate`, audio uses
  `playbackRate`).
- **Captions always on** (toggleable position, not toggleable off silently — the
  script *is* the content; audio is an enhancement). Audio starts muted until the
  user interacts (autoplay policy).
- **Take-over:** clicking any region or switching tabs pauses the tour and leaves
  the camera where it is; "Resume tour" returns to the active step's framing.
- **Reduced motion:** `prefers-reduced-motion` swaps camera tweens for cuts and
  disables the explode translation (layers fade only).
- **Dell clean-design skin** for all chrome; the schematic stays dark — it is the
  diagram. No eyebrow text, no step numbering in copy (the step list is a list of
  titles, not "Step 1/2/3" labels).

## 6. Invariants and tests (`tests/test_tour.py`, same style as the rest)

- `build_tour()` is pure — AST-checked like the engines (no IO/FastAPI imports).
- Every `region_ids` entry resolves against the anatomy; every `photo_id` resolves
  against shipped, credited photos; credit is required whenever a photo is present.
- Every camera box lies inside the map bounds and has positive area; consecutive
  steps' boxes overlap or the tween distance is bounded (no teleporting).
- `layer_reveal` is monotonic non-decreasing until the tour's "reassemble" beat (a
  tour peels inward, then closes back up — enforced as: at most one decrease, at the
  final step).
- When `trace_cursor` is set it is a valid index and **monotonic non-decreasing**
  across steps — the tour never runs the simulation backwards.
- Every step's `script` is non-empty and total tour length (sum of `duration_ms`)
  lands in 2–6 minutes.
- Each twin's tour must include its **signature step** (see §8) — a named step id
  the test asserts exists, so the tour cannot ship without the product's one idea.

## 7. Photos from research (`RESEARCH_ASSETS.md`)

Tour steps may overlay real product photography where licensing allows. Rules,
consistent with existing repo practice: photos are downloaded into
`frontend/public/` (no hotlinking except the GPU twin's established Wikimedia
pattern), every photo carries a rendered credit line, and tests forbid external
photo URLs. Products with no license-safe interior photography keep the schematic
only — the honestly-credited-illustration rule already in force.

## 8. Per-twin tour storyboards (the specs "for all the above")

Each tour is 6–9 beats. Beat 1 is always the exterior ("what is this thing"), beat 2
peels the first layer, and the **bolded beat** is the signature step whose id the
tests pin. Scripts live in `tour.py`; these are the storyboards they implement.

| Twin | Tour beats (camera → narration) | Signature step id |
|---|---|---|
| DellPowerEdgeR760 | Front bezel → drive bay → peel lid: airflow shroud, fans → DIMMs/CPUs (**dwell on DDR5 memory training with trace pinned**) → PERC/BOSS-N1 → iDRAC corner ("meet the brain — see its own twin") → reassemble | `memory-training` |
| DellPowerStore | 2U front, 25 NVMe slots → peel: the two controller nodes as mirrored twins → NVRAM + BBU (**write lands in both NVRAMs before the ack — camera splits across `-a`/`-b`**) → dual-ported drives → cluster/services phases → reassemble | `mirrored-ack` |
| DellAlienware | Closed laptop + 330 W brick → adapter internals → 1-Wire PSID handshake (**pin the stalled handshake state; explain the throttled path if unrecognized**) → power budget split CPU/GPU → battery hybrid supplement under load → charge ramp | `psid-handshake` |
| DellIDRAC | R760 exterior with host **off** → zoom to the one warm corner → block diagram: sideband buses left, SoC center → Root of Trust boot chain → **Lifecycle Controller init (longest stage, pinned)** → ready-and-watching, host still off | `always-on` |
| DellPowerMax | Rack elevation → node-pair engine → directors `-a`/`-b` → global-memory DRAM → **vault-to-flash: SPS carries the flush on power loss (pin vault phase)** → InfiniBand fabric out to the DME → drives are *not* on a director's bus → online | `vault-to-flash` |
| DellPowerSwitchE3200 | Front panel 48 ports → peel: ASIC as the actual switch, CPU as its manager → ONIE → NOS choice (OS10/SONiC) → ASIC tables programmed → **PoE: the power peak leaves through the front ports** → line rate | `poe-peak` |
| DellVxRail | Four-node rack elevation → one node's interior (it's a PowerEdge) → lockstep ESXi boot → discovery → **primary election: exactly one node breaks lockstep** → vSAN fuses local NVMe into one datastore → online | `primary-election` |
| DellCloudIQ | No box: the estate → Secure Connect Gateway → ingest → **ML analyze (longest stage): health score dips as the anomaly is found** → insight → AIOps Assistant → notify; telemetry flows one way | `analyze-dip` |
| DellPowerEdgeXE9712 | Rack exterior, no fans audible → coolant manifold first (**liquid before silicon**) → GB200 tray: 2 Grace + 4 Blackwell → mid-rack NVLink switch trays, why they sit centrally (copper reach) → fabric training (longest) → **the atomic fuse: 72 GPUs become one** → ready | `atomic-fuse` |
| DellIR7000 | The rack as plumbing → CDU internals → supply/return manifolds → cold plates over generic heat → **heat balance: liquid + air = IT load, exactly, on every step** → eRDHx catches the rest → facility loop / heat reuse | `heat-balance` |
| DellPowerProtect | Two sites, left/right → backup lands → **dedupe arithmetic: logical vs stored diverge on screen** → the gap opens *from the vault side* only → seal → CyberSense scan (longest) → the attack hits production, the vault is unreachable → recover from the vault | `airgap-discipline` |
| DellExascale | Client rack ↔ storage rack → mount: **the metadata server answers once, then leaves the picture** (camera literally moves it out of the data path) → stripes fan out across all four data servers → 6 TB/s aggregate → checkpoint burst → tier | `metadata-leaves` |
| DellPowerSwitchSN6000 | Leaf/spine mesh from above → one SN6000: 1.6 Tb/s ports, CPO vs pluggable optics → link training (longest) → collective traffic → **congestion at 95% on the hot link, and still zero drops** → adaptive reroute cools it without losing throughput | `zero-drops-under-stress` |
| DellProMaxPlus | Laptop exterior → peel: host side / PCIe strip / card side as three rooms → **the weights cross the PCIe strip exactly once** → 64 GB on-card pool pins them → prefill vs decode → host goes idle → pull the network cable: nothing changes | `weights-cross-once` |
| DellPowerFlex | Six ordinary servers, no controller row (**camera pans the empty space where the controller isn't**) → chunk scatter (longest, on purpose) → steady I/O, coordinator dark → a node dies mid-tour → every survivor rebuilds at once → faster with scale | `no-controller` |
| DellCyberDetect | Seven snapshots as a timeline → intrusion lands; timeline looks identical (**the blind step: the viewer genuinely cannot tell which are corrupt**) → byte-level inspection (longest) → confidence climbs only now → the verdict is a date → recover from the named copy | `blind-then-read` |
| DellFortZero | Seven co-equal pillars, no perimeter drawn → a request arrives → all seven pillars feed the decision → grant is a lease with a TTL → **the breach: attacker holds a position a perimeter would honor — and reaches nothing** → monitoring never stops (longest) | `breach-reaches-nothing` |
| DellNativeEdge (spec'd) | Factory floor → zero-touch onboarding of an edge node → blueprint push → fleet view; storyboard finalized when the twin is built | `zero-touch` |
| DellAIDataPlatform (spec'd) | Data estate → unstructured ingest → vector/index layer → serving to the AI factory; finalized when built | `ingest-to-serve` |
| DellTelecomBlocks (spec'd) | Cell site → far-edge server → CU/DU split → Wind River/Red Hat stack layers; finalized when built | `ran-split` |
| DellObjectScale (spec'd) | Bucket API in → erasure-coded spread across nodes → durability math on screen; finalized when built | `erasure-spread` |
| DellPowerEdgeXE7745 (spec'd) | 4U front → 8 double-wide GPU bay → air-cooled density limits vs the XE9712's liquid answer; finalized when built | `air-density` |
| DellAutomationStudio (spec'd) | Blueprint canvas → generated workflow → fleet rollout; finalized when built | `blueprint-to-fleet` |
| DellPowerScale (spec'd) | OneFS cluster → a file striped across nodes → node add = capacity+performance; finalized when built | `onefs-stripe` |
| DellCircularDesign (spec'd) | Concept Luna device → **disassembly tour: every fastener count shown** → material streams out → back into a new chassis | `disassembly` |

## 9. Stretch: true video export

Same tour data, no second authoring pass: render the SVG stage to a hidden
`<canvas>` per frame, capture with `canvas.captureStream()` + `MediaRecorder`,
mix Tier-2 audio via `AudioContext`, produce a WebM (MP4 via ffmpeg.wasm if
needed). Ship as a "Download this tour" button. Do this once, in one twin
(PowerStore — it has real local photos), before generalizing.

## 10. Rollout

1. Build the shared player + `tour.py` pattern in **DellPowerStore** (has local
   photos, dual-node drama, small anatomy) — 1 twin end-to-end including tests.
2. Extract the frontend player as a copy-in pattern (this repo deliberately keeps
   twins independent; no shared package).
3. Roll to the AI Factory quartet next (XE9712, IR7000, Exascale, SN6000) — their
   cross-references make the four tours a connected mini-series.
4. Then the remaining built twins; spec-only twins adopt the tour section in their
   `initial_spec.md` so they're born with one.
