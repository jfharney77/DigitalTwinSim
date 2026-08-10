// Wire types for the client-device physics simulator. These mirror the
// pydantic models in backend/app/models.py (snake_case → camelCase).

export type Product = "alienware" | "promax";
export type FormFactor = "laptop" | "desktop";
export type PerfMode = "quiet" | "balanced" | "performance";
export type InferenceEngine = "cpu" | "gpu" | "npu";

export const LAPTOP_CPU_PL1 = [45, 55, 65];
export const DESKTOP_CPU_PL1 = [65, 125, 150];
export const LAPTOP_GPU_TGP = [0, 80, 115, 140, 175];
export const DESKTOP_GPU_TGP = [0, 200, 300, 450];
export const BATTERY_WH = [68, 90, 97];
export const CHARGER_W = [130, 180, 240, 330];
export const DESKTOP_PSU_W = [750, 1000, 1500];

export interface DeviceConfig {
  product: Product;
  formFactor: FormFactor;
  cpuPl1W: number;
  gpuTgpW: number;
  npu: boolean;
  ramGb: number;
  nvmeCount: number;
  batteryWh: number;
  batteryHealthPct: number;
  chargerW: number;
  psuCapacityW: number;
}

export interface Workload {
  cpuPct: number;
  gpuPct: number;
  npuPct: number;
}

export interface Environment {
  ambientC: number;
  onLap: boolean;
  perfMode: PerfMode;
  pluggedIn: boolean;
  startChargePct: number;
}

export type EventAction =
  | "set-workload"
  | "unplug"
  | "plug-in"
  | "set-ambient"
  | "set-on-lap"
  | "set-mode"
  | "set-charger";

export interface SimEvent {
  atS: number;
  action: EventAction;
  value?: number | null;
  mode?: PerfMode | null;
  workload?: Workload | null;
}

export interface Scenario {
  config: DeviceConfig;
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

export type PlState =
  | "idle" | "pl2-boost" | "pl1" | "skin-limited" | "budget-limited";

export interface SimState {
  t: number;
  poweredOn: boolean;
  cpuPowerW: number;
  gpuPowerW: number;
  npuPowerW: number;
  basePowerW: number;
  fanPowerW: number;
  systemPowerW: number;
  acInputW: number;
  batteryDischargeW: number;
  chargeW: number;
  batteryPct: number;
  runtimeMin: number;
  psuEfficiency: number;
  plState: PlState;
  cpuTempC: number;
  gpuTempC: number;
  skinTempC: number;
  fanRpmPct: number;
  noiseDba: number;
  cpuThrottling: boolean;
  gpuThrottling: boolean;
  fpsProxy: number;
  tokensPerS: number;
  tokensPerJoule: number;
  activeEngine: InferenceEngine | null;
  regionTemps: Record<string, number>;
}

export interface LogEntry {
  t: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  peakSystemW: number;
  steadySystemW: number;
  fpsMinute1: number;
  fpsMinute15: number;
  minBatteryPct: number;
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
  | "cpu" | "gpu" | "npu" | "memory" | "storage" | "battery"
  | "cooling" | "power" | "board" | "skin";

export interface DeviceRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface DeviceMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: DeviceRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface ConfigPreset {
  id: string;
  name: string;
  blurb: string;
  comparePresetId?: string | null;
  config: DeviceConfig;
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

// Client-brand map (physics_specs/10 §8 — static explainer page).

export interface Brand {
  id: string;
  name: string;
  formerly: string;
  audience: string;
  tiers: string[];
  description: string;
}

export interface BrandMap {
  overview: string;
  namingNote: string;
  sinceNote: string;
  brands: Brand[];
  sources: { label: string; url: string }[];
}
