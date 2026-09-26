import type { BringUpPhase, FirstRunState, NodeAddPhase } from "../types";

const PHASE_LABEL: Record<BringUpPhase | NodeAddPhase, string> = {
  off: "off — AC only",
  power: "nodes powering on",
  esxi: "ESXi booting",
  discovery: "node discovery",
  primary: "primary election",
  cluster: "cluster build",
  vsan: "vSAN assembling",
  online: "serving VMs",
  serving: "four nodes serving",
  racked: "fifth node racked",
  found: "node discovered",
  check: "compatibility check",
  refused: "add refused",
  reimage: "re-imaging the node",
  recheck: "check passes",
  join: "node joining",
  rebalance: "vSAN rebalancing",
  expanded: "five nodes serving",
};

// One clock for the header and both panels: seconds while the numbers are
// small, minutes once a trace runs past two minutes, hours once a day-2 trace
// runs past one. The reading is when a stage *starts*.
export function clockLabel(seconds: number): string {
  if (seconds < 120) return `t+${seconds} s`;
  if (seconds < 3600) return `t+${Math.round(seconds / 60)} min`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `t+${h} h ${m} min`;
}

export function FirstRunCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: FirstRunState | null;
  stepIndex: number;
  stepCount: number;
}) {
  // The node-add scenario carries its own numbers; their presence is what
  // switches the panel, so a new scenario needs no code here.
  const dayTwo = state?.vsanNodes !== undefined;
  if (state && dayTwo) {
    const refused = state.phase === "refused";
    const mismatch = state.nodeVersion !== state.clusterVersion;
    return (
      <div className="an-panel">
        <h2>Telemetry</h2>
        <div className={refused ? "stat stat-failed" : "stat"}>
          <span>phase</span>
          <span>{PHASE_LABEL[state.phase]}</span>
        </div>
        <div className="stat">
          <span>step</span>
          <span>{`${stepIndex + 1} / ${stepCount}`}</span>
        </div>
        <div className="stat stat-hero">
          <span>nodes in vSAN</span>
          <span>{state.vsanNodes}</span>
        </div>
        <div className="stat stat-hero">
          <span>mismatched nodes in vSAN</span>
          <span>{state.mismatchedNodesInVsan}</span>
        </div>
        <div className="stat">
          <span>cluster version</span>
          <span>{state.clusterVersion}</span>
        </div>
        <div className={mismatch && state.step > 0 ? "stat stat-failed" : "stat"}>
          <span>new node version</span>
          <span>{state.step > 0 ? state.nodeVersion : "—"}</span>
        </div>
        <div className="stat">
          <span>datastore (raw)</span>
          <span>{state.datastoreTb} TB</span>
        </div>
        <div className="stat">
          <span>VMs running</span>
          <span>{state.vmsRunning}</span>
        </div>
        <div className="stat">
          <span>add-host progress</span>
          <span>{state.progressPercent}%</span>
        </div>
        <div className="stat">
          <span>rack power</span>
          <span>{state.powerWatts} W</span>
        </div>
        <div className="stat">
          <span>stage starts (illustrative)</span>
          <span>{clockLabel(state.elapsedSeconds)}</span>
        </div>
        <div className="mini" style={{ marginTop: 8 }}>
          Mismatched nodes in vSAN exists to be zero: the check sits ahead of
          every step that changes the cluster. Nodes in vSAN and the datastore
          move once, after the retry passes. The clock shows when each stage
          begins, so a stage lasts until the next step's reading — the
          re-image gets 90 minutes, the rebalance an hour. Version numbers,
          terabytes, VM count, watts and timings are illustrative.
        </div>
      </div>
    );
  }

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
        <span>stage starts (illustrative)</span>
        <span>{state ? clockLabel(state.elapsedSeconds) : "t+0 s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Watts are the whole four-node cluster plus its switches; build progress
        mirrors the VxRail Manager bar. The clock shows when each stage
        begins, so a stage lasts until the next step's reading; the cluster
        build gets 30 minutes, inside the 25 to 40 Dell quotes. Watts and the
        other timings are illustrative, not a measurement of your cluster.
      </div>
    </div>
  );
}
