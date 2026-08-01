// Wire types for the SN6000 fabric visualizer. These mirror the pydantic
// models in backend/app/models.py, which serialize snake_case → camelCase.

export type RegionKind =
  | "spine"
  | "leaf"
  | "endpoint"
  | "optics"
  | "telemetry"
  | "cooling"
  | "management";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface FabricRegion {
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

export interface FabricAnatomy {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: FabricRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type FabricPhase =
  | "off"
  | "power"
  | "linktrain"
  | "topology"
  | "ready"
  | "collective"
  | "congestion"
  | "reroute"
  | "steady";

export interface FabricState {
  step: number;
  phase: FabricPhase;
  label: string;
  description: string;
  activeRegions: string[];
  fabricTbps: number;
  peakLinkPercent: number;
  droppedPackets: number;
  elapsedSeconds: number;
  cycleCost: number;
}

export interface FabricResponse {
  trace: FabricState[];
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
