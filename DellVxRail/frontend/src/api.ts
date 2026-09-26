import { getLevel } from "./level";
import type {
  CatalogCategory,
  ClusterAnatomy,
  FirstRunResponse,
  ScenarioInfo,
  UseCase,
} from "./types";
import type { TourResponse } from "@twinsim/twin-ui";
import { apiFetch } from "@twinsim/twin-ui";

const BASE = "/api";

export const HAPPY_SCENARIO = "first-run";

// Every request carries the reader's current level. The backend
// resolves the prose server-side and returns plain strings, so the
// wire types are unchanged — see backend/app/leveling.py.
function url(path: string, scenario?: string): string {
  const q = `${BASE}${path}?level=${getLevel()}`;
  // The happy path is the backend's default, so it is requested exactly as
  // it was before scenarios existed.
  return scenario && scenario !== HAPPY_SCENARIO
    ? `${q}&scenario=${encodeURIComponent(scenario)}`
    : q;
}

// The node-add scenario is drawn on a taller map with a fifth node; every
// other caller gets the four-node map.
export async function fetchAnatomy(scenario?: string): Promise<ClusterAnatomy> {
  const r = await apiFetch(url("/anatomy", scenario));
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchFirstRun(scenario?: string): Promise<FirstRunResponse> {
  const r = await apiFetch(url("/firstrun", scenario));
  if (!r.ok) {
    throw new Error(
      r.status === 404 ? `Unknown scenario "${scenario}".` : `firstrun ${r.status}`,
    );
  }
  return r.json();
}

export async function fetchScenarios(): Promise<ScenarioInfo[]> {
  const r = await apiFetch(url("/scenarios"));
  if (!r.ok) throw new Error(`scenarios ${r.status}`);
  return r.json();
}

export async function fetchCatalog(): Promise<CatalogCategory[]> {
  const r = await apiFetch(url("/catalog"));
  if (!r.ok) throw new Error(`catalog ${r.status}`);
  return r.json();
}

export async function fetchUseCases(): Promise<UseCase[]> {
  const r = await apiFetch(url("/usecases"));
  if (!r.ok) throw new Error(`usecases ${r.status}`);
  return r.json();
}

export async function fetchTour(): Promise<TourResponse> {
  const r = await apiFetch(url("/tour"));
  if (!r.ok) throw new Error(`tour ${r.status}`);
  return r.json();
}
