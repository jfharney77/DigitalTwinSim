import { getLevel } from "./level";
import type {
  DieAnatomy,
  GpuProfile,
  LiveSessionInfo,
  LiveState,
  SimulateResponse,
  Workload,
} from "./types";

const BASE = "/api";

// Prose-bearing requests carry the reader's level; the backend
// resolves server-side, so the wire types are unchanged.
function lv(): string {
  return `?level=${getLevel()}`;
}

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

export async function fetchAnatomies(): Promise<DieAnatomy[]> {
  const r = await fetch(`${BASE}/anatomy${lv()}`);
  if (!r.ok) throw new Error(`anatomy ${r.status}`);
  return r.json();
}

// -- Live CUDA co-browsing (spec_08) ------------------------------------------

export async function startLiveSession(name: string): Promise<LiveSessionInfo> {
  const r = await fetch(`${BASE}/live/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error(`live/session ${r.status}`);
  return r.json();
}

export async function stopLiveSession(): Promise<void> {
  const r = await fetch(`${BASE}/live/session`, { method: "DELETE" });
  if (!r.ok) throw new Error(`live/session ${r.status}`);
}

export async function fetchLiveSessions(): Promise<LiveSessionInfo[]> {
  const r = await fetch(`${BASE}/live/sessions`);
  if (!r.ok) throw new Error(`live/sessions ${r.status}`);
  return r.json();
}

export async function fetchLiveTrace(id: string): Promise<LiveState[]> {
  const r = await fetch(`${BASE}/live/sessions/${encodeURIComponent(id)}/trace`);
  if (!r.ok) throw new Error(`live trace ${r.status}`);
  const body = await r.json();
  return body.trace as LiveState[];
}

export function liveStreamUrl(): string {
  return `${BASE}/live/stream`;
}

export async function simulate(
  profile: GpuProfile,
  workload: Workload,
): Promise<SimulateResponse> {
  const r = await fetch(`${BASE}/simulate${lv()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, workload }),
  });
  if (!r.ok) throw new Error(`simulate ${r.status}`);
  return r.json();
}
