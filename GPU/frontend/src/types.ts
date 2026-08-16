// Mirrors the backend pydantic models (camelCase JSON). See backend/app/models.py.

export type Phase =
  | "idle"
  | "load"
  | "compute"
  | "writeback"
  | "exchange" // spec_27: the all-gather over the die-to-die link
  | "done";
export type CoreState = "idle" | "loading" | "computing" | "wrote" | "mma"; // spec_23
export type DType = "fp32" | "fp16" | "bf16" | "int8" | "fp8" | "fp4"; // spec_04 + 23
export type Regime = "memory" | "compute";
export type Execution = "cuda" | "tensor"; // spec_23

// spec_23: illustrative MMA capability; absent => no tensor path. The
// multipliers key set is the die's supported-dtype declaration.
export interface TensorSpec {
  unitsPerSM: number; // drawn, not simulated per-unit (alias gotcha: SM caps)
  mmaM: number;
  mmaN: number;
  mmaK: number;
  multipliers: Partial<Record<DType, number>>;
}

export interface SMGrid {
  rows: number;
  cols: number;
}

export interface GpuProfile {
  name: string;
  sm: SMGrid;
  coresPerSM: SMGrid;
  memory: { stacks: number; label: string };
  hasL2Bus: boolean;
  bandwidth?: { bytesPerCycle: number; macsPerCycle: number };
  // Per-SM residency limits (spec_24; Ada defaults backend-side). Same casing
  // as DeviceInfo below — plain to_camel, no PerSM alias.
  maxThreadsPerSm?: number;
  maxBlocksPerSm?: number;
  warpSize?: number;
  // spec_23: null/absent = scalar-only die (tensor requests 422).
  tensor?: TensorSpec | null;
  // spec_30: the anatomy tab's DieAnatomy id this profile draws, or null —
  // the generics are abstractions and the 4060's AD107 has no entry yet.
  dieId?: string | null;
  // spec_25: illustrative power constants (fleet ratios honest, watts not).
  power?: { idleW: number; laneW: number; byteW: number };
  // spec_27: die-to-die link. null/absent = no scale-up path (gpus=2 422s);
  // rates illustrative, ratios honest (NVLink5 = 2x NVLink4).
  link?: { label: string; bytesPerCycle: number } | null;
}

export type WorkloadKind = "matmul" | "mlp_step" | "llm_decode";

export interface Workload {
  kind: WorkloadKind;
  N: number;
  // Rectangular matmul (spec_22): A is M×K, B is K×N, C is M×N.
  // 0 (or omitted) means "= N" — the square default. mlp_step is square-only.
  M?: number;
  K?: number;
  dtype: DType;
  seed?: number;
  tileSize?: number;
  doubleBuffer?: boolean;
  steps?: number; // SGD steps for mlp_step (spec_06)
  // spec_24: threads per block; 0 (or omitted) = derived (one tile = one
  // block). Feeds the occupancy read-out only — never the trace.
  blockSize?: number;
  // LLM decode (spec_26): starting KV-cache length (8–64) and the prefill
  // contrast switch. Ignored by other kinds.
  kvLen?: number;
  prefill?: boolean;
  // spec_23: "cuda" (default) is the scalar path, byte-for-byte unchanged;
  // "tensor" steps whole mmaK-rank MMA chunks per state.
  execution?: Execution;
  // spec_27: 1 (default) or 2 — split C's rows across two dies of this
  // profile, then pay an explicit exchange over the link. matmul only.
  gpus?: number;
}

