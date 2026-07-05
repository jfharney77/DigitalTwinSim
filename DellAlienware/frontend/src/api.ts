import type {
  Anatomy,
  LaptopProfile,
  Scenario,
  SimulateResponse,
  UseCase,
} from "./types";

const BASE = "/api";

export async function fetchCatalog(): Promise<LaptopProfile[]> {
  const r = await fetch(`${BASE}/catalog`);
  if (!r.ok) throw new Error(`catalog ${r.status}`);
  return r.json();
}

export async function fetchDefaultProfile(): Promise<LaptopProfile> {
  const r = await fetch(`${BASE}/catalog/default`);
  if (!r.ok) throw new Error(`catalog/default ${r.status}`);
  return r.json();
}

export async function fetchAnatomies(): Promise<Anatomy[]> {
  const r = await fetch(`${BASE}/anatomy`);
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

export async function fetchAnatomy(id: string): Promise<Anatomy> {
  const r = await fetch(`${BASE}/anatomy/${encodeURIComponent(id)}`);
  if (!r.ok) throw new Error(`anatomy/${id} ${r.status}`);
  return r.json();
}

export async function fetchUseCases(): Promise<UseCase[]> {
  const r = await fetch(`${BASE}/usecases`);
  if (!r.ok) throw new Error(`usecases ${r.status}`);
  return r.json();
}

export async function simulate(scenario: Scenario): Promise<SimulateResponse> {
  const r = await fetch(`${BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  if (!r.ok) throw new Error(`simulate ${r.status}`);
  return r.json();
}
