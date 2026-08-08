// Wire types for the security & resilience simulator.

export type Product = "powerprotect" | "cyberdetect" | "mdr" | "fortzero";
export type ResponseModel = "inhouse" | "mdr";
export type Architecture = "perimeter" | "zerotrust";

export interface ResilienceConfig {
  product: Product;
  estateTb: number;
  changeGbDay: number;
  backupEveryH: number;
  retentionCopies: number;
  dedupeRatio: number;
  vault: boolean;
  vaultSyncEveryH: number;
  restoreGbps: number;
  detection: boolean;
  sensitivity: number;
  response: ResponseModel;
  noiseAlertsDay: number;
  inhouseCapacityDay: number;
  architecture: Architecture;
  assets: number;
  grantsPerUser: number;
  microsegSegments: number;
  reviewCadenceDays: number;
}

export type EventAction =
  | "incident"
  | "slow-incident"
  | "attempt-restore"
  | "contain"
  | "compromise"
  | "access-review";

export interface SimEvent {
  atH: number;
  action: EventAction;
  value?: number | null;
}

export interface Scenario {
  config: ResilienceConfig;
  durationH: number;
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
  tH: number;
  cleanTb: number;
  corruptedTb: number;
  incidentActive: boolean;
  contained: boolean;
  backupStorageTb: number;
  repoCopiesIntact: number;
  vaultCopiesIntact: number;
  lastCleanPointAgeH: number;
  corruptionScore: number;
  detected: boolean;
  detectionLatencyH: number;
  falseAlarmsCum: number;
  investigationHoursCum: number;
  alertsBacklog: number;
  timeToContainH: number;
  blastRadiusGb: number;
  restoring: boolean;
  restoreProgressPct: number;
  rtoHours: number;
  recovered: boolean;
  failedRestores: number;
  reachableAssets: number;
  policyChecksPerSession: number;
  staleGrants: number;
  regionLoad: Record<string, number>;
}

export interface LogEntry {
  tH: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  rpoHours: number;
  rtoHours: number;
  blastRadiusGb: number;
  detectionLatencyH: number;
  timeToContainH: number;
  falseAlarms: number;
  dataRecoveredTb: number;
  recoverySucceeded: boolean;
  failedRestores: number;
  peakReachableAssets: number;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "estate" | "backup" | "gap" | "vault" | "analytics" | "queue"
  | "responder" | "identity" | "segment" | "policy";

export interface MapRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface ResilienceMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: MapRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface ConfigPreset {
  id: string;
  name: string;
  blurb: string;
  config: ResilienceConfig;
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
