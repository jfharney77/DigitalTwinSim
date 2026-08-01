import { getLevel } from "./level";
import type {
  CatalogCategory,
  ClusterAnatomy,
  NamespaceResponse,
  UseCase,
} from "./types";

const BASE = "/api";

// Every request carries the reader's current level. The backend
// resolves the prose server-side and returns plain strings, so the
// wire types are unchanged — see backend/app/leveling.py.
function url(path: string): string {
  return `${BASE}${path}?level=${getLevel()}`;
}

export async function fetchAnatomy(): Promise<ClusterAnatomy> {
  const r = await fetch(url("/anatomy"));
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchNamespace(): Promise<NamespaceResponse> {
  const r = await fetch(url("/namespace"));
  if (!r.ok) throw new Error(`namespace ${r.status}`);
  return r.json();
}

export async function fetchCatalog(): Promise<CatalogCategory[]> {
  const r = await fetch(url("/catalog"));
  if (!r.ok) throw new Error(`catalog ${r.status}`);
  return r.json();
}

export async function fetchUseCases(): Promise<UseCase[]> {
  const r = await fetch(url("/usecases"));
  if (!r.ok) throw new Error(`usecases ${r.status}`);
  return r.json();
}
