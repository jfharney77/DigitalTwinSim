// Wire types for the CDU physics simulator. These mirror the pydantic
// models in backend/app/models.py (snake_case → camelCase).

export type IrcPolicy = "coordinated" | "uncoordinated";

export const MAX_TRAY_GROUPS = 6;
export const PUMP_COUNTS = [2, 3];

export interface CduConfig {
  trayGroups: number;
  pumps: number;
  flowSetpointLpm: number;
  minSupplyC: number;
  policy: IrcPolicy;
}

export interface Workload {
  utilPct: number;
}

export interface Environment {
  facilitySupplyC: number;
  dewPointC: number;
}

export type EventAction =
  | "set-util"
  | "set-facility-supply"
  | "set-dew-point"
  | "set-min-supply"
  | "fail-pump"
  | "restore-pump"
  | "add-tray-group"
  | "remove-tray-group";

export interface SimEvent {
  atS: number;
  action: EventAction;
  index?: number | null;
  value?: number | null;
}

export interface Scenario {
  config: CduConfig;
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
  itLoadKw: number;
  heatRemovedKw: number;
  hxLoadPct: number;
  facSupplyC: number;
  facReturnC: number;
  facFlowLpm: number;
  secSupplyC: number;
  secReturnC: number;
  secFlowLpm: number;
  approachC: number;
  pumpSpeedPct: number;
  pumpsAlive: number;
  pumpPowerKw: number;
  groupsPresent: number;
  groupsOnline: number;
  bankStatus: ("absent" | "online" | "tripped")[];
  trips: number;
  capPct: number;
  capping: boolean;
  chipTempC: number;
  dewMarginC: number;
  floorActive: boolean;
  regionTemps: Record<string, number>;
}

export interface LogEntry {
  t: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  peakItKw: number;
  steadyItKw: number;
  peakChipC: number;
  minCapPct: number;
  cappedSeconds: number;
  trips: number;
  deliveredKwh: number;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "facility" | "pipe" | "hx" | "pump"
  | "controller" | "manifold" | "tray";

export interface LoopRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface LoopMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: LoopRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface ConfigPreset {
  id: string;
  name: string;
  blurb: string;
  config: CduConfig;
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
}
