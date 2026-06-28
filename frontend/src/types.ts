// Mirrors the backend pydantic models (camelCase JSON). See backend/app/models.py.

export type Phase = "idle" | "load" | "compute" | "writeback" | "done";
export type CoreState = "idle" | "loading" | "computing" | "wrote";

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
}

export interface Workload {
  kind: "matmul";
  N: number;
  dtype: "fp32";
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
}

export interface SimulateResponse {
  profile: GpuProfile;
  workload: Workload;
  totalCores: number;
  macTotal: number;
  trace: SimState[];
}

export function totalCores(p: GpuProfile): number {
  return p.sm.rows * p.sm.cols * p.coresPerSM.rows * p.coresPerSM.cols;
}
