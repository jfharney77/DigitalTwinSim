// Wire types for the Cyber Detect visualizer. These mirror the pydantic
// models in backend/app/models.py, which serialize snake_case → camelCase.

export type RegionKind =
  | "array"
  | "snapshot"
  | "inspect"
  | "classifier"
  | "models"
  | "verdict"
  | "recovery";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface DetectRegion {
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

export interface DetectAnatomy {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: DetectRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type DetectPhase =
  | "clean"
  | "intrusion"
  | "encrypt"
  | "blind"
  | "inspect"
  | "classify"
  | "verdict"
  | "recover"
  | "restored";

export interface DetectState {
  step: number;
  phase: DetectPhase;
  label: string;
  description: string;
  activeRegions: string[];
  snapshotsTaken: number;
  snapshotsCorrupted: number;
  metadataAlerts: number;
  contentConfidencePercent: number;
  lastCleanSnapshot: number;
  // When the named copy was taken (illustrative clock); null until named.
  lastCleanTakenAtHours: number | null;
  elapsedHours: number;
  cycleCost: number;
  // Additive, for failure scenarios (defaults on the baseline trace).
  snapshotsExpired: number;
  verdict: "" | "clean-copy-named" | "no-clean-copy-on-array";
  recoverySource: "" | "array-snapshot" | "powerprotect-vault";
  recoveryPointAgeHours: number;
  failedRegions: string[];
}

export interface DetectResponse {
  trace: DetectState[];
  scenario: string;
}

export interface ScenarioInfo {
  id: string;
  name: string;
  summary: string;
  heroLabel: string;
  heroValue: string;
  retentionHours: number;
  sources: SourceLink[];
  // Leveled page copy for the incident page under this scenario.
  heading: string;
  intro: string;
  mapNote: string;
  countersNote: string;
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
