import { apiFetch } from "@twinsim/twin-ui";
import { getLevel } from "./level";
import type {
  CatalogCategory,
  ChassisAnatomy,
  PowerOnResponse,
  ScenarioInfo,
  UseCase,
} from "./types";
import type { TourResponse } from "@twinsim/twin-ui";

const BASE = "/api";

// Every request carries the reader's current level. The backend
// resolves the prose server-side and returns plain strings, so the
// wire types are unchanged — see backend/app/leveling.py.
function url(path: string): string {
  return `${BASE}${path}?level=${getLevel()}`;
}

export async function fetchAnatomy(): Promise<ChassisAnatomy> {
  const r = await apiFetch(url("/anatomy"));
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

// The power-on trace, or a failure scenario served from the same endpoint.
// The default scenario sends no parameter, so that request is unchanged.
export const DEFAULT_SCENARIO = "power-on";

export async function fetchPowerOn(
  scenario: string = DEFAULT_SCENARIO,
): Promise<PowerOnResponse> {
  const q =
    scenario === DEFAULT_SCENARIO
      ? ""
      : `&scenario=${encodeURIComponent(scenario)}`;
  const r = await apiFetch(url("/poweron") + q);
  if (!r.ok) throw new Error(`poweron ${r.status}`);
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
