// Wire types for the storage-platforms simulator (mirror of
// backend/app/models.py).

export type Product =
  | "powerstore" | "powermax" | "powerscale" | "objectscale"
  | "powerflex" | "exascale";
export type DriveClass = "nvme" | "ssd" | "hdd";
export type Protection = "raid5" | "raid6" | "mirror" | "ec8+2" | "ec16+4";
export type Srdf = "off" | "sync" | "async";

export interface StorageConfig {
  product: Product;
  units: number;
  drivesPerUnit: number;
  driveTb: number;
  driveClass: DriveClass;
  protection: Protection;
  nicGbps: number;
  srdf: Srdf;
  distanceKm: number;
  smallObjects: boolean;
  immutable: boolean;
  lightningUnits: number;
  fileUnits: number;
  objectUnits: number;
  blockUnits: number;
}

export interface Workload {
  iopsDemandK: number;
  blockKb: number;
  readPct: number;
  sequentialPct: number;
  workingSetFitPct: number;
  ingestTbDay: number;
  snapshotsPerDay: number;
  reductionRatio: number;
}

export type EventAction =
  | "set-workload"
  | "fail-drive"
  | "fail-controller"
  | "fail-node"
  | "add-nodes"
  | "attempt-delete"
  | "write-burst";

export interface SimEvent {
  atH: number;
  action: EventAction;
  value?: number | null;
  workload?: Workload | null;
}

export interface Scenario {
  config: StorageConfig;
  workload: Workload;
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
  online: boolean;
  rawTb: number;
  usableTb: number;
  effectiveTb: number;
  usedTb: number;
  snapshotTb: number;
  usedPct: number;
  reductionRatio: number;
  capacityAlert: "none" | "80" | "90" | "95";
  iopsCapacityK: number;
  iopsDeliveredK: number;
  iopsDemandK: number;
  throughputGbs: number;
  latencyMs: number;
  p99Ms: number;
  utilizationPct: number;
  cacheHitPct: number;
  saturated: boolean;
  unitsOnline: number;
  rebuilding: boolean;
  rebuildPct: number;
  rebuildHoursLeft: number;
  exposure: boolean;
  srdfLatencyMs: number;
  rpoSeconds: number;
  poolUtilPct: Record<string, number>;
  gpuIdleDueToDataPct: number;
  regionLoad: Record<string, number>;
}

export interface LogEntry {
  tH: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  peakLatencyMs: number;
  steadyLatencyMs: number;
  minDeliveredRatio: number;
  hoursSaturated: number;
  rebuildHours: number;
  finalUsedPct: number;
  dataSurvived: boolean;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "controller" | "media" | "cache" | "node" | "network" | "namespace"
  | "replication" | "pool" | "client";

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

export interface ProductMap {
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
  config: StorageConfig;
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
