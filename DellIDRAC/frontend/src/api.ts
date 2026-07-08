import type {
  BringUpResponse,
  CatalogCategory,
  SubsystemMap,
  UseCase,
} from "./types";

const BASE = "/api";

export async function fetchAnatomy(): Promise<SubsystemMap> {
  const r = await fetch(`${BASE}/anatomy`);
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchBringUp(): Promise<BringUpResponse> {
  const r = await fetch(`${BASE}/bringup`);
  if (!r.ok) throw new Error(`bringup ${r.status}`);
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
