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
}

export interface LifecycleResponse {
  trace: LifecycleState[];
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