export interface SimState {
  cycle: number;
  phase: Phase;
  k: number;
  macDone: number;
  macTotal: number;
  memActive: boolean;
  coreState: CoreState[];
  activeCores: number;
  utilization: number;
  // Tiling context (spec_03); null outside a tile. Indices are in tile units.
  tileRow: number | null;
  tileCol: number | null;
  kTile: number | null;
  // Bandwidth model (spec_04)
  stalled: boolean;
  cycleCost: number;
  // Double-buffering (spec_05): next tile loading in the background during compute
  prefetching: boolean;
  // MLP op context (spec_06); null for plain matmul workloads. opIndex is
  // global across steps (stepIndex * opsPerStep + position).
  opIndex: number | null;
  opCount: number | null;
  opName: string | null;
  stepIndex: number | null;
  // spec_23: this compute step is one MMA instruction (the owning SM lights
  // as a block) consuming ranksPerStep k-ranks at once.
  mma: boolean;
  ranksPerStep: number | null;
  // spec_25: illustrative watts this state burns; joules at the cursor are
  // the replay-to-cursor sum of powerWatts × cycleCost.
  powerWatts: number;
  // spec_27: which die this state's coreState[] describes. null for
  // single-GPU traces and the shared idle/exchange/done states.
  gpu: number | null;
}

// --- MLP training step (spec_06) ---

export interface MlpOp {
  name: string;
  kind: "matmul" | "pointwise";
  a: number[][] | null;
  b: number[][] | null;
  aLabel: string | null;
  bLabel: string | null;
  cLabel: string | null;
}

export interface MlpInfo {
  ops: MlpOp[]; // steps × opsPerStep, aligned with SimState.opIndex
  opsPerStep: number;
  loss: number[]; // one per step
  eta: number;
}

// --- LLM decode (spec_26): ops reuse the MlpOp wire shape ---

export interface LlmInfo {
  ops: MlpOp[]; // variable per token: 6+2B matmuls + 5 pointwise
  opsPerToken: number[]; // op-strip boundaries; sums to ops.length
  kvLen: number[]; // cache length S_t per token — grows by one row
  intensity: number[]; // MACs/byte per token — the number to watch
  softmaxRow: number[]; // final token's stream-0 attention weights
  prefill: boolean;
}

// spec_24: the launch's resident-warp budget. Fixed at launch, so it rides on
// Summary, never per-state.
export interface Occupancy {
  blockSize: number;
  warpsPerBlock: number;
  blocksResident: number;
  occupancyPct: number;
  limiter: "threads" | "blocks" | "none";
}

export interface Summary {
  bytesMoved: number;
  loadCyclesTotal: number;
  computeCyclesTotal: number;
  arithmeticIntensity: number;
  ridgePoint: number;
  regime: Regime;
  serialCycles: number;
  pipelinedCycles: number;
  occupancy: Occupancy; // spec_24
  // spec_25 energy ledger (illustrative joules; comparisons are the product).
  energyJoules: number;
  avgPowerWatts: number;
  joulesPerMac: number;
  // spec_27: the all-gather's modeled cost and serial ÷ (max(die) + exchange)
  // — always < 2. Neutral 0 / 1.0 when gpus=1.
  exchangeCycles: number;
  scaleupSpeedup: number;
}

export interface SimulateResponse {
  profile: GpuProfile;
  workload: Workload;
  totalCores: number;
  macTotal: number;
  // Resolved dims (spec_22): the 0-sentinel applied server-side.
  m: number;
  k: number;
  n: number;
  tileSize: number;
  summary: Summary;
  a: number[][];
  b: number[][];
  trace: SimState[];
  mlp?: MlpInfo | null; // spec_06
  llm?: LlmInfo | null; // spec_26
}

// --- Die anatomy (annotated real-GPU floorplans; backend/app/anatomy.py) ---

export type RegionKind =
  | "compute"
  | "l2"
  | "mem"
  | "nvlink"
  | "io"
  | "media"
  | "cache"
  | "fabric";

// Real photograph of a part (hotlinked from Wikimedia Commons; credit is the
// attribution the CC license requires — always render it next to the image).
export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface DieRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
  photo?: Photo | null;
}

