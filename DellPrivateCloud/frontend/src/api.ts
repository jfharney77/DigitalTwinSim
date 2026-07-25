import type {
  CatalogCategory,
  CloudAnatomy,
  CloudResponse,
  UseCase,
} from "./types";

const BASE = "/api";

export async function fetchAnatomy(): Promise<CloudAnatomy> {
  const r = await fetch(`${BASE}/anatomy`);
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchCloud(): Promise<CloudResponse> {
  const r = await fetch(`${BASE}/cloud`);
  if (!r.ok) throw new Error(`cloud ${r.status}`);
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
