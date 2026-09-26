// "Fed by engines" mode (docs/COMPOSITION_DESIGN.md §7).
//
// The factory engine is not changed. In aggregate mode its inputs are one
// efficiency number per block; in fed mode the same inputs are computed by
// the detailed twins — Exascale's delivered throughput, the XE9712's measured
// GPU watts, the CDU's pump power and cap — and carried across tested seams by
// the composition layer. Both modes run the same simulate().
//
// The chain runs on the composition server (compose/, backend :8048), reached
// through the vite proxy key `/compose-api`. When it is not running the
// control disables itself and shows the start command; nothing else on the
// page depends on it.

import type { SimState } from "./types";

const BASE = "/compose-api";

export const START_COMMAND = "./compose/scripts/start_all.sh";

export type FedDivergence = {
  instrument: string;
  aggregate: number;
  fed: number;
  tolerance: number;
  cause: string | null;
  explanation: string;
};

export type FedRun = {
  /** The factory trace whose inputs came from the other engines. */
  trace: SimState[];
  /** Tokens, cost and the aggregate comparison the chain carries. */
  summary: Record<string, number>;
  divergences: FedDivergence[];
  notes: string[];
  estimatedConstants: string[];
  /** The seam identities the chain asserted on the way here. */
  seams: { coupling: string; identity: string; holds: boolean }[];
};

type Stage = {
  id: string;
  trace: Record<string, unknown>[];
  summary: Record<string, number>;
};

type CoupledTrace = {
  stages: Stage[];
  divergences: FedDivergence[];
  notes: string[];
  estimatedConstants: string[];
  seams: { coupling: string; identity: string; holds: boolean }[];
};

/** The capstone chain, run by the composition layer. Throws when the
 *  composition server is not up — the caller turns the control off. */
export async function fetchFedRun(chain = "factory-fed"): Promise<FedRun> {
  const r = await fetch(`${BASE}/run?chain=${encodeURIComponent(chain)}`);
  if (!r.ok) throw new Error(`compose ${r.status}`);
  const data: CoupledTrace = await r.json();
  const stage = data.stages.find((s) => s.id === "PhysicsAIFactory");
  if (!stage) throw new Error("that chain does not end in a factory run");
  return {
    trace: stage.trace as unknown as SimState[],
    summary: stage.summary,
    divergences: data.divergences,
    notes: data.notes,
    estimatedConstants: data.estimatedConstants,
    seams: data.seams,
  };
}
