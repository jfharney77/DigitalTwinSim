# GPU Matmul Visualizer — Project Spec

**Status:** v0.1 (foundation)
**Goal:** An interactive web app that draws the inner structure of a GPU and animates how a matrix multiplication executes across it. Generic/architecture-agnostic for now; built to grow toward real fidelity (tiling, tensor cores, memory bottlenecks).

---

## 1. Vision & scope

### What this is
A teaching/visualization tool. A user picks a small matmul workload, presses Run, and watches operands stream from memory into compute units, MACs accumulate across cores in parallel, and results flush back. Counters expose utilization, MAC progress, and cycle count.

### What this is NOT (yet)
- Not a cycle-accurate simulator. Timing is illustrative, not modeled from real latencies.
- Not tied to a specific vendor ISA (CUDA/ROCm/etc.). "CUDA core", "SM", "warp" are used as generic vocabulary and can be swapped per architecture profile later.
- Not performance-bound — it renders tens to low-hundreds of elements, not real GPU-scale tensors.

### Guiding principles
1. **Correct mental model over correct numbers.** The animation should teach how matmul maps to hardware, even where timing is simplified.
2. **Separation of concerns.** The hardware model, the simulation engine, and the rendering layer are independent. You can swap the renderer (SVG → Canvas/WebGL) or the workload without touching the others.
3. **Deterministic & steppable.** The sim is a pure state machine advanced by `step()`. Same inputs → same trace. No animation logic baked into simulation state.
4. **Profiles, not hardcoding.** Die dimensions (SM count, cores/SM, memory layout) come from a config object so new "GPU profiles" are data, not code.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│  UI layer (controls, counters, legend)              │
│  - emits: workload params, run/step/reset, speed    │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│  Simulation engine (pure, deterministic)            │
│  - input: GpuProfile + Workload                     │
│  - state: phase, k, macDone, perCoreState[]         │
│  - api: init(), step() -> SimState, isDone()        │
└───────────────┬─────────────────────────────────────┘
                │ SimState (plain data)
┌───────────────▼─────────────────────────────────────┐
│  Renderer (reads SimState, draws die)               │
│  - drawStatic(profile)  : die, SMs, cores, memory   │
│  - paint(simState)      : per-frame colors/labels   │
└─────────────────────────────────────────────────────┘
```

### Module breakdown (target structure)
```
src/
  model/
    profile.ts        // GpuProfile type + default profiles
    workload.ts       // Workload type (matmul dims, dtype)
  sim/
    engine.ts         // pure state machine: init/step/isDone
    mapping.ts        // maps output cells -> physical cores
    phases.ts         // LOAD / COMPUTE / WRITEBACK definitions
  render/
    die.ts            // static SVG/Canvas die layout
    paint.ts          // applies SimState -> visuals
    legend.ts
  ui/
    controls.ts       // sliders, buttons, wiring
    counters.ts
  app.ts              // composition root: wires the three layers
