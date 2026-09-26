// Wire types for the iDRAC9 visualizer. These mirror the pydantic models in
// backend/app/models.py, which serialize snake_case → camelCase.

export type RegionKind =
  | "soc"
  | "memory"
  | "network"
  | "sideband"
  | "io"
  | "power"
  | "security"
  | "sensor";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface Block {
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

export interface SubsystemMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: Block[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type BringUpPhase =
  | "off"
  | "standby"
  | "reset"
  | "bootldr"
  | "kernel"
  | "services"
  | "ready";

// The firmware-update failure scenario starts at "ready" and walks these.
export type UpdatePhase =
  | "upload"
  | "verify"
  | "stage"
  | "reboot"
  | "bootcheck"
  | "rollback"
  | "restored";

export type ScenarioId = "bring-up" | "firmware-update-rollback";

export interface ScenarioInfo {
  id: ScenarioId;
  name: string;
  summary: string;
  phases: string[];
  heroLabel: string;
  basis: string;
  /** The paragraph under the trace page's heading, at the reading level. */
  intro?: string;
  sources: SourceLink[];
}

export interface BringUpState {
  step: number;
  phase: BringUpPhase | UpdatePhase;
  label: string;
  description: string;
  activeRegions: string[];
  powerWatts: number;
  progressPercent: number;
  elapsedSeconds: number;
  cycleCost: number;
  // Failure-scenario fields: absent from the bring-up trace entirely.
  hostPowered?: boolean;
  activePartition?: "A" | "B";
  runningVersion?: string;
  writingPartition?: "A" | "B";
  signatureVerified?: boolean;
  bootableImages?: number;
  managementReachable?: boolean;
  managementOutageSeconds?: number;
  failedRegions?: string[];
  logEntry?: string;
}

export interface BringUpResponse {
  trace: BringUpState[];
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
