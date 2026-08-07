// Wire types for the R760 thermal simulator. These mirror the pydantic
// models in backend/app/models.py (snake_case → camelCase).

export type Heatsink = "standard" | "high-performance";
export type FanKit = "standard" | "gold";
export type Chassis = "12x3.5" | "24x2.5" | "16xE3.S";
export type Redundancy = "1+0" | "1+1";

export const CPU_TDP_TIERS = [125, 150, 185, 205, 250, 270, 300, 330, 350];
export const PSU_CAPACITIES = [800, 1100, 1400, 2400];
export const DIMM_COUNTS = [8, 16, 24, 32];

export interface ServerConfig {
  sockets: number;
  cpuTdpW: number;
  heatsink: Heatsink;
  fanKit: FanKit;
  dimms: number;
  chassis: Chassis;
  drives: number;
  gpusDoubleWide: number;
  accelsSingleWide: number;
  ioCardW: number;
  psuCount: number;
  psuCapacityW: number;
  redundancy: Redundancy;
}

export interface Workload {
  cpuPct: number;
  memPct: number;
  storagePct: number;
  gpuPct: number;
}

export interface Environment {
  inletC: number;
  altitudeM: number;
  recirculationPct: number;
  blockedIntakePct: number;
}

export type EventAction =
  | "set-workload"
  | "kill-fan"
  | "restore-fan"
  | "kill-psu"
  | "set-inlet"
  | "set-recirculation"
  | "set-blocked-intake";

export interface SimEvent {
  atS: number;
  action: EventAction;
  index?: number | null;
  value?: number | null;
  workload?: Workload | null;
}

export interface Scenario {
  config: ServerConfig;
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
  dimmPowerW: number;
  drivePowerW: number;
  ioPowerW: number;
  platformPowerW: number;
  fanPowerW: number;
  dcPowerW: number;
  acPowerW: number;
  psuEfficiency: number;
  psuLoadPct: number;
  alivePsus: number;
  fanRpmPct: number;
  aliveFans: number;
  airflowCfm: number;
  inletEffectiveC: number;
  cpuTempC: number;
  gpuTempC: number;
  driveTempC: number;
  exhaustC: number;
  deltaTC: number;
  cpuThrottling: boolean;
  gpuThrottling: boolean;
  perfLostPct: number;
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
  steadyCpuTempC: number;
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
  | "storage" | "cooling" | "memory" | "cpu"
  | "gpu" | "io" | "power" | "management";

export interface ThermalRegion {
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
  regions: ThermalRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface ConfigPreset {
  id: string;
  name: string;
  blurb: string;
  config: ServerConfig;
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
