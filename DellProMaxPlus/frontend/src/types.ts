// Wire types for the Pro Max Plus inference visualizer. These mirror the
// pydantic models in backend/app/models.py, which serialize snake_case →
// camelCase.

export type RegionKind =
  | "host"
  | "memory"
  | "storage"
  | "link"
  | "npu"
  | "aimemory"
  | "thermal"
  | "power"
  | "runtime";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface DeviceRegion {
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

export interface DeviceAnatomy {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: DeviceRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type InferencePhase =
  | "off"
  | "compile"
  | "load"
  | "resident"
  | "prefill"
  | "decode"
  | "sustained"
  | "offline";

export interface InferenceState {
  step: number;
  phase: InferencePhase;
  label: string;
  description: string;
  activeRegions: string[];
  weightsResidentGb: number;
  linkGbps: number;
  tokensPerSecond: number;
  npuWatts: number;
  elapsedSeconds: number;
  cycleCost: number;
}

export interface InferenceResponse {
  trace: InferenceState[];
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
