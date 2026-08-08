// Wire types for the network-fabrics simulator.

export type Product = "e3200" | "sn6000" | "x800";
export type Pattern = "uniform" | "incast" | "alltoall" | "elephant";

export interface FabricConfig {
  product: Product;
  spines: number;
  leaves: number;
  endpointsPerLeaf: number;
  downlinkGbps: number;
  uplinkGbps: number;
  adaptiveRouting: boolean;
  losslessRoce: boolean;
  cpoOptics: boolean;
  sharp: boolean;
  poeAps: number;
  poeCameras: number;
  poePhones: number;
  poeBudgetW: number;
  psuRedundant: boolean;
}

export interface Workload {
  demandGbps: number;
  pattern: Pattern;
  collectivePct: number;
}

export type EventAction =
  | "set-workload"
  | "kill-spine"
  | "restore-spine"
  | "kill-uplink"
  | "gray-failure"
  | "clear-gray"
  | "toggle-adaptive"
  | "toggle-sharp"
  | "kill-psu";

export interface SimEvent {
  atS: number;
  action: EventAction;
  value?: number | null;
  workload?: Workload | null;
}

export interface Scenario {
  config: FabricConfig;
  workload: Workload;
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
  demandedGbps: number;
  deliveredGbps: number;
  lostGbps: number;
  droppedPps: number;
  pauseEventsS: number;
  stallUsPerS: number;
  worstLinkPct: number;
  meanLinkPct: number;
  oversubRatio: number;
  latencyUs: number;
  fctMs: number;
  allreduceGbps: number;
  spinesAlive: number;
  fabricPowerW: number;
  opticsPowerW: number;
  asicPowerW: number;
  statusAllGreen: boolean;
  goodputPenaltyPct: number;
  poeBudgetW: number;
  poeDemandW: number;
  devicesPowered: number;
  devicesTotal: number;
  regionLoad: Record<string, number>;
}

export interface LogEntry {
  t: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  peakWorstLinkPct: number;
  totalDrops: number;
  minDeliveredRatio: number;
  secondsCongested: number;
  peakLatencyUs: number;
  fabricPowerW: number;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "spine" | "leaf" | "endpoint" | "optics" | "telemetry" | "manager"
  | "access" | "distribution" | "device" | "power";

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

export interface FabricMap {
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
  config: FabricConfig;
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
