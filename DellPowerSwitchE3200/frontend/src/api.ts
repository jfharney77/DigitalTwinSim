import type {
  BootResponse,
  CatalogCategory,
  ChassisAnatomy,
  UseCase,
} from "./types";

const BASE = "/api";

export async function fetchAnatomy(): Promise<ChassisAnatomy> {
  const r = await fetch(`${BASE}/anatomy`);
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchBoot(): Promise<BootResponse> {
  const r = await fetch(`${BASE}/boot`);
  if (!r.ok) throw new Error(`boot ${r.status}`);
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
