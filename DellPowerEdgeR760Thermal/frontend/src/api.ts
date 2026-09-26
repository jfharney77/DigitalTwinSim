import { apiFetch } from "@twinsim/twin-ui";
import { getLevel } from "./level";
import type {
  ChassisMap,
  ConfigPreset,
  ConstantsResponse,
  Explain,
  GuidedScenario,
  Scenario,
  SimResponse,
  WorkloadPreset,
} from "./types";

const BASE = "/api";

// Prose-bearing requests carry the reader's current level; the backend
// resolves server-side (see backend/app/leveling.py).
function url(path: string): string {
  return `${BASE}${path}?level=${getLevel()}`;
}

export async function fetchAnatomy(): Promise<ChassisMap> {
  const r = await apiFetch(url("/anatomy"));
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchConstants(): Promise<ConstantsResponse> {
  const r = await apiFetch(`${BASE}/constants`);
  if (!r.ok) throw new Error(`constants ${r.status}`);
  return r.json();
}

export async function fetchConfigPresets(): Promise<ConfigPreset[]> {
  const r = await apiFetch(`${BASE}/presets/configs`);
  if (!r.ok) throw new Error(`presets ${r.status}`);
  return r.json();
}

export async function fetchWorkloadPresets(): Promise<WorkloadPreset[]> {
  const r = await apiFetch(`${BASE}/presets/workloads`);
  if (!r.ok) throw new Error(`presets ${r.status}`);
  return r.json();
}

export async function fetchScenarios(): Promise<GuidedScenario[]> {
  const r = await apiFetch(url("/scenarios"));
  if (!r.ok) throw new Error(`scenarios ${r.status}`);
  return r.json();
}

export async function fetchExplain(): Promise<Explain[]> {
  const r = await apiFetch(url("/explain"));
  if (!r.ok) throw new Error(`explain ${r.status}`);
  return r.json();
}

// The trace itself is numbers, but the event log is prose, so the
// simulate request carries the level too.
export async function simulate(scenario: Scenario): Promise<SimResponse> {
  const r = await apiFetch(url("/simulate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
  });
  if (!r.ok) throw new Error(`simulate ${r.status}`);
  return r.json();
}
