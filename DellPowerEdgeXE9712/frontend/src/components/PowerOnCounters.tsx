import type { PowerOnPhase, PowerOnState } from "../types";

const PHASE_LABEL: Record<PowerOnPhase, string> = {
  off: "off — facility connected",
  power: "busbar energizing",
  coolant: "coolant loop priming",
  trayboot: "compute trays booting",
  gpuinit: "GPUs waking",
  fabric: "NVLink links training",
  fused: "domain fused — one GPU",
  ready: "accepting jobs",
};

function fmtWatts(w: number): string {
  return w >= 10_000 ? `${Math.round(w / 100) / 10} kW` : `${w} W`;
}

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
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>rack power</span>
        <span>{state ? fmtWatts(state.powerWatts) : "0 W"}</span>
      </div>
      <div className="stat">
        <span>GPUs in NVLink domain</span>
        <span>{state ? `${state.gpusInDomain} / 72` : "0 / 72"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Watts are the whole rack — shelves, trays, fabric, and pumps. The
        domain counter is the rack's defining number: it stays at zero all
        through bring-up, then snaps to 72 the moment the NVLink fabric
        fuses. Values are typical, meant to show shape and order of
        magnitude — not a measurement of your rack.
      </div>
    </div>
  );
}
