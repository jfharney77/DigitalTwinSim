// Wire types for the PowerProtect visualizer. These mirror the pydantic
// models in backend/app/models.py, which serialize snake_case → camelCase.

export type RegionKind =
  | "workload"
  | "backup"
  | "appliance"
  | "gap"
  | "analytics"
  | "recovery"
  | "mgmt";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface SiteRegion {
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

export interface SiteAnatomy {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: SiteRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type LifecyclePhase =
  | "idle"
  | "backup"
  | "dedupe"
  | "replicate"
  | "airgap"
  | "scan"
  | "attack"
  | "recover"
  | "restored";

export interface LifecycleState {
  step: number;
  phase: LifecyclePhase;
  label: string;
  description: string;
  activeRegions: string[];
  logicalTb: number;
  storedTb: number;
  elapsedHours: number;
  cycleCost: number;
  // CyberSense's verdicts so far; both zero until the scan step.
  copiesScanned: number;
  copiesFlagged: number;
}

export interface LifecycleResponse {
  trace: LifecycleState[];
}

// The cleaning (garbage collection) failure scenario. Its states extend the
// happy path's with a capacity ledger; see backend/app/cleaning.py.
export type CleaningPhase =
  | "steady"
  | "expire"
  | "ingest"
  | "alert"
  | "clean"
  | "pinned"
  | "release"
  | "reclean"
  | "settled";

export interface CleaningFields {
  capacityTb: number;
  liveTb: number;
  reclaimableTb: number;
  heldByReplicationTb: number;
  heldBySnapshotTb: number;
  heldByLockTb: number;
  cleanableTb: number;
  reclaimedTb: number;
  lockDaysLeft: number;
  cleanRunning: boolean;
  failedRegions: string[];
  alerts: string[];
}

// One playable step of either trace: the ledger fields are present only in
// the cleaning scenario.
export type TraceState = Omit<LifecycleState, "phase"> & {
  phase: LifecyclePhase | CleaningPhase;
} & Partial<CleaningFields>;

export interface TraceResponse {
  scenario?: string;
  trace: TraceState[];
}

export interface ScenarioInfo {
  id: string;
  title: string;
  summary: string;
  hero: string;
  isFailure: boolean;
  // Leveled page prose for the lifecycle page; empty keeps the page's own.
  intro: string;
  countersNote: string;
  sources: SourceLink[];
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
