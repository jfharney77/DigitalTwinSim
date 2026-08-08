// Wire types for the telecom & sustainability simulator.

export type Product = "telecomblocks" | "circulardesign";
export type DeployMode = "diy" | "blocks";
export type Grid = "clean" | "average" | "coal";

export interface LifecycleConfig {
  product: Product;
  sites: number;
  deployMode: DeployMode;
  extendedTemp: boolean;
  spareCapacity: boolean;
  remoteRemediation: boolean;
  subscribersPerSiteK: number;
  batteryReplaceable: boolean;
  ramSocketed: boolean;
  chassisRecycled: boolean;
  portsModular: boolean;
  grid: Grid;
  firstOwnerYears: number;
  annualKwh: number;
}

export type EventAction = "deploy-sites" | "heatwave" | "bundle-update";

export interface SimEvent {
  atD: number;
  action: EventAction;
  value?: number | null;
}

export interface Scenario {
  config: LifecycleConfig;
  durationD: number;
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
  tD: number;
  sitesTotal: number;
  sitesUp: number;
  coveragePct: number;
  subscribersServedK: number;
  integrationHoursCum: number;
  mismatchEventsCum: number;
  availabilityPct: number;
  ambientC: number;
  updating: boolean;
  embodiedKgCum: number;
  useKgCum: number;
  totalCarbonKg: number;
  usefulYears: number;
  carbonPerUsefulYear: number;
  devicesConsumed: number;
  ewasteKg: number;
  tcoUsd: number;
  deviceAlive: boolean;
  onSecondLife: boolean;
  disassemblyMinutes: number;
  regionLoad: Record<string, number>;
}

export interface LogEntry {
  tD: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  integrationHours: number;
  mismatchEvents: number;
  availabilityPct: number;
  minCoveragePct: number;
  totalCarbonKg: number;
  carbonPerUsefulYear: number;
  devicesConsumed: number;
  ewasteKg: number;
  tcoUsd: number;
  gotSecondLife: boolean;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "coverage" | "site" | "integration" | "environment" | "device"
  | "battery" | "materials" | "grid" | "ledger" | "secondlife";

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

export interface LifecycleMap {
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
  config: LifecycleConfig;
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
