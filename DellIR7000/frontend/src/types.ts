// Wire types for the IR7000 + PowerCool visualizer. These mirror the
// pydantic models in backend/app/models.py, which serialize snake_case →
// camelCase.

export type RegionKind =
  | "cdu"
  | "manifold"
  | "coldplate"
  | "airdoor"
  | "power"
  | "facility"
  | "sensor";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface RackRegion {
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

export interface RackAnatomy {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: RackRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type ThermalPhase =
  | "off"
  | "fill"
  | "pump"
  | "verify"
  | "airdoor"
  | "load"
  | "balance"
  | "steady";

export interface ThermalState {
  step: number;
  phase: ThermalPhase;
  label: string;
  description: string;
  activeRegions: string[];
  itLoadWatts: number;
  liquidWatts: number;
  airWatts: number;
  flowLpm: number;
  elapsedSeconds: number;
  cycleCost: number;
}

export interface ThermalResponse {
  trace: ThermalState[];
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
