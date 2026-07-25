import type {
  AccessResponse,
  CatalogCategory,
  UseCase,
  ZeroTrustMap,
} from "./types";

const BASE = "/api";

export async function fetchAnatomy(): Promise<ZeroTrustMap> {
  const r = await fetch(`${BASE}/anatomy`);
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchAccess(): Promise<AccessResponse> {
  const r = await fetch(`${BASE}/access`);
  if (!r.ok) throw new Error(`access ${r.status}`);
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
