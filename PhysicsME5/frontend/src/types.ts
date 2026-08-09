// Wire types for the ME5 RAID physics simulator. These mirror the
// pydantic models in backend/app/models.py (snake_case → camelCase).

export type ArrayModel = "ME5012" | "ME5024";
export type DriveType = "hdd-7.2k" | "hdd-10k" | "ssd";
export type RaidLevel = "1" | "5" | "6" | "10";
export type HostInterface = "iSCSI" | "SAS" | "FC";

export const MODEL_MAX_DRIVES: Record<ArrayModel, number> = {
  ME5012: 12,
  ME5024: 24,
};
export const DRIVE_TB_OPTIONS = [2, 4, 8, 12, 16, 20];
export const WRITE_PENALTY: Record<RaidLevel, number> = {
  "1": 2,
  "10": 2,
  "5": 4,
  "6": 6,
};

export interface ArrayConfig {
  model: ArrayModel;
  driveType: DriveType;
  driveCount: number;
  driveTb: number;
  raidLevel: RaidLevel;
  spares: number;
  controllers: number;
  hostInterface: HostInterface;
}

export interface Workload {
  offeredKiops: number;
  readPct: number;
  blockKb: number;
}

export type EventAction =
  | "set-workload"
  | "fail-drive"
  | "replace-drive"
  | "fail-controller"
  | "restore-controller"
  | "set-offered";

export interface SimEvent {
  atMin: number;
  action: EventAction;
  index?: number | null;
  value?: number | null;
  workload?: Workload | null;
}

export interface Scenario {
  config: ArrayConfig;
  workload: Workload;
  durationMin: number;
  tickMinutes: number;
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
  online: boolean;
  offeredKiops: number;
  servedReadKiops: number;
  servedWriteKiops: number;
  servedKiops: number;
  throughputMbps: number;
  latencyMs: number;
  backendDiskKiops: number;
  readCost: number;
  writePenalty: number;
  diskUtilPct: number;
  saturated: boolean;
  controllersAlive: number;
  drivesServing: number;
  drivesFailed: number;
  sparesLeft: number;
  degraded: boolean;
  rebuilding: boolean;
  rebuildPct: number;
  rebuildHoursRemaining: number;
  riskIndex: number;
  rawTb: number;
  usableTb: number;
  overheadTb: number;
  spareTb: number;
  regionStates: Record<string, string>;
}

export interface LogEntry {
  t: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  peakServedKiops: number;
  peakLatencyMs: number;
  steadyServedKiops: number;
  rebuildHoursTotal: number;
  dataLost: boolean;
  offlineReason: string;
  usableTb: number;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind = "drive" | "controller" | "power" | "cache";

export interface ArrayRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface ArrayMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: ArrayRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface ConfigPreset {
  id: string;
  name: string;
  blurb: string;
  config: ArrayConfig;
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
  riskFactors: Record<string, number>;
  riskFactorSource: string;
}
