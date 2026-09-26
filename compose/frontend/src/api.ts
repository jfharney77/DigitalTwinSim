import { apiFetch } from "@twinsim/twin-ui";
import { getLevel } from "./level";
import type { ChainInfo, ConstantsResponse, CoupledTrace, CouplingInfo } from "./types";

const BASE = "/api";

// Prose-bearing requests carry the reader's current level; the backend
// resolves server-side (compose/leveling.py).
function url(path: string): string {
  return `${BASE}${path}?level=${getLevel()}`;
}

export async function fetchCouplings(): Promise<CouplingInfo[]> {
  const r = await apiFetch(url("/couplings"));
  if (!r.ok) throw new Error(`couplings ${r.status}`);
  return r.json();
}

export async function fetchChains(): Promise<ChainInfo[]> {
  const r = await apiFetch(url("/chains"));
  if (!r.ok) throw new Error(`chains ${r.status}`);
  return r.json();
}

export async function fetchConstants(): Promise<ConstantsResponse> {
  const r = await apiFetch(`${BASE}/constants`);
  if (!r.ok) throw new Error(`constants ${r.status}`);
  return r.json();
}

/** A preset chain with its default scenarios. Static builds answer this from
 *  the snapshot written at build time (docs/STATIC_HOSTING.md). */
export async function runChain(chainId: string): Promise<CoupledTrace> {
  const r = await apiFetch(`${BASE}/run?chain=${encodeURIComponent(chainId)}`);
  if (!r.ok) throw new Error(`run ${r.status}`);
  return r.json();
}

/** An edited chain. Its own route so a static build can host the presets and
 *  leave this one out — the page keeps to the presets when there is no
 *  backend behind it. */
export async function postChain(chain: Record<string, unknown>): Promise<CoupledTrace> {
  const r = await apiFetch(`${BASE}/run/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(chain),
  });
  if (!r.ok) throw new Error(`run ${r.status}`);
  return r.json();
}
