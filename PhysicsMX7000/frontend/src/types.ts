// Wire types for the MX7000 shared-infrastructure simulator. These mirror
// the pydantic models in backend/app/models.py (snake_case → camelCase).

export type SledKind = "compute" | "storage" | "empty";
export type Redundancy = "grid" | "n+1" | "none";

export const SLED_COUNT = 8;
export const FAN_COUNT = 9;
export const CPU_TDP_TIERS = [125, 165, 205, 250, 270, 350];
export const DIMM_COUNTS = [8, 16, 24, 32];

export interface SledConfig {
  kind: SledKind;
  cpuTdpW: number;
  dimms: number;
  drives: number;
  ownerSlot?: number | null;
}

export interface ChassisConfig {
  sleds: SledConfig[];
  psuCount: number;
  redundancy: Redundancy;
  powerCapW: number;
}

export interface SledLoad {
  cpuPct: number;
  memPct: number;
  storagePct: number;
}

export interface Workload {
  loads: SledLoad[];
}

export interface Environment {
  inletC: number;
}

export type EventAction =
  | "set-sled-load"
  | "set-all-load"
  | "kill-fan"
  | "restore-fan"
  | "kill-psu"
  | "lose-feed"
  | "restore-feed"
  | "set-inlet"
  | "reassign-storage";

export interface SimEvent {
  atS: number;
  action: EventAction;
  index?: number | null;
  value?: number | null;
  load?: SledLoad | null;
}

export interface Scenario {
  config: ChassisConfig;
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
  sledPowerW: number[];
  sledTempC: number[];
  sledThrottling: boolean[];
  hottestSlot: number;
  fabricPowerW: number;
  mgmtPowerW: number;
  fanPowerW: number;
  dcPowerW: number;
  acPowerW: number;
  psuEfficiency: number;
  psuLoadPct: number;
  alivePsus: number;
  feedAUp: boolean;
  feedBUp: boolean;
  fanRpmPct: number;
  aliveFans: number;
  airflowCfm: number;
  inletC: number;
  exhaustC: number;
  deltaTC: number;
  chassisCapped: boolean;
  regionTemps: Record<string, number>;
}

export interface LogEntry {
  t: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  peakDcW: number;
  peakAcW: number;
  steadyDcW: number;
  steadyFanW: number;
  hottestSledC: number;
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

export type RegionKind = "bay" | "cooling" | "power" | "management" | "fabric";

export interface ChassisRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface ChassisMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: ChassisRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface ConfigPreset {
  id: string;
  name: string;
  blurb: string;
  config: ChassisConfig;
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

export interface ConstantInfo {
  value: number;
  unit: string;
  source: string;
  estimated: boolean;
  blurb: string;
}

export interface ConstantsResponse {
  constants: Record<string, ConstantInfo>;
  psuEfficiencyCurve: [number, number][];
  psuCurveSource: string;
}
