// Wire types for the Alienware m18 digital twin. These hand-mirror the
// pydantic models in backend/app/models.py, which serialize snake_case →
// camelCase, per the normative contract (dellalienware_api_contract.md).

// --- Catalog ---

export type Connector = "barrel" | "usbc";

export interface AdapterOption {
  id: string;
  name: string;
  watts: number;
  connector: Connector;
  voltage: number;
  amps: number;
  recognized: boolean; // false models a failed PSID handshake / third-pin damage
  description: string;
}

export interface Battery {
  wh: number;
  cells: number;
  voltage: number;
  expressCharge: boolean;
}

export interface LaptopProfile {
  id: string;
  name: string;
  family: string;
  cpu: string;
  cpuMaxW: number;
  gpu: string;
  gpuTgpW: number;
  battery: Battery;
  adapters: AdapterOption[];
  defaultAdapterId: string;
  idleW: number;
  anatomyId: string; // ties profile → anatomy floorplan
  description: string;
}

// --- Simulation ---

export type ThermalMode = "quiet" | "balanced" | "performance" | "fullSpeed";
export type WorkloadKind = "idle" | "gaming" | "fullLoad";

export interface Scenario {
  profileId: string;
  adapterId: string;
  startBatteryPct: number; // 0..100
  thermalMode: ThermalMode;
  workload: WorkloadKind;
}

export interface SimulateRequest {
  scenario: Scenario;
}

// Phase machine (monotonic, never regresses):
//   off → detect → handshake → budget → charge → boot → load → steady
export type PowerPhase =
  | "off"
  | "detect"
  | "handshake"
  | "budget"
  | "charge"
  | "boot"
  | "load"
  | "steady";

export type ChargeStage = "idle" | "precharge" | "cc" | "cv" | "full";

export interface PowerState {
  cycle: number; // == index in trace
  phase: PowerPhase;
  stageId: string; // stable kebab-case id (research S0..S10)
  label: string; // short UI label
  description: string;
  activeRegions: string[]; // region ids in the profile's anatomy
  acW: number; // power drawn from adapter (0 when unplugged)
  systemW: number; // CPU+GPU+rest platform draw
  chargeW: number; // >0 charging into battery
  batteryW: number; // >0 battery DIScharging (hybrid supplement)
  batteryPct: number; // 0..100
  chargeStage: ChargeStage;
  cpuW: number;
  gpuW: number;
  fanPct: number; // 0..100
  hybrid: boolean; // true while battery supplements adapter
  stalled: boolean; // true on long stages the UI should dwell on
  cycleCost: number; // dwell weight, >=1
}

export type Regime = "adapter-limited" | "within-budget" | "throttled";

export interface Summary {
  adapterW: number;
  peakSystemW: number;
  peakHybridW: number; // max battery supplement
  hybridUsed: boolean;
  endBatteryPct: number;
  regime: Regime;
  minutesTo80Pct: number | null; // illustrative ExpressCharge estimate
  notes: string[];
}

export interface SimulateResponse {
  profile: LaptopProfile;
  scenario: Scenario;
  adapter: AdapterOption;
  summary: Summary;
  trace: PowerState[];
}

// --- Anatomy ---

export type RegionKind =
  | "board"
  | "power"
  | "battery"
  | "cooling"
  | "memory"
  | "storage"
  | "io"
  | "display"
  | "wireless";

export interface Photo {
  url: string;
  caption: string;
  credit: string; // ALWAYS rendered by the UI
}

export interface Region {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
  photo?: Photo | null;
}

export interface SourceLink {
  label: string;
  url: string;
}

export interface Stat {
  label: string;
  value: string;
}

export interface Anatomy {
  id: string;
  name: string;
  vendor: string;
  platform: string;
  year: number;
  width: number; // 100
  height: number; // 62
  regions: Region[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo; // the interior jpg (/alienware-interior.jpg)
}

// --- Use cases ---

export interface UseCaseStep {
  title: string;
  body: string;
  regionIds: string[]; // resolve against anatomy
}

export interface UseCase {
  id: string;
  title: string;
  summary: string;
  persona: string;
  steps: UseCaseStep[];
  outcome: string;
  sources: SourceLink[];
}
