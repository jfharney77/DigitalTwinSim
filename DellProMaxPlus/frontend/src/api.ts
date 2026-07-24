import type {
  CatalogCategory,
  DeviceAnatomy,
  InferenceResponse,
  UseCase,
} from "./types";

const BASE = "/api";

export async function fetchAnatomy(): Promise<DeviceAnatomy> {
  const r = await fetch(`${BASE}/anatomy`);
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchInference(): Promise<InferenceResponse> {
  const r = await fetch(`${BASE}/inference`);
  if (!r.ok) throw new Error(`inference ${r.status}`);
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
