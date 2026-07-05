// Mirrors the backend pydantic models (camelCase JSON). See backend/app/models.py.

export type Phase = "idle" | "load" | "compute" | "writeback" | "done";
export type CoreState = "idle" | "loading" | "computing" | "wrote";
export type DType = "fp32" | "fp16" | "bf16" | "int8";
export type Regime = "memory" | "compute";

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
}

export type WorkloadKind = "matmul" | "mlp_step";

export interface Workload {
  kind: WorkloadKind;
  N: number;
  dtype: DType;
  seed?: number;
  tileSize?: number;
  doubleBuffer?: boolean;
  steps?: number; // SGD steps for mlp_step (spec_06)
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

export interface Summary {
  bytesMoved: number;
  loadCyclesTotal: number;
  computeCyclesTotal: number;
  arithmeticIntensity: number;
  ridgePoint: number;
  regime: Regime;
  serialCycles: number;
  pipelinedCycles: number;
}

export interface SimulateResponse {
  profile: GpuProfile;
  workload: Workload;
  totalCores: number;
  macTotal: number;
  tileSize: number;
  summary: Summary;
  a: number[][];
  b: number[][];
  trace: SimState[];
  mlp?: MlpInfo | null; // spec_06
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
