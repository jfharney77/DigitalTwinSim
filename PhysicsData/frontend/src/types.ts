// Wire types for the data & observability simulator.

export type Product = "aidataplatform" | "cloudiq";

export interface DataConfig {
  product: Product;
  ingestTbh: number;
  processTbh: number;
  indexTbh: number;
  serveTbh: number;
  gpuProcessing: boolean;
  gpuAnalytics: boolean;
  kvOffload: boolean;
  anomalyK: number;
  weightCapacity: number;
  weightPerformance: number;
  weightConfig: number;
}

export interface Workload {
  rawArrivalTbh: number;
  gpuReadDemandTbh: number;
  inferenceSessionsDemand: number;
  longContextPct: number;
  analyticsScanTbh: number;
}

export type EventAction =
  | "set-workload"
  | "fix-stage"
  | "toggle-kv"
  | "toggle-gpu-process"
  | "inject-capacity"
  | "inject-gray"
  | "inject-fan-drift"
  | "demand-change"
  | "expand-capacity";

export interface SimEvent {
  atH: number;
  action: EventAction;
  value?: number | null;
  workload?: Workload | null;
}

export interface Scenario {
  config: DataConfig;
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
  stageRatesTbh: Record<string, number>;
  stageBacklogsTb: Record<string, number>;
  bottleneck: string;
  throughputTbh: number;
  freshnessLagH: number;
  gpuIdleDueToDataPct: number;
  sessionsCapacity: number;
  sessionsActive: number;
  tokenLatencyTaxPct: number;
  analyticsScanRateTbh: number;
  healthScoreWorst: number;
  healthScoreMean: number;
  anomaliesFlaggedCum: number;
  truePositivesCum: number;
  falsePositivesCum: number;
  precisionPct: number;
  recallPct: number;
  issuesActive: number;
  issuesDetected: number;
  mttdH: number;
  arrayFillPct: number;
  daysToFullForecast: number;
  forecastErrorDays: number;
  deviceStatusAllGreen: boolean;
  regionLoad: Record<string, number>;
}

export interface LogEntry {
  tH: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  meanThroughputTbh: number;
  finalBottleneck: string;
  peakFreshnessLagH: number;
  meanGpuIdlePct: number;
  precisionPct: number;
  recallPct: number;
  mttdH: number;
  capacityOutage: boolean;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "source" | "stage" | "gpu" | "kvcache" | "analytics" | "fleet"
  | "detector" | "forecast" | "console";

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

export interface DataMap {
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
  config: DataConfig;
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
