// Wire types for the XR rugged-edge simulator. These mirror the pydantic
// models in backend/app/models.py (snake_case → camelCase).

export type Platform = "xr8000" | "xr4000";
export type DriveType = "ssd" | "hdd";
export type ThermalConfig = "standard" | "extended";
export type Redundancy = "1+0" | "1+1";
export type Dust = "clean" | "moderate" | "heavy";
export type Vibration = "none" | "roadside" | "vehicle";

export const PLATFORM_TDP_TIERS: Record<Platform, number[]> = {
  xr8000: [125, 185, 225, 250],
  xr4000: [65, 80, 100, 122],
};
export const PSU_CAPACITIES = [800, 1100, 1400];
export const DIMM_COUNTS = [4, 8, 16];

export interface ServerConfig {
  platform: Platform;
  cpuTdpW: number;
  thermalConfig: ThermalConfig;
  dimms: number;
  driveType: DriveType;
  drives: number;
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
  accelPct: number;
}

export interface Environment {
  inletC: number;
  altitudeM: number;
  dust: Dust;
  filterMonths: number;
  vibration: Vibration;
}

export type EventAction =
  | "set-workload"
  | "kill-fan"
  | "restore-fan"
  | "kill-psu"
  | "set-inlet"
  | "set-filter-months"
  | "clean-filter"
  | "voltage-sag";

export interface SimEvent {
  atS: number;
  action: EventAction;
  index?: number | null;
  value?: number | null;
  seconds?: number | null;
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
  accelPowerW: number;
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
  inputVPct: number;
  inputCurrentA: number;
  fanRpmPct: number;
  aliveFans: number;
  airflowCfm: number;
  foulingPct: number;
  inletEffectiveC: number;
  cpuTempC: number;
  accelTempC: number;
  driveTempC: number;
  exhaustC: number;
  deltaTC: number;
  cpuThrottling: boolean;
  accelThrottling: boolean;
  perfLostPct: number;
  storagePerfLostPct: number;
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
  | "filter" | "storage" | "cooling" | "memory" | "cpu"
  | "accel" | "io" | "power" | "management";

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
