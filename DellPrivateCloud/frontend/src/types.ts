// Wire types for the Private Cloud visualizer. These mirror the pydantic
// models in backend/app/models.py, which serialize snake_case → camelCase.

export type RegionKind =
  | "controlplane"
  | "workload"
  | "hypervisor"
  | "compute"
  | "storage"
  | "network"
  | "fabric";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface CloudRegion {
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

export interface CloudAnatomy {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: CloudRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type CloudPhase =
  | "off"
  | "pools"
  | "control"
  | "install"
  | "deploy"
  | "run"
  | "growstorage"
  | "switch"
  | "mixed";

export interface CloudState {
  step: number;
  phase: CloudPhase;
  label: string;
  description: string;
  activeRegions: string[];
  computeUnits: number;
  storageTb: number;
  hypervisorsActive: number;
  workloads: number;
  controlPlanes: number;
  workloadDowntimeSeconds: number;
  elapsedMinutes: number;
  cycleCost: number;
}

export interface CloudResponse {
  trace: CloudState[];
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