export interface DieAnatomy {
  id: string;
  name: string;
  vendor: string;
  architecture: string;
  process: string;
  dieSize: string;
  transistors: string;
  year: number;
  width: number;
  height: number;
  regions: DieRegion[];
  stats: { label: string; value: string }[];
  sources: { label: string; url: string }[];
  overview: string;
  photo?: Photo | null;
}

export function totalCores(p: GpuProfile): number {
  return p.sm.rows * p.sm.cols * p.coresPerSM.rows * p.coresPerSM.cols;
}

// -- Live CUDA co-browsing (spec_08 + specs 10/12/14/15/16/17/18).
// Mirrors backend/app/live.py and tour.py. -----------------------------------

export type Dim3 = [number, number, number];

export interface DeviceInfo {
  name: string;
  smCount: number;
  maxThreadsPerSm: number | null;
  warpSize: number | null;
  vramMb: number | null;
}

export interface SmActivity {
  smId: number;
  blocksRun: number; // blocks this SM ran in the current kernel
  busy: boolean;
  estimated: boolean; // spec_16: scaled from a declared sample
}

export interface BlockSpan {
  smId: number;
  startNorm: number; // 0..1 over the kernel's own span (spec_10)
  endNorm: number;
}

export interface LiveState {
  sessionId: string;
  tMs: number;
  kind: "kernel" | "sample" | "device" | "progress";
  device: DeviceInfo | null;
  kernel: string | null;
  grid: Dim3 | null;
  block: Dim3 | null;
  smActivity: SmActivity[];
  recordsDropped: number; // >0: the probe truncated records; frame is partial
  running: boolean; // spec_14: kernel mid-flight (progress frames)
  blockSpans: BlockSpan[] | null; // spec_10
  spansSampled: boolean;
  source: "probe" | "cupti"; // spec_17: cupti = timing-only
  occupancySource: "theoretical" | "measured";
  // spec_28: "modeled" = SM placement invented by a fleet remap; recordedOn
  // then names the die the data was actually measured on.
  placement: "measured" | "modeled";
  recordedOn: string | null;
  occupancyPct: number | null;
  elapsedMs: number | null;
  utilPct: number | null;
  vramMb: number | null;
  powerW: number | null;
  tempC: number | null;
}

export interface LiveSessionInfo {
  id: string;
  name: string;
  eventCount: number;
  active: boolean;
}

// spec_15 (+ spec_20 #7 history): latest calibration per metric.
export type Measurements = Record<
  string,
  { value: number; kernel: string | null; measuredAt: string; history?: number[] }
>;

// spec_20 #1.
export interface SessionSummary {
  sessionId: string;
  frames: number;
  kernelLaunches: number;
  deviceName: string | null;
  durationMs: number;
  kernelStats: {
    kernel: string;
    runs: number;
    bestMs: number | null;
    worstMs: number | null;
  }[];
}

// spec_18: lesson tours.
export interface TourStep {
  id: string;
  title: string;
  script: string;
  lessonId: string;
  cursor: number;
  provenance: "hardware" | "representative";
  experiment: string | null;
  // spec_30: optional hash URL rendered as a real button ("#", "#anatomy/…",
  // "#anatomy/<a>/vs/<b>", "#live"). Authored backend-side as data.
  link: string | null;
}

export interface LessonTour {
  id: string;
  title: string;
  intro: string;
  steps: TourStep[];
}

// --- spec_30: the cross-navigation atlas (GET /api/atlas) --------------------

export interface AtlasPair {
  profileName: string;
  dieId: string;
  deviceMatch: string[]; // substrings matched against live device names
}

export interface Atlas {
  pairs: AtlasPair[];
}

// The Live tab's die badge: a reported device name → the die it draws, or
// null (the local 4060 stays unbadged until an AD107 anatomy lands).
export function dieForDevice(
  atlas: Atlas | null,
  deviceName: string | null | undefined,
): string | null {
  if (!atlas || !deviceName) return null;
  for (const p of atlas.pairs) {
    if (p.deviceMatch.some((m) => deviceName.includes(m))) return p.dieId;
  }
  return null;
}
