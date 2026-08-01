import type { DataPhase, DataState } from "../types";

const PHASE_LABEL: Record<DataPhase, string> = {
  idle: "idle — no job attached",
  mount: "client mounting",
  layout: "fetching layout",
  stripe: "parallel read fanning out",
  feed: "GPUs saturated",
  checkpoint: "checkpoint burst",
  tier: "tiering to object",
  steady: "training loop",
};

function tbps(gbps: number): string {
  return gbps >= 1000 ? `${Math.round(gbps / 100) / 10} Tb/s` : `${gbps} Gb/s`;
}

export function DataCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: DataState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const mdsInPath =
    state !== null && state.activeRegions.includes("metadata");
  return (
    <div className="an-panel">
      <h2>Telemetry</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>throughput</span>
        <span>{state ? tbps(state.throughputGbps) : "0 Gb/s"}</span>
      </div>
      <div className="stat">
        <span>servers streaming</span>
        <span>{state ? `${state.dataServersStreaming} / 4` : "0 / 4"}</span>
      </div>
      <div className="stat">
        <span>layout held</span>
        <span>{state ? (state.layoutHeld ? "yes" : "no") : "—"}</span>
      </div>
      <div className="stat">
        <span>metadata in path</span>
        <span>{state ? (mdsInPath ? "yes" : "no — bypassed") : "—"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Watch two rows together. Once the client holds a layout, the
        metadata server drops out of the path and stays out — and throughput
        is the sum of the servers streaming, not one controller's ceiling.
        That is what makes this a parallel file system. Values are typical,
        meant to show shape and order of magnitude.
      </div>
    </div>
  );
}
