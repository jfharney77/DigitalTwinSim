// Graded labs (docs/LAB_PATTERN.md): wire types, the two API calls, and the
// per-viewer best-score store. The shapes mirror twinkit/labs.py exactly.
import { apiFetch } from "@twinsim/twin-ui";
import { getLevel } from "./level";
import type { Scenario } from "./types";

export type Op = "<=" | ">=" | "==" | "<" | ">";

export interface Criterion {
  id: string;
  label: string;
  metric: string;
  op: Op;
  threshold: number;
  unit: string;
  weight: number;
  guardsWork: boolean;
  explainId: string;
  equation: string;
  why: string;
}

export interface Objective {
  label: string;
  metric: string;
  direction: "minimize" | "maximize";
  par: number;
  worst: number;
  unit: string;
  explainId: string;
  equation: string;
}

export interface Lab {
  id: string;
  title: string;
  difficulty: number;
  goal: { statement: string; constraints: string[]; deliveredWork: string };
  criteria: Criterion[];
  objective: Objective | null;
  hints: string[];
  start: Scenario;
}

export interface CriterionResult {
  id: string;
  label: string;
  passed: boolean;
  measured: number;
  op: Op;
  threshold: number;
  unit: string;
  guardsWork: boolean;
  explainId: string;
  equation: string;
  why: string;
}

export interface ObjectiveResult {
  label: string;
  measured: number;
  par: number;
  worst: number;
  unit: string;
  direction: "minimize" | "maximize";
  fraction: number;
  explainId: string;
  equation: string;
}

export interface LabResult {
  labId: string;
  passed: boolean;
  score: number;
  criteria: CriterionResult[];
  objective: ObjectiveResult | null;
  metrics: Record<string, number>;
  verdict: string;
}

export async function fetchLabs(): Promise<Lab[]> {
  const r = await apiFetch(`/api/labs?level=${getLevel()}`);
  if (!r.ok) throw new Error(`labs ${r.status}`);
  return r.json();
}

export async function gradeLab(id: string, scenario: Scenario): Promise<LabResult> {
  const r = await apiFetch(`/api/labs/${encodeURIComponent(id)}/grade?level=${getLevel()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
  });
  if (!r.ok) throw new Error(`grade ${r.status}`);
  return r.json();
}

// #labs opens the lab list; #lab=<id> opens one lab.
export function labFromHash(): { open: boolean; id: string | null } {
  const h = window.location.hash;
  const m = h.match(/^#lab=([a-z0-9-]+)$/i);
  if (m) return { open: true, id: m[1] };
  return { open: h === "#labs", id: null };
}

// Best score per lab: a per-viewer convenience, so localStorage is the right
// home. Every access is guarded; the page works without it.
const BEST_KEY = "physicsmx7000-lab-best";

export function readBest(): Record<string, number> {
  try {
    const raw = window.localStorage.getItem(BEST_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? (parsed as Record<string, number>) : {};
  } catch {
    return {};
  }
}

export function recordBest(id: string, score: number): Record<string, number> {
  const best = readBest();
  if (!(id in best) || score > best[id]) best[id] = score;
  try {
    window.localStorage.setItem(BEST_KEY, JSON.stringify(best));
  } catch {
    /* private window or blocked storage: the score just is not remembered */
  }
  return best;
}
