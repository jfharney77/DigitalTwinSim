// Wire types for the Fort Zero visualizer. These mirror the pydantic models
// in backend/app/models.py, which serialize snake_case → camelCase.

export type RegionKind =
  | "identity"
  | "device"
  | "network"
  | "workload"
  | "data"
  | "visibility"
  | "automation"
  | "policy";

export interface Photo {
  url: string;
  caption: string;
  credit: string;
}

export interface Pillar {
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

export interface ZeroTrustMap {
  id: string;
  name: string;
  vendor: string;
  formFactor: string;
  generation: string;
  year: number;
  width: number;
  height: number;
  regions: Pillar[];
  stats: Stat[];
  sources: SourceLink[];
  overview: string;
  photo: Photo | null;
}

export type AccessPhase =
  | "idle"
  | "request"
  | "verify"
  | "context"
  | "decide"
  | "grant"
  | "monitor"
  | "expire"
  | "breach"
  | "contained";

export interface AccessState {
  step: number;
  phase: AccessPhase;
  label: string;
  description: string;
  activeRegions: string[];
  trustScore: number;
  resourcesReachable: number;
  implicitTrustGrants: number;
  verifications: number;
  trustTtlSeconds: number;
  elapsedSeconds: number;
  cycleCost: number;
}

export interface AccessResponse {
  trace: AccessState[];
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
