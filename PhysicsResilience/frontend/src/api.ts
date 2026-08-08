import { getLevel } from "./level";
import type {
  ConfigPreset,
  Explain,
  GuidedScenario,
  ResilienceMap,
  Scenario,
  SimResponse,
} from "./types";

const BASE = "/api";

function url(path: string, extra = ""): string {
  return `${BASE}${path}?level=${getLevel()}${extra}`;
}

export async function fetchAnatomy(product: string): Promise<ResilienceMap> {
  const r = await fetch(url("/anatomy", `&product=${product}`));
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchScope(): Promise<string> {
  const r = await fetch(`${BASE}/scope`);
  if (!r.ok) throw new Error(`scope ${r.status}`);
  return (await r.json()).scope;
}

export async function fetchConfigPresets(): Promise<ConfigPreset[]> {
  const r = await fetch(`${BASE}/presets/configs`);
  if (!r.ok) throw new Error(`presets ${r.status}`);
  return r.json();
}

export async function fetchScenarios(): Promise<GuidedScenario[]> {
  const r = await fetch(url("/scenarios"));
  if (!r.ok) throw new Error(`scenarios ${r.status}`);
  return r.json();
}

export async function fetchExplain(): Promise<Explain[]> {
  const r = await fetch(url("/explain"));
  if (!r.ok) throw new Error(`explain ${r.status}`);
  return r.json();
}

export async function simulate(scenario: Scenario): Promise<SimResponse> {
  const r = await fetch(`${BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
  });
  if (!r.ok) throw new Error(`simulate ${r.status}`);
  return r.json();
}
