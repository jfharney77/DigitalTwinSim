import { apiFetch } from "@twinsim/twin-ui";
import { getLevel } from "./level";
import type {
  BrandMap,
  ConfigPreset,
  DeviceMap,
  Explain,
  GuidedScenario,
  PageIntro,
  Scenario,
  SimResponse,
  WorkloadPreset,
} from "./types";

const BASE = "/api";

function url(path: string, extra = ""): string {
  return `${BASE}${path}?level=${getLevel()}${extra}`;
}

function mapId(product: string, formFactor: string): string {
  if (product === "promax") return "promax";
  return formFactor === "desktop" ? "aw-desktop" : "aw-laptop";
}

export async function fetchAnatomy(
  product: string,
  formFactor: string,
): Promise<DeviceMap> {
  const r = await apiFetch(
    // `view` repeats the same choice as a map id: the hosted static build keys
    // its snapshots on it (the aliased formFactor cannot be snapshotted).
    url("/anatomy", `&product=${product}&formFactor=${formFactor}&view=${mapId(product, formFactor)}`),
  );
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

export async function fetchIntro(): Promise<PageIntro> {
  const r = await apiFetch(url("/intro"));
  if (!r.ok) throw new Error(`intro ${r.status}`);
  return r.json();
}

export async function fetchExplain(): Promise<Explain[]> {
  const r = await apiFetch(url("/explain"));
  if (!r.ok) throw new Error(`explain ${r.status}`);
  return r.json();
}

export async function fetchBrandMap(): Promise<BrandMap> {
  const r = await apiFetch(url("/brandmap"));
  if (!r.ok) throw new Error(`brandmap ${r.status}`);
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
