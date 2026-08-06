// Wire types for the NativeEdge visualizer. These mirror the pydantic
// models in backend/app/models.py, which serialize snake_case → camelCase.

export type RegionKind =
  | "endpoint"
  | "network"
  | "identity"
  | "orchestrator"
  | "blueprint"
  | "catalog"
  | "policy"
  | "observability";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface PlatformRegion {
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

export interface PlatformMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: PlatformRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type OnboardPhase =
  | "crated"
  | "power"
  | "attest"
  | "onboard"
  | "provision"
  | "blueprint"
  | "workload"
  | "managed";

export interface OnboardState {
  step: number;
  phase: OnboardPhase;
  label: string;
  description: string;
  activeRegions: string[];
  endpointsOnline: number;
  operatorActions: number;
  trustEstablished: boolean;
  progressPercent: number;
  elapsedSeconds: number;
  cycleCost: number;
}

export interface OnboardResponse {
  trace: OnboardState[];
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
