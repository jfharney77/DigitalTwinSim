// Wire types for the PowerScale namespace visualizer. These mirror the
// pydantic models in backend/app/models.py, which serialize
// snake_case → camelCase.

export type RegionKind =
  | "node"
  | "media"
  | "protocol"
  | "interconnect"
  | "namespace"
  | "management";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface ClusterRegion {
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

export interface ClusterAnatomy {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: ClusterRegion[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type NamespacePhase =
  | "off"
  | "form"
  | "stripe"
  | "serve"
  | "fill"
  | "addnode"
  | "rebalance"
  | "served";

export interface NamespaceState {
  step: number;
  phase: NamespacePhase;
  label: string;
  description: string;
  activeRegions: string[];
  nodes: number;
  namespaces: number;
  capacityTb: number;
  usedPercent: number;
  migrationsRequired: number;
  rebalancing: boolean;
  elapsedSeconds: number;
  cycleCost: number;
}

export interface NamespaceResponse {
  trace: NamespaceState[];
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
