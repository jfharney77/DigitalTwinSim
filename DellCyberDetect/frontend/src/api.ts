import { apiFetch } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import { getLevel } from "./level";
import type {
  CatalogCategory,
  DetectAnatomy,
  DetectResponse,
  ScenarioInfo,
  UseCase,
} from "./types";

const BASE = "/api";

// Every request carries the reader's current level. The backend
// resolves the prose server-side and returns plain strings, so the
// wire types are unchanged — see backend/app/leveling.py.
function url(path: string): string {
  return `${BASE}${path}?level=${getLevel()}`;
}

export async function fetchAnatomy(): Promise<DetectAnatomy> {
  const r = await apiFetch(url("/anatomy"));
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

// The baseline incident is the endpoint's default, so it is requested
// exactly as it always was; a failure scenario adds ?scenario=.
export async function fetchDetect(
  scenario: string = "baseline",
): Promise<DetectResponse> {
  const q =
    scenario === "baseline" ? "" : `&scenario=${encodeURIComponent(scenario)}`;
  const r = await apiFetch(url("/detect") + q);
  if (!r.ok) throw new Error(`detect ${r.status}`);
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
