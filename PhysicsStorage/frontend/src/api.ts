import { apiFetch } from "@twinsim/twin-ui";
import { getLevel } from "./level";
import type {
  ConfigPreset,
  Explain,
  GuidedScenario,
  ProductMap,
  Scenario,
  SimResponse,
  WorkloadPreset,
} from "./types";

const BASE = "/api";

function url(path: string, extra = ""): string {
  return `${BASE}${path}?level=${getLevel()}${extra}`;
}

export async function fetchAnatomy(product: string): Promise<ProductMap> {
  const r = await apiFetch(url("/anatomy", `&product=${product}`));
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
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

export async function simulate(scenario: Scenario): Promise<SimResponse> {
  const r = await apiFetch(`${BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
  });
  if (!r.ok) throw new Error(`simulate ${r.status}`);
  return r.json();
}


export interface ProductMediaWire {
  name: string;
  tagline: string;
  kind: "photo" | "illustration";
  src?: string | null;
  shape?: string | null;
  credit: string;
  underlay?: string | null;
  caption?: string | null;
}

export async function fetchMedia(): Promise<Record<string, ProductMediaWire>> {
  const r = await apiFetch(`${BASE}/media`);
  if (!r.ok) throw new Error(`media ${r.status}`);
  return r.json();
}
