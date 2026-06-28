import type { SimState } from "../types";

export function Counters({ state }: { state: SimState | null }) {
  const macs = state?.macDone ?? 0;
  const total = state?.macTotal ?? 0;
  const active = state?.activeCores ?? 0;
  const util = state ? Math.round(state.utilization * 100) : 0;

  return (
    <div>
      <h2>Counters</h2>
      <div className="stat">
        <span>MACs done</span>
        <span>{macs}</span>
      </div>
      <div className="stat">
        <span>of total</span>
        <span>{total}</span>
      </div>
      <div className="stat">
        <span>active cores</span>
        <span>{active}</span>
      </div>
      <div className="stat">
        <span>utilization</span>
        <span>{util}%</span>
      </div>
    </div>
  );
}
