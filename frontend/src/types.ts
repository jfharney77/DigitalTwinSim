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

export interface Workload {
  kind: "matmul";
  N: number;
  dtype: DType;
  seed?: number;
  tileSize?: number;
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
}

export interface Summary {
  bytesMoved: number;
  loadCyclesTotal: number;
  computeCyclesTotal: number;
  arithmeticIntensity: number;
  ridgePoint: number;
  regime: Regime;
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
}

export function totalCores(p: GpuProfile): number {
  return p.sm.rows * p.sm.cols * p.coresPerSM.rows * p.coresPerSM.cols;
}
