import type { GpuProfile, SimulateResponse, Workload } from "./types";

const BASE = "/api";

export async function fetchDefaultProfile(): Promise<GpuProfile> {
  const r = await fetch(`${BASE}/profiles/default`);
  if (!r.ok) throw new Error(`profiles/default ${r.status}`);
  return r.json();
}

export async function fetchProfiles(): Promise<GpuProfile[]> {
  const r = await fetch(`${BASE}/profiles`);
  if (!r.ok) throw new Error(`profiles ${r.status}`);
  return r.json();
}

export async function simulate(
  profile: GpuProfile,
  workload: Workload,
): Promise<SimulateResponse> {
  const r = await fetch(`${BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, workload }),
  });
  if (!r.ok) throw new Error(`simulate ${r.status}`);
  return r.json();
}
