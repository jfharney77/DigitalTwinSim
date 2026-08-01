// Wire types for the Exascale + Lightning visualizer. These mirror the
// pydantic models in backend/app/models.py, which serialize snake_case →
// camelCase.

export type RegionKind =
  | "client"
  | "fabric"
  | "metadata"
  | "dataserver"
  | "media"
  | "protocol"
  | "management";

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

export interface PlatformAnatomy {
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

export type DataPhase =
  | "idle"
  | "mount"
  | "layout"
  | "stripe"
  | "feed"
  | "checkpoint"
  | "tier"
  | "steady";

export interface DataState {
  step: number;
  phase: DataPhase;
  label: string;
  description: string;
  activeRegions: string[];
  throughputGbps: number;
  dataServersStreaming: number;
  layoutHeld: boolean;
  elapsedSeconds: number;
  cycleCost: number;
}

export interface DataResponse {
  trace: DataState[];
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
