import type { BringUpPhase, FirstRunState } from "../types";

const PHASE_LABEL: Record<BringUpPhase, string> = {
  off: "off — AC only",
  power: "nodes powering on",
  esxi: "ESXi booting",
  discovery: "node discovery",
  primary: "primary election",
  cluster: "cluster build",
  vsan: "vSAN assembling",
  online: "serving VMs",
};

export function FirstRunCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: FirstRunState | null;
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
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>cluster power</span>
        <span>{state ? `${state.powerWatts} W` : "0 W"}</span>
      </div>
      <div className="stat">
        <span>build progress</span>
        <span>{state ? `${state.progressPercent}%` : "0%"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Watts are the whole four-node cluster plus its switches; build progress
        mirrors the VxRail Manager bar. Values are typical, meant to show shape
        and order of magnitude — not a measurement of your cluster.
      </div>
    </div>
  );
}
