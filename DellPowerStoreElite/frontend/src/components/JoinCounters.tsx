import type { JoinPhase, JoinState } from "../types";

const PHASE_LABEL: Record<JoinPhase, string> = {
  steady: "prior generation serving",
  power: "Elite waking",
  join: "cluster join",
  mesh: "RDMA mesh up",
  rebalance: "live rebalance",
  cutover: "cutover to Elite",
  repurpose: "prior gen repurposed",
  elite: "Elite serving · mixed-gen",
};

function fmtElapsed(s: number): string {
  if (s < 60) return `t+${s}s`;
  if (s < 3600) return `t+${Math.round(s / 60)}m`;
  return `t+${(s / 3600).toFixed(1)}h`;
}

export function JoinCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: JoinState | null;
  stepIndex: number;
  stepCount: number;
}) {
  return (
    <div className="an-panel">
      <h2>Telemetry</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>
          {stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}
        </span>
      </div>
      <div className="stat">
        <span>served IOPS</span>
        <span>{state ? `${state.iopsThousands}K` : "—"}</span>
      </div>
      <div className="stat">
        <span>downtime</span>
        <span>{state ? `${state.downtimeSeconds} s` : "0 s"}</span>
      </div>
      <div className="stat">
        <span>generations in cluster</span>
        <span>{state ? state.generationsInCluster : "—"}</span>
      </div>
      <div className="stat">
        <span>effective capacity</span>
        <span>
          {state ? `${(state.effectiveTb / 1000).toFixed(1)} PB` : "—"}
        </span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? fmtElapsed(state.elapsedSeconds) : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        The downtime counter is the point: it never leaves zero. IOPS,
        capacities and timings are illustrative, shaped by Dell's launch
        figures (3x performance, 6:1 reduction, 5.8 PB per 3U) — not a
        measurement of your cluster.
      </div>
    </div>
  );
}
