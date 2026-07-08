import type {
  CatalogCategory,
  PipelineResponse,
  PlatformMap,
  UseCase,
} from "./types";

const BASE = "/api";

export async function fetchAnatomy(): Promise<PlatformMap> {
  const r = await fetch(`${BASE}/anatomy`);
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchPipeline(): Promise<PipelineResponse> {
  const r = await fetch(`${BASE}/pipeline`);
  if (!r.ok) throw new Error(`pipeline ${r.status}`);
  return r.json();
}

export async function fetchCatalog(): Promise<CatalogCategory[]> {
  const r = await fetch(`${BASE}/catalog`);
  if (!r.ok) throw new Error(`catalog ${r.status}`);
  return r.json();
}

export async function fetchUseCases(): Promise<UseCase[]> {
  const r = await fetch(`${BASE}/usecases`);
  if (!r.ok) throw new Error(`usecases ${r.status}`);
  return r.json();
}
