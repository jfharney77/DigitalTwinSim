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
  | "notify"
  // The "connected, but no data" failure scenario's own phases.
  | "register"
  | "handshake"
  | "blocked"
  | "starved"
  | "stale"
  | "repair"
  | "backfill"
  | "resume";

// "no-data": nothing has arrived, so there is no score to show (a grey dash).
export type ScoreState = "fresh" | "no-data";

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
  // Additive, for failure scenarios; the healthy trace carries the defaults.
  failedRegions: string[];
  scoreState: ScoreState;
  minutesWithoutData: number;
  backlogPoints: number;
}

export interface PipelineResponse {
  trace: PipelineState[];
  scenario: string;
}

export interface ScenarioInfo {
  id: string;
  name: string;
  summary: string;
  // The pipeline page's opening paragraph and the counters note, leveled.
  intro: string;
  note: string;
  heroField: string;
  phases: string[];
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
