// Wire types for the Data Domain dedupe simulator. These mirror the
// pydantic models in backend/app/models.py (snake_case → camelCase).

export type ApplianceId = "dd3410" | "dd9910" | "dd-all-flash";

export interface Appliance {
  id: ApplianceId;
  name: string;
  usableTb: number;
  indexRamGb: number;
  baseIngestGbps: number;
  blurb: string;
  source: string;
  estimated: boolean;
}

export interface Dataset {
  fullTb: number;
  dailyChangePct: number;
  entropyPct: number;
}

export interface Schedule {
  retentionDays: number;
}

export type EventAction =
  | "set-change-rate"
  | "set-entropy"
  | "enable-host-encryption"
  | "disable-host-encryption"
  | "ransomware-start"
  | "ransomware-stop";

export interface SimEvent {
  atDay: number;
  action: EventAction;
  value?: number | null;
}

export interface Scenario {
  appliance: ApplianceId;
  dataset: Dataset;
  schedule: Schedule;
  durationDays: number;
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
  day: number;
  generationsRetained: number;
  logicalTb: number;
  physicalTb: number;
  dedupeRatio: number;
  todaysLogicalTb: number;
  todaysNovelPhysicalTb: number;
  gcReclaimedTb: number;
  capacityUsedPct: number;
  streamEntropyPct: number;
  entropyAlarm: boolean;
  hostEncrypted: boolean;
  ransomwareActive: boolean;
  encryptedFractionPct: number;
  uniqueChunksM: number;
  indexGb: number;
  indexPressurePct: number;
  ingestGbps: number;
  logicalIngestGbps: number;
  backupWindowHours: number;
  regionLoad: Record<string, number>;
}

export interface LogEntry {
  day: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  finalRatio: number;
  finalLogicalTb: number;
  finalPhysicalTb: number;
  peakStreamEntropyPct: number;
  alarmDay: number;
  capacityFullDay: number;
  finalCapacityUsedPct: number;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "source" | "transport" | "chunk" | "index" | "store" | "clean";

export interface PipelineRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface PipelineMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: PipelineRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface DatasetPreset {
  id: string;
  name: string;
  blurb: string;
  appliance: ApplianceId;
  dataset: Dataset;
  schedule: Schedule;
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
