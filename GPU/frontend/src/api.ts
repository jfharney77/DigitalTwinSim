import { getLevel } from "./level";
import type {
  Atlas,
  DieAnatomy,
  GpuProfile,
  LessonTour,
  LiveSessionInfo,
  LiveState,
  Measurements,
  SessionSummary,
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

// spec_30: the profile↔die pairs + deviceMatch substrings, served as data
// so the frontend hardcodes nothing.
export async function fetchAtlas(): Promise<Atlas> {
  const r = await fetch(`${BASE}/atlas`);
  if (!r.ok) throw new Error(`atlas ${r.status}`);
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

export async function fetchLiveTrace(
  id: string,
  asProfile?: string | null, // spec_28: remap the replay onto a fleet die
): Promise<LiveState[]> {
  const q = asProfile ? `?asProfile=${encodeURIComponent(asProfile)}` : "";
  const r = await fetch(
    `${BASE}/live/sessions/${encodeURIComponent(id)}/trace${q}`,
  );
  if (!r.ok) throw new Error(`live trace ${r.status}`);
  const body = await r.json();
  return body.trace as LiveState[];
}

export function liveStreamUrl(): string {
  return `${BASE}/live/stream`;
}

export async function deleteLiveSession(id: string): Promise<void> {
  const r = await fetch(`${BASE}/live/sessions/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!r.ok) throw new Error(`delete session ${r.status}`);
}

export function sessionDownloadUrl(id: string): string {
  return `${BASE}/live/sessions/${encodeURIComponent(id)}/download`;
}

export function sessionCsvUrl(id: string): string {
  return `${BASE}/live/sessions/${encodeURIComponent(id)}/events.csv`;
}

export async function fetchSessionSummary(id: string): Promise<SessionSummary> {
  const r = await fetch(`${BASE}/live/sessions/${encodeURIComponent(id)}/summary`);
  if (!r.ok) throw new Error(`summary ${r.status}`);
  return r.json();
}

export async function importLiveSession(
  name: string,
  jsonl: string,
): Promise<LiveSessionInfo> {
  const r = await fetch(`${BASE}/live/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, jsonl }),
  });
  if (!r.ok) throw new Error(`import ${r.status}`);
  return r.json();
}

export async function fetchMeasurements(): Promise<Measurements> {
  const r = await fetch(`${BASE}/measurements`);
  if (!r.ok) throw new Error(`measurements ${r.status}`);
  return r.json();
}

export async function fetchLessonTour(): Promise<LessonTour> {
  // spec_29: the tour carries prose, so it rides the reading level.
  const r = await fetch(`${BASE}/tour${lv()}`);
  if (!r.ok) throw new Error(`tour ${r.status}`);
  return r.json();
}

export async function fetchTourRecording(
  lessonId: string,
  asProfile?: string | null, // spec_28
): Promise<LiveState[]> {
  const q = asProfile ? `?asProfile=${encodeURIComponent(asProfile)}` : "";
  const r = await fetch(
    `${BASE}/tour/recordings/${encodeURIComponent(lessonId)}${q}`,
  );
  if (!r.ok) throw new Error(`tour recording ${r.status}`);
  return (await r.json()).trace as LiveState[];
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
