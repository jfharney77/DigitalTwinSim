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
  | "steady"
  // The gray-link failure scenario's own phases (backend/app/scenarios.py).
  | "degrade"
  | "blind"
  | "telemetry"
  | "steer"
  | "drain"
  | "replace"
  | "restored";

export type LinkStatus = "up" | "admin-down" | "training";

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
  // What losslessness costs (illustrative). hotLink is "<leaf id>:<spine id>",
  // set only while that link is saturated.
  hotLink: string | null;
  ecnMarkedPercent: number;
  pfcPausesPerSec: number;
  // Failure-scenario fields; all at their nothing-is-wrong defaults on the
  // healthy trace. sickLink is "<leaf id>:<spine id>".
  sickLink: string | null;
  sickLinkStatus: LinkStatus | null;
  sickLinkLocated: boolean;
  trafficSteered: boolean;
  symbolErrorsPerSec: number;
  retransmitsPerSec: number;
  collectiveMs: number;
}

export interface FabricResponse {
  trace: FabricState[];
  scenario: string;
}

export interface Scenario {
  id: string;
  name: string;
  summary: string;
  heroField: string | null;
  heroLabel: string | null;
  // Leveled page prose that belongs to the scenario.
  intro: string;
  telemetryNote: string;
  playbackHint: string;
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
