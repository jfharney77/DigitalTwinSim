// Wire types for the rack PDU & UPS simulator. These mirror the pydantic
// models in backend/app/models.py (snake_case → camelCase).

export type Phase = "A" | "B" | "C";
export type Chemistry = "vrla" | "lithium";

export const BREAKER_AMP_TIERS = [16, 20, 30, 32];
export const UPS_WH_TIERS = [500, 1000, 2000];
export const LOAD_SLOTS = 8;

export interface RackLoad {
  label: string;
  powerW: number;
  phase: Phase;
}

export interface RackConfig {
  loads: RackLoad[];
  breakerAmps: number;
  upsChemistry: Chemistry;
  upsNameplateWh: number;
  upsAgeYears: number;
  startChargePct: number;
}

export interface Environment {
  roomTempC: number;
}

export type EventAction =
  | "utility-fail"
  | "utility-restore"
  | "move-load"
  | "set-load"
  | "self-test";

export interface SimEvent {
  atS: number;
  action: EventAction;
  index?: number | null;
  value?: number | null;
  phase?: Phase | null;
}

export interface Scenario {
  config: RackConfig;
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
  utilityOn: boolean;
  onBattery: boolean;
  rackPowered: boolean;
  phaseAW: number;
  phaseBW: number;
  phaseCW: number;
  phaseAAmps: number;
  phaseBAmps: number;
  phaseCAmps: number;
  phaseAPct: number;
  phaseBPct: number;
  phaseCPct: number;
  trippedPhases: Phase[];
  imbalancePct: number;
  pduInputW: number;
  acInputW: number;
  batteryOutputW: number;
  inverterLossW: number;
  chargeDrawW: number;
  chargePct: number;
  batteryWhRemaining: number;
  predictedRuntimeMin: number;
  actualRuntimeMin: number;
  selfTested: boolean;
  regionWatts: Record<string, number>;
}

export interface LogEntry {
  t: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  peakInputW: number;
  worstImbalancePct: number;
  batteryCapacityFraction: number;
  predictedRuntimeMinAtFailure: number;
  actualRuntimeMinSurvived: number;
  trippedPhases: Phase[];
  rackWentDark: boolean;
  darkReason: string;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind = "load" | "pdu" | "ups" | "battery";

export interface RackRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface RackMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: RackRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface ConfigPreset {
  id: string;
  name: string;
  blurb: string;
  config: RackConfig;
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
}
