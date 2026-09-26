import { apiFetch, warmEngine } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import { getLevel } from "./level";
import type {
  Anatomy,
  LaptopProfile,
  Scenario,
  SimulateResponse,
  TraceScenario,
  UseCase,
} from "./types";

const BASE = "/api";

// Static-hosted build only (a no-op otherwise): POST /api/simulate is answered
// by the real engine.py running in the browser, and its answer depends on
// ?level= and ?scenario=, so it is never prebaked. Start that download now
// rather than on the first simulate call.
warmEngine();

// Prose-bearing requests carry the reader's level; the backend
// resolves server-side, so the wire types are unchanged.
function lv(): string {
  return `?level=${getLevel()}`;
}

export async function fetchCatalog(): Promise<LaptopProfile[]> {
  const r = await apiFetch(`${BASE}/catalog${lv()}`);
  if (!r.ok) throw new Error(`catalog ${r.status}`);
  return r.json();
}

export async function fetchDefaultProfile(): Promise<LaptopProfile> {
  const r = await apiFetch(`${BASE}/catalog/default${lv()}`);
  if (!r.ok) throw new Error(`catalog/default ${r.status}`);
  return r.json();
}

export async function fetchAnatomies(): Promise<Anatomy[]> {
  const r = await apiFetch(`${BASE}/anatomy${lv()}`);
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

// One anatomy is read out of the list endpoint rather than
// /api/anatomy/{id}: the payload is identical (same data, same level), and a
// query-only route is one the static-hosted build can snapshot
// (docs/STATIC_HOSTING.md — path parameters are not snapshotted).
export async function fetchAnatomy(id: string): Promise<Anatomy> {
  const all = await fetchAnatomies();
  const found = all.find((a) => a.id === id);
  if (!found) throw new Error(`anatomy/${id} 404`);
  return found;
}

export async function fetchUseCases(): Promise<UseCase[]> {
  const r = await apiFetch(`${BASE}/usecases${lv()}`);
  if (!r.ok) throw new Error(`usecases ${r.status}`);
  return r.json();
}

// The plug-in trace is the endpoint with no scenario parameter, as it always
// was; a failure trace is the same endpoint with ?scenario=<id>.
export const BASELINE_TRACE = "plug-in";

export async function simulate(
  scenario: Scenario,
  traceScenario: string = BASELINE_TRACE,
): Promise<SimulateResponse> {
  const which =
    traceScenario === BASELINE_TRACE
      ? ""
      : `&scenario=${encodeURIComponent(traceScenario)}`;
  const r = await apiFetch(`${BASE}/simulate${lv()}${which}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  if (!r.ok) throw new Error(`simulate ${r.status}`);
  return r.json();
}

export async function fetchScenarios(): Promise<TraceScenario[]> {
  const r = await apiFetch(`${BASE}/scenarios${lv()}`);
  if (!r.ok) throw new Error(`scenarios ${r.status}`);
  return r.json();
}

// The narrated guided tour (GET /api/tour): leveled narration plus the layer
// map and bounds the player frames its camera in.
export async function fetchTour(): Promise<TourResponse> {
  const r = await apiFetch(`${BASE}/tour${lv()}`);
  if (!r.ok) throw new Error(`tour ${r.status}`);
  return r.json();
}
