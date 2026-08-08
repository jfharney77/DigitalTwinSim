// Wire types for the fleet-operations simulator.

export type Product =
  | "vxrail" | "privatecloud" | "apex" | "nativeedge" | "automationstudio";
export type OpsMode = "manual" | "automated";
export type DemandCurve = "steady" | "seasonal" | "spiky";
export type SiteClass = "factory" | "store" | "clinic";

export interface FleetConfig {
  product: Product;
  sites: number;
  nodesPerSite: number;
  opsMode: OpsMode;
  ftt: number;
  stacks: number;
  catalog: boolean;
  committedVms: number;
  bufferPct: number;
  demandCurve: DemandCurve;
  siteClass: SiteClass;
  twoNodeHa: boolean;
  wanReliable: boolean;
  testGate: boolean;
}

export interface Workload {
  vmsPerSite: number;
  growthPctMonth: number;
  vmSizeCapacity: number;
}

export type EventAction =
  | "deploy-sites"
  | "node-fault"
  | "cluster-update"
  | "bad-change"
  | "wan-outage"
  | "demand-spike";

export interface SimEvent {
  atD: number;
  action: EventAction;
  value?: number | null;
}

export interface Scenario {
  config: FleetConfig;
  workload: Workload;
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
  adminHoursToday: number;
  adminHoursCum: number;
  adminHoursPerMonth: number;
  sitesDeployed: number;
  nodesTotal: number;
  nodesHealthy: number;
  vmsRunning: number;
  vmsDemand: number;
  capacityVms: number;
  headroomPct: number;
  exposure: boolean;
  versionCurrentPct: number;
  driftCount: number;
  outageMinutesCum: number;
  availabilityPct: number;
  truckRolls: number;
  faultsCum: number;
  updating: boolean;
  monthlyBill: number;
  commitmentUtilizationPct: number;
  costPerVmHourAsvc: number;
  costPerVmHourCapex: number;
  regionLoad: Record<string, number>;
}

export interface LogEntry {
  tD: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  adminHoursTotal: number;
  availabilityPct: number;
  outageMinutes: number;
  truckRolls: number;
  faults: number;
  finalVersionCurrentPct: number;
  totalBill: number;
  meanCostPerVmHourAsvc: number;
  meanCostPerVmHourCapex: number;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "controlplane" | "site" | "node" | "workload" | "ops" | "economics"
  | "pipeline" | "catalog" | "wan";

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

export interface FleetMap {
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
  config: FleetConfig;
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
