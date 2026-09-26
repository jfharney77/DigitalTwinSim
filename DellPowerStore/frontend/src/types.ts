// Wire types for the PowerStore visualizer. These mirror the pydantic
// models in backend/app/models.py, which serialize snake_case → camelCase.

export type RegionKind =
  | "storage"
  | "nvram"
  | "cpu"
  | "memory"
  | "io"
  | "power"
  | "cooling"
  | "battery"
  | "management"
  | "board";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface ChassisRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
  photo: Photo | null;
}

export interface SourceLink {
  label: string;
  url: string;
}

export interface Stat {
  label: string;
  value: string;
}

export interface ChassisAnatomy {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: ChassisRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type PowerPhase =
  | "off"
  | "power"
  | "boot"
  | "drives"
  | "cluster"
  | "services"
  | "online";

export interface PowerOnState {
  step: number;
  phase: PowerPhase;
  label: string;
  description: string;
  activeRegions: string[];
  powerWatts: number;
  fanPercent: number;
  elapsedSeconds: number;
  cycleCost: number;
}

// Failure scenarios extend the state additively: a power-on state carries
// none of these, a failover state carries all of them.
export type FailoverPhase =
  | "online"
  | "fault"
  | "failover"
  | "degraded"
  | "rejoin"
  | "resync"
  | "rebalance"
  | "restored";

export interface FailoverFields {
  failedRegions: string[];
  ackedWritesLost: number;
  ioPercent: number;
  nodesServing: number;
  nodeBLoadPercent: number;
  optimizedPathsPercent: number;
  writesMirrored: boolean;
  nodeAJoined: boolean;
}

export type TraceState = Omit<PowerOnState, "phase"> & {
  phase: PowerPhase | FailoverPhase;
} & Partial<FailoverFields>;

export interface ScenarioInfo {
  id: string;
  name: string;
  summary: string;
  heroMetric: string;
  basis: string;
  sources: SourceLink[];
}

export interface PowerOnResponse {
  trace: TraceState[];
  // Present on failure scenarios only.
  scenario?: ScenarioInfo;
}

export interface CatalogOption {
  id: string;
  name: string;
  summary: string;
  details: string;
}

export interface CatalogCategory {
  id: string;
  name: string;
  blurb: string;
  limits: string;
  regionIds: string[];
  options: CatalogOption[];
}

export interface UseCaseItem {
  categoryId: string;
  optionId: string;
  qty: number;
  rationale: string;
}

export interface UseCase {
  id: string;
  title: string;
  summary: string;
  narrative: string[];
  config: UseCaseItem[];
  outcomes: Stat[];
}
