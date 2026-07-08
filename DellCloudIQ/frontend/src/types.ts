// Wire types for the CloudIQ / Dell AIOps visualizer. These mirror the
// pydantic models in backend/app/models.py, which serialize snake_case →
// camelCase. The shapes are renamed for the SaaS domain (PlatformMap /
// PlatformRegion / PipelineState) but are wire-compatible with the hardware
// twins' ChassisAnatomy / ChassisRegion / PowerOnState.

export type RegionKind =
  | "source"
  | "gateway"
  | "ingest"
  | "analytics"
  | "security"
  | "insight"
  | "assistant"
  | "action";

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

export type PipelinePhase =
  | "idle"
  | "collect"
  | "transmit"
  | "ingest"
  | "analyze"
  | "detect"
  | "surface"
  | "assist"
  | "notify";

export interface PipelineState {
  step: number;
  phase: PipelinePhase;
  label: string;
  description: string;
  activeRegions: string[];
  progressPercent: number;
  healthScore: number;
  dataPoints: number;
  elapsedSeconds: number;
  cycleCost: number;
}

export interface PipelineResponse {
  trace: PipelineState[];
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
