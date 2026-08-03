// Wire types for the circular-design lifecycle visualizer. These mirror the
// pydantic models in backend/app/models.py, which serialize
// snake_case → camelCase.

export type RegionKind =
  | "materials"
  | "manufacture"
  | "packaging"
  | "deployment"
  | "service"
  | "recovery"
  | "refurbish"
  | "reclaim"
  | "loss";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

// A LifecycleRegion is a ClusterRegion plus `flowsTo`: the directed edges of
// the loop. The map's shape — including its returns and its leak — is
// backend data, not frontend code; LoopView just draws the edges it is sent.
export interface LifecycleRegion {
  id: string;
  kind: RegionKind;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  description: string;
  photo: Photo | null;
  flowsTo: string[];
}

export interface SourceLink {
  label: string;
  url: string;
}

export interface Stat {
  label: string;
  value: string;
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
  regions: LifecycleRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type MaterialPhase =
  | "materials"
  | "manufacture"
  | "ship"
  | "deploy"
  | "serve"
  | "repair"
  | "extend"
  | "recover"
  | "sort"
  | "reborn";

export interface MaterialState {
  step: number;
  phase: MaterialPhase;
  label: string;
  description: string;
  activeRegions: string[];
  elapsedMonths: number;
  cycleCost: number;
  massKg: number;
  recycledInputPercent: number;
  reusedKg: number;
  reclaimedKg: number;
  lostKg: number;
  yearsInService: number;
  repairs: number;
}

export interface MaterialResponse {
  trace: MaterialState[];
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
