// Wire types for the AI Factory capstone simulator. These mirror the
// pydantic models in backend/app/models.py (snake_case → camelCase).

export type FabricType = "spectrum-x" | "quantum-ib";
export type Cooling = "liquid" | "air";

export const GPU_WATT_TIERS = [700, 1000, 1200];

export interface ComputeBlock {
  racks: number;
  gpusPerRack: number;
  gpuPeakW: number;
}

export interface FabricBlock {
  type: FabricType;
  oversubscription: number;
}

export interface DataBlock {
  storageGbps: number;
}

export interface FacilityBlock {
  mwBudget: number;
  cooling: Cooling;
}

export interface ResilienceBlock {
  checkpointIntervalMin: number;
  restartMin: number;
  gpuMtbfH: number;
}

export interface CostBlock {
  usdPerKwh: number;
  capexMusdPerRack: number;
  amortizationYears: number;
}

export interface FactoryConfig {
  compute: ComputeBlock;
  fabric: FabricBlock;
  data: DataBlock;
  facility: FacilityBlock;
  resilience: ResilienceBlock;
  costs: CostBlock;
}

export interface TrainingJob {
  tokensPerGpuS: number;
  dataGbpsPerGpu: number;
  stateGbPerGpu: number;
  rampH: number;
}

export type EventAction =
  | "degrade-storage"
  | "restore-storage"
  | "warm-day"
  | "end-warm-day"
  | "fail-gpus";

export interface SimEvent {
  atH: number;
  action: EventAction;
  value?: number | null;
}

export interface Scenario {
  config: FactoryConfig;
  job: TrainingJob;
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

export type Phase = "procure" | "install" | "bringup" | "train";

export interface SimState {
  tH: number;
  phase: Phase;
  gpusInstalled: number;
  gpusOnline: number;
  tokensPerS: number;
  tokensTotalB: number;
  gpuIdleDataPct: number;
  usdPerMtok: number;
  pue: number;
  facilityMw: number;
  gpuUtilPct: number;
  dataUtilPct: number;
  fabricEffPct: number;
  overheadPct: number;
  storageDemandGbps: number;
  storageSupplyGbps: number;
  gpuMw: number;
  fabricMw: number;
  storageMw: number;
  otherMw: number;
  itMw: number;
  mwBudget: number;
  powerCapped: boolean;
  failuresCum: number;
  costUsdM: number;
  regionStatus: Record<string, number>;
}

export interface LogEntry {
  tH: number;
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface Summary {
  timeToFirstTokenH: number;
  tokensTotalB: number;
  avgIdleDataPct: number;
  avgPue: number;
  usdPerMtok: number;
  peakFacilityMw: number;
  failures: number;
  powerCappedHours: number;
}

export interface SimResponse {
  validations: Validation[];
  trace: SimState[];
  log: LogEntry[];
  summary: Summary;
}

export type RegionKind =
  | "operations" | "compute" | "fabric" | "data"
  | "power" | "cooling" | "resilience";

export interface FactoryRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
}

export interface FactoryMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: FactoryRegion[];
  overview: string;
  sources: { label: string; url: string }[];
}

export interface FactoryPreset {
  id: string;
  name: string;
  blurb: string;
  config: FactoryConfig;
}

export interface JobPreset {
  id: string;
  name: string;
  job: TrainingJob;
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
