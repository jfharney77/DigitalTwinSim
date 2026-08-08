// Wire types for the AI-compute physics simulator (mirror of
// backend/app/models.py, snake_case → camelCase).

export type Product = "xe7745" | "xe9680" | "xe9712";

export const CPU_TDP_TIERS = [250, 300, 350, 400, 500];
export const PCIE_GPU_TDP = [300, 450, 600];
export const SXM_GPU_TDP = [700, 1000];
export const PSU_7745_W = [2400, 2800];
export const SHELF_KW = [66, 132, 198];

export interface SystemConfig {
  product: Product;
  cpuTdpW: number;
  pcieGpus: number;
  pcieGpuTdpW: number;
  psuCapacityW: number;
  sxmGpuTdpW: number;
  nics: number;
  trays: number;
  shelfCapacityKw: number;
  manifoldCapacityLpm: number;
  coolantSupplyC: number;
  coolantFlowLpm: number;
}

export interface Workload {
  gpuPct: number;
  cpuPct: number;
  dataFeedPct: number;
}

export interface Environment {
  inletC: number;
}

export type EventAction =
  | "set-workload"
  | "set-inlet"
  | "set-data-feed"
  | "set-coolant-supply"
  | "degrade-pump"
  | "restrict-tray"
  | "kill-psu";

export interface SimEvent {
  atS: number;
  action: EventAction;
  index?: number | null;
  value?: number | null;
  workload?: Workload | null;
}

export interface Scenario {
  config: SystemConfig;
  workload: Workload;
  environment: Environment;
  durationS: number;
  events: SimEvent[];
}

export type RuleLevel = "ok" | "warning" | "error";

export interface Validation {
  ruleId: string;
  level: RuleLevel;
  message: string;
  source: string;
}

export interface SimState {
  t: number;
  poweredOn: boolean;
  cpuPowerW: number;
  gpuPowerW: number;
  nicPowerW: number;
  basePowerW: number;
  fanPowerW: number;
  pumpPowerW: number;
  dcPowerW: number;
  acPowerW: number;
  psuEfficiency: number;
  alivePsus: number;
  gpuTempHotC: number;
  gpuTempCoolC: number;
  cpuTempC: number;
  gpusThrottled: number;
  liquidWatts: number;
  airWatts: number;
  coolantSupplyC: number;
  coolantReturnC: number;
  coolantDeltaTC: number;
  flowLpm: number;
  fanRpmPct: number;
  effectiveGpuUtilPct: number;
  tokensPerS: number;
  gpuHoursWasted: number;
  coolingOverheadPct: number;
  regionTemps: Record<string, number>;
}

export interface LogEntry {
  t: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  peakDcW: number;
  steadyDcW: number;
  idleDcW: number;
  peakTokensPerS: number;
  gpuHoursWasted: number;
  throttleSeconds: number;
  shutdown: boolean;
  shutdownReason: string;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "gpu" | "cpu" | "memory" | "storage" | "network" | "nvswitch"
  | "cooling" | "power" | "management" | "cdu" | "manifold" | "tray";

export interface SystemRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface SystemMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: SystemRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface ConfigPreset {
  id: string;
  name: string;
  blurb: string;
  config: SystemConfig;
}

export interface WorkloadPreset {
  id: string;
  name: string;
  workload: Workload;
}

export interface GuidedScenario {
  id: string;
  title: string;
  narration: string[];
  question: string;
  scenario: Scenario;
}

export interface Explain {
  id: string;
  title: string;
  equation: string;
  inputs: string[];
  explanation: string;
}