```

---

## 3. Data models

### GpuProfile
Describes the die. Everything visual/structural derives from this.
```ts
interface GpuProfile {
  name: string;              // "Generic-128"
  sm: { rows: number; cols: number };       // grid of SMs (e.g. 2x4 = 8)
  coresPerSM: { rows: number; cols: number };// e.g. 4x4 = 16
  memory: {
    stacks: number;          // HBM stacks (e.g. 2, drawn on edges)
    label: string;           // "HBM"
  };
  hasL2Bus: boolean;
  // future: tensorCores?, registerFileKB?, sharedMemKB?, clockGHz?
}
```
`totalCores = sm.rows*sm.cols * coresPerSM.rows*coresPerSM.cols`

### Workload
```ts
interface Workload {
  kind: "matmul";
  N: number;        // square N×N · N×N for now (generalize to M,K,N later)
  dtype: "fp32";    // future: fp16, bf16, int8 (changes tensor-core path)
}
```
Total MACs for square matmul = `N * N * N` (N² output cells, N MACs each).

### SimState (emitted each step; pure data the renderer consumes)
```ts
interface SimState {
  cycle: number;
  phase: "idle" | "load" | "compute" | "writeback" | "done";
  k: number;                 // current accumulation step (0..N)
  macDone: number;
  macTotal: number;
  memActive: boolean;
  coreState: CoreState[];    // length = totalCores
  activeCores: number;
  utilization: number;       // 0..1
}
type CoreState = "idle" | "loading" | "computing" | "wrote";
```

---

## 4. Simulation model (current, simplified)

Output cell `C[i][j] = Σ_k A[i][k]·B[k][j]`. The engine walks three phases:

1. **LOAD** — operand tiles conceptually move HBM → shared memory. Memory highlights; cores show `loading`. One step.
2. **COMPUTE** — `N` accumulation steps. On each k-step, every mapped core performs one MAC for its output cell(s) in lockstep. `macDone += N²` per step. Cores show `computing`.
3. **WRITEBACK** — results flush to C. Cores flash `wrote`. Phase → `done`.

**Cell→core mapping** (`mapping.ts`): round-robin, `core = (i*N + j) % totalCores`. This is deliberately naive — see roadmap for real warp/tile scheduling.

**Determinism:** `step()` is a pure function of current `SimState`. No timers inside; the UI layer owns the clock (setInterval / rAF) and just calls `step()`.

---

## 5. Rendering spec

- **Static layer** drawn once from `GpuProfile`: die substrate, HBM stacks on left/right edges, L2/interconnect bus across the top, SM grid, per-SM shared-memory strip + warp-scheduler tick, core grid inside each SM.
- **Dynamic layer** = `paint(simState)`: recolor cores by `CoreState`, toggle memory highlight, update phase label + counters. No geometry recomputed per frame.
- **Current impl:** inline SVG, hand-built via DOM. Fine up to a few hundred cores. If profiles scale past ~1k cores, migrate `render/` to Canvas2D or WebGL behind the same `drawStatic`/`paint` interface.

### Visual language (keep stable across versions)
| State / element     | Color token        | Meaning                    |
|---------------------|--------------------|----------------------------|
| memory active       | `--mem-active`     | HBM transfer in flight     |
| core computing      | `--core-on` amber  | MAC executing              |
| core wrote          | `--core-hot` orange| result written to C        |
| core idle           | `--core-off`       | lane idle                  |

---

## 6. UI contract

**Inputs:** matrix size N (slider), Run / Step / Reset, speed slider.
**Outputs (counters):** cycle, MACs done / total, active cores, utilization %, current phase string.
**Behavior:** changing N resets the sim. Speed retunes the interval live. Step pauses any running loop and advances exactly one phase-step.

---

## 7. Roadmap (priority order)

**Near term**
1. Generalize `Workload` from square `N` to `M × K × N`.
2. Show the actual A / B / C matrices beside the die, filling in as MACs complete.
3. Real **tiling**: block the matmul, stream tiles HBM → shared mem → registers, visualize reuse.

**Mid term**
4. **Tensor-core mode**: systolic-array animation (data marching through a PE grid) vs. the current scalar-core mode; gated by `dtype`.
5. Memory-bandwidth model: make LOAD duration depend on tile size / dtype to show memory-bound vs. compute-bound regimes.
6. Multiple `GpuProfile`s selectable from a dropdown (small/large dies).

**Longer term**
7. Approximate cycle/latency model for a "roofline"-style readout.
8. Warp scheduling + occupancy visualization (warps per SM, stalls).
9. Export trace (JSON) and step scrubber (timeline you can drag).

---

## 8. Tech notes for Claude Code

- **Current artifact** is a single `gpu-sim.html` (inline SVG + vanilla JS). Treat it as the working reference implementation / behavior oracle, not the target architecture.
- **First refactor task:** split that file into the `src/` module layout above. Suggested stack: Vite + TypeScript, no heavy framework needed; the three-layer split keeps it framework-optional. React is fine if you want it for the controls panel.
- **Keep the sim engine framework-free and pure** so it stays unit-testable. Write tests against `step()` traces (e.g. "for N=4, after compute phase macDone === 64; macTotal === 64").
- **Invariants to assert in tests:** `macDone <= macTotal`; `activeCores <= totalCores`; phases advance idle→load→compute→writeback→done with no skips; `utilization === activeCores/totalCores`.
- **Don't bake animation timing into SimState.** UI owns the clock.

---

## 9. Open questions

- How realistic should timing get before it's misleading? (Pick a fidelity ceiling and document it.)
- One unified renderer, or separate "scalar core" and "systolic array" views?
- Do we want to support non-square and non-power-of-two dims in the visual grid early, or defer?
