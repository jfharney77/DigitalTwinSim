import { getLevel } from "./level";
import type {
  BrandMap,
  ConfigPreset,
  DeviceMap,
  Explain,
  GuidedScenario,
  Scenario,
  SimResponse,
  WorkloadPreset,
} from "./types";

const BASE = "/api";

function url(path: string, extra = ""): string {
  return `${BASE}${path}?level=${getLevel()}${extra}`;
}

export async function fetchAnatomy(
  product: string,
  formFactor: string,
): Promise<DeviceMap> {
  const r = await fetch(
    url("/anatomy", `&product=${product}&formFactor=${formFactor}`),
  );
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchConfigPresets(): Promise<ConfigPreset[]> {
  const r = await fetch(`${BASE}/presets/configs`);
  if (!r.ok) throw new Error(`presets ${r.status}`);
  return r.json();
}

export async function fetchWorkloadPresets(): Promise<WorkloadPreset[]> {
  const r = await fetch(`${BASE}/presets/workloads`);
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

export async function fetchBrandMap(): Promise<BrandMap> {
  const r = await fetch(url("/brandmap"));
  if (!r.ok) throw new Error(`brandmap ${r.status}`);
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
