import type { PowerOnState, PowerPhase } from "../types";

const PHASE_LABEL: Record<PowerPhase, string> = {
  off: "off — AC only",
  power: "power & standby",
  boot: "nodes booting",
  drives: "drive discovery",
  cluster: "cluster forming",
  services: "data services",
  online: "serving I/O",
};

export function PowerOnCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: PowerOnState | null;
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
        <span>power draw</span>
        <span>{state ? `${state.powerWatts} W` : "0 W"}</span>
      </div>
      <div className="stat">
        <span>fan speed</span>
        <span>{state ? `${state.fanPercent}%` : "0%"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Watts and timings are typical values for a mid-range dual-node
        appliance, meant to show shape and order of magnitude — not a
        measurement of your array.
      </div>
    </div>
  );
}
